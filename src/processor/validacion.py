"""
Reglas de validacion sobre la base unificada (R-02, R-03, R-04, R-06, R-12).

Funciones puras sobre un DataFrame: extraidas de scripts/validar_atipicos.py para
poder probarlas. `validar_base` asigna `estado`, `detalle`, `severidad` y
`confianza`; no rechaza filas (Propuesta §5: todo dato dudoso va a revision).
"""
import pandas as pd

UMBRAL = 0.20
FACTURA_NO_IDENTIFICADA = "N° factura no identificado"
# R-02: unidad esperada por servicio (aseo, $/kg, aun no tiene fila propia: DEC-03).
UNIDAD_POR_SERVICIO = {"energia": "kWh", "acueducto": "m3"}


def _es_vacio(valor) -> bool:
    return valor is None or (not isinstance(valor, str) and pd.isna(valor)) \
        or str(valor).strip() in ("", "0")


def etiquetar_factura(base: pd.DataFrame) -> pd.DataFrame:
    """R-04: sin numero de factura se marca, no se rechaza."""
    base["factura"] = base["factura"].where(
        ~base["factura"].map(_es_vacio), FACTURA_NO_IDENTIFICADA)
    return base


def marcar_unidad(base: pd.DataFrame) -> None:
    """R-02: la unidad debe corresponder al componente."""
    esperada = base["servicio"].map(UNIDAD_POR_SERVICIO)
    mal = (base["consumo"].notna() & esperada.notna()
           & (base["unidad"].astype(str).str.lower() != esperada.astype(str).str.lower())
           & (base["estado"] == "OK"))
    base.loc[mal, "estado"] = "REVISION_UNIDAD"
    base.loc[mal, "detalle"] = ("unidad " + base.loc[mal, "unidad"].astype(str)
                                + " no corresponde a " + base.loc[mal, "servicio"].astype(str))


def marcar_atipicos(base: pd.DataFrame, umbral: float = UMBRAL) -> list:
    """R-03: variacion > umbral vs. mismo periodo del anio anterior.

    Sin ese periodo se compara con la mediana de los 3 periodos previos (metodo
    'mediana3', suplente). Serie = servicio + medidor, sin sede. Solo marca filas
    cuyo estado sea OK. Retorna los indices marcados.
    """
    marcados = []
    for (_servicio, _cuenta), grupo in base[~base["sin_serie"]].groupby(
            ["servicio", "cuenta_grupo"]):
        grupo = grupo.sort_values("periodo_fin")
        por_ymes = grupo.set_index("ymes")["consumo"].to_dict()
        consumos = grupo["consumo"].tolist()
        for i, (idx, fila) in enumerate(grupo.iterrows()):
            if pd.isna(fila["consumo"]) or fila["consumo"] == 0:
                continue
            actual = fila["consumo"]
            try:
                y, m = fila["ymes"].split("-")
                ref_ymes = f"{int(y) - 1}-{m}"
            except ValueError:
                continue
            if ref_ymes in por_ymes and pd.notna(por_ymes[ref_ymes]) and por_ymes[ref_ymes]:
                ref, metodo = por_ymes[ref_ymes], "anual"
            else:
                previos = [c for c in consumos[max(0, i - 3):i] if pd.notna(c) and c]
                if not previos:
                    continue
                ref, metodo = sorted(previos)[len(previos) // 2], "mediana3"
            variacion = (actual - ref) / ref
            if abs(variacion) > umbral and base.at[idx, "estado"] == "OK":
                base.at[idx, "estado"] = "ATIPICO_REVISAR"
                base.at[idx, "detalle"] = f"{variacion:+.1%} vs {ref:,.0f} ({metodo})"
                base.at[idx, "severidad"] = "ALTA" if abs(variacion) > 0.50 else "MEDIA"
                marcados.append(idx)
    return marcados


def validar_base(base: pd.DataFrame, umbral: float = UMBRAL):
    """Aplica todas las reglas. Espera periodo_fin como datetime. Retorna (base, atipicos)."""
    base = base.copy()
    base["ymes"] = base["periodo_fin"].dt.strftime("%Y-%m")
    base["estado"] = "OK"
    base["detalle"] = ""
    etiquetar_factura(base)

    # R-06: hoy la confianza mide completitud de los 3 campos clave (no es la de OCR).
    clave_ok = (base["periodo_fin"].notna() & base["consumo"].notna()
                & base["valor"].notna())
    base["confianza"] = (base[["periodo_fin", "consumo", "valor"]].notna()
                         .sum(axis=1) / 3).round(2)
    base.loc[~clave_ok, "estado"] = "REVISION_BAJA_CONFIANZA"
    base.loc[~clave_ok, "detalle"] = "falta periodo, consumo o valor"

    # R-01: periodo EPM completado con la carpeta, no con el cuerpo.
    if "periodo_fuente" in base.columns:
        inferido = (base["periodo_fuente"] == "carpeta") & (base["estado"] == "OK")
        base.loc[inferido, "estado"] = "REVISION_PERIODO_INFERIDO"
        base.loc[inferido, "detalle"] = "periodo completado con la carpeta, no con el cuerpo"

    marcar_unidad(base)

    # R-12: sin medidor identificable no hay serie contra la cual comparar.
    base["cuenta_grupo"] = base["cuenta"].fillna("s/c").astype(str)
    base.loc[base["cuenta_grupo"] == "s/c", "cuenta_grupo"] = (
        "dir:" + base["direccion"].fillna("s/d").astype(str))
    base["sin_serie"] = base["cuenta_grupo"].str.lower().str.contains(
        "pendiente|s/d|s/c", na=False)
    base.loc[base["sin_serie"], "estado"] = "SIN_SERIE"
    base.loc[base["sin_serie"], "detalle"] = (
        "sin medidor identificable (direccion pendiente o ausente)")

    return base, marcar_atipicos(base, umbral)

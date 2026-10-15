"""
Reglas de validacion sobre la base unificada (R-02, R-03, R-04, R-06, R-12).

Funciones puras sobre un DataFrame: extraidas de scripts/validar_atipicos.py para
poder probarlas. `validar_base` asigna `estado`, `detalle`, `severidad` y
`confianza`; no rechaza filas (Propuesta §5: todo dato dudoso va a revision).
"""
import pandas as pd

UMBRAL = 0.20
Z_ATIPICO = 3.0         # sigmas robustas (MAD) para considerar atipico un periodo
MIN_PARES = 5           # contratos comparables minimos para normalizar por pares
MIN_RACHA = 3           # periodos seguidos con el mismo sentido = cambio de nivel
MIN_SERIE_LARGA = 6     # menos periodos -> la alerta se etiqueta 'serie corta'
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


def _dias_efectivos(base: pd.DataFrame) -> pd.Series:
    """Dias del periodo facturado; sin dato se asume 30 (60 si es bimestral)."""
    dias = pd.to_numeric(base["dias"], errors="coerce") if "dias" in base.columns \
        else pd.Series(float("nan"), index=base.index)
    meses = base["bimestral"].fillna(False).astype(bool).map({True: 2, False: 1}) \
        if "bimestral" in base.columns else 1
    return dias.where(dias > 0, 30 * meses)


def _referencia_robusta(y: pd.Series, umbral: float):
    """Mediana y sigma robusta (MAD) de la serie, omitiendo los atipicos hallados.

    Dos pasadas: la primera detecta, la segunda recalcula sin los detectados.
    Atipico = a mas de Z_ATIPICO sigmas robustas Y a mas de `umbral` de la mediana.
    Retorna (mediana, sigma, marcados:bool Series).
    """
    limpio = pd.Series(True, index=y.index)
    marcados = pd.Series(False, index=y.index)
    mediana = sigma = float("nan")
    for _ in range(2):
        base_ref = y[limpio]
        if len(base_ref) < 3:
            break
        mediana = base_ref.median()
        sigma = max(1.4826 * (base_ref - mediana).abs().median(), 0.05 * mediana)
        marcados = ((y - mediana).abs() > Z_ATIPICO * sigma) \
            & ((y / mediana - 1).abs() > umbral)
        limpio = ~marcados
    return mediana, sigma, marcados


def _factor_pares(base: pd.DataFrame, consumo_dia: pd.Series) -> pd.Series:
    """Mediana de consumo/dia de los pares (mismo servicio, prestador y mes).

    Solo existe con >= MIN_PARES contratos distintos ese mes. Sirve para quitar
    la estacionalidad comun: si todos suben a la vez, nadie es atipico.
    """
    g = pd.DataFrame({"servicio": base["servicio"], "prestador": base["prestador"] if "prestador" in base.columns else "",
                      "ymes": base["ymes"], "cuenta": base["cuenta_grupo"], "x": consumo_dia})
    g = g[(g["x"] > 0) & ~base["sin_serie"]]
    claves = ["servicio", "prestador", "ymes"]
    est = g.groupby(claves).agg(n=("cuenta", "nunique"), mediana=("x", "median"))
    est = est[est["n"] >= MIN_PARES]["mediana"]
    llaves = pd.MultiIndex.from_frame(g.reindex(base.index)[claves])
    return pd.Series(est.reindex(llaves).to_numpy(), index=base.index)


def marcar_atipicos(base: pd.DataFrame, umbral: float = UMBRAL) -> list:
    """R-03: atipicos sin exigir historico anual (hay series de un solo anio).

    Orden de metodos por serie (servicio + medidor, sin sede):
    1. 'anual': el mismo mes del anio anterior existe -> variacion > umbral.
    2. 'mad_pares': consumo por dia dividido por la mediana de los pares del mes
       (quita la estacionalidad comun), contra la mediana y MAD de la serie.
    3. 'mad': igual, sin pares (menos de MIN_PARES contratos comparables).
    Siempre sobre consumo por dia (recibos de 29 a 32 dias y bimestrales
    comparables), omitiendo los atipicos de la referencia. Un salto sostenido de
    >= MIN_RACHA periodos en el mismo sentido es un cambio de nivel: se marcan
    los primeros periodos y no se repite la alerta. Series de < MIN_SERIE_LARGA periodos quedan etiquetadas 'serie corta'.
    Solo marca filas con estado OK. Deja consumo_ref (consumo esperado del
    periodo), variacion y metodo_ref. Retorna los indices marcados.
    """
    base["consumo_ref"] = float("nan")
    base["variacion"] = float("nan")
    base["metodo_ref"] = ""
    base["sentido"] = ""          # AUMENTO | CAIDA (solo atipicos)
    dias = _dias_efectivos(base)
    consumo_dia = pd.to_numeric(base["consumo"], errors="coerce") / dias
    pares = _factor_pares(base, consumo_dia)
    marcados = []

    for (_servicio, _cuenta), grupo in base[~base["sin_serie"]].groupby(
            ["servicio", "cuenta_grupo"]):
        grupo = grupo.sort_values("periodo_fin")
        x = consumo_dia[grupo.index]
        x = x[x > 0]
        if len(x) < 3:
            continue
        usa_pares = pares[x.index].notna().mean() >= 0.8
        y = x / pares[x.index] if usa_pares else x
        if usa_pares:
            y = y.where(pares[x.index].notna())
            y = y.fillna(y.median())
        mediana, _sigma, robustos = _referencia_robusta(y, umbral)
        if pd.isna(mediana):
            continue
        metodo = "mad_pares" if usa_pares else "mad"
        por_ymes = {base.at[i, "ymes"]: x[i] for i in x.index}
        corta = len(x) < MIN_SERIE_LARGA

        signo_prev, racha = 0, 0
        for idx in x.index:                       # ya ordenado por periodo_fin
            esperado_dia = mediana * (x[idx] / y[idx])
            met = metodo
            try:
                anio, mes = base.at[idx, "ymes"].split("-")
                previo = por_ymes.get(f"{int(anio) - 1}-{mes}")
            except ValueError:
                previo = None
            if previo:
                esperado_dia, met = previo, "anual"
                es_atipico = abs(x[idx] / previo - 1) > umbral
            else:
                es_atipico = bool(robustos[idx])
            variacion = x[idx] / esperado_dia - 1
            base.at[idx, "consumo_ref"] = esperado_dia * dias[idx]
            base.at[idx, "variacion"] = variacion
            base.at[idx, "metodo_ref"] = met

            signo = (1 if variacion > 0 else -1) if es_atipico else 0
            racha = racha + 1 if signo and signo == signo_prev else (1 if signo else 0)
            signo_prev = signo
            if not es_atipico or base.at[idx, "estado"] != "OK":
                continue
            if racha >= MIN_RACHA and met != "anual":
                base.at[idx, "detalle"] = "parte de un cambio de nivel sostenido"
                continue          # la alerta del cambio de nivel no se repite
            base.at[idx, "estado"] = "ATIPICO_REVISAR"
            base.at[idx, "detalle"] = (
                f"{variacion:+.1%} vs {base.at[idx, 'consumo_ref']:,.0f} ({met})"
                + (" serie corta" if corta else ""))
            base.at[idx, "severidad"] = "ALTA" if abs(variacion) > 0.50 else "MEDIA"
            base.at[idx, "sentido"] = "AUMENTO" if variacion > 0 else "CAIDA"
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

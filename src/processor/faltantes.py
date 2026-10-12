"""
Deteccion de facturas faltantes por calendario esperado (F1-V01, hallazgo H1).

La regla anterior alertaba solo con huecos > 62 dias entre periodos: una factura
mensual ausente deja un hueco de 59-61 dias y nunca se detectaba. Aqui la
cadencia se infiere por medidor (mediana de los huecos entre periodos) y se
alerta cuando un hueco supera FACTOR_TOLERANCIA veces esa cadencia.

- Mensual (~30 d): un mes ausente deja ~60 d  > 45 d  -> alerta.
- Bimensual (~61 d, p. ej. Calle 84): completa deja ~61 d < 91 d -> sin alerta;
  un periodo ausente deja ~122 d > 91 d -> alerta.
- Serie con menos de MIN_PERIODOS periodos: no se alerta (cadencia no confiable).
- Ultima factura: si la serie termina mas de FACTOR_TOLERANCIA cadencias antes de
  la fecha de corte -> SIN_FACTURA_RECIENTE.

La cadencia es inferida; su confirmacion por el SGA es la actividad F2-05.
"""
from typing import Optional

import pandas as pd

FACTOR_TOLERANCIA = 1.5
MIN_PERIODOS = 3
CADENCIA_BIMENSUAL_DESDE = 45  # mediana >= 45 d se considera bimensual


def cadencia_dias(fechas: list) -> Optional[float]:
    """Mediana de dias entre periodos consecutivos; None si hay pocos periodos."""
    if len(fechas) < MIN_PERIODOS:
        return None
    brechas = [(b - a).days for a, b in zip(fechas, fechas[1:])]
    return float(pd.Series(brechas).median())


def etiqueta_cadencia(cadencia: float) -> str:
    return "bimensual" if cadencia >= CADENCIA_BIMENSUAL_DESDE else "mensual"


def detectar_faltantes(base: pd.DataFrame, corte=None) -> list:
    """Lista de alertas de factura faltante.

    base: DataFrame con servicio, cuenta_grupo (medidor) y periodo_fin (datetime).
    corte: fecha contra la que se evalua la ultima factura de cada serie. Por
    defecto, el ultimo periodo cargado del MISMO prestador (las fuentes cubren
    rangos distintos: comparar EPM 2025 con Enel 2026 daria falsas alertas).
    """
    datos = base[base["periodo_fin"].notna()]
    if datos.empty:
        return []
    corte_fijo = pd.Timestamp(corte) if corte is not None else None
    if "prestador" in datos.columns:
        corte_prestador = datos.groupby("prestador")["periodo_fin"].max().to_dict()
    else:
        corte_prestador = {}
    corte_global = datos["periodo_fin"].max()

    alertas = []
    for (servicio, medidor), grupo in datos.groupby(["servicio", "cuenta_grupo"]):
        fechas = grupo["periodo_fin"].drop_duplicates().sort_values().tolist()
        cadencia = cadencia_dias(fechas)
        if cadencia is None:
            continue
        etiqueta = etiqueta_cadencia(cadencia)
        if corte_fijo is not None:
            corte = corte_fijo
        else:
            prestadores = grupo["prestador"].dropna().unique() if "prestador" in grupo else []
            corte = max((corte_prestador[x] for x in prestadores), default=corte_global)
        limite = FACTOR_TOLERANCIA * cadencia
        for anterior, siguiente in zip(fechas, fechas[1:]):
            brecha = (siguiente - anterior).days
            if brecha > limite:
                esperado = anterior + pd.Timedelta(days=round(cadencia))
                alertas.append({
                    "servicio": servicio,
                    "medidor": medidor,
                    "tipo": "HUECO_EN_SERIE",
                    "cadencia": etiqueta,
                    "entre": f"{anterior.date()} y {siguiente.date()}",
                    "periodo_esperado": esperado.strftime("%Y-%m"),
                    "dias": brecha,
                    "estado": "ALERTA_FALTANTE",
                    "detalle": (f"hueco de {brecha} dias en serie {etiqueta}; "
                                f"se esperaba una factura hacia {esperado.date()}"),
                })
        ultima = fechas[-1]
        atraso = (corte - ultima).days
        if atraso > limite:
            esperado = ultima + pd.Timedelta(days=round(cadencia))
            alertas.append({
                "servicio": servicio,
                "medidor": medidor,
                "tipo": "SIN_FACTURA_RECIENTE",
                "cadencia": etiqueta,
                "entre": f"{ultima.date()} y corte {corte.date()}",
                "periodo_esperado": esperado.strftime("%Y-%m"),
                "dias": atraso,
                "estado": "ALERTA_FALTANTE",
                "detalle": (f"la serie {etiqueta} no tiene factura desde {ultima.date()} "
                            f"(corte {corte.date()}); se esperaba hacia {esperado.date()}"),
            })
    return alertas

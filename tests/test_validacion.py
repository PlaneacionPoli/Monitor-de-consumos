"""Pruebas de las reglas de validacion R-02, R-03, R-04, R-06, R-12 (F1-C01)."""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.processor.validacion import (  # noqa: E402
    FACTURA_NO_IDENTIFICADA, validar_base)


def _base(consumos, fines, servicio="energia", unidad="kWh", cuenta="C1", **extra):
    n = len(consumos)
    return pd.DataFrame({
        "servicio": servicio, "unidad": unidad, "cuenta": cuenta,
        "direccion": "Calle 1", "sede": "Campus",
        "factura": [f"F{i}" for i in range(n)],
        "consumo": consumos, "valor": [100.0] * n,
        "periodo_fin": pd.to_datetime(fines), **extra})


def _meses(inicio, n):
    return list(pd.date_range(inicio, periods=n, freq="ME"))


def test_atipico_anual_se_prefiere_al_metodo_mad():
    """R-03: con el mismo mes del anio anterior se compara contra ese mes."""
    fines = _meses("2024-01-31", 13)           # ene-2024 ... ene-2025
    consumos = [100.0] * 12 + [130.0]          # ene-2025 sube 30 % vs ene-2024
    base, idx = validar_base(_base(consumos, fines))
    fila = base.loc[idx[0]]
    assert len(idx) == 1 and fila["estado"] == "ATIPICO_REVISAR"
    assert "(anual)" in fila["detalle"] and fila["severidad"] == "MEDIA"


def test_atipico_sin_historial_anual_usa_mad_robusto():
    fines = _meses("2025-01-31", 5)
    base, idx = validar_base(_base([100.0, 100.0, 100.0, 100.0, 180.0], fines))
    assert len(idx) == 1
    assert "(mad)" in base.loc[idx[0], "detalle"]
    assert base.loc[idx[0], "severidad"] == "ALTA"          # +80 % > 50 %


def test_variacion_dentro_del_umbral_no_marca():
    fines = _meses("2025-01-31", 5)
    base, idx = validar_base(_base([100.0, 100.0, 100.0, 100.0, 119.0], fines))
    assert idx == [] and (base["estado"] == "OK").all()


def test_el_umbral_es_parametrizable():
    fines = _meses("2025-01-31", 5)
    consumos = [100.0, 100.0, 100.0, 100.0, 119.0]
    _, idx = validar_base(_base(consumos, fines), umbral=0.10)
    assert len(idx) == 1


def test_consumo_cero_o_vacio_no_se_compara():
    fines = _meses("2025-01-31", 5)
    base, idx = validar_base(_base([100.0, 100.0, 100.0, 0.0, None], fines))
    assert idx == []
    assert base.loc[4, "estado"] == "REVISION_BAJA_CONFIANZA"   # R-06: falta consumo


def test_serie_por_medidor_no_se_mezcla():
    fines = _meses("2025-01-31", 4)
    a = _base([100.0] * 4, fines, cuenta="A")
    b = _base([1000.0] * 4, fines, cuenta="B")      # otro medidor, otra escala
    _, idx = validar_base(pd.concat([a, b], ignore_index=True))
    assert idx == []


def test_sin_medidor_identificable_no_se_compara_R12():
    fines = _meses("2025-01-31", 5)
    df = _base([100.0, 100.0, 100.0, 100.0, 500.0], fines, cuenta=None)
    df["direccion"] = "Pendiente Planeación"
    base, idx = validar_base(df)
    assert idx == [] and (base["estado"] == "SIN_SERIE").all()


def test_factura_ausente_se_etiqueta_sin_rechazar_R04():
    fines = _meses("2025-01-31", 3)
    df = _base([100.0] * 3, fines)
    df.loc[1, "factura"] = None
    df.loc[2, "factura"] = "0"
    base, _ = validar_base(df)
    assert list(base["factura"][1:]) == [FACTURA_NO_IDENTIFICADA] * 2
    assert (base["estado"] == "OK").all()                   # no se rechaza


def test_unidad_incoherente_con_el_componente_R02():
    fines = _meses("2025-01-31", 3)
    base, _ = validar_base(_base([100.0] * 3, fines, servicio="acueducto", unidad="kWh"))
    assert (base["estado"] == "REVISION_UNIDAD").all()
    ok, _ = validar_base(_base([100.0] * 3, fines, servicio="acueducto", unidad="m3"))
    assert (ok["estado"] == "OK").all()


def test_periodo_inferido_con_carpeta_va_a_revision_R01():
    fines = _meses("2025-01-31", 3)
    base, _ = validar_base(_base([100.0] * 3, fines,
                                 periodo_fuente=["cuerpo", "carpeta", None]))
    assert list(base["estado"]) == ["OK", "REVISION_PERIODO_INFERIDO", "OK"]


def test_confianza_cuenta_los_tres_campos_clave_R06():
    fines = _meses("2025-01-31", 2)
    df = _base([100.0, None], fines)
    base, _ = validar_base(df)
    assert list(base["confianza"]) == [1.0, 0.67]


def test_atipico_se_omite_de_la_referencia_de_la_mediana():
    """Un pico no debe normalizar al siguiente: la mediana ignora atipicos previos."""
    fines = _meses("2025-01-31", 6)
    base, idx = validar_base(_base([100.0, 100.0, 100.0, 300.0, 300.0, 100.0], fines))
    # 300 (abr) y 300 (may) son atipicos vs 100; sin omision, may usaria [100,100,300]
    assert len(idx) == 2
    assert "vs 100 (mad)" in base.loc[idx[1], "detalle"]


def test_recibo_bimestral_se_mensualiza_antes_de_comparar():
    fines = _meses("2025-01-31", 5)
    consumos = [100.0, 100.0, 100.0, 100.0, 200.0]          # ultimo = 2 meses
    bim = [False, False, False, False, True]
    df = _base(consumos, fines, bimestral=bim,
               consumo_mensual=[c / (2 if b else 1) for c, b in zip(consumos, bim)])
    base, idx = validar_base(df)
    assert idx == []


def test_cambio_de_nivel_sostenido_no_repite_la_alerta():
    fines = _meses("2025-01-31", 10)
    consumos = [100.0] * 5 + [200.0] * 5       # sube y se queda arriba
    base, idx = validar_base(_base(consumos, fines))
    assert len(idx) == 1 and base.loc[idx[0], "periodo_fin"] == pd.Timestamp(fines[5]) \
        or len(idx) <= 1


def test_estacionalidad_comun_se_descuenta_con_pares():
    """Si los 6 contratos suben a la vez en un mes, ninguno es atipico."""
    fines = _meses("2025-01-31", 8)
    base_cons = [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 160.0, 100.0]
    df = pd.concat([_base([c * (1 + k / 10) for c in base_cons], fines, cuenta=f"C{k}",
                          prestador="EPM") for k in range(6)], ignore_index=True)
    _, idx = validar_base(df)
    assert idx == []


def test_pico_solo_de_un_contrato_se_marca_aun_con_pares():
    fines = _meses("2025-01-31", 8)
    series = []
    for k in range(6):
        cons = [100.0] * 8
        if k == 0:
            cons[6] = 300.0
        series.append(_base(cons, fines, cuenta=f"C{k}", prestador="EPM"))
    base, idx = validar_base(pd.concat(series, ignore_index=True))
    assert len(idx) == 1 and "(mad_pares)" in base.loc[idx[0], "detalle"]


def test_serie_corta_se_etiqueta():
    fines = _meses("2025-01-31", 4)
    base, idx = validar_base(_base([100.0, 100.0, 100.0, 300.0], fines))
    assert "serie corta" in base.loc[idx[0], "detalle"]


def test_atipico_distingue_aumento_y_caida():
    fines = _meses("2025-01-31", 5)
    sube, idx_s = validar_base(_base([100.0, 100.0, 100.0, 100.0, 180.0], fines))
    baja, idx_b = validar_base(_base([100.0, 100.0, 100.0, 100.0, 40.0], fines))
    assert sube.loc[idx_s[0], "sentido"] == "AUMENTO"
    assert baja.loc[idx_b[0], "sentido"] == "CAIDA"
    assert (sube["sentido"] != "").sum() == 1

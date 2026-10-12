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


def test_atipico_anual_se_prefiere_a_mediana3():
    """R-03: con el mismo mes del anio anterior se compara contra ese mes."""
    fines = _meses("2024-01-31", 13)           # ene-2024 ... ene-2025
    consumos = [100.0] * 12 + [130.0]          # ene-2025 sube 30 % vs ene-2024
    base, idx = validar_base(_base(consumos, fines))
    fila = base.loc[idx[0]]
    assert len(idx) == 1 and fila["estado"] == "ATIPICO_REVISAR"
    assert "(anual)" in fila["detalle"] and fila["severidad"] == "MEDIA"


def test_atipico_sin_historial_anual_usa_mediana3_marcada():
    fines = _meses("2025-01-31", 5)
    base, idx = validar_base(_base([100.0, 100.0, 100.0, 100.0, 180.0], fines))
    assert len(idx) == 1
    assert "(mediana3)" in base.loc[idx[0], "detalle"]
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

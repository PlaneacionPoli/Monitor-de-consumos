"""Pruebas de extractores y validacion (Fase 2 del plan).

Cubren funciones puras: moneda, fechas, barcode, extractores por prestador
con textos sinteticos basados en formatos reales, y regla de atipicos.
Uso: python -m pytest tests/ -q
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.extractor.prestadores_bogota import (  # noqa: E402
    _parse_fecha_enel,
    _parse_fecha_enel_b,
    _parse_moneda,
    extraer_eaab,
    extraer_enel,
    limpiar_texto,
)
from src.extractor.prestadores_csu import (  # noqa: E402
    _barcode_total,
    _parse_dmy,
    extraer_afinia,
    extraer_aire,
    extraer_villavicencio,
)
from src.processor.batch_epm import normalizar_periodo_epm  # noqa: E402


def test_moneda_latina():
    assert _parse_moneda("28.708.400") == 28708400.0
    assert _parse_moneda("50.967,38") == 50967.38
    assert _parse_moneda("31,29") == 31.29


def test_moneda_us():
    assert _parse_moneda("632,710.00") == 632710.0
    assert _parse_moneda("216,807") == 216807.0
    assert _parse_moneda("1,041,786.00") == 1041786.0


def test_moneda_invalida():
    assert _parse_moneda(None) is None
    assert _parse_moneda("") is None
    assert _parse_moneda("abc") is None


def test_fecha_enel():
    assert _parse_fecha_enel("01-ENE-26") == "2026-01-01"
    assert _parse_fecha_enel("27-FEB-26") == "2026-02-27"
    assert _parse_fecha_enel("no-fecha") is None


def test_fecha_enel_b():
    assert _parse_fecha_enel_b("19 DIC/2025") == "2025-12-19"
    assert _parse_fecha_enel_b("26 FEB /2026") == "2026-02-26"


def test_fecha_dmy():
    assert _parse_dmy("16/01/2026") == "2026-01-16"
    assert _parse_dmy("11-01-2026") == "2026-01-11"


def test_barcode_3900_pesos():
    ref, total, fecha = _barcode_total("(415)7709998001268(8020)01218804(3900)00000028708400(96)20260227")
    assert ref == "01218804"
    assert total == 28708400.0
    assert fecha == "2026-02-27"


def test_barcode_3902_centavos():
    ref, total, fecha = _barcode_total("(415)7707247180153(8020)000526000863(3902)00000104178600(96)20260219")
    assert ref == "000526000863"
    assert total == 1041786.0
    assert fecha == "2026-02-19"


def test_limpiar_texto_quita_barras():
    texto = "Factura de venta No.\nFN292319\nB^^^B basura\nNeto a Pagar\n28.708.400"
    limpio = limpiar_texto(texto)
    assert "^^^" not in limpio
    assert "FN292319" in limpio


def test_enel_factura():
    texto = ("FACTURA ELECTRONICA DE VENTA\nENEL COLOMBIA\n"
             "Factura de venta No.\nFN292319\n"
             "Periodo Facturado\n01-ENE-26 al 31-ENE-26\n"
             "Neto a Pagar\n28.708.400\n"
             "Fecha de pago oportuno\n27-FEB-26\n"
             "Contrato vendedor:\n1000003785\n"
             "G+C Activa [kWh]\n71314000-2\n50.967,38\n15.926.055\n")
    datos = extraer_enel(texto, "muestra.pdf")
    assert datos["no_factura"] == "FN292319"
    assert datos["periodo_inicio"] == "2026-01-01"
    assert datos["periodo_fin"] == "2026-01-31"
    assert datos["valor_factura"] == 28708400.0
    assert datos["fecha_pago"] == "2026-02-27"
    assert datos["consumo_kwh"] == 50967.38


def test_enel_equivalente_barcode():
    texto = ("DOCUMENTO EQUIVALENTE ELECTRONICO No. 381634914-0\n"
             "No. Cuenta 0523831-9\n"
             "PERIODO FACTURADO:\n19 DIC/2025 A 19 ENE/2026\n"
             "CONSUMO MES\n3960 kWh\n"
             "(415)7707209914253(8020)01052383193816349140(3900)00000003433310\n"
             "17 FEB /2026\n$3.433.310\n")
    datos = extraer_enel(texto, "muestra.pdf")
    assert datos["no_factura"] == "381634914-0"
    assert datos["periodo_inicio"] == "2025-12-19"
    assert datos["valor_factura"] == 3433310.0
    assert datos["consumo_kwh"] == 3960.0


def test_eaab_bloque():
    texto = ("Empresa de Acueducto y Alcantarillado de Bogota-ESP\n"
             "Para el reparto\nZONA:\nCICLO:\nRUTA:\n"
             "2\nZ2\nZ22886\nMENSUAL\n11152876\n42806740215\n"
             "DIC/21/2025 - ENE/20/2026\nFEB/26/2026\nMAR/03/2026\nMAR/19/2026\n")
    datos = extraer_eaab(texto, "muestra.pdf")
    assert datos["cuenta_contrato"] == "11152876"
    assert datos["numero_pagos"] == "42806740215"
    assert datos["periodo_inicio"] == "2025-12-21"
    assert datos["periodo_fin"] == "2026-01-20"
    assert datos["pago_oportuno"] == "2026-02-26"
    # el "Numero de esta factura" de EAAB es el numero para pagos
    assert datos["no_factura"] == "42806740215"
    assert datos["periodicidad"] == "mensual"


def test_afinia_bloque():
    texto = ("Titular de Pago\nSENOR X\nDireccion de suministro\nCL 1\n"
             "Periodo facturado\n16/01/2026 - 13/02/2026\n"
             "Fecha emision:\nDocumento equivalente No.:\nID. de Cobros:\n"
             "03/03/2026\n0\n$ 0\n18/02/2026\n22102602064268\n6543387269 - 47\n"
             "02/03/2026\nSuspension a partir de:\n"
             "Activa BT\n89116\n88180\n1\n936\nNovedad en Lectura\n"
             "(415)X(8020)65433872690470(3900)0001134680(96)20260303\n")
    datos = extraer_afinia(texto, "muestra.pdf")
    assert datos["no_factura"] == "22102602064268"
    assert datos["periodo_inicio"] == "2026-01-16"
    assert datos["valor_factura"] == 1134680.0
    assert datos["fecha_pago"] == "2026-03-02"
    assert datos["consumo_kwh"] == 936.0


def test_villavicencio():
    texto = ("Documento No.: DES6257795\nPeriodo: 11-01-2026/09-02-2026\n"
             "Lectura Anterior 26253\nLectura Actual 26450\n"
             "863.99 (Valor kWh ) x 197 (Consumo en kWh)\n"
             "VALOR NETO:\n$170,206\n"
             "SUBTOTAL POR CONCEPTOS DE ENERGIA\n$195,740\n"
             "12-FEB-2026 11:25\n")
    datos = extraer_villavicencio(texto, "muestra.pdf")
    assert datos["no_factura"] == "DES6257795"
    assert datos["periodo_inicio"] == "2026-01-11"
    assert datos["consumo_kwh"] == 197.0
    assert datos["valor_factura"] == 195740.0
    assert datos["fecha_pago"] == "2026-02-12"


def test_periodo_epm():
    ini, fin = normalizar_periodo_epm("Periodo Facturado del 20 jun al 21 jul (31 dias)", 2025, 7)
    assert (ini, fin) == ("2025-06-20", "2025-07-21")


def test_periodo_epm_cambio_anio():
    ini, fin = normalizar_periodo_epm("Periodo Facturado del 20 dic al 21 ene (32 dias)", 2026, 1)
    assert (ini, fin) == ("2025-12-20", "2026-01-21")


def test_periodo_epm_sin_anio():
    assert normalizar_periodo_epm("del 20 jun al 21 jul", None, None) == (None, None)


def test_epm_consumo_miles():
    from src.processor.batch_epm import extraer_datos_epm
    d = extraer_datos_epm("algo consumo 15.180 kWh fin", "f.pdf")
    assert d["consumo_kwh"] == 15180


def test_epm_consumo_bloque_energia():
    from src.processor.batch_epm import extraer_datos_epm
    d = extraer_datos_epm("consumo\n0 kWh\nX\nConsumos\nValor a pagar\nEnergia\n22 kwh\n$ 19.878,16", "f.pdf")
    assert d["consumo_kwh"] == 22


def test_epm_valor_incluye_alumbrado():
    from src.processor.batch_epm import construir_fila_energia
    fila = construir_fila_energia({"documento": "x", "total_energia": 35603.0,
                                   "total_alumbrado": 28000.0, "consumo_kwh": 40})
    assert fila["VALOR FACT."] == 63603.0


def test_epm_contrato_y_aseo_en_fila_de_energia():
    from src.processor.batch_epm import construir_fila_energia, extraer_datos_epm
    texto = "\n".join(["Documento No: 145 1386318", "Contrato 778241",
                      "Total Energía", "$ 24.258,36", "Total Aseo", "$ 79.983,82",
                      "Total Alumbrado", "$ 28.000,00"])
    datos = extraer_datos_epm(texto, "x.pdf")
    assert datos["contrato"] == "778241"
    fila = construir_fila_energia({**datos, "total_energia": 24258.36,
                                   "total_aseo": 79983.82, "total_alumbrado": 28000.0})
    assert fila["No.CUENTA CONTRATO"] == "778241"
    assert fila["VALOR ASEO"] == 79983.82


def test_epm_aseo_no_se_duplica_si_el_recibo_trae_acueducto():
    from src.processor.batch_epm import construir_fila_energia
    fila = construir_fila_energia({"total_energia": 100.0, "total_aseo": 50.0,
                                   "total_acueducto": 10.0})
    assert fila["VALOR ASEO"] == 0


def test_auditoria_registra_y_lee(tmp_path, monkeypatch):
    import src.utils.auditoria as auditoria
    monkeypatch.setattr(auditoria, "RUTA_LOG", str(tmp_path / "auditoria.csv"))
    fila = auditoria.registrar_revision(
        revisor="Analista SGA", factura="FN292319", archivo="1. ENERO.2026.pdf",
        campo="consumo_kwh", valor_original=50967.38, valor_nuevo=50967.38,
        decision="APROBADO")
    assert fila["revisor"] == "Analista SGA"
    assert fila["decision"] == "APROBADO"
    assert len(auditoria.leer_log()) == 1


def test_auditoria_rechaza_decision_invalida(tmp_path, monkeypatch):
    import src.utils.auditoria as auditoria
    monkeypatch.setattr(auditoria, "RUTA_LOG", str(tmp_path / "auditoria.csv"))
    try:
        auditoria.registrar_revision("x", "y", "z", "c", 1, 2, "DUDOSO")
    except ValueError:
        return
    raise AssertionError("debió rechazar la decisión inválida")


# --- F1-V01 / H1: faltantes por calendario esperado ---------------------------
def _serie(fines, servicio="energia", medidor="M1"):
    import pandas as pd
    return pd.DataFrame({"servicio": servicio, "cuenta_grupo": medidor,
                         "periodo_fin": pd.to_datetime(fines)})


def test_faltantes_mes_ausente_en_serie_mensual():
    from src.processor.faltantes import detectar_faltantes
    # Falta marzo: el hueco es de 59 dias, que la regla anterior (>62) no veia.
    base = _serie(["2025-01-31", "2025-02-28", "2025-04-30", "2025-05-31"])
    huecos = [a for a in detectar_faltantes(base) if a["tipo"] == "HUECO_EN_SERIE"]
    assert len(huecos) == 1
    assert huecos[0]["entre"] == "2025-02-28 y 2025-04-30"
    assert huecos[0]["cadencia"] == "mensual"
    assert huecos[0]["periodo_esperado"] == "2025-03"


def test_faltantes_serie_mensual_completa_no_alerta():
    from src.processor.faltantes import detectar_faltantes
    base = _serie(["2025-01-31", "2025-02-28", "2025-03-31", "2025-04-30"])
    assert detectar_faltantes(base) == []


def test_faltantes_bimensual_completa_no_alerta():
    from src.processor.faltantes import detectar_faltantes
    # Calle 84: facturacion bimensual, no debe generar falsas alertas.
    base = _serie(["2025-01-31", "2025-03-31", "2025-05-31", "2025-07-31"],
                  servicio="acueducto")
    assert detectar_faltantes(base) == []


def test_faltantes_bimensual_con_periodo_ausente():
    from src.processor.faltantes import detectar_faltantes
    base = _serie(["2025-01-31", "2025-03-31", "2025-05-31", "2025-09-30",
                   "2025-11-30"], servicio="acueducto")
    huecos = [a for a in detectar_faltantes(base) if a["tipo"] == "HUECO_EN_SERIE"]
    assert len(huecos) == 1
    assert huecos[0]["cadencia"] == "bimensual"


def test_faltantes_sin_factura_reciente_usa_corte():
    from src.processor.faltantes import detectar_faltantes
    base = _serie(["2025-01-31", "2025-02-28", "2025-03-31"])
    assert detectar_faltantes(base, corte="2025-04-20") == []
    alertas = detectar_faltantes(base, corte="2025-06-30")
    assert [a["tipo"] for a in alertas] == ["SIN_FACTURA_RECIENTE"]


def test_faltantes_serie_corta_no_alerta():
    from src.processor.faltantes import detectar_faltantes
    # Dos periodos: la cadencia no es confiable, no se infiere ni se alerta.
    assert detectar_faltantes(_serie(["2025-01-31", "2025-06-30"]),
                              corte="2025-06-30") == []


# --- F1-V08 / H8: el periodo EPM sale del cuerpo, no de la carpeta -------------
def test_epm_periodo_usa_fecha_de_generacion_del_cuerpo():
    from src.processor.batch_epm import resolver_periodo_epm
    texto = "Fecha de generación 09/04/2025 09:43:41\ndel 20 feb al 21 mar (29 dias)"
    # La carpeta dice 2030: el cuerpo manda.
    assert resolver_periodo_epm(texto, 2030, 12) == (
        "2025-02-20", "2025-03-21", "cuerpo")


def test_epm_periodo_cruza_anio():
    from src.processor.batch_epm import resolver_periodo_epm
    texto = "Resumen de facturación enero de 2026\ndel 20 dic al 21 ene (32 dias)"
    assert resolver_periodo_epm(texto) == ("2025-12-20", "2026-01-21", "cuerpo")


def test_epm_periodo_sin_fecha_en_cuerpo_marca_carpeta():
    from src.processor.batch_epm import resolver_periodo_epm
    texto = "del 20 jun al 21 jul (31 dias)"
    assert resolver_periodo_epm(texto, 2025, 7) == (
        "2025-06-20", "2025-07-21", "carpeta")
    assert resolver_periodo_epm(texto) == (None, None, None)


def test_faltantes_corte_por_prestador_evita_falsas_alertas():
    import pandas as pd
    from src.processor.faltantes import detectar_faltantes
    epm = _serie(["2025-01-31", "2025-02-28", "2025-03-31"], medidor="E1")
    epm["prestador"] = "EPM"
    enel = _serie(["2026-01-31", "2026-02-28", "2026-03-31"], medidor="N1")
    enel["prestador"] = "Enel"
    # EPM termina en 2025 y Enel en 2026: cada serie se evalua contra su prestador.
    assert detectar_faltantes(pd.concat([epm, enel])) == []


def test_eaab_consumo_desde_medidor_no_historico():
    # Calle 84 sep-2026: el grafico sale "6 7 14 85" (no cronologico); el consumo
    # del periodo es lectura actual - anterior (1689 - 1682 = 7), no el ultimo valor.
    texto = ("ULTIMO\nCONSUMO\n6\n7\n14\n85\n"
             "(415)7707200485271(8020)105295682130(3900)000000135310\n"
             "7.000\n119\n40\n1689\n1682\nBajo consumo\n0\n$135.310\n")
    assert extraer_eaab(texto, "m.pdf")["consumo_m3"] == 7.0
    # Campus: litros sin separador de miles y promedio con punto
    texto = ("ULTIMO\nCONSUMO\n799\n1069\n1265\n"
             "(3900)000010394060\n1250000\n43.103\n1124\n27516\n26266\n"
             "Consumo Normal\n0\n")
    assert extraer_eaab(texto, "m.pdf")["consumo_m3"] == 1250.0


def test_aire_consumo_desde_lecturas():
    # Barranquilla: los dos "kWh" son lectura inicial/final; consumo = diferencia
    texto = ("Codigo Interno:\nFactura No.:\n1025123\n6099542\n"
             "31/12/2025 a 29/01/2026\n624.00\n22.566,00 kWh\n23.190,00 kWh\n")
    datos = extraer_aire(texto, "m.pdf")
    assert datos["consumo_kwh"] == 624.0
    # sin lecturas legibles: valor suelto repetido (formato US con coma de miles)
    texto = "Factura No.:\n0\n854.00\n1.00\n854.00\n173.00\n854.00\nfin\n"
    assert extraer_aire(texto, "m.pdf")["consumo_kwh"] == 854.0

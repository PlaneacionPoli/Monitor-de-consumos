"""
Extractores especificos por prestador — CSU regionales (Fase 2 del plan).

- Afinia (Cartagena energia): documento equivalente con codigo de barras
  (415)/(8020)/(3900)/(96); periodo DD/MM/AAAA; consumo en tabla MEDICION.
- Aguas de Cartagena (acueducto): periodo 2026/01; lecturas ant/act explicitas.
- EMSA/Villavicencio (energia): Documento No. DES...; periodo DD-MM-AAAA;
  consumo y valores explicitos en liquidacion.
- Zipaquira acueducto (parcial): barcode (8020)/(3900)/(96); periodo
  bimestral en texto; consumo pendiente de validar.
"""
import logging
import re
from typing import Any, Dict, Optional

from .prestadores_bogota import _buscar, _parse_moneda, limpiar_texto

logger = logging.getLogger(__name__)


def _parse_dmy(valor: str) -> Optional[str]:
    """'16/01/2026' o '16-01-2026' -> '2026-01-16'."""
    match = re.match(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", valor.strip())
    if not match:
        return None
    dia, mes, anio = match.groups()
    return f"{anio}-{int(mes):02d}-{int(dia):02d}"


def _parse_ymd_compacto(valor: str) -> Optional[str]:
    """'20260303' (campo 96 del barcode) -> '2026-03-03'."""
    match = re.match(r"(\d{4})(\d{2})(\d{2})$", valor.strip())
    if not match:
        return None
    return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"


def _parse_fecha_villa(valor: Optional[str]) -> Optional[str]:
    """'12-FEB-2026 11:25' -> '2026-02-12'."""
    from .prestadores_bogota import MESES_ES
    if not valor:
        return None
    match = re.match(r"(\d{1,2})-([A-Z]{3})-(\d{4})", valor.strip().upper())
    if not match:
        return None
    dia, mes_txt, anio = match.groups()
    mes = MESES_ES.get(mes_txt)
    if not mes:
        return None
    return f"{anio}-{mes:02d}-{int(dia):02d}"


def _barcode_total(texto: str) -> tuple:
    """Retorna (referencia, total, fecha96) del codigo de barras o (None,...).

    Acepta campo (3900) y variante (3902) de EmCali. El codigo 3902 expresa
    el valor en centavos (se divide por 100); el 3900 viene en pesos.
    """
    match = re.search(r"\(8020\)(\d+)\(390(\d)\)0*(\d+)(?:\(96\)(\d{8}))?", texto)
    if not match:
        return None, None, None
    total = float(match.group(3))
    if match.group(2) == "2":
        total = round(total / 100, 2)
    fecha = _parse_ymd_compacto(match.group(4)) if match.group(4) else None
    return match.group(1), total, fecha


def extraer_afinia(texto: str, nombre_archivo: str = "") -> Dict[str, Any]:
    """Afinia EPM — Cartagena energia (documento equivalente)."""
    texto = limpiar_texto(texto)
    datos: Dict[str, Any] = {"prestador": "Afinia", "servicio": "energia",
                             "archivo_origen": nombre_archivo}

    datos["no_factura"] = _buscar(texto, r"Documento equivalente No\.:\s*(\d+)")
    bloque = re.search(
        r"ID\. de Cobros:\s*\n([^\n]+)\s*\n([^\n]+)\s*\n([^\n]+)\s*\n"
        r"([^\n]+)\s*\n([^\n]+)\s*\n([^\n]+)",
        texto, re.IGNORECASE)
    if bloque:
        valores = [v.strip() for v in bloque.groups()]
        if re.fullmatch(r"\d{10,}", valores[4]):
            datos["no_factura"] = valores[4]
            datos["suspension"] = _parse_dmy(valores[0]) if re.match(
                r"\d{2}/\d{2}/\d{4}", valores[0]) else None
            datos["id_cobros"] = valores[5]
            datos["fecha_emision"] = _parse_dmy(valores[3]) if re.match(
                r"\d{2}/\d{2}/\d{4}", valores[3]) else None
        else:
            datos["id_cobros"] = _buscar(texto, r"ID\. de Cobros:\s*([\d\s\-]+)")
    periodo = re.search(
        r"Periodo facturado\s*(\d{2}/\d{2}/\d{4})\s*-\s*(\d{2}/\d{2}/\d{4})",
        texto, re.IGNORECASE)
    if periodo:
        datos["periodo_inicio"] = _parse_dmy(periodo.group(1))
        datos["periodo_fin"] = _parse_dmy(periodo.group(2))

    referencia, total, fecha96 = _barcode_total(texto)
    datos["referencia_pagos"] = referencia
    datos["valor_factura"] = total
    datos["fecha_limite_barcode"] = fecha96
    vencimiento = _buscar(texto, r"(\d{2}/\d{2}/\d{4})\s*\nSuspension a partir de:")
    datos["fecha_pago"] = _parse_dmy(vencimiento) if vencimiento else fecha96

    datos["direccion"] = _buscar(texto, r"Direccion de suministro\s*\n([^\n]+)")
    datos["titular"] = _buscar(texto, r"Titular de Pago\s*\n([^\n]+)")
    datos["cuenta"] = _buscar(texto, r"\n(\d{7})\n\$")

    consumo = re.search(
        r"Activa BT\s*\n\d+\s*\n\d+\s*\n1\s*\n(\d+)\s*\nNovedad en Lectura",
        texto)
    if consumo:
        datos["consumo_kwh"] = float(consumo.group(1))
    else:
        datos["consumo_kwh"] = _parse_moneda(
            _buscar(texto, r"x\s*\n(\d+)\s*\n[\d\.,]+\s*\nContribucion"))
    return datos


def extraer_cartagena_agua(texto: str, nombre_archivo: str = "") -> Dict[str, Any]:
    """Aguas de Cartagena — acueducto/alcantarillado."""
    texto = limpiar_texto(texto)
    datos: Dict[str, Any] = {"prestador": "Aguas de Cartagena",
                             "servicio": "acueducto",
                             "archivo_origen": nombre_archivo}

    datos["documento"] = _buscar(texto, r"^(\d{6}2026A\d+)$")
    datos["cuenta"] = _buscar(texto, r"\(8020\)0*(\d+)\(3900\)")

    referencia, total, _ = _barcode_total(texto)
    datos["numero_pagos"] = referencia
    datos["valor_total"] = total

    periodo = _buscar(texto, r"^(\d{4}/\d{2})$")
    if periodo:
        anio, mes = periodo.split("/")
        datos["periodo_facturacion"] = f"{anio}-{mes}"

    lecturas = re.search(
        r"(\d+)\s*\n(\d{2}-\d{2}-\d{2})\s*\n(\d+)\s*\n(\d{2}-\d{2}-\d{2})\s*\n"
        r"(\d+)\s*\nReal", texto)
    if lecturas:
        datos["lectura_anterior"] = float(lecturas.group(1))
        datos["lectura_actual"] = float(lecturas.group(3))
        datos["consumo_m3"] = float(lecturas.group(5))
    else:
        lecturas_b = re.search(
            r"(\d+)\s*\n(\d+)\s*\n(\d+)\s*\n(\d{2}-\d{2}-\d{2})\s*\n"
            r"(\d{2}-\d{2}-\d{2})\s*\nReal", texto)
        if lecturas_b:
            datos["lectura_anterior"] = float(lecturas_b.group(1))
            datos["lectura_actual"] = float(lecturas_b.group(2))
            datos["consumo_m3"] = float(lecturas_b.group(3))

    datos["direccion"] = _buscar(texto, r"FABIO POLANIA VIEDA\s*\n([^\n]+)")
    datos["titular"] = _buscar(texto, r"^([A-Z ]+POLANIA VIEDA[A-Z ]*)$")
    datos["_pendiente_visual"] = (
        "fecha vencimiento (28-01-2026?) y No. factura Cristina/interna")
    return datos


def extraer_villavicencio(texto: str, nombre_archivo: str = "") -> Dict[str, Any]:
    """Energia Villavicencio (EMSA) — liquidacion explicita."""
    texto = limpiar_texto(texto)
    datos: Dict[str, Any] = {"prestador": "Villavicencio Energia",
                             "servicio": "energia",
                             "archivo_origen": nombre_archivo}

    datos["no_factura"] = _buscar(texto, r"Documento No\.:\s*([A-Z0-9]+)")
    periodo = re.search(
        r"Periodo:\s*(\d{2}-\d{2}-\d{4})/(\d{2}-\d{2}-\d{4})", texto)
    if periodo:
        datos["periodo_inicio"] = _parse_dmy(periodo.group(1))
        datos["periodo_fin"] = _parse_dmy(periodo.group(2))

    datos["fecha_pago"] = _parse_fecha_villa(
        _buscar(texto, r"^(\d{2}-[A-Z]{3}-\d{4} \d{2}:\d{2})$"))
    consumo = re.search(
        r"x (\d+) \(Consumo en kWh\)", texto)
    datos["consumo_kwh"] = float(consumo.group(1)) if consumo else None
    datos["valor_neto"] = _parse_moneda(_buscar(texto, r"VALOR NETO:\s*\$([\d\.,]+)"))
    datos["valor_factura"] = _parse_moneda(
        _buscar(texto, r"SUBTOTAL POR CONCEPTOS DE ENERGIA\s*\$([\d\.,]+)"))

    lecturas = re.search(
        r"Lectura Anterior (\d+)\s*\nLectura Actual (\d+)", texto)
    if lecturas:
        datos["lectura_anterior"] = float(lecturas.group(1))
        datos["lectura_actual"] = float(lecturas.group(2))

    datos["direccion"] = _buscar(
        texto, r"CENTRO DE ESTETICA[^\n]*\n([^\n]+)")
    datos["cuenta_ruta"] = _buscar(texto, r"Ruta:\s*([^\n]+)")
    return datos


def extraer_zipaquira_agua(texto: str, nombre_archivo: str = "") -> Dict[str, Any]:
    """Zipaquira acueducto (parcial: barcode + periodo bimestral)."""
    texto = limpiar_texto(texto)
    datos: Dict[str, Any] = {"prestador": "Zipaquira Acueducto",
                             "servicio": "acueducto",
                             "archivo_origen": nombre_archivo}

    referencia, total, fecha96 = _barcode_total(texto)
    datos["cuenta"] = referencia.lstrip("0") if referencia else None
    datos["valor_total"] = total
    datos["fecha_pago"] = fecha96

    datos["periodo_bimestral"] = _buscar(
        texto, r"([A-Z][a-z]+-[A-Z][a-z]+ \d{4})")
    datos["direccion"] = _buscar(texto, r"CONGREGACION[^\n]*\n([^\n]+)")
    datos["_pendiente_visual"] = "consumo m3 y No. factura sin rotulo claro"
    return datos


MESES_FULL = {"ENERO": 1, "FEBRERO": 2, "MARZO": 3, "ABRIL": 4, "MAYO": 5,
              "JUNIO": 6, "JULIO": 7, "AGOSTO": 8, "SEPTIEMBRE": 9,
              "OCTUBRE": 10, "NOVIEMBRE": 11, "DICIEMBRE": 12}


def _parse_fecha_nombre(valor: Optional[str]) -> Optional[str]:
    """'Febrero 19-2026' o 'Feb 01-26' -> ISO."""
    from .prestadores_bogota import MESES_ES
    if not valor:
        return None
    v = valor.strip().upper()
    match = re.match(r"([A-Z]+) (\d{1,2})-(\d{4}|\d{2})\b", v)
    if not match:
        return None
    mes_txt, dia, anio = match.groups()
    mes = MESES_FULL.get(mes_txt) or MESES_ES.get(mes_txt[:3])
    if not mes:
        return None
    if len(anio) == 2:
        anio = "20" + anio
    return f"{anio}-{mes:02d}-{int(dia):02d}"


def extraer_triple_a(texto: str, nombre_archivo: str = "") -> Dict[str, Any]:
    """Triple A — Barranquilla acueducto/alcantarillado/aseo.

    Total = suma de componentes (39,923 + 25,304 + 85,580 + 66,000 =
    216,807 verificado en muestra). Vencimiento anterior a emision en la
    muestra: se transcribe con bandera.
    """
    texto = limpiar_texto(texto)
    datos: Dict[str, Any] = {"prestador": "Triple A", "servicio": "acueducto",
                             "archivo_origen": nombre_archivo}

    datos["factura_electronica"] = _buscar(
        texto, r"Factura electronica de venta:\s*([A-Z0-9]+)")
    datos["no_factura"] = _buscar(texto, r"No\. de factura\s*(\d+)")

    triple = re.search(
        r"Fecha y hora de emision Periodo facturado Fecha de vencimiento\s*\n"
        r"([^\n]+)\s*\n([^\n]+)\s*\n([^\n]+)", texto)
    if triple:
        datos["fecha_emision"] = _parse_fecha_nombre(triple.group(1))
        datos["periodo_facturacion"] = triple.group(2).strip()
        mes = re.match(r"([A-Za-z]+)-(\d{4})", triple.group(2).strip())
        if mes and mes.group(1).upper() in MESES_FULL:
            datos["periodo_inicio"] = f"{mes.group(2)}-{MESES_FULL[mes.group(1).upper()]:02d}-01"
        datos["fecha_pago"] = _parse_fecha_nombre(triple.group(3))

    ultimo = re.search(
        r"Fecha ultimo pago Ultimo pago Fecha de suspension\s*\n"
        r"([^\n]+)\s*\n([^\n]+)\s*\n([^\n]+)", texto)
    if ultimo:
        datos["suspension"] = _parse_fecha_nombre(ultimo.group(3))

    datos["cliente"] = _buscar(texto, r"Nombre del cliente:\s*\n([^\n]+)")
    datos["direccion"] = _buscar(
        texto, r"Direccion donde se presta el servicio:\s*\n([^\n]+)")
    datos["cuenta_poliza"] = _buscar(texto, r"Poliza\s*\n(\d+)")
    datos["medidor"] = _buscar(texto, r"MEDIDOR VOL\. SAPPEL\s*\n([^\n]+)")

    acueducto = _buscar(texto, r"TOTAL ACUEDUCTO\s*\n\$([\d\.,]+)")
    alcantarillado = _buscar(texto, r"TOTAL ALCANTARILLADO\s*\n\$([\d\.,]+)")
    aseo = _buscar(texto, r"TOTAL ASEO\s*\n\$([\d\.,]+)")
    alumbrado = _buscar(texto, r"Impuesto Alumbrado Publico BQ\s*\n\$([\d\.,]+)")
    componentes = [_parse_moneda(v) for v in
                   [acueducto, alcantarillado, aseo, alumbrado]]
    if all(c is not None for c in componentes):
        datos["valor_total"] = round(sum(componentes), 2)
    datos["valor_acueducto"] = componentes[0]
    datos["valor_alcantarillado"] = componentes[1]
    datos["valor_aseo"] = componentes[2]
    datos["valor_alumbrado"] = componentes[3]

    seccion = re.search(r"Consumo basico Comercial(.*?)TOTAL ACUEDUCTO",
                        texto, re.DOTALL)
    if seccion:
        cantidades = re.findall(r"\n(\d+)\s*\n\$", seccion.group(1))
        if cantidades:
            datos["consumo_m3"] = float(cantidades[0])
    datos["_bandera"] = "vencimiento/suspension segun texto (validar ciclo)"
    return datos


def extraer_aire(texto: str, nombre_archivo: str = "") -> Dict[str, Any]:
    """Air-e/Caribesol — Barranquilla energia (layout posicional denso).

    Factura y consumo con bandera de validacion visual: el layout mezcla
    columnas y la asignacion es posicional.
    """
    texto = limpiar_texto(texto)
    datos: Dict[str, Any] = {"prestador": "Air-e", "servicio": "energia",
                             "archivo_origen": nombre_archivo}

    par = re.search(
        r"Codigo Interno:\s*\nFactura No\.:\s*\n(\d+)\s*\n(\d+)", texto)
    if par:
        datos["codigo_interno"] = par.group(1)
        datos["no_factura"] = par.group(2)

    datos["documento_equivalente"] = _buscar(
        texto, r"Credito/Otro\s*\n\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}\s*\n([A-Z0-9]+)")
    datos["referencia_pago"] = _buscar(texto, r"Referencia de pago\s*\n(\d+)")
    datos["niu"] = _buscar(texto, r"(\d{10})\s*\nFactura generada")
    if not datos["niu"]:   # el orden del texto cambia entre facturas: NIU = el de 10 digitos mas repetido
        diez = re.findall(r"\n(\d{10})\n", texto)
        if diez:
            datos["niu"] = max(set(diez), key=diez.count)

    venc = re.search(
        r"Fecha vencimiento\s*\nValor a pagar\s*\n(\d{2}/\d{2}/\d{4})\s*\n"
        r"\$ ([\d\.,]+)", texto)
    if venc:
        datos["fecha_pago"] = _parse_dmy(venc.group(1))
        datos["valor_factura"] = _parse_moneda(venc.group(2))

    periodo = re.search(r"(\d{2}/\d{2}/\d{4}) a (\d{2}/\d{2}/\d{4})", texto)
    if periodo:
        datos["periodo_inicio"] = _parse_dmy(periodo.group(1))
        datos["periodo_fin"] = _parse_dmy(periodo.group(2))

    expedicion = _buscar(
        texto, r"Credito/Otro\s*\n(\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2})")
    datos["fecha_expedicion"] = expedicion

    datos["direccion"] = _buscar(
        texto, r"\n((?:CL|KR|CR|AV)\s+[^\n]{5,50})")
    datos["titular"] = _buscar(texto, r"Informacion Cliente\s*\n([^\n]+)")

    candidatos = re.findall(r"([\d\.,]+ kWh)", texto)
    datos["consumo_candidatos"] = candidatos
    pendiente = "factura vs codigo interno"
    # Los dos "kWh" del texto son lectura inicial y final del medidor (acumuladas,
    # formato 22.566,00); el consumo facturado es su diferencia (factor 1). El mismo
    # consumo aparece suelto en formato US ("1,103.00") varias veces en el texto.
    sueltos = [float(v.replace(",", "")) for v in re.findall(r"(?<=\n)(\d[\d,]*\.00)(?=\n)", texto)]
    lecturas = [_parse_moneda(c.replace(" kWh", "")) for c in candidatos[:2]]
    consumo = None
    if len(lecturas) == 2 and None not in lecturas and lecturas[1] >= lecturas[0]:
        datos["lectura_anterior"], datos["lectura_actual"] = lecturas
        consumo = round(lecturas[1] - lecturas[0], 2)
        if consumo not in sueltos:
            pendiente += "; consumo = lectura final - inicial, sin confirmar en el texto"
    else:
        # Sin lecturas legibles: el valor (>1) que mas se repite como numero suelto.
        repetidos = [v for v in set(sueltos) if v and v > 1 and sueltos.count(v) >= 3]
        if repetidos:
            consumo = max(repetidos, key=sueltos.count)
            pendiente += "; consumo tomado del valor repetido en el texto (sin lecturas)"
        else:
            pendiente += "; consumo no identificado"
    if consumo is not None:
        datos["consumo_kwh"] = consumo
    datos["_pendiente_visual"] = pendiente
    return datos


def extraer_emcali(texto: str, nombre_archivo: str = "") -> Dict[str, Any]:
    """EmCali — factura unificada (energia + acueducto + alcantarillado).

    Retorna un dict con secciones 'energia' y 'acueducto'. Periodo tipo
    'DIC 25 a ENE 23' se interpreta DD MMM con anio inferido del mes cuenta.
    """
    from .prestadores_bogota import MESES_ES
    texto = limpiar_texto(texto)
    base: Dict[str, Any] = {"prestador": "EmCali",
                            "archivo_origen": nombre_archivo}

    base["estado_cuenta"] = _buscar(texto, r"Estado de Cuenta No\.\s*\n(\d+)")
    base["contrato"] = _buscar(texto, r"CONTRATO\s*\n(\d+)")
    base["documento_equivalente"] = _buscar(
        texto, r"DOCUMENTO EQUIVALENTE\s*\nELECTRONICO\s*\n(\d+)")
    base["mes_cuenta"] = _buscar(texto, r"Mes Cuenta\s*\n([^\n]+)")
    base["direccion"] = _buscar(
        texto, r"(AV 6 NORTE 20-67 LC 101)")
    base["titular"] = _buscar(texto, r"(SURTIACEITES[^\n]*)")
    base["ruta"] = _buscar(texto, r"Ruta\s*\n([^\n]+)")
    base["niu"] = _buscar(texto, r"NIU\s*\n(\d+)")

    mes_cuenta = re.match(r"([A-Za-z]+)\.?\s*(\d{4})", base["mes_cuenta"] or "")
    anio_cuenta = int(mes_cuenta.group(2)) if mes_cuenta else None
    mes_cuenta_n = (MESES_FULL.get(mes_cuenta.group(1).upper())
                    if mes_cuenta else None)

    periodo = re.search(r"Periodo Facturacion\s*\n([A-Z]{3}) (\d{1,2}) a ([A-Z]{3}) (\d{1,2})",
                        texto)
    if periodo and anio_cuenta and mes_cuenta_n:
        m1, d1, m2, d2 = (MESES_ES[periodo.group(1)], int(periodo.group(2)),
                          MESES_ES[periodo.group(3)], int(periodo.group(4)))
        anio_fin = anio_cuenta if m2 <= mes_cuenta_n else anio_cuenta - 1
        anio_ini = anio_fin if m1 <= m2 else anio_fin - 1
        base["periodo_inicio"] = f"{anio_ini}-{m1:02d}-{d1:02d}"
        base["periodo_fin"] = f"{anio_fin}-{m2:02d}-{d2:02d}"

    base["dias_facturados"] = _buscar(texto, r"Dias Facturados\s*\n(\d+)")
    base["fecha_pago"] = _parse_fecha_nombre(
        _buscar(texto, r"FECHA DE VENCIMIENTO\s*\n([^\n]+)"))

    referencia, total, fecha96 = _barcode_total(texto)
    base["referencia_pagos"] = referencia
    base["valor_total"] = total

    energia = dict(base)
    energia["servicio"] = "energia"
    energia["medidor"] = _buscar(
        texto, r"Consumos Anteriores \(kWh\)\s*\nNo\. Medidor M1\s*\n([^\n]+)")
    lect = re.search(
        r"Lectura Actual\s*\n([\d\.,]+)\s*\nLectura Anterior\s*\n([\d\.,]+)\s*\n"
        r"Diferencia\s*\n([\d\.,]+)\s*\n((?:(?!Consumo Actual)[^\n]*\n){0,4}?)"
        r"Consumo Actual\s*\n([\d\.,]+) KWH",
        texto)
    if lect:
        energia["lectura_actual"] = _parse_moneda(lect.group(1))
        energia["lectura_anterior"] = _parse_moneda(lect.group(2))
        energia["consumo_kwh"] = _parse_moneda(lect.group(5))
        # Entre "Diferencia" y "Consumo Actual" EmCali agrega observaciones cuando el
        # consumo es estimado ("Consumo En Investigacion - Consumo Estimado"): el
        # consumo facturado no coincide con la diferencia de lecturas.
        observacion = " ".join(l.strip() for l in lect.group(4).splitlines() if l.strip())
        if "ESTIMADO" in observacion.upper() or \
                _parse_moneda(lect.group(3)) != energia["consumo_kwh"]:
            energia["consumo_estimado"] = True
            diferencia = _parse_moneda(lect.group(3))

            def miles(x):
                return f"{x:,.0f}".replace(",", ".")
            energia["_pendiente_visual"] = (
                f"Consumo estimado por el prestador: se facturaron {miles(energia['consumo_kwh'])} kWh, "
                f"pero la diferencia de lecturas del medidor es {miles(diferencia)} kWh "
                f"({miles(energia['lectura_actual'])} - {miles(energia['lectura_anterior'])})"
                + (f". Observación en la factura: {observacion}" if observacion else "")
                + ". Suele ajustarse en una factura posterior.")
    seccion_e = texto.split("ENERGIA", 1)[1] if "ENERGIA" in texto else ""
    total_e = re.search(r"TOTAL\s*\n\$([\d\.,]+)", seccion_e)
    energia["valor_factura"] = _parse_moneda(total_e.group(1)) if total_e else None

    agua = dict(base)
    agua["servicio"] = "acueducto"
    agua["medidor"] = _buscar(
        texto, r"Consumos Anteriores \(M3\)\s*\nUso\s*\nComercial\s*\n"
                r"No\. Medidor M1\s*\n([^\n]+)")
    lect_a = re.search(
        r"Lectura Actual\s*\n(\d+)\s*\nLectura Anterior\s*\n(\d+)\s*\n"
        r"Diferencia\s*\n(\d+)\s*\nConsumo del mes en M3\s*\n(\d+)", texto)
    if lect_a:
        agua["lectura_actual"] = float(lect_a.group(1))
        agua["lectura_anterior"] = float(lect_a.group(2))
        agua["consumo_m3"] = float(lect_a.group(4))
    seccion_a = texto.split("ACUEDUCTO", 1)[1].split("ALCANTARILLADO")[0] \
        if "ACUEDUCTO" in texto else ""
    total_a = re.search(r"TOTAL\s*\n\$([\d\.,]+)", seccion_a)
    agua["valor_acueducto"] = _parse_moneda(total_a.group(1)) if total_a else None
    seccion_al = texto.split("ALCANTARILLADO", 1)[1].split("ENERGIA")[0] \
        if "ALCANTARILLADO" in texto else ""
    total_al = re.search(r"TOTAL\s*\n\$([\d\.,]+)", seccion_al)
    agua["valor_alcantarillado"] = _parse_moneda(total_al.group(1)) if total_al else None
    vert = _buscar(texto, r"Vertimiento\s*\n(\d+) M3")
    agua["vertimiento_m3"] = float(vert) if vert else None

    return {"energia": energia, "acueducto": agua}

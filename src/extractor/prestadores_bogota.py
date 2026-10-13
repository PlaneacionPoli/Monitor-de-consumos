"""
Extractores especificos por prestador — Bogota (Fase 2 del plan).

Cubre los formatos verificados en data/raw:
- Enel Colombia: factura electronica ("Factura de venta No.", periodo DD-MMM-AA).
- EAAB: documento equivalente ("Numero de esta factura", periodo MMM/DD/AAAA).

Disena contra texto de fitz (PDF digital). El ruido de codigo de barras/QR
(lineas con '^^^' y caracteres no alfanumericos) se elimina antes de extraer.
"""
import logging
import re
import unicodedata
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

MESES_ES = {
    "ENE": 1, "FEB": 2, "MAR": 3, "ABR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AGO": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DIC": 12,
}


def normalizar(texto: str) -> str:
    """Quita acentos para que los regex ASCII coincidan."""
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")


def limpiar_texto(texto: str) -> str:
    """Normaliza acentos y elimina lineas de ruido (codigo de barras/QR)."""
    texto = normalizar(texto)
    lineas = []
    for linea in texto.splitlines():
        if "^^^" in linea:
            continue
        if len(linea) > 20:
            alfanum = sum(1 for c in linea if c.isalnum() or c.isspace())
            if alfanum / len(linea) < 0.5:
                continue
        lineas.append(linea)
    return "\n".join(lineas)


def _buscar(texto: str, patrones) -> Optional[str]:
    if isinstance(patrones, str):
        patrones = [patrones]
    for patron in patrones:
        match = re.search(patron, texto, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip()
    return None


def _parse_fecha_enel(valor: str) -> Optional[str]:
    """'01-ENE-26' -> '2026-01-01'. Retorna None si no parsea."""
    match = re.match(r"(\d{1,2})-([A-Z]{3})-(\d{2})", valor.strip().upper())
    if not match:
        return None
    dia, mes_txt, anio = match.groups()
    mes = MESES_ES.get(mes_txt)
    if not mes:
        return None
    return f"20{anio}-{mes:02d}-{int(dia):02d}"


def _parse_fecha_eaab(valor: str) -> Optional[str]:
    """'DIC/21/2025' o 'FEB/26/2026' -> '2025-12-21'. Retorna None si no parsea."""
    match = re.match(r"([A-Z]{3})/(\d{1,2})/(\d{4})", valor.strip().upper())
    if not match:
        return None
    mes_txt, dia, anio = match.groups()
    mes = MESES_ES.get(mes_txt)
    if not mes:
        return None
    return f"{anio}-{mes:02d}-{int(dia):02d}"


def _parse_moneda(valor: Optional[str]) -> Optional[float]:
    """'28.708.400' -> 28708400.0 ; '31,29' -> 31.29 ; '216,807' -> 216807.0.

    Formato US con solo comas ('216,807') se distingue de decimal latino
    ('31,29'): coma seguida de 3 digitos al final = miles.
    """
    if not valor:
        return None
    limpio = valor.strip().replace("$", "").replace(" ", "")
    if "," in limpio and "." in limpio:
        if limpio.rfind(",") > limpio.rfind("."):
            limpio = limpio.replace(".", "").replace(",", ".")
        else:
            limpio = limpio.replace(",", "")
    elif "," in limpio:
        if re.search(r",\d{3}$", limpio):
            limpio = limpio.replace(",", "")
        else:
            limpio = limpio.replace(",", ".")
    else:
        limpio = limpio.replace(".", "")
    try:
        return float(limpio)
    except ValueError:
        return None


def _parse_fecha_enel_b(valor: str) -> Optional[str]:
    """'19 DIC/2025' o '26 FEB /2026' -> ISO. Retorna None si no parsea."""
    match = re.match(r"(\d{1,2})\s*([A-Z]{3})\s*/\s*(\d{4})", valor.strip().upper())
    if not match:
        return None
    dia, mes_txt, anio = match.groups()
    mes = MESES_ES.get(mes_txt)
    if not mes:
        return None
    return f"{anio}-{mes:02d}-{int(dia):02d}"


def extraer_enel(texto: str, nombre_archivo: str = "") -> Dict[str, Any]:
    """Despacha segun formato: factura electronica (Campus) o
    documento equivalente (City/Calle 84/CSU)."""
    texto = limpiar_texto(texto)
    if "FACTURA ELECTRONICA DE VENTA" in texto.upper():
        return _extraer_enel_factura(texto, nombre_archivo)
    return _extraer_enel_equivalente(texto, nombre_archivo)


def _extraer_enel_factura(texto: str, nombre_archivo: str = "") -> Dict[str, Any]:
    """Factura electronica Enel (formato Campus)."""
    texto = limpiar_texto(texto)
    datos: Dict[str, Any] = {"prestador": "Enel Colombia", "servicio": "energia",
                             "archivo_origen": nombre_archivo}

    datos["no_factura"] = _buscar(texto, r"Factura de venta No\.\s*([A-Z0-9]+)")

    periodo = re.search(
        r"Periodo Facturado\s*(\d{1,2}-[A-Z]{3}-\d{2})\s*al\s*(\d{1,2}-[A-Z]{3}-\d{2})",
        texto, re.IGNORECASE)
    if periodo:
        datos["periodo_inicio"] = _parse_fecha_enel(periodo.group(1))
        datos["periodo_fin"] = _parse_fecha_enel(periodo.group(2))

    datos["valor_factura"] = _parse_moneda(_buscar(texto, r"Neto a Pagar\s*([\d\.,]+)"))

    fecha_pago = _buscar(texto, r"Fecha de pago oportuno\s*(\d{1,2}-[A-Z]{3}-\d{2})")
    datos["fecha_pago"] = _parse_fecha_enel(fecha_pago) if fecha_pago else None

    datos["contrato_vendedor"] = _buscar(texto, r"Contrato vendedor:\s*(\d+)")
    datos["referencia_pagos"] = _buscar(
        texto, r"Referencia para pagos\s*(?:\([^)]*\))?\s*(\d+)")
    datos["numero_identificacion"] = _buscar(texto, r"Numero de identificacion\s*(\d+)")
    datos["direccion"] = _buscar(texto, r"^Servicio\s*\n(.+)$")
    datos["nit_cliente"] = _buscar(texto, r"NIT:\s*([\d\.\s]+\-\s*\d)")

    consumo = _buscar(texto, r"G\+C Activa \[kWh\]\s*[\d\-]+\s*([\d\.,]+)")
    if not consumo:
        consumo = _buscar(texto, r"Tot\. Energia\s*([\d\.,]+)")
    datos["consumo_kwh"] = _parse_moneda(consumo)
    return datos


def _extraer_enel_equivalente(texto: str, nombre_archivo: str = "") -> Dict[str, Any]:
    """Documento equivalente electronico Enel (City/Calle 84/CSU).

    Total tomado del codigo de barras (3900); fecha de pago = fecha
    adyacente al total (convencion verificada en muestra Calle 84).
    Incluye seccion de aseo cuando existe (valor_aseo).
    """
    datos: Dict[str, Any] = {"prestador": "Enel Colombia", "servicio": "energia",
                             "formato": "documento_equivalente",
                             "archivo_origen": nombre_archivo}

    datos["no_factura"] = _buscar(
        texto, r"DOCUMENTO EQUIVALENTE ELECTRONICO No\.\s*([\d\-]+)")
    datos["no_cuenta"] = _buscar(texto, r"No\. Cuenta\s*([\d\-]+)")
    datos["no_medidor"] = _buscar(
        texto, [r"No\. Medidor:\s*(\d+)", r"MEDIDOR NO:\s*(\d+)"])
    direccion = _buscar(texto, r"POLITECNICO GRAN[A-Z ]*COL[A-Z]*\s*\n(.+)")
    if not direccion:
        direccion = _buscar(
            texto, r"\n((?:CL|KR|CR|AV|TV|DG|AC|CRA)\s+[^\n]{5,60})")
    datos["direccion"] = direccion

    periodo = re.search(
        r"PERIODO FACTURADO:\s*(\d{1,2} [A-Z]{3}/\d{4})\s*A\s*(\d{1,2} [A-Z]{3}/\d{4})",
        texto, re.IGNORECASE)
    if not periodo:
        periodo = re.search(
            r"Del\s*(\d{1,2} [A-Z]{3}/\d{4})\s*(?:\||\n)\s*al\s*(\d{1,2} [A-Z]{3}/\d{4})",
            texto, re.IGNORECASE)
    if periodo:
        datos["periodo_inicio"] = _parse_fecha_enel_b(periodo.group(1))
        datos["periodo_fin"] = _parse_fecha_enel_b(periodo.group(2))
    dias = _buscar(texto, [r"DIAS\s*\nFACTURADOS:\s*(\d+)", r"(\d+)\s*dias"])
    datos["dias_facturados"] = dias

    consumo = _buscar(texto, r"CONSUMO MES\s*([\d\.,]+)\s*kWh")
    if not consumo:
        tabla = re.search(
            r"ENERGIA ACTIVA FP(.*?)\$([\d\.,]+)\s*\$([\d\.,]+)",
            texto, re.IGNORECASE | re.DOTALL)
        if tabla:
            candidatos = re.findall(r"[\d\.,]+", tabla.group(1).replace("|", " "))
            if candidatos:
                consumo = candidatos[-1]
    datos["consumo_kwh"] = _parse_moneda(consumo)

    codigo_barras = re.search(r"\(8020\)(\d+)\(3900\)0*(\d+)", texto)
    if codigo_barras:
        datos["referencia_pagos"] = codigo_barras.group(1)
        datos["valor_factura"] = float(codigo_barras.group(2))
        total_fmt = f"{float(codigo_barras.group(2)):,.0f}".replace(",", ".")
        pago = re.search(
            r"(\d{1,2} [A-Z]{3} /?\d{4})\s*\n\$" + re.escape(total_fmt), texto)
        if not pago:
            pago = re.search(
                r"Pago Oportuno\s*\|\s*(\d{1,2} [A-Z]{3} /\d{4})", texto)
        if pago:
            datos["fecha_pago"] = _parse_fecha_enel_b(pago.group(1))

    datos["valor_aseo"] = _parse_moneda(
        _buscar(texto, r"ASEO - SERVICIO NO RESIDENCIAL\s*\$([\d\.,]+)"))

    # Variante 2025 (City 2025): sin rotulo DOCUMENTO EQUIVALENTE; el numero
    # antecede al periodo y el consumo va en la tabla CONSUMO ACTIVA SENCILLA.
    if not datos.get("no_factura"):
        alt = re.search(
            r"(\d{9}-\d)\s*(?:\||\n)\s*\d{1,2} [A-Z]{3}/\d{4} A \d{1,2} [A-Z]{3}/\d{4}",
            texto)
        if alt:
            datos["no_factura"] = alt.group(1)
            datos["formato"] = "documento_equivalente_2025"
    if not datos.get("periodo_inicio"):
        periodo2 = re.search(
            r"(\d{1,2} [A-Z]{3}/\d{4})\s*A\s*(\d{1,2} [A-Z]{3}/\d{4})",
            texto, re.IGNORECASE)
        if periodo2:
            datos["periodo_inicio"] = _parse_fecha_enel_b(periodo2.group(1))
            datos["periodo_fin"] = _parse_fecha_enel_b(periodo2.group(2))
    if not datos.get("fecha_pago"):
        pago2 = re.search(
            r"(\d{1,2} [A-Z]{3} /\d{4})\s*\n\$([\d\.,]+)", texto)
        if pago2:
            datos["fecha_pago"] = _parse_fecha_enel_b(pago2.group(1))
    if not datos.get("consumo_kwh"):
        sencilla = re.search(
            r"CONSUMO ACTIVA SENCILLA(.*?)\$([\d\.,]+)\s*\$([\d\.,]+)",
            texto, re.IGNORECASE | re.DOTALL)
        if sencilla:
            candidatos = re.findall(r"[\d\.,]+", sencilla.group(1).replace("|", " "))
            if candidatos:
                datos["consumo_kwh"] = _parse_moneda(candidatos[-1])
    return datos


def extraer_eaab(texto: str, nombre_archivo: str = "") -> Dict[str, Any]:
    """Extrae campos de factura EAAB (Bogota).

    El texto de fitz separa etiquetas (bloque superior) de valores (bloque
    posterior al ancla 'MENSUAL' del reparto). El mapeo posicional es:
    MENSUAL -> cuenta_contrato, numero_pagos, periodo, pago_oportuno,
    suspension, proxima_factura. Verificado en muestra Campus ENE-2026.
    El 'Numero de esta factura' es el numero para pagos (verificado en PDF).
    """
    texto = limpiar_texto(texto)
    datos: Dict[str, Any] = {"prestador": "EAAB", "servicio": "acueducto",
                             "archivo_origen": nombre_archivo}

    bloque = re.search(
        r"(?:MENSUAL|BIMESTRAL)\s*\n(\d+)\s*\n(\d+)\s*\n"
        r"([A-Z]{3}/\d{1,2}/\d{4})\s*-\s*([A-Z]{3}/\d{1,2}/\d{4})\s*\n"
        r"([A-Z]{3}/\d{1,2}/\d{4})\s*\n([A-Z]{3}/\d{1,2}/\d{4})\s*\n"
        r"([A-Z]{3}/\d{1,2}/\d{4})",
        texto)
    if bloque:
        datos["cuenta_contrato"] = bloque.group(1)
        datos["numero_pagos"] = bloque.group(2)
        # En el recibo EAAB el "Numero para pagos" rotula "Numero de esta factura".
        datos["no_factura"] = bloque.group(2)
        datos["periodicidad"] = "bimestral" if "BIMESTRAL" in bloque.group(0) else "mensual"
        datos["periodo_inicio"] = _parse_fecha_eaab(bloque.group(3))
        datos["periodo_fin"] = _parse_fecha_eaab(bloque.group(4))
        datos["pago_oportuno"] = _parse_fecha_eaab(bloque.group(5))
        datos["suspension"] = _parse_fecha_eaab(bloque.group(6))
        datos["proxima_factura"] = _parse_fecha_eaab(bloque.group(7))
    else:
        periodo = re.search(
            r"([A-Z]{3}/\d{1,2}/\d{4})\s*-\s*([A-Z]{3}/\d{1,2}/\d{4})", texto)
        if periodo:
            datos["periodo_inicio"] = _parse_fecha_eaab(periodo.group(1))
            datos["periodo_fin"] = _parse_fecha_eaab(periodo.group(2))

    titular = re.search(
        r"[A-Z]{3}/\d{1,2}/\d{4} \d{2}:\d{2}:\d{2}\s*\n([^\n]+)\s*\n(\d+)\s*\n(\d+)\s*\n(\d+)\s*\n"
        r"([^\n]+)\s*\n([^\n]+)\s*\n([^\n]+)\s*\n([^\n]+)",
        texto)
    if titular:
        datos["clase_uso"] = titular.group(1).strip()
        datos["estrato"] = titular.group(2)
        datos["factura_nombre"] = titular.group(5).strip()
        datos["direccion"] = titular.group(6).strip()
        datos["barrio"] = titular.group(7).strip()
        datos["localidad"] = titular.group(8).strip()

    codigo_barras = re.search(r"\(3900\)0*(\d+)", texto)
    datos["valor_total"] = float(codigo_barras.group(1)) if codigo_barras else None

    historico = re.search(r"ULTIMO\s*\nCONSUMO\s*\n((?:\d+\s*\n)+)", texto)
    if historico:
        valores = re.findall(r"\d+", historico.group(1))
        datos["consumo_m3"] = float(valores[-1]) if valores else None

    datos["_pendiente_visual"] = "id_predio sin valor en texto"
    return datos

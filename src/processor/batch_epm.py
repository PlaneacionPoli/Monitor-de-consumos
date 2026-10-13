"""
PoliEcoConsumo - Procesamiento por lotes de facturas EPM
Extrae datos de PDFs de EPM y genera Excel para Energía y Acueducto
"""

import os
import re
import sys
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

import fitz
import pandas as pd

BOGOTA_TZ = ZoneInfo('America/Bogota')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MESES_EPM = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
             "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12,
             "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5,
             "junio": 6, "julio": 7, "agosto": 8, "septiembre": 9,
             "octubre": 10, "noviembre": 11, "diciembre": 12}


def referencia_emision_epm(texto):
    """(anio, mes) de emision leidos del CUERPO de la factura, o (None, None).

    Prioridad: 'Fecha de generacion dd/mm/aaaa'; luego 'facturacion <mes> de <aaaa>'.
    Propuesta §9: el periodo se toma del cuerpo, nunca de la carpeta de recepcion.
    """
    m = re.search(r"Fecha de generaci.n\s+(\d{2})/(\d{2})/(\d{4})", texto)
    if m:
        return int(m.group(3)), int(m.group(2))
    m = re.search(r"facturaci.n\s+([a-z]+)\s+de\s+(20\d{2})", texto, re.IGNORECASE)
    if m and MESES_EPM.get(m.group(1).lower()):
        return int(m.group(2)), MESES_EPM[m.group(1).lower()]
    return None, None


def resolver_periodo_epm(texto, anio_carpeta=None, mes_carpeta=None):
    """'del 20 jun al 21 jul' -> (inicio_iso, fin_iso, fuente).

    El texto del periodo no trae anio: se completa con la fecha de emision del
    cuerpo (fuente='cuerpo'). Solo si el cuerpo no la trae se usa la carpeta
    (fuente='carpeta'), que es el mes de RECEPCION: ese caso se marca para
    revision. Retorna (None, None, None) si no hay periodo o anio.
    """
    match = re.search(
        r"del\s+(\d{1,2})\s+([a-z]{3})\s+al\s+(\d{1,2})\s+([a-z]{3})",
        texto, re.IGNORECASE)
    if not match:
        return None, None, None
    anio, mes_ref = referencia_emision_epm(texto)
    fuente = "cuerpo"
    if not anio:
        anio, mes_ref, fuente = anio_carpeta, mes_carpeta, "carpeta"
    if not anio:
        return None, None, None
    d1, m1, d2, m2 = (int(match.group(1)), MESES_EPM.get(match.group(2).lower()),
                      int(match.group(3)), MESES_EPM.get(match.group(4).lower()))
    if not m1 or not m2:
        return None, None, None
    # El fin del periodo cae en el mes de emision o antes.
    anio_fin = anio - 1 if (mes_ref and m2 > mes_ref) else anio
    anio_ini = anio_fin if m1 <= m2 else anio_fin - 1
    return (f"{anio_ini}-{m1:02d}-{d1:02d}", f"{anio_fin}-{m2:02d}-{d2:02d}", fuente)


def normalizar_periodo_epm(texto, anio=None, mes_carpeta=None):
    """Compatibilidad: (inicio_iso, fin_iso) de resolver_periodo_epm."""
    ini, fin, _ = resolver_periodo_epm(texto, anio, mes_carpeta)
    return ini, fin


def extraer_datos_epm(texto, filename, anio=None):
    """Extrae campos estructurados de factura EPM (texto directo del PDF)"""
    data = {'archivo': filename}

    m = re.search(r'Direcci.n prestaci.n servicio:\s*(.+?)(?:\n|$)', texto)
    if m: data['direccion'] = m.group(1).strip()

    m = re.search(r'(?:Periodo Facturado|C.lculo Consumo)\s+del\s+(.+?)\s+al\s+(.+?)\s+\((\d+)\s+d.as\)', texto)
    if m:
        data['periodo_inicio'] = m.group(1).strip()
        data['periodo_fin'] = m.group(2).strip()
        data['dias_facturados'] = int(m.group(3))

    m = re.search(r'consumo\s+([\d\.]+)\s+kWh', texto)
    if m:
        try:
            data['consumo_kwh'] = int(m.group(1).replace('.', ''))
        except ValueError:
            pass
    if not data.get('consumo_kwh'):
        # Formato alterno: bloque 'Consumos / Valor a pagar / Energia / 22 kwh'
        m = re.search(r'Energ.i?a\s*\n(\d+)\s*kwh', texto, re.IGNORECASE)
        if m:
            data['consumo_kwh'] = int(m.group(1))

    m = re.search(r'consumo\s+([\d\.]+)\s+m3', texto)
    if m:
        try:
            data['consumo_m3'] = int(m.group(1).replace('.', ''))
        except ValueError:
            pass

    def parse_valor(texto, etiqueta):
        m = re.search(rf'{etiqueta}\s+\$?\s*([\d.,\s]+?)(?:\n|$)', texto)
        if m:
            val = m.group(1).strip()
            val = val.replace(' ', '')
            val = val.replace('.', '').replace(',', '.')
            try:
                return float(val)
            except ValueError:
                return None
        return None

    data['total_acueducto'] = parse_valor(texto, 'Total Acueducto')
    data['total_alcantarillado'] = parse_valor(texto, 'Total Alcantarillado')
    data['total_energia'] = parse_valor(texto, 'Total Energ.a')
    data['total_aseo'] = parse_valor(texto, 'Total Aseo')
    data['total_alumbrado'] = parse_valor(texto, 'Total Alumbrado')

    m = re.search(r'Categor.a:\s*(.+?)(?:\n|$)', texto)
    if m: data['categoria'] = m.group(1).strip()

    m = re.search(r'Documento No:\s*([\d\s\-]+)', texto)
    if m: data['documento'] = m.group(1).strip()

    # La cuenta de EPM es el 'Contrato' (el 'Producto' es por servicio).
    m = re.search(r'\bContrato\s+(\d{4,})', texto)
    if m: data['contrato'] = m.group(1)

    m = re.search(r'Cliente:\s*(.+?)(?:\n|$)', texto)
    if m: data['cliente'] = m.group(1).strip()

    m = re.search(r'Cc NIT:\s*(.+?)(?:\n|$)', texto)
    if m: data['nit'] = m.group(1).strip()

    data['municipio'] = 'Medellin'
    data['departamento'] = 'Antioquia'
    data['fecha_extraccion'] = datetime.now(BOGOTA_TZ).strftime('%Y-%m-%d %H:%M:%S')

    ini_iso, fin_iso, fuente = resolver_periodo_epm(
        texto, anio_carpeta=data.get('_anio'), mes_carpeta=data.get('_mes_carpeta'))
    if ini_iso:
        data['periodo_inicio_iso'] = ini_iso
        data['periodo_fin_iso'] = fin_iso
        data['periodo_fuente'] = fuente

    return data


def construir_fila_energia(data):
    """Construye fila estandarizada para libro de Energia (columnas segun config.yaml)

    VALOR FACT. = Total Energia + Total Alumbrado: la prueba control contra
    la base manual (MARZO 2025) muestra diferencia constante de $28.000,
    correspondiente al alumbrado publico incluido en el valor manual.
    """
    total_energia = data.get('total_energia', 0) or 0
    total_alumbrado = data.get('total_alumbrado', 0) or 0
    # El aseo (Emvarias) viene en el mismo recibo; si ese recibo tambien trae
    # acueducto, el aseo se registra en la fila de acueducto para no duplicarlo.
    con_acueducto = bool(data.get('total_acueducto') or data.get('total_alcantarillado'))
    aseo = 0 if con_acueducto else (data.get('total_aseo', 0) or 0)
    return {
        'No.FACTURA': data.get('documento', ''),
        'PERIODO INICIO': data.get('periodo_inicio_iso') or data.get('periodo_inicio', ''),
        'PERIODO FINAL': data.get('periodo_fin_iso') or data.get('periodo_fin', ''),
        'DIRECCION': data.get('direccion', ''),
        'PROVEEDOR': 'EPM',
        'VALOR FACT.': total_energia + total_alumbrado,
        'VALOR ASEO': aseo,
        'FECHA DE PAGO': '',
        'No.CUENTA CONTRATO': data.get('contrato', ''),
        'DIAS FACTURADOS': data.get('dias_facturados', ''),
        'CONSUMO Kwh': data.get('consumo_kwh', 0),
        'CIUDAD': data.get('municipio', ''),
        'TIPO': 'Energia',
        'ARCHIVO ORIGEN': data.get('archivo', ''),
        'PERIODO FUENTE': data.get('periodo_fuente', ''),
        'FECHA EXTRACCION': datetime.now(BOGOTA_TZ).strftime('%Y-%m-%d %H:%M:%S'),
    }


def construir_fila_acueducto(data):
    """Construye fila estandarizada para libro de Acueducto (columnas segun config.yaml)"""
    val_total = (data.get('total_acueducto', 0) or 0) + (data.get('total_alcantarillado', 0) or 0) + (data.get('total_aseo', 0) or 0)
    return {
        'No. FACTURA': data.get('documento', ''),
        'PERIODO INICIO': data.get('periodo_inicio_iso') or data.get('periodo_inicio', ''),
        'PERIODO FIN': data.get('periodo_fin_iso') or data.get('periodo_fin', ''),
        'DIRECCION': data.get('direccion', ''),
        'COMPAÑÍA': 'EPM',
        'VALOR ACUEDUCTO': data.get('total_acueducto', 0),
        'RECOLECCION BASURAS': data.get('total_aseo', 0),
        'VALOR TOTAL': val_total,
        'FECHA DE PAGO': '',
        'CONTRATO': data.get('contrato', ''),
        'DIAS FACTURADOS': data.get('dias_facturados', ''),
        'CONSUMO M3': data.get('consumo_m3', 0),
        'CIUDAD': data.get('municipio', ''),
        'TIPO': 'Acueducto',
        'ARCHIVO ORIGEN': data.get('archivo', ''),
        'PERIODO FUENTE': data.get('periodo_fuente', ''),
        'FECHA EXTRACCION': datetime.now(BOGOTA_TZ).strftime('%Y-%m-%d %H:%M:%S'),
    }


def procesar_pdf(ruta_pdf):
    """Procesa un PDF EPM y devuelve datos estructurados"""
    try:
        doc = fitz.open(ruta_pdf)
        texto = ''
        for pagina in doc:
            texto += pagina.get_text() + '\n'
        doc.close()

        if len(texto.strip()) < 50:
            logger.warning(f'Poco texto extraible: {ruta_pdf}')
            return None

        return extraer_datos_epm(texto, os.path.basename(ruta_pdf))
    except Exception as e:
        logger.error(f'Error procesando {ruta_pdf}: {e}')
        return None


def procesar_lote(carpeta_pdfs, output_dir='data/outputs'):
    """Procesa todos los PDFs en una carpeta y genera excels"""
    os.makedirs(output_dir, exist_ok=True)

    archivos = sorted(Path(carpeta_pdfs).glob('*.pdf'))
    logger.info(f'Encontrados {len(archivos)} PDFs en {carpeta_pdfs}')

    filas_energia = []
    filas_acueducto = []

    for archivo in archivos:
        logger.info(f'Procesando: {archivo.name}')
        data = procesar_pdf(str(archivo))
        if data is None:
            continue

        if data.get('total_energia'):
            filas_energia.append(construir_fila_energia(data))
        if data.get('total_acueducto') or data.get('total_alcantarillado'):
            filas_acueducto.append(construir_fila_acueducto(data))

    timestamp = datetime.now(BOGOTA_TZ).strftime('%Y%m%d_%H%M%S')

    # Excel Energia
    if filas_energia:
        df_energia = pd.DataFrame(filas_energia)
        ruta_energia = os.path.join(output_dir, f'Energia_{timestamp}.xlsx')
        df_energia.to_excel(ruta_energia, index=False, sheet_name='Energia')
        logger.info(f'Energia: {len(filas_energia)} registros -> {ruta_energia}')
    else:
        logger.warning('Sin datos de Energia para exportar')

    # Excel Acueducto
    if filas_acueducto:
        df_acueducto = pd.DataFrame(filas_acueducto)
        ruta_acueducto = os.path.join(output_dir, f'Acueducto_{timestamp}.xlsx')
        df_acueducto.to_excel(ruta_acueducto, index=False, sheet_name='Acueducto')
        logger.info(f'Acueducto: {len(filas_acueducto)} registros -> {ruta_acueducto}')
    else:
        logger.warning('Sin datos de Acueducto para exportar')

    if filas_energia or filas_acueducto:
        ruta_combinada = os.path.join(output_dir, f'facturas_{timestamp}.xlsx')
        with pd.ExcelWriter(ruta_combinada, engine='openpyxl') as writer:
            if filas_energia:
                df_energia.to_excel(writer, sheet_name='Energia', index=False)
            if filas_acueducto:
                df_acueducto.to_excel(writer, sheet_name='Acueducto', index=False)
        logger.info(f'Combinado: {ruta_combinada}')

    return len(filas_energia), len(filas_acueducto)


if __name__ == '__main__':
    carpeta = sys.argv[1] if len(sys.argv) > 1 else 'data/EPM/EPM JULIO 2025'
    n_energia, n_acueducto = procesar_lote(carpeta)
    print(f'\nResumen: {n_energia} energia, {n_acueducto} acueducto')

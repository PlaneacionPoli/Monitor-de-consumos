"""
Extraccion unificada de una factura PDF: un solo punto de entrada para la app.

Reemplaza la decision "que lote corre sobre que carpeta" por una decision por
CONTENIDO: lee el PDF (texto digital o OCR), detecta el prestador y llama al
extractor correspondiente. Devuelve filas con el mismo esquema que los lotes
historicos (hojas Energia / Acueducto), de modo que consolidar_base las acepta.

Un PDF nunca detiene el proceso: si falla o no se reconoce, el resultado trae
estado PENDIENTE o ERROR y un motivo redactado para una persona no tecnica.

Uso:
    from src.processor.extraccion import extraer_pdf
    resultado = extraer_pdf("ruta/factura.pdf")
"""
import os
import re
import shutil
from typing import Any, Dict, List, Optional

import fitz

from src.extractor.prestadores_bogota import extraer_eaab, extraer_enel, limpiar_texto
from src.extractor.prestadores_csu import (
    extraer_afinia,
    extraer_aire,
    extraer_cartagena_agua,
    extraer_emcali,
    extraer_triple_a,
    extraer_villavicencio,
    extraer_zipaquira_agua,
)
from src.processor.batch_epm import (
    MESES_EPM,
    construir_fila_acueducto,
    construir_fila_energia,
    extraer_datos_epm,
    resolver_periodo_epm,
)

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UMBRAL_TEXTO = 50           # menos caracteres => PDF escaneado (requiere OCR)

OK, PENDIENTE, ERROR, OMITIDA = "OK", "PENDIENTE", "ERROR", "OMITIDA"   # OMITIDA: fuera de alcance

# Subir esta version cuando cambie cualquier extractor: la app reprocesa lo anterior.
VERSION_EXTRACTORES = "2026.10.1"

NOMBRES_PRESTADOR = {
    "enel": "Enel", "eaab": "Acueducto de Bogotá", "afinia": "Afinia",
    "villavicencio": "Villavicencio", "zipaquira": "Zipaquirá (agua)",
    "cartagena_agua": "Aguas de Cartagena", "epm": "EPM", "triple_a": "Triple A",
    "aire": "Air-e", "emcali": "EmCali", "aseo": "Emvarias (aseo)",
}


def detectar_prestador(texto: str) -> Optional[str]:
    """Prestador por palabras clave del texto (None si el formato no se conoce)."""
    t = limpiar_texto(texto).upper()
    if "ENEL" in t:
        return "enel"
    if "AFINIA" in t:
        return "afinia"
    if "VILLAVICENCIO" in t and "LIQUIDACION" in t:
        return "villavicencio"
    if "ZIPAQUIRA" in t and "AQUAFORJAS" in t:
        return "zipaquira"
    if "AGUAS DE CARTAGENA" in t or "AQUACIS" in t:
        return "cartagena_agua"
    if "EPM" in t and ("PERIODO FACTURADO DEL" in t or "HISTORICO" in t):
        return "epm"
    if "TRIPLE A" in t:
        return "triple_a"
    if "CARIBESOL" in t or "MITHRA" in t:
        return "aire"
    if "EMCALI" in t:
        return "emcali"
    if "EAAB" in t or "ACUEDUCTO Y ALCANTARILLADO DE BOGOT" in t:
        return "eaab"
    if "EMVARIAS" in t:
        return "aseo"
    return None


def etiqueta_origen(ruta: str) -> str:
    """Etiqueta de sede/origen con la misma convencion que los lotes historicos.

    Dentro de data/raw o data/EPM conserva el criterio de siempre (CSU/<sede>,
    EPM/<carpeta>, carpeta relativa a raw). Fuera de ellas usa la carpeta madre.
    """
    ruta = os.path.abspath(ruta)
    carpeta = os.path.dirname(ruta)
    raw = os.path.join(BASE, "data", "raw")
    csu = os.path.join(raw, "SERVICIOS PUBLICOS CSUs.2026")
    epm = os.path.join(BASE, "data", "EPM")

    def dentro(raiz):
        try:
            return os.path.commonpath([carpeta, raiz]) == raiz
        except ValueError:                    # otro disco
            return False

    if dentro(csu):
        return "CSU/" + os.path.relpath(carpeta, csu)
    if dentro(epm):
        return "EPM/" + os.path.relpath(carpeta, epm).split(os.sep)[0]
    if dentro(raw):
        return os.path.relpath(carpeta, raw)
    return os.path.basename(carpeta)


def _anio_mes_carpeta(origen: str):
    """'EPM/EPM JULIO 2025' -> (2025, 7); (None, None) si no hay mes en el nombre."""
    m = re.search(r"EPM\s+([A-Z]+)\s+(\d{4})", origen.upper())
    if not m:
        return None, None
    return int(m.group(2)), MESES_EPM.get(m.group(1).lower())


class TesseractFaltante(OSError):
    """Tesseract no esta instalado o le falta el idioma español; el mensaje es para el usuario."""


MSG_SIN_TESSERACT = ("El PDF es una imagen escaneada y este equipo no tiene Tesseract para leerla. "
                     "Instálalo con Instalar.bat o desde https://github.com/UB-Mannheim/tesseract/wiki "
                     "y vuelve a cargar estas facturas (las facturas digitales no lo necesitan).")
MSG_SIN_IDIOMA = ("El PDF es una imagen escaneada y a Tesseract le falta el idioma español. "
                  "Copia spa.traineddata en la carpeta config/tessdata del proyecto y vuelve a cargar estas facturas.")


def buscar_tesseract() -> Optional[str]:
    """Ruta de tesseract.exe: variable TESSERACT_PATH, PATH y carpetas habituales de Windows."""
    candidatos = [os.environ.get("TESSERACT_PATH"), shutil.which("tesseract")]
    for var in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        raiz = os.environ.get(var)
        if raiz:
            candidatos.append(os.path.join(raiz, "Tesseract-OCR", "tesseract.exe"))
            candidatos.append(os.path.join(raiz, "Programs", "Tesseract-OCR", "tesseract.exe"))
    return next((c for c in candidatos if c and os.path.isfile(c)), None)


def _preparar_tesseract() -> None:
    """Localiza Tesseract, corrige TESSDATA_PREFIX obsoleto y exige el idioma español."""
    exe = buscar_tesseract()
    if not exe:
        raise TesseractFaltante(MSG_SIN_TESSERACT)
    os.environ["TESSERACT_PATH"] = exe                 # OCREngine lo usa como tesseract_cmd
    previo = os.environ.get("TESSDATA_PREFIX")
    for c in (previo, os.path.join(BASE, "config", "tessdata"), os.path.join(os.path.dirname(exe), "tessdata")):
        if c and os.path.isfile(os.path.join(c, "spa.traineddata")):
            os.environ["TESSDATA_PREFIX"] = c
            return
    if previo and not os.path.isdir(previo):
        del os.environ["TESSDATA_PREFIX"]              # apunta a una carpeta que ya no existe
    raise TesseractFaltante(MSG_SIN_IDIOMA)


def leer_texto(ruta: str, ocr=None):
    """(texto, via_ocr). Texto digital con PyMuPDF; OCR solo si el PDF es imagen."""
    doc = fitz.open(ruta)
    try:
        texto = "\n".join(pg.get_text() for pg in doc)
    finally:
        doc.close()
    if len(texto.strip()) >= UMBRAL_TEXTO:
        return texto, False
    if ocr is None:
        _preparar_tesseract()
        from src.ocr.ocr_engine import crear_engine_ocr
        ocr = crear_engine_ocr({"idioma": "spa", "config_tesseract": "--psm 6 --oem 3"})
    return ocr.procesar_archivo(ruta), True


def _filas(prestador: str, texto: str, nombre: str, origen: str) -> List[Dict[str, Any]]:
    """Filas [{'hoja': 'Energia'|'Acueducto', 'datos': {...}}] segun el prestador."""
    filas: List[Dict[str, Any]] = []

    def agregar(hoja, datos, clave_sede="sede_origen"):
        datos[clave_sede] = origen
        filas.append({"hoja": hoja, "datos": datos})

    if prestador == "enel":
        datos = extraer_enel(texto, nombre)
        datos["servicio"] = "energia"
        agregar("Energia", datos)
    elif prestador in ("afinia", "villavicencio", "aire"):
        extractor = {"afinia": extraer_afinia, "villavicencio": extraer_villavicencio,
                     "aire": extraer_aire}[prestador]
        agregar("Energia", extractor(texto, nombre))
    elif prestador in ("cartagena_agua", "zipaquira", "triple_a", "eaab"):
        extractor = {"cartagena_agua": extraer_cartagena_agua,
                     "zipaquira": extraer_zipaquira_agua,
                     "triple_a": extraer_triple_a, "eaab": extraer_eaab}[prestador]
        agregar("Acueducto", extractor(texto, nombre))
    elif prestador == "emcali":
        partes = extraer_emcali(texto, nombre)
        agregar("Energia", partes["energia"])
        agregar("Acueducto", partes["acueducto"])
    elif prestador == "epm":
        datos = extraer_datos_epm(texto, nombre)
        anio, mes = _anio_mes_carpeta(origen)
        datos["_anio"], datos["_mes_carpeta"] = anio, mes
        ini, fin, fuente = resolver_periodo_epm(texto, anio, mes)
        if ini:
            datos["periodo_inicio_iso"] = ini
            datos["periodo_fin_iso"] = fin
            datos["periodo_fuente"] = fuente
        datos["sede_origen"] = origen
        if datos.get("total_energia"):
            agregar("Energia", construir_fila_energia(datos), "CIUDAD")
        if datos.get("total_acueducto") or datos.get("total_alcantarillado"):
            agregar("Acueducto", construir_fila_acueducto(datos), "CIUDAD")
    return filas


def extraer_pdf(ruta: str, ocr=None, origen: Optional[str] = None) -> Dict[str, Any]:
    """Procesa un PDF. Nunca lanza excepcion: informa estado y motivo.

    Retorna {archivo, ruta, origen, estado (OK/PENDIENTE/ERROR), motivo,
             prestador, via_ocr, filas}.
    """
    nombre = os.path.basename(ruta)
    origen = origen or etiqueta_origen(ruta)
    res = {"archivo": nombre, "ruta": ruta, "origen": origen, "estado": OK,
           "motivo": "", "prestador": None, "via_ocr": False, "filas": []}
    try:
        texto, res["via_ocr"] = leer_texto(ruta, ocr)
    except Exception as exc:  # noqa: BLE001
        res["estado"] = ERROR
        if isinstance(exc, TesseractFaltante):
            res["motivo"] = str(exc)
        elif isinstance(exc, (ImportError, OSError)) and "tesseract" in str(exc).lower():
            res["motivo"] = MSG_SIN_TESSERACT
        else:
            res["motivo"] = f"No se pudo abrir o leer el PDF ({exc})."
        return res
    if len(texto.strip()) < UMBRAL_TEXTO:
        res["estado"] = PENDIENTE
        res["motivo"] = "No se pudo leer texto del PDF (imagen ilegible o vacío)."
        return res
    prestador = detectar_prestador(texto)
    res["prestador"] = NOMBRES_PRESTADOR.get(prestador)
    if prestador is None:
        res["estado"] = PENDIENTE
        if len(texto.strip()) < 300:
            res["motivo"] = ("El PDF tiene casi nada de texto legible (escaneo de baja "
                             "calidad o carátula interna); hay que revisarlo a mano.")
        else:
            res["motivo"] = "Formato de factura no reconocido (prestador nuevo o distinto)."
        return res
    if prestador == "aseo":
        res["estado"] = OMITIDA
        res["motivo"] = "Factura de aseo (Emvarias): fuera del alcance de energía y acueducto."
        return res
    try:
        res["filas"] = _filas(prestador, texto, nombre, origen)
    except Exception as exc:  # noqa: BLE001
        res["estado"] = ERROR
        res["motivo"] = f"Se reconoció la factura de {res['prestador']} pero falló la lectura ({exc})."
        return res
    if not res["filas"] and "EMVARIAS" in texto.upper():
        res["estado"] = OMITIDA
        res["motivo"] = "Factura de aseo (Emvarias): fuera del alcance de energía y acueducto."
    elif not res["filas"]:
        res["estado"] = PENDIENTE
        res["motivo"] = (f"Factura de {res['prestador']} sin valores de consumo "
                         "o total legibles.")
    return res

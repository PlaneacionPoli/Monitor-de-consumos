"""
Lote Bogota: Enel + EAAB con metrica de exito por campo (Fase 2 del plan).
- PDF digital -> texto fitz directo; PDF imagen (<50 chars) -> OCR Tesseract.
- Deteccion de prestador por palabras clave; exporta Excel + resumen en consola.
Uso: python scripts/procesar_lote_bogota.py
"""
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import fitz
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.extractor.prestadores_bogota import extraer_eaab, extraer_enel, limpiar_texto
from src.ocr.ocr_engine import crear_engine_ocr

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
from src.utils import rutas  # noqa: E402
CARPETAS = [
    os.path.join(BASE, "data", "raw", "RECIBOS DE ENERGIA SEDES"),
    os.path.join(BASE, "data", "raw", "RECIBOS ACUEDUCTO SEDES"),
]
CAMPOS_CLAVE = ["no_factura", "cuenta_contrato", "periodo_inicio", "periodo_fin",
                "valor_factura", "valor_total", "consumo_kwh", "consumo_m3"]


def detectar_prestador(texto: str):
    t = texto.lower()
    if "enel" in t:
        return "enel"
    if "acueducto" in t or "eaab" in t or "alcantarillado" in t:
        return "eaab"
    return None


def main():
    ocr = crear_engine_ocr({"idioma": "spa", "config_tesseract": "--psm 6 --oem 3"})
    energia, acueducto, fallos, via_ocr = [], [], [], 0

    pdfs = []
    for carpeta in CARPETAS:
        for dirpath, _, archivos in os.walk(carpeta):
            pdfs += [os.path.join(dirpath, a) for a in sorted(archivos)
                     if a.lower().endswith(".pdf")]
    print(f"PDF a procesar: {len(pdfs)}")

    for ruta in pdfs:
        nombre = os.path.basename(ruta)
        sede = os.path.relpath(os.path.dirname(ruta), os.path.join(BASE, "data", "raw"))
        try:
            doc = fitz.open(ruta)
            texto = "\n".join(pg.get_text() for pg in doc)
            doc.close()
            if len(texto.strip()) < 50:
                texto = ocr.procesar_archivo(ruta)
                via_ocr += 1
            prestador = detectar_prestador(limpiar_texto(texto))
            if prestador == "enel":
                datos = extraer_enel(texto, nombre)
                datos["servicio"] = "energia"
                datos["sede_origen"] = sede
                energia.append(datos)
            elif prestador == "eaab":
                datos = extraer_eaab(texto, nombre)
                datos["sede_origen"] = sede
                acueducto.append(datos)
            else:
                fallos.append((sede + "/" + nombre, "prestador no detectado"))
        except Exception as exc:  # noqa: BLE001
            fallos.append((nombre, f"error: {exc}"))

    print(f"Energia: {len(energia)} | Acueducto: {len(acueducto)} | "
          f"Fallos: {len(fallos)} | Via OCR: {via_ocr}")
    for nombre, motivo in fallos:
        print(f"  FALLO {nombre}: {motivo}")

    for etiqueta, filas in (("energia", energia), ("acueducto", acueducto)):
        if not filas:
            continue
        print(f"--- {etiqueta} (n={len(filas)}) ---")
        for campo in CAMPOS_CLAVE:
            ok = sum(1 for f in filas if f.get(campo) not in (None, ""))
            print(f"  {campo}: {ok}/{len(filas)}")

    if energia or acueducto:
        fecha = datetime.now(ZoneInfo("America/Bogota")).strftime("%Y%m%d_%H%M%S")
        salida = rutas.ruta(f"bogota_{fecha}.xlsx")
        with pd.ExcelWriter(salida, engine="openpyxl") as writer:
            if energia:
                pd.DataFrame(energia).to_excel(writer, sheet_name="Energia", index=False)
            if acueducto:
                pd.DataFrame(acueducto).to_excel(writer, sheet_name="Acueducto", index=False)
            if fallos:
                pd.DataFrame(
                    [{"archivo": n, "motivo": m, "estado": "REVISION_MANUAL"}
                     for n, m in fallos]
                ).to_excel(writer, sheet_name="Pendientes", index=False)
        print(f"Excel: {salida}")


if __name__ == "__main__":
    main()

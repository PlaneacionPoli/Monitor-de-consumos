"""
Lote CSU: enruta Enel->extractor Bogota, EPM->batch_epm, resto->Pendientes.
Uso: python scripts/procesar_lote_csu.py
"""
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import fitz
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.extractor.prestadores_bogota import extraer_enel, limpiar_texto
from src.extractor.prestadores_csu import (
    extraer_afinia,
    extraer_aire,
    extraer_cartagena_agua,
    extraer_emcali,
    extraer_triple_a,
    extraer_villavicencio,
    extraer_zipaquira_agua,
)
from src.ocr.ocr_engine import crear_engine_ocr
from src.processor.batch_epm import (
    construir_fila_acueducto,
    construir_fila_energia,
    extraer_datos_epm,
)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
from src.utils import rutas  # noqa: E402
CARPETA = os.path.join(BASE, "data", "raw", "SERVICIOS PUBLICOS CSUs.2026")


def detectar(texto: str):
    t = texto.upper()
    if "ENEL" in t:
        return "enel"
    if "AFINIA" in t:
        return "afinia"
    if "VILLAVICENCIO" in t and "LIQUIDACION" in t:
        return "villavicencio"
    if "ZIPAQUIRA" in t and "AQUAFORJAS" in t.upper():
        return "zipaquira"
    if "AGUAS DE CARTAGENA" in t or "AQUACIS" in t.upper():
        return "cartagena_agua"
    if "EPM" in t and ("PERIODO FACTURADO DEL" in t or "HISTORICO" in t.upper()):
        return "epm"
    if "TRIPLE A" in t:
        return "triple_a"
    if "CARIBESOL" in t or "MITHRA" in t.upper():
        return "aire"
    if "EMCALI" in t:
        return "emcali"
    for marca, etiqueta in [("EMCALI", "emcali"), ("AFINIA", "afinia"),
                            ("TRIPLE A", "aaa"), ("EMSA", "emsa"),
                            ("ACUEDUCTO", "acueducto_otro"),
                            ("ENERGIA", "energia_otro")]:
        if marca in t:
            return etiqueta
    return None


def main():
    ocr = crear_engine_ocr({"idioma": "spa", "config_tesseract": "--psm 6 --oem 3"})
    energia, acueducto, pendientes, via_ocr = [], [], [], 0

    pdfs = []
    for dirpath, _, archivos in os.walk(CARPETA):
        pdfs += [os.path.join(dirpath, a) for a in sorted(archivos)
                 if a.lower().endswith(".pdf")]
    print(f"PDF CSU: {len(pdfs)}")

    for ruta in pdfs:
        nombre = os.path.basename(ruta)
        sede = os.path.relpath(os.path.dirname(ruta), CARPETA)
        try:
            doc = fitz.open(ruta)
            texto = "\n".join(pg.get_text() for pg in doc)
            doc.close()
            if len(texto.strip()) < 50:
                texto = ocr.procesar_archivo(ruta)
                via_ocr += 1
            tipo = detectar(limpiar_texto(texto))
            if tipo == "enel":
                datos = extraer_enel(texto, nombre)
                datos["servicio"] = "energia"
                datos["sede_origen"] = "CSU/" + sede
                energia.append(datos)
            elif tipo in ("afinia", "villavicencio"):
                extractor = (extraer_afinia if tipo == "afinia"
                             else extraer_villavicencio)
                datos = extractor(texto, nombre)
                datos["sede_origen"] = "CSU/" + sede
                energia.append(datos)
            elif tipo in ("cartagena_agua", "zipaquira"):
                extractor = (extraer_cartagena_agua if tipo == "cartagena_agua"
                             else extraer_zipaquira_agua)
                datos = extractor(texto, nombre)
                datos["sede_origen"] = "CSU/" + sede
                acueducto.append(datos)
            elif tipo == "triple_a":
                datos = extraer_triple_a(texto, nombre)
                datos["sede_origen"] = "CSU/" + sede
                acueducto.append(datos)
            elif tipo == "aire":
                datos = extraer_aire(texto, nombre)
                datos["sede_origen"] = "CSU/" + sede
                energia.append(datos)
            elif tipo == "emcali":
                partes = extraer_emcali(texto, nombre)
                for seccion, lista in (("energia", energia),
                                       ("acueducto", acueducto)):
                    fila = partes[seccion]
                    fila["sede_origen"] = "CSU/" + sede
                    lista.append(fila)
            elif tipo == "epm":
                datos = extraer_datos_epm(texto, nombre)
                if datos.get("total_energia"):
                    fila = construir_fila_energia(datos)
                    fila["CIUDAD"] = "CSU/" + sede
                    energia.append(fila)
                if datos.get("total_acueducto") or datos.get("total_alcantarillado"):
                    fila = construir_fila_acueducto(datos)
                    fila["CIUDAD"] = "CSU/" + sede
                    acueducto.append(fila)
            else:
                pendientes.append((f"CSU/{sede}/{nombre}", f"formato nuevo: {tipo}"))
        except Exception as exc:  # noqa: BLE001
            pendientes.append((f"CSU/{sede}/{nombre}", f"error: {exc}"))

    print(f"Energia: {len(energia)} | Acueducto: {len(acueducto)} | "
          f"Pendientes: {len(pendientes)} | Via OCR: {via_ocr}")
    for nombre, motivo in pendientes:
        print(f"  PENDIENTE {nombre}: {motivo}")

    fecha = datetime.now(ZoneInfo("America/Bogota")).strftime("%Y%m%d_%H%M%S")
    salida = rutas.ruta(f"csu_{fecha}.xlsx")
    with pd.ExcelWriter(salida, engine="openpyxl") as writer:
        if energia:
            pd.DataFrame(energia).to_excel(writer, sheet_name="Energia", index=False)
        if acueducto:
            pd.DataFrame(acueducto).to_excel(writer, sheet_name="Acueducto", index=False)
        if pendientes:
            pd.DataFrame(
                [{"archivo": n, "motivo": m, "estado": "FORMATO_NUEVO"}
                 for n, m in pendientes]
            ).to_excel(writer, sheet_name="Pendientes", index=False)
    print(f"Excel: {salida}")


if __name__ == "__main__":
    main()

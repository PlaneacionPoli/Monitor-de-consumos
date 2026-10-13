"""
Lote EPM-Medellin: procesa las 11 carpetas mensuales con periodo ISO (Fase 2).
Anio/mes inferidos del nombre de carpeta ('EPM JULIO 2025' -> 2025/7).
Salida: data/outputs/epm_<fecha>.xlsx (Energia + Acueducto, esquema config).
Uso: python scripts/procesar_lote_epm.py
"""
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import fitz
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.processor.batch_epm import (
    MESES_EPM,
    construir_fila_acueducto,
    construir_fila_energia,
    extraer_datos_epm,
    resolver_periodo_epm,
)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
from src.utils import rutas  # noqa: E402
CARPETA_EPM = os.path.join(BASE, "data", "EPM")


def carpeta_fecha(nombre: str):
    """'EPM JULIO 2025' -> (2025, 7)."""
    match = re.search(r"EPM\s+([A-Z]+)\s+(\d{4})", nombre.upper())
    if not match:
        return None, None
    return int(match.group(2)), MESES_EPM.get(match.group(1).lower())


def main():
    filas_energia, filas_acueducto, fallos = [], [], []
    total = 0
    for carpeta in sorted(Path(CARPETA_EPM).iterdir()):
        if not carpeta.is_dir():
            continue
        anio, mes = carpeta_fecha(carpeta.name)
        pdfs = sorted(carpeta.glob("*.pdf"))
        if not pdfs:
            continue
        print(f"{carpeta.name}: {len(pdfs)} PDF (anio={anio}, mes={mes})")
        total += len(pdfs)
        for pdf in pdfs:
            try:
                doc = fitz.open(str(pdf))
                texto = "\n".join(pg.get_text() for pg in doc)
                doc.close()
                if len(texto.strip()) < 50:
                    fallos.append((pdf.name, "sin texto extraible"))
                    continue
                datos = extraer_datos_epm(texto, pdf.name)
                datos["_anio"] = anio
                datos["_mes_carpeta"] = mes
                ini, fin, fuente = resolver_periodo_epm(texto, anio, mes)
                if ini:
                    datos["periodo_inicio_iso"] = ini
                    datos["periodo_fin_iso"] = fin
                    datos["periodo_fuente"] = fuente
                datos["sede_origen"] = f"EPM/{carpeta.name}"
                if datos.get("total_energia"):
                    fila = construir_fila_energia(datos)
                    fila["CIUDAD"] = f"EPM/{carpeta.name}"
                    filas_energia.append(fila)
                if datos.get("total_acueducto") or datos.get("total_alcantarillado"):
                    fila = construir_fila_acueducto(datos)
                    fila["CIUDAD"] = f"EPM/{carpeta.name}"
                    filas_acueducto.append(fila)
            except Exception as exc:  # noqa: BLE001
                fallos.append((pdf.name, f"error: {exc}"))

    print(f"Total PDF: {total} | Energia: {len(filas_energia)} | "
          f"Acueducto: {len(filas_acueducto)} | Fallos: {len(fallos)}")
    for nombre, motivo in fallos[:10]:
        print(f"  FALLO {nombre}: {motivo}")

    fecha = datetime.now(ZoneInfo("America/Bogota")).strftime("%Y%m%d_%H%M%S")
    salida = rutas.ruta(f"epm_{fecha}.xlsx")
    with pd.ExcelWriter(salida, engine="openpyxl") as writer:
        if filas_energia:
            pd.DataFrame(filas_energia).to_excel(writer, sheet_name="Energia", index=False)
        if filas_acueducto:
            pd.DataFrame(filas_acueducto).to_excel(writer, sheet_name="Acueducto", index=False)
        if fallos:
            pd.DataFrame(
                [{"archivo": n, "motivo": m, "estado": "REVISION_MANUAL"}
                 for n, m in fallos]
            ).to_excel(writer, sheet_name="Pendientes", index=False)
    print(f"Excel: {salida}")


if __name__ == "__main__":
    main()

"""
Inventario y clasificacion digital vs. imagen de facturas (Fase 1 del plan).
Recorre carpetas 5, 6, 7 de data/raw + data/EPM y genera data/outputs/inventario_pdfs.csv
Criterio: <50 caracteres extraibles => IMAGEN (requiere OCR); en otro caso DIGITAL.
Uso: python scripts/clasificar_pdfs.py
"""
import csv
import os
import sys

import fitz

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTAS = [
    os.path.join(BASE, "data", "raw", "RECIBOS ACUEDUCTO SEDES"),
    os.path.join(BASE, "data", "raw", "RECIBOS DE ENERGIA SEDES"),
    os.path.join(BASE, "data", "raw", "SERVICIOS PUBLICOS CSUs.2026"),
    os.path.join(BASE, "data", "EPM"),
]
SALIDA = os.path.join(BASE, "data", "outputs", "inventario_pdfs.csv")
UMBRAL_CHARS = 50


def clasificar(ruta_pdf):
    """Retorna (n_chars, n_paginas, n_imagenes, tipo)."""
    doc = fitz.open(ruta_pdf)
    texto = "".join(pagina.get_text() for pagina in doc)
    n_chars = len(texto.strip())
    n_pag = len(doc)
    n_img = sum(len(pagina.get_images()) for pagina in doc)
    doc.close()
    tipo = "IMAGEN" if n_chars < UMBRAL_CHARS else "DIGITAL"
    return n_chars, n_pag, n_img, tipo


def main():
    filas = []
    for raiz in RUTAS:
        if not os.path.isdir(raiz):
            print(f"AVISO: no existe {raiz}, se omite")
            continue
        for dirpath, _, archivos in os.walk(raiz):
            for archivo in sorted(archivos):
                if not archivo.lower().endswith(".pdf"):
                    continue
                ruta = os.path.join(dirpath, archivo)
                rel = os.path.relpath(ruta, BASE)
                try:
                    n_chars, n_pag, n_img, tipo = clasificar(ruta)
                    filas.append([rel, n_chars, n_pag, n_img, tipo, ""])
                except Exception as exc:  # noqa: BLE001
                    filas.append([rel, 0, 0, 0, "ERROR", str(exc)][:5] + [str(exc)])
    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    with open(SALIDA, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["archivo", "chars", "paginas", "imagenes", "tipo", "error"])
        writer.writerows(filas)

    total = len(filas)
    n_dig = sum(1 for r in filas if r[4] == "DIGITAL")
    n_img = sum(1 for r in filas if r[4] == "IMAGEN")
    n_err = total - n_dig - n_img
    print(f"Total: {total} PDF | DIGITAL: {n_dig} | IMAGEN: {n_img} | ERROR: {n_err}")
    print(f"Inventario: {SALIDA}")
    return 0 if n_err == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

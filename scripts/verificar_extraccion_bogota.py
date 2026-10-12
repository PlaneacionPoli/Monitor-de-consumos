"""Verificacion de extractores Enel/EAAB contra muestras reales (Fase 2)."""
import fitz
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.extractor.prestadores_bogota import extraer_eaab, extraer_enel

BASE = r"C:\Users\ximen\OneDrive\Proyectos_DS\OCR Facturas\data\raw"
MUESTRAS = [
    (r"RECIBOS DE ENERGIA SEDES\1. CAMPUS POLITECNICO\1. ENERO.2026.pdf", extraer_enel),
    (r"RECIBOS ACUEDUCTO SEDES\1. SEDE CAMPUS POLITECNICO\1. ENERO.2026.pdf", extraer_eaab),
]
for rel, extractor in MUESTRAS:
    doc = fitz.open(os.path.join(BASE, rel))
    texto = "\n".join(pg.get_text() for pg in doc)
    doc.close()
    datos = extractor(texto, os.path.basename(rel))
    print("=" * 80)
    print(rel)
    for k, v in datos.items():
        print(f"  {k}: {v}")

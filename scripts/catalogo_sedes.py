"""
Catalogo sede<-direccion (Fase 2 del plan).

Genera data/outputs/catalogo_sedes.csv con las direcciones distintas de la
base, sede de carpeta mayoritaria, sugerencia por reglas y columna
sede_confirmada vacia para validacion del Analista SGA.
Uso: python scripts/catalogo_sedes.py
"""
import glob
import os
import sys
import re

import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
from src.utils import rutas  # noqa: E402
SALIDAS = os.path.join(BASE, "data", "outputs")

REGLAS = [
    (r"PENDIENTE", "SIN_MAPEO"),
    (r"BELLO", "BELLO"),
    (r"CR 74|CL 53|CR 73|CL 50.*70|CR 50", "MEDELLIN-LOS COLORES"),
    (r"CL 57", "BOGOTA-CAMPUS"),
    (r"CL 61", "BOGOTA-CITY CAMPUS"),
    (r"KR 19|CALLE 84", "BOGOTA-CALLE 84"),
    (r"CL 65|BOSA", "CSU BOSA"),
    (r"PORTAL 80|KR 7", "CSU PORTAL 80"),
    (r"CHIA", "CSU CHIA"),
    (r"SOACHA", "CSU SOACHA"),
    (r"ZIPAQUIRA|CL 1 NO 10", "CSU ZIPAQUIRA"),
    (r"CARTAGENA|PLAZUELA|AFINIA", "CSU CARTAGENA"),
    (r"BARRANQUILLA|TRIPLE A|AIR-E|CARIBESOL", "CSU BARRANQUILLA"),
    (r"CALI|EMCALI", "CSU CALI"),
    (r"VILLAVICENCIO", "CSU VILLAVICENCIO"),
]


CARPETA_SEDE = [
    ("BELLO", "BELLO"),
    ("CAMPUS POLITECNICO", "BOGOTA-CAMPUS"),
    ("CITY CAMPUS", "BOGOTA-CITY CAMPUS"),
    ("CALLE 84", "BOGOTA-CALLE 84"),
    ("ZIPAQUIRA", "CSU ZIPAQUIRA"),
    ("CHIA", "CSU CHIA"),
    ("SOACHA", "CSU SOACHA"),
    ("BOSA", "CSU BOSA"),
    ("PORTAL 80", "CSU PORTAL 80"),
    ("CARTAGENA", "CSU CARTAGENA"),
    ("BARRANQUILLA", "CSU BARRANQUILLA"),
    ("CALI", "CSU CALI"),
    ("VILLAVICENCIO", "CSU VILLAVICENCIO"),
    ("EPM/", "MEDELLIN-LOS COLORES"),
]


def sugerir(prestador, direccion, sede_carpeta):
    if "PENDIENTE" in direccion.upper():
        return "SIN_MAPEO"
    carpeta = sede_carpeta.upper()
    for token, sede in CARPETA_SEDE:
        if token in carpeta:
            return sede
    texto = f"{prestador} {direccion}".upper()
    for patron, sede in REGLAS:
        if re.search(patron, texto):
            return sede
    return "REVISAR"


def main():
    ruta = rutas.todos("base_unificada_*.xlsx")[-1]
    base = pd.read_excel(ruta, sheet_name="Base")
    base["direccion_norm"] = (base["direccion"].astype(str)
                              .str.replace(r"\s*\|\s*\d+$", "", regex=True)
                              .str.strip())
    cat = (base.groupby(["prestador", "direccion_norm"])
           .agg(filas=("factura", "size"),
                sede_carpeta=("sede", lambda s: s.mode().iloc[0] if not s.mode().empty else ""))
           .reset_index())
    cat["sede_sugerida"] = [sugerir(p, d, s) for p, d, s in
                            zip(cat["prestador"], cat["direccion_norm"], cat["sede_carpeta"])]
    cat["sede_confirmada"] = ""
    salida = rutas.ruta("catalogo_sedes.csv")
    cat.to_csv(salida, index=False)
    print(f"Direcciones: {len(cat)}")
    print(cat["sede_sugerida"].value_counts().to_string())
    print(f"Salida: {salida}")


if __name__ == "__main__":
    main()

"""
Validacion de atipicos >20% y cola de revision (Fase 2 del plan).

- Lee la ultima base_unificada_*.xlsx (hoja Base) + hojas Pendientes de
  bogota_*.xlsx / csu_*.xlsx.
- Regla Propuesta §9: variacion de consumo >20% frente al mismo periodo del
  ano anterior -> ATIPICO_REVISAR. Sin historico anual: compara contra la
  mediana de los 3 periodos previos (criterio suplente, marcado).
- Salida: validacion_<fecha>.xlsx con hojas Base (columna estado),
  Atipicos y ColaRevision (atipicos + pendientes manuales).
Uso: python scripts/validar_atipicos.py
"""
import glob
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.processor.validacion import validar_base  # noqa: E402
from src.utils import rutas  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALIDAS = os.path.join(BASE, "data", "outputs")
UMBRAL = 0.20


ultimo = rutas.ultimo   # busca en la carpeta de la etapa (data/outputs/<etapa>/)


def main():
    ruta = ultimo("base_unificada_*.xlsx")
    if not ruta:
        print("Sin base unificada. Ejecute consolidar_base.py primero.")
        return 1
    base = pd.read_excel(ruta, sheet_name="Base")
    base["periodo_fin"] = pd.to_datetime(base["periodo_fin"], errors="coerce")
    base = base[base["periodo_fin"].notna()].copy()
    base, atipicos_idx = validar_base(base, UMBRAL)

    print(f"Filas evaluadas: {len(base)} | Atipicos: {len(atipicos_idx)}")

    pendientes = []
    for patron in ["bogota_*.xlsx", "csu_*.xlsx"]:
        ruta_lote = ultimo(patron)
        if not ruta_lote:
            continue
        libro = pd.read_excel(ruta_lote, sheet_name=None)
        if "Pendientes" in libro:
            for _, r in libro["Pendientes"].iterrows():
                pendientes.append({
                    "archivo": r.get("archivo"),
                    "motivo": r.get("motivo"),
                    "estado": r.get("estado", "REVISION_MANUAL"),
                })
    cola = pd.DataFrame(pendientes)
    print(f"Pendientes manuales: {len(cola)}")

    fecha = datetime.now(ZoneInfo("America/Bogota")).strftime("%Y%m%d_%H%M%S")
    salida = rutas.ruta(f"validacion_{fecha}.xlsx")
    with pd.ExcelWriter(salida, engine="openpyxl") as writer:
        base.to_excel(writer, sheet_name="Base", index=False)
        base.loc[atipicos_idx].to_excel(writer, sheet_name="Atipicos", index=False)
        if not cola.empty:
            cola.to_excel(writer, sheet_name="ColaRevision", index=False)
    print(f"Salida: {salida}")
    for _, r in base.loc[atipicos_idx][
            ["sede", "factura", "periodo_fin", "consumo", "detalle"]].iterrows():
        print(f"  ATIPICO {r['sede']}: {r['factura']} "
              f"{r['periodo_fin'].date()} consumo={r['consumo']:,.0f} {r['detalle']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

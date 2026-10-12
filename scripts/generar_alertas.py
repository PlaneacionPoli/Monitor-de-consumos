"""
Motor de alertas: faltantes por huecos de serie + resumen (Fase 2 del plan).

- Faltante: la cadencia (mensual/bimensual) se infiere por medidor y se alerta
  si un hueco supera 1.5 cadencias o si la serie termina antes del corte
  (src/processor/faltantes.py). Cada caso = posible factura no llegada ->
  ALERTA_FALTANTE para el Analista SGA.
- Combina atipicos (validacion_*.xlsx) y faltantes en alertas_<fecha>.xlsx.
Uso: python scripts/generar_alertas.py [--corte AAAA-MM-DD]
"""
import glob
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.processor.faltantes import detectar_faltantes  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALIDAS = os.path.join(BASE, "data", "outputs")


def main():
    corte = None
    if "--corte" in sys.argv:
        corte = sys.argv[sys.argv.index("--corte") + 1]
    validacion = sorted(glob.glob(os.path.join(SALIDAS, "validacion_*.xlsx")))
    if not validacion:
        print("Sin validacion. Ejecute validar_atipicos.py primero.")
        return 1
    libro = pd.read_excel(validacion[-1], sheet_name=None)
    base = libro["Base"].copy()
    base["periodo_fin"] = pd.to_datetime(base["periodo_fin"], errors="coerce")
    base = base[base["periodo_fin"].notna()].sort_values(
        ["servicio", "cuenta_grupo", "periodo_fin"])

    faltantes = detectar_faltantes(base, corte=corte)

    atipicos = base[base["estado"] == "ATIPICO_REVISAR"]
    print(f"Atipicos: {len(atipicos)} | Faltantes: {len(faltantes)}")

    fecha = datetime.now(ZoneInfo("America/Bogota")).strftime("%Y%m%d_%H%M%S")
    salida = os.path.join(SALIDAS, f"alertas_{fecha}.xlsx")
    with pd.ExcelWriter(salida, engine="openpyxl") as writer:
        atipicos.to_excel(writer, sheet_name="Atipicos", index=False)
        if faltantes:
            pd.DataFrame(faltantes).to_excel(
                writer, sheet_name="Faltantes", index=False)
        resumen = pd.DataFrame([
            {"indicador": "filas_base", "valor": len(base)},
            {"indicador": "atipicos", "valor": len(atipicos)},
            {"indicador": "faltantes", "valor": len(faltantes)},
            {"indicador": "ok", "valor": int((base['estado'] == 'OK').sum())},
        ])
        resumen.to_excel(writer, sheet_name="Resumen", index=False)
    print(f"Salida: {salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

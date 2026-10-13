"""
Carga la ultima validacion_*.xlsx al almacen local y aplica la compuerta
(F1-D03/V05, hallazgo H4).

  python scripts/cargar_almacen.py              # carga y muestra conteos
  python scripts/cargar_almacen.py --publicar   # CONFIRMADO -> OFICIAL
  python scripts/cargar_almacen.py --exportar   # escribe base_oficial_<fecha>.xlsx

Solo las filas OFICIAL llegan a la exportacion: lo EN_REVISION espera al Analista.
La recarga es idempotente y no pisa las revisiones ya hechas.
"""
import glob
import os
import re
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
from src.utils import rutas  # noqa: E402
sys.path.insert(0, BASE)
from src.storage.repositorio import Repositorio  # noqa: E402

SALIDAS = os.path.join(BASE, "data", "outputs")
RUTA_DB = rutas.ruta("monitor.db")


def main():
    validaciones = rutas.todos("validacion_*.xlsx")
    if not validaciones:
        print("Sin validacion. Ejecute validar_atipicos.py primero.")
        return 1
    ruta = validaciones[-1]
    run_id = re.search(r"validacion_(\d{8}_\d{6})", ruta).group(1)
    repo = Repositorio(RUTA_DB)
    base = pd.read_excel(ruta, sheet_name="Base")
    r = repo.cargar_validacion(base, run_id=run_id, origen=os.path.basename(ruta))
    print(f"Lote {run_id}: nuevos {r['nuevos']} | omitidos {r['omitidos']}")
    if "--publicar" in sys.argv:
        r = repo.publicar_oficial()
        print(f"Publicados a OFICIAL: {r['publicados']}")
    print("Estados:", repo.conteo())
    if "--exportar" in sys.argv:
        oficial = repo.exportar_oficial()
        fecha = datetime.now(ZoneInfo("America/Bogota")).strftime("%Y%m%d_%H%M%S")
        salida = rutas.ruta(f"base_oficial_{fecha}.xlsx")
        oficial.to_excel(salida, sheet_name="Base", index=False)
        print(f"Base oficial: {len(oficial)} filas -> {salida}")
    rotos = repo.verificar_auditoria()
    print("Auditoria:", "integra" if not rotos else f"ALTERADA en revisiones {rotos}")
    repo.cerrar()
    return 0


if __name__ == "__main__":
    sys.exit(main())

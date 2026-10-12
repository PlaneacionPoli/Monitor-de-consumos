"""
Orquestador unico del pipeline (DoD: lote autonomo por el Analista SGA).

Encadena: clasificar -> lotes (bogota, csu, epm) -> consolidar -> validar ->
alertas -> prueba_control. Mide tiempo por etapa y escribe resumen.
Uso: python scripts/pipeline.py
"""
import os
import subprocess
import sys
import time
from datetime import timedelta

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ETAPAS = [
    ("clasificar", [sys.executable, "scripts/clasificar_pdfs.py"]),
    ("lote_bogota", [sys.executable, "scripts/procesar_lote_bogota.py"]),
    ("lote_csu", [sys.executable, "scripts/procesar_lote_csu.py"]),
    ("lote_epm", [sys.executable, "scripts/procesar_lote_epm.py"]),
    ("consolidar", [sys.executable, "scripts/consolidar_base.py"]),
    ("validar", [sys.executable, "scripts/validar_atipicos.py"]),
    ("alertas", [sys.executable, "scripts/generar_alertas.py"]),
    ("almacen", [sys.executable, "scripts/cargar_almacen.py"]),
    ("prueba_control", [sys.executable, "scripts/prueba_control.py"]),
    ("pruebas", [sys.executable, "-m", "pytest", "tests/", "-q"]),
]


def main():
    print("=== PIPELINE PoliEcoConsumo ===")
    inicio = time.time()
    tiempos = {}
    for nombre, cmd in ETAPAS:
        t0 = time.time()
        print(f"\n--- etapa: {nombre} ---")
        r = subprocess.run(cmd, cwd=BASE)
        dt = time.time() - t0
        tiempos[nombre] = dt
        print(f"[{nombre}] {timedelta(seconds=int(dt))} "
              f"({'OK' if r.returncode == 0 else 'FALLO'})")
        if r.returncode != 0:
            print(f"Pipeline detenido en {nombre}.")
            return 1
    total = time.time() - inicio
    print("\n=== RESUMEN ===")
    for nombre, dt in tiempos.items():
        print(f"  {nombre}: {timedelta(seconds=int(dt))}")
    print(f"  TOTAL: {timedelta(seconds=int(total))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

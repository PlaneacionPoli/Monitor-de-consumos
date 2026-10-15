"""
Carga incremental por linea de comandos (la misma logica que usa la app).

Uso:
    python scripts/procesar_archivos.py <carpeta|pdf> [<carpeta|pdf> ...] [--solo-extraer] [--forzar] [--simular]

  --simular      muestra el plan (nuevas / ya cargadas) y no procesa nada
  --solo-extraer extrae y registra, sin actualizar el libro final
  --forzar       reprocesa tambien lo ya cargado
"""
import argparse
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
from src.processor import actualizacion, carga  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("rutas", nargs="+")
    ap.add_argument("--solo-extraer", action="store_true")
    ap.add_argument("--forzar", action="store_true")
    ap.add_argument("--simular", action="store_true")
    a = ap.parse_args()

    plan = carga.planificar(a.rutas)
    print(f"Nuevas: {len(plan['nuevos'])} | Ya cargadas: {len(plan['ya_cargados'])} | "
          f"A reprocesar: {len(plan['reprocesar'])} | Repetidas en la selección: "
          f"{len(plan['repetidos_en_seleccion'])} | Ignoradas (no PDF): {len(plan['ignorados'])}")
    if a.simular:
        return 0

    def progreso(i, n, archivo):
        if archivo:
            print(f"  [{i + 1}/{n}] {archivo}")

    r = carga.procesar(a.rutas, progreso=progreso, forzar=a.forzar)
    print(f"Leídas: {r['leidas']} | Correctas: {r['ok']} | Pendientes: {r['pendientes']} | "
          f"Errores: {r['errores']} | Fuera de alcance: {r['fuera_de_alcance']} | "
          f"Ya cargadas (omitidas): {r['omitidas']}")
    for d in r["detalle"]:
        if d["estado"] != "OK":
            print(f"  {d['estado']}: {d['archivo']} -> {d['motivo']}")
    if a.solo_extraer:
        return 0
    res = actualizacion.actualizar(lambda i, n, e: print(f"[{i}/{n}] {e}"))
    if not res["ok"]:
        print(f"FALLÓ en '{res['etapa_fallida']}':\n{res['detalle']}")
        return 1
    print(f"Archivo actualizado: {res['libro']}")
    for aviso in res.get("avisos", []):
        print(f"AVISO: {aviso}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

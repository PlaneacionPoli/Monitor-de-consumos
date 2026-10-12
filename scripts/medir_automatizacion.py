"""
Mide el % de facturas procesadas sin revision manual (F1-C04, hallazgo H7).

Propuesta §7: meta >= 80%, minimo >= 60%. Lee la ultima validacion_*.xlsx y
cuenta como 'sin revision' las filas con estado OK. Desglosa el resto por causa
y, en los atipicos, por metodo de comparacion (anual vs. mediana de 3 periodos):
los atipicos por mediana3 son el efecto de no tener 12 meses de historico.
Uso: python scripts/medir_automatizacion.py
"""
import glob
import os
import sys

import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALIDAS = os.path.join(BASE, "data", "outputs")
META, MINIMO = 0.80, 0.60


def main():
    rutas = sorted(glob.glob(os.path.join(SALIDAS, "validacion_*.xlsx")))
    if not rutas:
        print("Sin validacion. Ejecute validar_atipicos.py primero.")
        return 1
    base = pd.read_excel(rutas[-1], sheet_name="Base")
    total = len(base)
    ok = int((base["estado"] == "OK").sum())
    pct = ok / total
    print(f"Fuente: {os.path.basename(rutas[-1])} | filas: {total}")
    print(f"Sin revision (OK): {ok} = {pct:.1%} "
          f"(meta {META:.0%}, minimo {MINIMO:.0%}) -> "
          f"{'CUMPLE META' if pct >= META else 'CUMPLE MINIMO' if pct >= MINIMO else 'BAJO EL MINIMO'}")

    causas = base["estado"].value_counts().rename_axis("estado").reset_index(name="filas")
    causas["pct"] = (causas["filas"] / total).round(3)
    print("\nPor estado:")
    print(causas.to_string(index=False))

    atip = base[base["estado"] == "ATIPICO_REVISAR"].copy()
    atip["metodo"] = atip["detalle"].str.extract(r"\((anual|mediana3)\)")
    por_metodo = atip["metodo"].value_counts()
    print("\nAtipicos por metodo de comparacion:")
    print(por_metodo.to_string())
    if "mediana3" in por_metodo.index:
        sin_sup = ok + int(por_metodo["mediana3"])
        print(f"\nSi los atipicos por mediana3 (historico < 12 m) quedaran fuera de revision, "
              f"el % seria {sin_sup / total:.1%}: cota superior, no una medicion.")

    salida = os.path.join(SALIDAS, "medicion_automatizacion.csv")
    causas.to_csv(salida, index=False)
    print(f"\nSalida: {salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

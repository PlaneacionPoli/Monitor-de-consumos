"""
Sede por contrato/cuenta, para facturas cuya direccion no identifica la sede.

EPM factura algunos contratos con la direccion "Pendiente Planeacion": la
direccion no sirve, pero el contrato (cuenta) si. El archivo
data/outputs/catalogos/sedes_por_contrato.csv (cuenta,sede,nota) se edita a mano.
Solo completa las filas que el catalogo de direcciones no pudo mapear.

Uso: from src.utils.sedes import completar_sede_por_cuenta
"""
import os

import pandas as pd

from src.utils import rutas


def mapa_cuentas() -> dict:
    ruta = rutas.ruta("sedes_por_contrato.csv")
    if not os.path.exists(ruta):
        return {}
    cat = pd.read_csv(ruta, dtype=str).fillna("")
    return {r["cuenta"].strip(): r["sede"].strip()
            for _, r in cat.iterrows() if r["cuenta"].strip() and r["sede"].strip()}


def completar_sede_por_cuenta(base: pd.DataFrame, sin_mapeo: str) -> pd.DataFrame:
    """Asigna `sede_final` por cuenta donde sigue valiendo `sin_mapeo`."""
    por_cuenta = base["cuenta"].astype(str).str.strip().map(mapa_cuentas())
    pendiente = base["sede_final"] == sin_mapeo
    base.loc[pendiente, "sede_final"] = por_cuenta[pendiente].fillna(sin_mapeo)
    return base

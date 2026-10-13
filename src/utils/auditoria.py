"""
Log de auditoria de revisiones humanas (Fase 2 del plan).

Propuesta §5/§9: ninguna modificacion manual sin registro (quien, cuando,
valor original vs. nuevo). Cada decision del Analista SGA sobre la cola de
revision (atipicos + pendientes) se anexa a data/outputs/control/auditoria.csv.
"""
import csv
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from src.utils import rutas

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUTA_LOG = rutas.ruta("auditoria.csv")
CAMPOS = ["fecha", "revisor", "factura", "archivo", "campo", "valor_original",
          "valor_nuevo", "decision", "observacion"]

DECISIONES_VALIDAS = {"APROBADO", "CORREGIDO", "RECHAZADO"}


def registrar_revision(revisor, factura, archivo, campo, valor_original,
                       valor_nuevo, decision, observacion=""):
    """Anexa una decision de revision al log. Retorna la fila registrada."""
    if decision not in DECISIONES_VALIDAS:
        raise ValueError(f"decision debe ser una de {DECISIONES_VALIDAS}")
    fila = {
        "fecha": datetime.now(ZoneInfo("America/Bogota")).strftime("%Y-%m-%d %H:%M:%S"),
        "revisor": revisor,
        "factura": factura,
        "archivo": archivo,
        "campo": campo,
        "valor_original": valor_original,
        "valor_nuevo": valor_nuevo,
        "decision": decision,
        "observacion": observacion,
    }
    existe = os.path.exists(RUTA_LOG)
    with open(RUTA_LOG, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CAMPOS)
        if not existe:
            writer.writeheader()
        writer.writerow(fila)
    return fila


def leer_log():
    """Retorna las revisiones registradas (lista de dicts)."""
    if not os.path.exists(RUTA_LOG):
        return []
    with open(RUTA_LOG, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

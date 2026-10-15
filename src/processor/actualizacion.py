"""
Actualizacion del archivo final despues de una carga: encadena las etapas de la
cadena existente sobre lo acumulado por carga.py.

Etapas: extraccion (libro acumulado) -> consolidar -> validar -> alertas ->
almacen -> exportar libro -> dashboard local -> ordenar. Cada etapa tiene un nombre legible para
mostrarlo en la app. Se detiene en la primera que falle y lo informa.

Uso:
    from src.processor.actualizacion import actualizar
    resultado = actualizar(avance=lambda i, n, etapa: print(i, n, etapa))
"""
import os
import shutil
import subprocess
import sys
from typing import Callable, Dict, Optional

from src.processor import carga

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# (nombre legible, script, opcional): si una etapa opcional falla, la actualizacion sigue y se avisa.
ETAPAS = [
    ("Consolidando facturas y quitando duplicados", "scripts/consolidar_base.py", False),
    ("Buscando consumos atípicos", "scripts/validar_atipicos.py", False),
    ("Generando alertas", "scripts/generar_alertas.py", False),
    ("Guardando en el almacén de datos", "scripts/cargar_almacen.py", False),
    ("Actualizando el archivo Consumos_Consolidado.xlsx", "scripts/exportar_consolidado.py", False),
    ("Actualizando el dashboard", "scripts/publicar_dashboard.py --local", True),
    ("Ordenando archivos de salida", "scripts/ordenar_outputs.py", False),
]

LIBRO_FINAL = os.path.join(BASE, "data", "outputs", "Consumos_Consolidado.xlsx")
SITIO_LOCAL = os.path.join(BASE, "data", "outputs", "sitio_local")   # dashboard del equipo (ingreso automatico)


def _aviso_dashboard(detalle: str) -> str:
    if "Sin correos autorizados" in detalle:
        return ("El dashboard no se actualizó: no hay correos autorizados. Agrega uno por línea en "
                "config/accesos_dashboard.txt y vuelve a pulsar «Actualizar el archivo». "
                "El archivo Excel sí quedó actualizado.")
    return ("El dashboard no se pudo actualizar (el archivo Excel sí quedó actualizado). "
            "Detalle para el equipo técnico: " + detalle.strip()[-400:])


def actualizar(avance: Optional[Callable[[int, int, str], None]] = None) -> Dict[str, object]:
    """Retorna {'ok', 'libro', 'etapa_fallida', 'detalle'}."""
    total = len(ETAPAS) + 1
    if avance:
        avance(0, total, "Reuniendo todo lo extraído")
    libro = carga.exportar_extraccion()
    if libro is None:
        return {"ok": False, "libro": None, "etapa_fallida": "Reuniendo todo lo extraído",
                "detalle": "Todavía no hay facturas extraídas correctamente."}
    avisos = []
    for i, (nombre, script, opcional) in enumerate(ETAPAS, 1):
        if avance:
            avance(i, total, nombre)
        r = subprocess.run([sys.executable, *script.split()], cwd=BASE, capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            detalle = (r.stderr or r.stdout)[-1500:]
            if opcional:
                avisos.append(_aviso_dashboard(detalle))
                continue
            return {"ok": False, "libro": None, "etapa_fallida": nombre, "detalle": detalle}
    if avance:
        avance(total, total, "Listo")
    return {"ok": True, "libro": LIBRO_FINAL, "etapa_fallida": None, "detalle": "", "avisos": avisos}

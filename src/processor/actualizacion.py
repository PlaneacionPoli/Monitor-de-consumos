"""
Actualizacion del archivo final despues de una carga: encadena las etapas de la
cadena existente sobre lo acumulado por carga.py.

Etapas: extraccion (libro acumulado) -> consolidar -> validar -> alertas ->
almacen -> exportar libro -> dashboard HTML (site/, cifrado) -> ordenar. Cada etapa tiene un nombre legible para
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

ETAPAS = [
    ("Consolidando facturas y quitando duplicados", "scripts/consolidar_base.py"),
    ("Buscando consumos atípicos", "scripts/validar_atipicos.py"),
    ("Generando alertas", "scripts/generar_alertas.py"),
    ("Guardando en el almacén de datos", "scripts/cargar_almacen.py"),
    ("Actualizando el archivo Consumos_Consolidado.xlsx", "scripts/exportar_consolidado.py"),
    ("Actualizando el dashboard", "scripts/publicar_dashboard.py"),
    ("Ordenando archivos de salida", "scripts/ordenar_outputs.py"),
]

LIBRO_FINAL = os.path.join(BASE, "data", "outputs", "Consumos_Consolidado.xlsx")
SITIO = os.path.join(BASE, "site")
SITIO_LOCAL = os.path.join(BASE, "app", "static", "dashboard")   # copia que sirve Streamlit


def copiar_dashboard_local() -> bool:
    """Copia site/ (dashboard HTML oficial) a la carpeta estatica de la app."""
    if not os.path.isfile(os.path.join(SITIO, "index.html")):
        return False
    shutil.rmtree(SITIO_LOCAL, ignore_errors=True)
    shutil.copytree(SITIO, SITIO_LOCAL, dirs_exist_ok=True)   # tolera archivos bloqueados por el visor
    return True


def actualizar(avance: Optional[Callable[[int, int, str], None]] = None) -> Dict[str, object]:
    """Retorna {'ok', 'libro', 'etapa_fallida', 'detalle'}."""
    total = len(ETAPAS) + 1
    if avance:
        avance(0, total, "Reuniendo todo lo extraído")
    libro = carga.exportar_extraccion()
    if libro is None:
        return {"ok": False, "libro": None, "etapa_fallida": "Reuniendo todo lo extraído",
                "detalle": "Todavía no hay facturas extraídas correctamente."}
    for i, (nombre, script) in enumerate(ETAPAS, 1):
        if avance:
            avance(i, total, nombre)
        r = subprocess.run([sys.executable, script], cwd=BASE, capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            return {"ok": False, "libro": None, "etapa_fallida": nombre,
                    "detalle": (r.stderr or r.stdout)[-1500:]}
    copiar_dashboard_local()
    if avance:
        avance(total, total, "Listo")
    return {"ok": True, "libro": LIBRO_FINAL, "etapa_fallida": None, "detalle": ""}

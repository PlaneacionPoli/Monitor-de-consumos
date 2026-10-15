"""
Organizacion de data/outputs por etapa del pipeline.

Cada archivo vive en la carpeta de su etapa, segun el prefijo de su nombre:

  01_extraccion/   bogota_*, csu_*, epm_*, extraccion_*  (lotes extraidos de los PDF)
  02_consolidado/  base_unificada_*                 (esquema comun, sin duplicados)
  03_validacion/   validacion_*                     (estado, severidad, confianza)
  04_alertas/      alertas_*                        (atipicos y faltantes)
  05_oficial/      base_oficial_*, monitor.db       (solo lo confirmado)
  catalogos/       catalogo_sedes.csv, sedes_por_contrato.csv, inventario_pdfs.csv
  control/         auditoria.csv, medicion_automatizacion.csv, accesos_dashboard.csv
  _historico/<etapa>/  versiones anteriores de cada etapa (no se borran)
  _legado/         salidas del diseno original (Energia_*, Acueducto_*, facturas_*)

En la raiz queda solo el libro final Consumos_Consolidado.xlsx y el LEEME.md.
Los scripts piden las rutas aqui; ninguno arma rutas de data/outputs a mano.
"""
import filecmp
import glob
import os
import shutil

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SALIDAS = os.path.join(BASE, "data", "outputs")

# prefijo del nombre de archivo -> carpeta de la etapa (el mas largo primero)
CARPETAS = [
    ("base_unificada_", "02_consolidado"),
    ("base_oficial_", "05_oficial"),
    ("bogota_", "01_extraccion"),
    ("csu_", "01_extraccion"),
    ("epm_", "01_extraccion"),
    ("extraccion_", "01_extraccion"),
    ("validacion_", "03_validacion"),
    ("alertas_", "04_alertas"),
    ("monitor.db", "05_oficial"),
    ("catalogo_sedes", "catalogos"),
    ("sedes_por_contrato", "catalogos"),
    ("inventario_pdfs", "catalogos"),
    ("auditoria", "control"),
    ("registro_extracciones", "control"),
    ("medicion_automatizacion", "control"),
    ("accesos_dashboard", "control"),
    ("Energia_", "_legado"),
    ("Acueducto_", "_legado"),
    ("facturas_", "_legado"),
]
# prefijos con una version por corrida (las anteriores se archivan)
VERSIONADOS = ["bogota_", "csu_", "epm_", "extraccion_", "base_unificada_", "validacion_", "alertas_", "base_oficial_"]
HISTORICO = "_historico"


def carpeta_de(nombre: str) -> str:
    """Carpeta (se crea si no existe) donde debe vivir el archivo `nombre` o patron."""
    for prefijo, sub in CARPETAS:
        if nombre.startswith(prefijo):
            ruta = os.path.join(SALIDAS, sub)
            os.makedirs(ruta, exist_ok=True)
            return ruta
    os.makedirs(SALIDAS, exist_ok=True)
    return SALIDAS


def ruta(nombre: str) -> str:
    """Ruta completa del archivo `nombre` en su carpeta de etapa."""
    return os.path.join(carpeta_de(nombre), nombre)


CONFIG_CATALOGOS = os.path.join(BASE, "config", "catalogos")


def catalogo(nombre: str) -> str:
    """Ruta de un catalogo (catalogo_sedes.csv, sedes_por_contrato.csv).

    Manda la version de trabajo de data/outputs/catalogos si existe; si no (equipo nuevo, sin data/),
    la copia semilla de config/catalogos que viaja con el proyecto."""
    trabajo = ruta(nombre)
    semilla = os.path.join(CONFIG_CATALOGOS, nombre)
    return trabajo if os.path.exists(trabajo) or not os.path.exists(semilla) else semilla


def todos(patron: str) -> list:
    """Archivos que cumplen el patron (p. ej. 'validacion_*.xlsx'), del mas antiguo al mas reciente."""
    return sorted(glob.glob(os.path.join(carpeta_de(patron), patron)))


def ultimo(patron: str):
    encontrados = todos(patron)
    return encontrados[-1] if encontrados else None


def _mover(origen: str, destino_dir: str) -> bool:
    os.makedirs(destino_dir, exist_ok=True)
    destino = os.path.join(destino_dir, os.path.basename(origen))
    try:
        if os.path.exists(destino):
            # ya movido (p. ej. la copia salio bien y el borrado del original fallo): limpia si son iguales
            if not filecmp.cmp(origen, destino, shallow=False):
                return False
            os.remove(origen)
            return True
        shutil.move(origen, destino)
        return True
    except PermissionError:
        return False     # archivo abierto en otro programa; se reintenta en la proxima corrida


def archivar(prefijo: str) -> int:
    """Deja solo la version mas reciente de `prefijo` y mueve las demas a _historico/<etapa>/."""
    archivos = todos(prefijo + "*")
    etapa = os.path.basename(carpeta_de(prefijo))
    n = 0
    for viejo in archivos[:-1]:
        n += _mover(viejo, os.path.join(SALIDAS, HISTORICO, etapa))
    return n


def ordenar() -> dict:
    """Lleva cada archivo suelto de la raiz a su carpeta y archiva las versiones anteriores."""
    movidos, bloqueados = [], []
    if os.path.isdir(SALIDAS):
        for nombre in sorted(os.listdir(SALIDAS)):
            origen = os.path.join(SALIDAS, nombre)
            if not os.path.isfile(origen) or nombre.startswith("~$"):
                continue
            destino = carpeta_de(nombre)
            if destino == SALIDAS:
                continue
            (movidos if _mover(origen, destino) else bloqueados).append(nombre)
    archivadas = sum(archivar(p) for p in VERSIONADOS)
    return {"movidos": movidos, "bloqueados": bloqueados, "archivadas": archivadas}

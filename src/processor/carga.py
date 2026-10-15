"""
Carga incremental de facturas: lo que la app hace cuando el usuario elige archivos.

- planificar(): vista previa (nuevas / ya cargadas / a reprocesar) sin extraer nada.
- procesar(): extrae solo lo nuevo, guarda el resultado en un registro por hash
  del archivo (SQLite en data/outputs/control/) y reporta progreso.
- exportar_extraccion(): vuelca TODO lo acumulado en 01_extraccion/extraccion_<fecha>.xlsx,
  que la cadena (consolidar -> validar -> ...) lee en lugar de los lotes sueltos.

El hash identifica el contenido: la misma factura copiada a otra carpeta o
renombrada no se vuelve a extraer. Si cambia VERSION_EXTRACTORES, lo anterior
se marca "a reprocesar".

Uso:
    from src.processor import carga
    plan = carga.planificar(["C:/facturas/mayo"])
    resumen = carga.procesar(["C:/facturas/mayo"], progreso=lambda i, n, a: print(i, n, a))
"""
import hashlib
import json
import os
import sqlite3
from datetime import datetime
from typing import Callable, Dict, Iterable, List, Optional
from zoneinfo import ZoneInfo

import pandas as pd

from src.processor.extraccion import (
    ERROR, OK, OMITIDA, PENDIENTE, VERSION_EXTRACTORES, etiqueta_origen, extraer_pdf,
)
from src.utils import rutas

Progreso = Callable[[int, int, str], None]


def _conectar(db: Optional[str] = None) -> sqlite3.Connection:
    con = sqlite3.connect(db or rutas.ruta("registro_extracciones.db"))
    con.execute("""CREATE TABLE IF NOT EXISTS extracciones (
        hash TEXT PRIMARY KEY, archivo TEXT, ruta TEXT, origen TEXT, estado TEXT,
        motivo TEXT, prestador TEXT, via_ocr INTEGER, filas TEXT,
        version TEXT, procesado TEXT)""")
    return con


def hash_archivo(ruta: str) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def expandir_rutas(entradas: Iterable[str]):
    """(pdfs, ignorados): archivos y carpetas (recursivo) -> PDFs unicos y ordenados."""
    pdfs, ignorados = [], []
    for entrada in entradas:
        entrada = os.path.abspath(entrada)
        if os.path.isdir(entrada):
            for dirpath, _, archivos in os.walk(entrada):
                for a in sorted(archivos):
                    if a.startswith("~$"):
                        continue
                    (pdfs if a.lower().endswith(".pdf") else ignorados).append(
                        os.path.join(dirpath, a))
        elif os.path.isfile(entrada):
            (pdfs if entrada.lower().endswith(".pdf") else ignorados).append(entrada)
        else:
            ignorados.append(entrada)
    return sorted(dict.fromkeys(pdfs)), ignorados


def _previo(con, h: str):
    fila = con.execute(
        "SELECT estado, version, archivo, origen FROM extracciones WHERE hash=?", (h,)
    ).fetchone()
    return dict(zip(("estado", "version", "archivo", "origen"), fila)) if fila else None


def planificar(entradas: Iterable[str], db: Optional[str] = None) -> Dict[str, list]:
    """Clasifica cada PDF antes de procesar. Claves: nuevos, ya_cargados,
    reprocesar, repetidos_en_seleccion, ignorados (cada elemento es un dict o ruta)."""
    pdfs, ignorados = expandir_rutas(entradas)
    plan = {"nuevos": [], "ya_cargados": [], "reprocesar": [],
            "repetidos_en_seleccion": [], "ignorados": ignorados}
    vistos: Dict[str, str] = {}
    with _conectar(db) as con:
        for ruta in pdfs:
            h = hash_archivo(ruta)
            item = {"ruta": ruta, "archivo": os.path.basename(ruta), "hash": h}
            if h in vistos:
                plan["repetidos_en_seleccion"].append({**item, "igual_a": vistos[h]})
                continue
            vistos[h] = ruta
            previo = _previo(con, h)
            if previo is None:
                plan["nuevos"].append(item)
            elif previo["estado"] in (OK, OMITIDA) and previo["version"] == VERSION_EXTRACTORES:
                plan["ya_cargados"].append({**item, "cargado_como": previo["archivo"]})
            else:
                plan["reprocesar"].append({**item, "estado_previo": previo["estado"]})
    return plan


def procesar(entradas: Iterable[str], progreso: Optional[Progreso] = None,
             forzar: bool = False, db: Optional[str] = None) -> Dict[str, object]:
    """Extrae los PDF nuevos (o todos con forzar=True) y los registra.

    Retorna {'leidas', 'ok', 'pendientes', 'errores', 'omitidas', 'detalle'};
    detalle trae por archivo: archivo, estado, motivo, prestador, filas.
    """
    plan = planificar(entradas, db)
    pendientes_de_proceso = plan["nuevos"] + plan["reprocesar"]
    if forzar:
        pendientes_de_proceso += plan["ya_cargados"]
    total = len(pendientes_de_proceso)
    resumen = {"leidas": 0, "ok": 0, "pendientes": 0, "errores": 0, "fuera_de_alcance": 0,
               "omitidas": 0 if forzar else len(plan["ya_cargados"]),
               "repetidas": len(plan["repetidos_en_seleccion"]), "detalle": []}
    ocr = None
    ahora = lambda: datetime.now(ZoneInfo("America/Bogota")).isoformat(timespec="seconds")  # noqa: E731
    with _conectar(db) as con:
        for i, item in enumerate(pendientes_de_proceso, 1):
            if progreso:
                progreso(i - 1, total, item["archivo"])
            res = extraer_pdf(item["ruta"], ocr, etiqueta_origen(item["ruta"]))
            con.execute(
                "INSERT OR REPLACE INTO extracciones VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (item["hash"], res["archivo"], res["ruta"], res["origen"], res["estado"],
                 res["motivo"], res["prestador"], int(res["via_ocr"]),
                 json.dumps(res["filas"], ensure_ascii=False, default=str),
                 VERSION_EXTRACTORES, ahora()))
            con.commit()
            resumen["leidas"] += 1
            clave = {OK: "ok", PENDIENTE: "pendientes", ERROR: "errores",
                     OMITIDA: "fuera_de_alcance"}[res["estado"]]
            resumen[clave] += 1
            resumen["detalle"].append({k: res[k] for k in
                                       ("archivo", "origen", "estado", "motivo", "prestador")}
                                      | {"filas": len(res["filas"])})
        if progreso:
            progreso(total, total, "")
    return resumen


def estado_registro(db: Optional[str] = None) -> Dict[str, int]:
    with _conectar(db) as con:
        return dict(con.execute(
            "SELECT estado, COUNT(*) FROM extracciones GROUP BY estado").fetchall())


LOTES_HISTORICOS = ("bogota_*.xlsx", "csu_*.xlsx", "epm_*.xlsx")


def _lotes_historicos() -> Dict[str, list]:
    """Hojas de los ultimos lotes de los scripts por carpeta (anteriores a la app).

    Sin esto, el primer extraccion_* haria desaparecer lo ya extraido con los lotes: el
    libro acumulado los incluye y consolidar_base quita los duplicados (primero gana el
    registro de la app)."""
    hojas: Dict[str, list] = {"Energia": [], "Acueducto": [], "Pendientes": []}
    for patron in LOTES_HISTORICOS:
        ruta = rutas.ultimo(patron)
        if not ruta:
            continue
        for nombre, df in pd.read_excel(ruta, sheet_name=None).items():
            if nombre in hojas and not df.empty:
                hojas[nombre].append(df)
    return hojas


def exportar_extraccion(db: Optional[str] = None, destino: Optional[str] = None,
                        incluir_historico: bool = True) -> Optional[str]:
    """Escribe el libro acumulado (Energia / Acueducto / Pendientes). None si no hay datos.

    Incluye lo extraido por la app y, por defecto, los lotes historicos (ver _lotes_historicos)."""
    energia, acueducto, pendientes = [], [], []
    with _conectar(db) as con:
        filas = con.execute(
            "SELECT archivo, origen, estado, motivo, filas FROM extracciones "
            "ORDER BY origen, archivo").fetchall()
    for archivo, origen, estado, motivo, js in filas:
        if estado == OMITIDA:
            continue
        if estado == OK:
            for f in json.loads(js):
                (energia if f["hoja"] == "Energia" else acueducto).append(f["datos"])
        else:
            pendientes.append({"archivo": f"{origen}/{archivo}", "motivo": motivo,
                               "estado": "FORMATO_NUEVO" if estado == PENDIENTE
                               else "REVISION_MANUAL"})
    libros = {"Energia": [pd.DataFrame(energia)] if energia else [],
              "Acueducto": [pd.DataFrame(acueducto)] if acueducto else [],
              "Pendientes": [pd.DataFrame(pendientes)] if pendientes else []}
    if incluir_historico:
        for hoja, dfs in _lotes_historicos().items():
            libros[hoja] += dfs
    if not (libros["Energia"] or libros["Acueducto"]):
        return None
    fecha = datetime.now(ZoneInfo("America/Bogota")).strftime("%Y%m%d_%H%M%S")
    salida = destino or rutas.ruta(f"extraccion_{fecha}.xlsx")
    with pd.ExcelWriter(salida, engine="openpyxl") as w:
        for hoja, dfs in libros.items():
            if dfs:
                pd.concat(dfs, ignore_index=True).to_excel(w, sheet_name=hoja, index=False)
    return salida

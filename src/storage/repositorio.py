"""
Almacen local con ciclo de vida de fila y compuerta de confirmacion
(F1-D03, F1-V05, F1-V07; hallazgos H3 y H4).

Propuesta §5: la consolidacion ocurre "solo tras la confirmacion del Analista
SGA" y §9: "ninguna modificacion manual sin registro (quien, cuando, valor
original vs. nuevo)". Ciclo de vida de un registro:

    EN_REVISION --revisar(APROBADO|CORREGIDO)--> CONFIRMADO --publicar--> OFICIAL
         |                                            ^
         +--revisar(RECHAZADO)--> RECHAZADO           |
    OK (validacion) -------------auto-confirma--------+   (politica AUTOCONFIRMAR)

Solo las filas OFICIAL salen en la exportacion oficial. Una fila OFICIAL no se
modifica. Cada decision humana se anexa a `revision`, una cadena con hash que
permite detectar que el historial fue alterado (verificar_auditoria).

SQLite (biblioteca estandar): local, sin servidor, compatible con la restriccion
"no cloud". La logica depende solo de esta clase, asi que se puede cambiar.
La politica de auto-confirmacion es la decision DEC-13 (pendiente del SGA).
"""
import hashlib
import json
import sqlite3
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

import pandas as pd

from src.processor.validacion import FACTURA_NO_IDENTIFICADA

EN_REVISION, CONFIRMADO, OFICIAL, RECHAZADO = (
    "EN_REVISION", "CONFIRMADO", "OFICIAL", "RECHAZADO")
DECISIONES = {"APROBADO", "CORREGIDO", "RECHAZADO"}
# DEC-13 (pendiente): estados de validacion que pasan solos a CONFIRMADO.
AUTOCONFIRMAR = {"OK"}
CAMPOS_CORREGIBLES = {"consumo", "valor", "periodo_inicio", "periodo_fin", "factura",
                      "sede", "unidad", "cuenta"}

CAMPOS = ["prestador", "servicio", "sede", "cuenta", "factura", "periodo_inicio",
          "periodo_fin", "consumo", "unidad", "valor", "fecha_pago", "archivo",
          "direccion", "periodo_fuente", "confianza", "estado_validacion",
          "severidad", "detalle"]

ESQUEMA = """
CREATE TABLE IF NOT EXISTS lote (
    run_id TEXT PRIMARY KEY, creado TEXT NOT NULL, origen TEXT
);
CREATE TABLE IF NOT EXISTS registro (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clave TEXT NOT NULL UNIQUE,
    run_id TEXT NOT NULL REFERENCES lote(run_id),
    prestador TEXT, servicio TEXT, sede TEXT, cuenta TEXT, factura TEXT,
    periodo_inicio TEXT, periodo_fin TEXT, consumo REAL, unidad TEXT, valor REAL,
    fecha_pago TEXT, archivo TEXT, direccion TEXT, periodo_fuente TEXT,
    confianza REAL, estado_validacion TEXT, severidad TEXT, detalle TEXT,
    estado TEXT NOT NULL,
    confirmado_por TEXT, confirmado_en TEXT, publicado_en TEXT
);
CREATE INDEX IF NOT EXISTS ix_registro_estado ON registro(estado);
CREATE TABLE IF NOT EXISTS revision (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT NOT NULL, revisor TEXT NOT NULL,
    registro_id INTEGER NOT NULL REFERENCES registro(id),
    campo TEXT, valor_original TEXT, valor_nuevo TEXT,
    decision TEXT NOT NULL, observacion TEXT,
    hash_prev TEXT NOT NULL, hash TEXT NOT NULL
);
"""


class ErrorCicloDeVida(Exception):
    """Operacion no permitida para el estado actual del registro."""


def _ahora() -> str:
    return datetime.now(ZoneInfo("America/Bogota")).strftime("%Y-%m-%d %H:%M:%S")


def _limpio(valor):
    """NaN/NaT -> None; fechas -> 'AAAA-MM-DD'; numpy -> tipos nativos."""
    if valor is None or (not isinstance(valor, str) and pd.isna(valor)):
        return None
    if isinstance(valor, pd.Timestamp):
        return valor.strftime("%Y-%m-%d")
    if hasattr(valor, "item"):
        return valor.item()
    return valor


def clave_registro(fila: dict) -> str:
    """Identificador unico: (prestador, servicio, factura); sin factura, sede + archivo.

    Incluye el servicio porque una factura unificada de EPM produce una fila por
    servicio (Propuesta §9.5; ver Plan: los falsos duplicados EPM).
    """
    factura = fila.get("factura")
    if factura and factura != FACTURA_NO_IDENTIFICADA:
        return f"{fila.get('prestador')}|{fila.get('servicio')}|{factura}"
    # Sin nº de factura: sede + archivo (el mismo nombre se repite entre sedes).
    return (f"{fila.get('prestador')}|{fila.get('servicio')}|"
            f"ARCHIVO:{fila.get('sede')}/{fila.get('archivo')}")


def _hash(prev: str, payload: dict) -> str:
    cuerpo = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256((prev + cuerpo).encode("utf-8")).hexdigest()


class Repositorio:
    def __init__(self, ruta: str = ":memory:"):
        self.con = sqlite3.connect(ruta)
        self.con.row_factory = sqlite3.Row
        self.con.executescript(ESQUEMA)

    def cerrar(self):
        self.con.close()

    # --- carga -------------------------------------------------------------
    def cargar_validacion(self, df: pd.DataFrame, run_id: str, origen: str = "") -> dict:
        """Inserta las filas de la hoja Base de validacion_*.xlsx.

        Idempotente: una clave ya existente NO se pisa (conserva la revision
        humana). Retorna conteos por estado y las filas omitidas.
        """
        self.con.execute(
            "INSERT OR IGNORE INTO lote(run_id, creado, origen) VALUES (?,?,?)",
            (run_id, _ahora(), origen))
        nuevos = omitidas = 0
        ahora = _ahora()
        for fila in df.to_dict("records"):
            fila = {k: _limpio(v) for k, v in fila.items()}
            fila["estado_validacion"] = fila.get("estado_validacion") or fila.get("estado")
            clave = clave_registro(fila)
            auto = fila["estado_validacion"] in AUTOCONFIRMAR
            valores = [fila.get(c) for c in CAMPOS]
            cur = self.con.execute(
                f"INSERT OR IGNORE INTO registro (clave, run_id, {', '.join(CAMPOS)}, "
                f"estado, confirmado_por, confirmado_en) "
                f"VALUES (?,?,{','.join('?' * len(CAMPOS))},?,?,?)",
                [clave, run_id, *valores,
                 CONFIRMADO if auto else EN_REVISION,
                 "AUTO" if auto else None, ahora if auto else None])
            if cur.rowcount:
                nuevos += 1
            else:
                omitidas += 1
        self.con.commit()
        return {"nuevos": nuevos, "omitidos": omitidas, **self.conteo()}

    # --- consultas ---------------------------------------------------------
    def conteo(self) -> dict:
        filas = self.con.execute(
            "SELECT estado, COUNT(*) n FROM registro GROUP BY estado").fetchall()
        return {f["estado"]: f["n"] for f in filas}

    def cola_revision(self) -> pd.DataFrame:
        return pd.read_sql_query(
            "SELECT * FROM registro WHERE estado = ? ORDER BY severidad, id",
            self.con, params=(EN_REVISION,))

    def exportar_oficial(self) -> pd.DataFrame:
        """Unica salida hacia el Excel oficial / GreenMetric / GEI."""
        return pd.read_sql_query(
            "SELECT * FROM registro WHERE estado = ? ORDER BY periodo_fin, id",
            self.con, params=(OFICIAL,))

    def _registro(self, registro_id: int) -> sqlite3.Row:
        fila = self.con.execute(
            "SELECT * FROM registro WHERE id = ?", (registro_id,)).fetchone()
        if fila is None:
            raise KeyError(f"registro {registro_id} no existe")
        return fila

    # --- revision humana ---------------------------------------------------
    def revisar(self, registro_id: int, revisor: str, decision: str,
                campo: Optional[str] = None, valor_nuevo=None,
                observacion: str = "") -> dict:
        """Aplica una decision del Analista y la deja en el historial."""
        if not revisor or not str(revisor).strip():
            raise ValueError("el revisor es obligatorio")
        if decision not in DECISIONES:
            raise ValueError(f"decision debe ser una de {sorted(DECISIONES)}")
        reg = self._registro(registro_id)
        if reg["estado"] == OFICIAL:
            raise ErrorCicloDeVida("un registro OFICIAL no se modifica")
        if reg["estado"] == RECHAZADO:
            raise ErrorCicloDeVida("el registro ya fue rechazado")
        original = None
        if decision == "CORREGIDO":
            if campo not in CAMPOS_CORREGIBLES:
                raise ValueError(f"campo corregible debe ser uno de {sorted(CAMPOS_CORREGIBLES)}")
            if valor_nuevo is None:
                raise ValueError("CORREGIDO requiere valor_nuevo")
            original = reg[campo]
            self.con.execute(f"UPDATE registro SET {campo} = ? WHERE id = ?",
                             (valor_nuevo, registro_id))
        nuevo_estado = RECHAZADO if decision == "RECHAZADO" else CONFIRMADO
        ahora = _ahora()
        self.con.execute(
            "UPDATE registro SET estado = ?, confirmado_por = ?, confirmado_en = ? WHERE id = ?",
            (nuevo_estado, revisor, ahora, registro_id))
        fila = self._anexar_revision(ahora, revisor, registro_id, campo,
                                     original, valor_nuevo, decision, observacion)
        self.con.commit()
        return fila

    def _anexar_revision(self, fecha, revisor, registro_id, campo, original,
                         nuevo, decision, observacion) -> dict:
        ultimo = self.con.execute(
            "SELECT hash FROM revision ORDER BY id DESC LIMIT 1").fetchone()
        prev = ultimo["hash"] if ultimo else "GENESIS"
        # Se guardan y se hashean como texto para que la verificacion sea exacta.
        original = None if original is None else str(original)
        nuevo = None if nuevo is None else str(nuevo)
        payload = {"fecha": fecha, "revisor": revisor, "registro_id": registro_id,
                   "campo": campo, "valor_original": original, "valor_nuevo": nuevo,
                   "decision": decision, "observacion": observacion}
        h = _hash(prev, payload)
        self.con.execute(
            "INSERT INTO revision (fecha, revisor, registro_id, campo, valor_original, "
            "valor_nuevo, decision, observacion, hash_prev, hash) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (fecha, revisor, registro_id, campo, original, nuevo,
             decision, observacion, prev, h))
        return {**payload, "hash": h}

    def historial(self, registro_id: Optional[int] = None) -> pd.DataFrame:
        if registro_id is None:
            return pd.read_sql_query("SELECT * FROM revision ORDER BY id", self.con)
        return pd.read_sql_query(
            "SELECT * FROM revision WHERE registro_id = ? ORDER BY id",
            self.con, params=(registro_id,))

    # --- compuerta ---------------------------------------------------------
    def publicar_oficial(self) -> dict:
        """Compuerta: CONFIRMADO -> OFICIAL. Lo EN_REVISION se queda fuera."""
        cur = self.con.execute(
            "UPDATE registro SET estado = ?, publicado_en = ? WHERE estado = ?",
            (OFICIAL, _ahora(), CONFIRMADO))
        self.con.commit()
        return {"publicados": cur.rowcount, **self.conteo()}

    # --- integridad --------------------------------------------------------
    def verificar_auditoria(self) -> list:
        """Recalcula la cadena. Retorna los ids de revision alterados (vacio = integra)."""
        rotos, prev = [], "GENESIS"
        for r in self.con.execute("SELECT * FROM revision ORDER BY id"):
            payload = {"fecha": r["fecha"], "revisor": r["revisor"],
                       "registro_id": r["registro_id"], "campo": r["campo"],
                       "valor_original": r["valor_original"], "valor_nuevo": r["valor_nuevo"],
                       "decision": r["decision"], "observacion": r["observacion"]}
            if r["hash_prev"] != prev or _hash(prev, payload) != r["hash"]:
                rotos.append(r["id"])
            prev = r["hash"]
        return rotos

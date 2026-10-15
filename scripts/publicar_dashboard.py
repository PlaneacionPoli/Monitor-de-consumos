"""
Publica el dashboard como sitio estatico CIFRADO para GitHub Pages.

GitHub Pages solo sirve archivos estaticos: un login en JavaScript no protege
datos que viajen en claro. Aqui los datos se cifran (AES-256-GCM) y la clave se
envuelve una vez por usuario autorizado con PBKDF2-SHA256 (600.000 iteraciones)
derivado de SU contrasena. El navegador descifra solo si el correo y la
contrasena son correctos. En el repositorio solo queda texto cifrado.

Entrada : data/outputs/validacion_*.xlsx (+ monitor.db si existe)
Correos  : config/accesos_dashboard.txt (un correo por linea; no se versiona)
Claves   : data/outputs/accesos_dashboard.csv (se reutilizan; no se versiona)
Salida   : site/  (index.html, app.js, descifrar.js, estilos.css, logo_poli.png, echarts.min.js, colombia.geojson, data.enc.json)

Limites: quitar a un usuario solo cierra el acceso a los datos publicados DESDE
la siguiente corrida (la clave de datos se rota); las copias anteriores del
repositorio siguen siendo descifrables por quien ya tenia acceso.

Uso: python scripts/publicar_dashboard.py            (sitio publicado en site/)
     python scripts/publicar_dashboard.py --local    (dashboard del equipo, ingreso automatico)
"""
import argparse
import base64
import csv
import glob
import hashlib
import json
import os
import secrets
import shutil
import sqlite3
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
from src.utils import rutas  # noqa: E402
from src.utils.sedes import completar_sede_por_cuenta  # noqa: E402
from src.processor.faltantes import detectar_faltantes  # noqa: E402
from src.storage.repositorio import clave_registro  # noqa: E402

SALIDAS = os.path.join(BASE, "data", "outputs")
PLANTILLA = os.path.join(BASE, "src", "dashboard_estatico")
SITIO = os.path.join(BASE, "site")
SITIO_LOCAL = os.path.join(SALIDAS, "sitio_local")      # uso local: no se versiona ni se publica
CORREO_LOCAL = "local@este-equipo.local"
RUTA_CORREOS = os.path.join(BASE, "config", "accesos_dashboard.txt")
RUTA_CLAVES = rutas.ruta("accesos_dashboard.csv")
ITERACIONES = 600_000
AAD_DATOS = b"monitor-consumos-v1"
ARCHIVOS_SITIO = ["index.html", "app.js", "descifrar.js", "estilos.css", "logo_poli.png"]
VENDOR = ["echarts.min.js", "colombia.geojson"]  # src/dashboard_estatico/vendor; se sirve desde el sitio, sin CDN


def b64(datos: bytes) -> str:
    return base64.b64encode(datos).decode("ascii")


def id_usuario(correo: str) -> str:
    return hashlib.sha256(correo.strip().lower().encode("utf-8")).hexdigest()


def derivar(contrasena: str, sal: bytes) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=sal, iterations=ITERACIONES)
    return kdf.derive(contrasena.encode("utf-8"))


def leer_correos() -> list:
    if not os.path.exists(RUTA_CORREOS):
        return []
    with open(RUTA_CORREOS, encoding="utf-8") as f:
        lineas = [x.strip().lower() for x in f if x.strip() and not x.startswith("#")]
    return sorted(set(c for c in lineas if "@" in c))


def asignar_contrasenas(correos: list) -> dict:
    """Reutiliza las existentes; genera una aleatoria (20 caracteres) para las nuevas."""
    existentes = {}
    if os.path.exists(RUTA_CLAVES):
        with open(RUTA_CLAVES, newline="", encoding="utf-8") as f:
            existentes = {r["correo"]: r["contrasena"] for r in csv.DictReader(f)}
    claves = {c: existentes.get(c) or secrets.token_urlsafe(15) for c in correos}
    with open(RUTA_CLAVES, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["correo", "contrasena"])
        w.writerows(claves.items())
    return claves


def mapa_sedes() -> dict:
    ruta = rutas.catalogo("catalogo_sedes.csv")
    if not os.path.exists(ruta):
        return {}
    cat = pd.read_csv(ruta, dtype=str).fillna("")
    mapa = {}
    for _, r in cat.iterrows():
        sede = r["sede_confirmada"].strip() or r["sede_sugerida"].strip()
        if sede and sede != "SIN_MAPEO":
            mapa[r["direccion_norm"]] = sede
    return mapa


def estados_almacen() -> dict:
    ruta = rutas.ruta("monitor.db")
    if not os.path.exists(ruta):
        return {}
    con = sqlite3.connect(ruta)
    try:
        return dict(con.execute("SELECT clave, estado FROM registro"))
    finally:
        con.close()


def construir_datos() -> dict:
    validaciones = rutas.todos("validacion_*.xlsx")
    if not validaciones:
        raise SystemExit("Sin validacion. Ejecute validar_atipicos.py primero.")
    base = pd.read_excel(validaciones[-1], sheet_name="Base")
    base["periodo_fin"] = pd.to_datetime(base["periodo_fin"], errors="coerce")

    faltantes = detectar_faltantes(base)
    sedes = mapa_sedes()
    estados = estados_almacen()
    direccion = (base["direccion"].astype(str)
                 .str.replace(r"\s*\|\s*\d+$", "", regex=True).str.strip())
    base["sede_final"] = direccion.map(sedes).fillna("SIN_MAPEO")
    base = completar_sede_por_cuenta(base, "SIN_MAPEO")

    def limpio(v):
        if v is None or (not isinstance(v, str) and pd.isna(v)):
            return None
        if isinstance(v, pd.Timestamp):
            return v.strftime("%Y-%m-%d")
        return v.item() if hasattr(v, "item") else v

    filas = []
    for r in base.to_dict("records"):
        r = {k: limpio(v) for k, v in r.items()}
        filas.append({
            "sede": r["sede_final"], "prestador": r.get("prestador"),
            "servicio": r.get("servicio"), "factura": r.get("factura"),
            "cuenta": r.get("cuenta"), "direccion": r.get("direccion"),
            "archivo": r.get("archivo"), "periodo_inicio": r.get("periodo_inicio"),
            "periodo_fin": r.get("periodo_fin"), "ymes": r.get("ymes"),
            "consumo": r.get("consumo"), "unidad": r.get("unidad"),
            "valor": r.get("valor"), "valor_servicio": r.get("valor_servicio"),
            "valor_aseo": r.get("valor_aseo"), "bimestral": bool(r.get("bimestral")),
            "dias": r.get("dias"), "consumo_mensual": r.get("consumo_mensual"),
            "consumo_ref": r.get("consumo_ref"), "variacion": r.get("variacion"),
            "metodo_ref": r.get("metodo_ref"), "sentido": r.get("sentido"), "estado": r.get("estado"),
            "severidad": r.get("severidad"), "detalle": r.get("detalle"),
            "confianza": r.get("confianza"),
            "revision": estados.get(clave_registro(
                {"prestador": r.get("prestador"), "servicio": r.get("servicio"),
                 "factura": r.get("factura"), "sede": r.get("sede"),
                 "archivo": r.get("archivo")})),
        })
    return {
        "generado": datetime.now(ZoneInfo("America/Bogota")).strftime("%Y-%m-%d %H:%M"),
        "fuente": os.path.basename(validaciones[-1]),
        "facturas": filas,
        "faltantes": faltantes,
    }


def cifrar(datos: dict, claves: dict) -> dict:
    clave_datos = AESGCM.generate_key(bit_length=256)
    iv = os.urandom(12)
    cuerpo = json.dumps(datos, ensure_ascii=False, default=str).encode("utf-8")
    cifrado = AESGCM(clave_datos).encrypt(iv, cuerpo, AAD_DATOS)
    usuarios = []
    for correo, contrasena in claves.items():
        uid, sal, iv_u = id_usuario(correo), os.urandom(16), os.urandom(12)
        envuelta = AESGCM(derivar(contrasena, sal)).encrypt(
            iv_u, clave_datos, uid.encode("ascii"))
        usuarios.append({"id": uid, "salt": b64(sal), "iv": b64(iv_u), "key": b64(envuelta)})
    return {"v": 1, "iter": ITERACIONES, "iv": b64(iv), "data": b64(cifrado),
            "usuarios": usuarios}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Publica el dashboard cifrado (site/) o lo prepara para uso local.")
    ap.add_argument("--local", action="store_true",
                    help="modo local: genera data/outputs/sitio_local con ingreso automatico, sin correos ni claves")
    args = ap.parse_args(argv)

    if args.local:
        # Uso en el equipo del usuario: un solo usuario local con clave aleatoria que el tablero lee de
        # auto.json (solo existe en esta carpeta; nunca se publica). No toca site/ ni los accesos.
        correos, destino = [CORREO_LOCAL], SITIO_LOCAL
        claves = {CORREO_LOCAL: secrets.token_urlsafe(15)}
    else:
        correos, destino = leer_correos(), SITIO
        if not correos:
            os.makedirs(os.path.dirname(RUTA_CORREOS), exist_ok=True)
            if not os.path.exists(RUTA_CORREOS):
                with open(RUTA_CORREOS, "w", encoding="utf-8") as f:
                    f.write("# Un correo autorizado por linea. Este archivo no se versiona.\n")
            print(f"Sin correos autorizados. Agregue uno por linea en {RUTA_CORREOS}")
            return 1
        claves = asignar_contrasenas(correos)
    datos = construir_datos()
    blob = cifrar(datos, claves)

    os.makedirs(destino, exist_ok=True)
    for nombre in ARCHIVOS_SITIO:
        shutil.copy2(os.path.join(PLANTILLA, nombre), os.path.join(destino, nombre))
    for nombre in VENDOR:
        shutil.copy2(os.path.join(PLANTILLA, "vendor", nombre), os.path.join(destino, nombre))
    with open(os.path.join(destino, "data.enc.json"), "w", encoding="utf-8") as f:
        json.dump(blob, f)
    open(os.path.join(destino, ".nojekyll"), "w").close()
    auto = os.path.join(destino, "auto.json")
    if args.local:
        with open(auto, "w", encoding="utf-8") as f:
            json.dump({"correo": CORREO_LOCAL, "contrasena": claves[CORREO_LOCAL]}, f)
    elif os.path.exists(auto):
        os.remove(auto)          # nunca debe viajar en el sitio publicado

    print(f"Fuente: {datos['fuente']} | facturas: {len(datos['facturas'])} | "
          f"faltantes: {len(datos['faltantes'])}")
    if args.local:
        print(f"Dashboard local (ingreso automatico): {destino}")
    else:
        print(f"Usuarios autorizados: {len(correos)}")
        print(f"Contrasenas (no versionar): {RUTA_CLAVES}")
        print(f"Sitio cifrado: {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

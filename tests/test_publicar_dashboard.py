"""Pruebas del cifrado del dashboard estatico (scripts/publicar_dashboard.py).

Es la unica barrera entre los datos y un repositorio publico: si alguien cambia el
formato o el cifrado sin darse cuenta, estas pruebas deben fallar.
"""
import base64
import importlib.util
import json
import os
import shutil
import subprocess
import sys

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

spec = importlib.util.spec_from_file_location(
    "publicar_dashboard", os.path.join(RAIZ, "scripts", "publicar_dashboard.py"))
pub = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pub)

DATOS = {"generado": "x", "fuente": "y",
         "facturas": [{"factura": "FACTURA-SECRETA-123", "valor": 987654321.0,
                       "direccion": "Calle Reservada 45", "sede": "Campus"}],
         "faltantes": []}
CLAVES = {"ana@example.com": "contrasena-de-ana-123456", "luis@example.com": "otra-clave-de-luis-9876"}


@pytest.fixture(autouse=True)
def pocas_iteraciones(monkeypatch):
    monkeypatch.setattr(pub, "ITERACIONES", 1000)   # rapido; el formato lleva 'iter'


def _descifrar_python(blob, correo, contrasena):
    uid = pub.id_usuario(correo)
    u = next(x for x in blob["usuarios"] if x["id"] == uid)
    sal = base64.b64decode(u["salt"])
    kek = pub.derivar(contrasena, sal)
    clave = AESGCM(kek).decrypt(base64.b64decode(u["iv"]), base64.b64decode(u["key"]),
                                uid.encode("ascii"))
    claro = AESGCM(clave).decrypt(base64.b64decode(blob["iv"]), base64.b64decode(blob["data"]),
                                  pub.AAD_DATOS)
    return json.loads(claro)


def test_cada_usuario_descifra_con_su_contrasena():
    blob = pub.cifrar(DATOS, CLAVES)
    for correo, clave in CLAVES.items():
        assert _descifrar_python(blob, correo, clave)["facturas"][0]["valor"] == 987654321.0


def test_contrasena_de_otro_usuario_no_sirve():
    blob = pub.cifrar(DATOS, CLAVES)
    with pytest.raises(Exception):
        _descifrar_python(blob, "ana@example.com", CLAVES["luis@example.com"])


def test_el_archivo_publicado_no_contiene_datos_en_claro():
    texto = json.dumps(pub.cifrar(DATOS, CLAVES))
    for secreto in ("FACTURA-SECRETA-123", "987654321", "Calle Reservada", "ana@example.com",
                    "luis@example.com"):
        assert secreto not in texto


def test_cada_cifrado_rota_la_clave_de_datos():
    a, b = pub.cifrar(DATOS, CLAVES), pub.cifrar(DATOS, CLAVES)
    assert a["data"] != b["data"] and a["iv"] != b["iv"]


def test_id_de_usuario_ignora_mayusculas_y_espacios():
    assert pub.id_usuario("  Ana@Example.COM ") == pub.id_usuario("ana@example.com")


def test_el_codigo_js_del_navegador_descifra_lo_que_cifra_python(tmp_path):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node no disponible")
    blob = pub.cifrar(DATOS, CLAVES)
    ruta_blob = tmp_path / "data.enc.json"
    ruta_blob.write_text(json.dumps(blob), encoding="utf-8")
    script = tmp_path / "prueba.cjs"
    script.write_text(
        "const fs=require('fs');"
        "const {descifrar}=require(process.argv[2]);"
        "const blob=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));"
        "(async()=>{"
        " const d=await descifrar(blob,process.argv[4],process.argv[5]);"
        " console.log('OK:'+d.facturas[0].factura);"
        " try{await descifrar(blob,process.argv[4],'incorrecta');console.log('ENTRO');}"
        " catch(e){console.log('RECHAZADO:'+e.message);}"
        "})();", encoding="utf-8")
    modulo = os.path.join(RAIZ, "src", "dashboard_estatico", "descifrar.js")
    salida = subprocess.run(
        [node, str(script), modulo, str(ruta_blob), "Ana@example.com", CLAVES["ana@example.com"]],
        capture_output=True, text=True, timeout=60)
    assert "OK:FACTURA-SECRETA-123" in salida.stdout, salida.stderr
    assert "RECHAZADO:credenciales" in salida.stdout

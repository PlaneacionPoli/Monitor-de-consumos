"""Humo de la app local (Dash): el layout se construye y los callbacks no fallan sin clics."""
import importlib.util
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _cargar_app():
    spec = importlib.util.spec_from_file_location("aplicacion", os.path.join(BASE, "app", "aplicacion.py"))
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_layout_y_rutas():
    m = _cargar_app()
    cliente = m.server.test_client()
    assert cliente.get("/").status_code == 200
    assert cliente.get("/_dash-layout").status_code == 200
    assert cliente.get("/_dash-dependencies").status_code == 200


def test_pagina_marca_activa_la_ruta():
    m = _cargar_app()
    cargar, dash_, nav1, nav2, _ = m.pagina("/dashboard")
    assert cargar == {"display": "none"} and nav2 == "activo" and nav1 == ""


def test_lista_vacia_deshabilita_continuar():
    m = _cargar_app()
    _, continuar_off, quitar_off = m.lista([])
    assert continuar_off and quitar_off


def test_dibujar_muestra_solo_el_panel_del_paso():
    m = _cargar_app()
    salida = m.dibujar(1, {"nuevos": 2, "ya_cargados": 0, "reprocesar": 0, "repetidos_en_seleccion": 0,
                           "ignorados": 0}, None, None, [])
    estilos = salida[1:5]
    assert [e["display"] for e in estilos] == ["none", "block", "none", "none"]

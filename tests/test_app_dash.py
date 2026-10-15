"""Humo de la app local (Dash): el layout se construye y los callbacks no fallan sin clics."""
import importlib.util
import json
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
    cargar, dash_, nav1, nav2, _, clase = m.pagina("/dashboard")
    assert cargar == {"display": "none"} and nav2 == "activo" and nav1 == ""
    assert clase == "principal completa"       # el dashboard ocupa toda la pantalla


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


def test_menu_plegado_por_defecto_y_se_expande_solo_con_el_boton(monkeypatch):
    """La barra lateral arranca plegada a iconos; el boton la abre y elegir una pagina la pliega."""
    m = _cargar_app()
    from plotly.utils import PlotlyJSONEncoder
    layout = json.dumps(m.app.layout, cls=PlotlyJSONEncoder)
    assert '"id": "shell"' in layout and '"className": "app"' in layout and "btn-menu" in layout

    monkeypatch.setattr(m, "ctx", type("C", (), {"triggered_id": "btn-menu"})())
    assert m.menu(1, "/", "app") == ("app abierto", "true")          # el boton expande
    assert m.menu(2, "/", "app abierto") == ("app", "false")          # y vuelve a plegar

    monkeypatch.setattr(m, "ctx", type("C", (), {"triggered_id": "url"})())
    assert m.menu(2, "/dashboard", "app abierto") == ("app", "false")  # elegir pagina pliega


def test_dashboard_local_se_sirve_desde_su_carpeta(tmp_path, monkeypatch):
    """/sitio/ entrega siempre lo que hay en data/outputs/sitio_local (sin copias que se queden viejas)."""
    m = _cargar_app()
    monkeypatch.setattr(m.actualizacion, "SITIO_LOCAL", str(tmp_path))
    cliente = m.server.test_client()
    assert cliente.get("/sitio/index.html").status_code == 404          # aun no generado
    assert b"Todav" in cliente.get("/sin-dashboard").data
    (tmp_path / "index.html").write_text("<html>ok</html>")
    (tmp_path / "data.enc.json").write_text("v1")
    assert cliente.get("/sitio/data.enc.json").data == b"v1"
    (tmp_path / "data.enc.json").write_text("v2")
    assert cliente.get("/sitio/data.enc.json").data == b"v2"

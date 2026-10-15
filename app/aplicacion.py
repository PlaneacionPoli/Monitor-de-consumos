"""
Monitor de Consumos: aplicacion local unica (Dash) con extractor y dashboard.

Paginas:
  /            Cargar facturas: asistente de 4 pasos (elegir, revisar, procesar, resultado)
  /dashboard   Dashboard oficial (HTML/JS de site/) incrustado, con boton para regenerarlo

La logica vive en src/processor/carga.py y actualizacion.py; aqui solo hay pantalla.
El procesamiento corre en un hilo y la pantalla consulta su avance (la app es local y
de un solo usuario, por eso el estado del trabajo es global).

Uso: python app/aplicacion.py          (o doble clic en Iniciar_App.bat)
     abre http://localhost:8050
"""
import json
import os
import subprocess
import sys
import threading
import time
import webbrowser
from urllib.parse import quote

import dash
from dash import Input, Output, State, ctx, dcc, html, no_update
from flask import abort, send_from_directory

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
from src.processor import actualizacion, carga  # noqa: E402

PUERTO = int(os.environ.get("PUERTO_APP", "8050"))
PASOS = ["Elegir facturas", "Revisar", "Procesar", "Resultado"]

app = dash.Dash(__name__, title="Monitor de Consumos", suppress_callback_exceptions=True,
                update_title=None)
server = app.server

# --------------------------------------------------------------------------- trabajo en hilo
JOB = {"tipo": None, "estado": "libre", "i": 0, "n": 0, "texto": "", "resultado": None}


def _lanzar(tipo, funcion):
    """Ejecuta funcion(progreso) en un hilo; una sola tarea a la vez."""
    if JOB["estado"] == "corriendo":
        return False
    JOB.update(tipo=tipo, estado="corriendo", i=0, n=1, texto="Preparando…", resultado=None)

    def progreso(i, n, texto):
        JOB.update(i=i, n=max(n, 1), texto=texto)

    def correr():
        try:
            JOB["resultado"] = funcion(progreso)
        except Exception as exc:  # noqa: BLE001
            JOB["resultado"] = {"ok": False, "etapa_fallida": "Error inesperado", "detalle": str(exc)}
        JOB["estado"] = "terminado"

    threading.Thread(target=correr, daemon=True).start()
    return True


# --------------------------------------------------------------------------- iconos y piezas
_ICONOS = {
    "subir": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/>'
             '<line x1="12" y1="3" x2="12" y2="15"/>',
    "tablero": '<rect x="3" y="3" width="7" height="9"/><rect x="14" y="3" width="7" height="5"/>'
               '<rect x="14" y="12" width="7" height="9"/><rect x="3" y="16" width="7" height="5"/>',
    "menu": '<line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>',
    "carpeta": '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>',
    "archivo": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
               '<polyline points="14 2 14 8 20 8"/>',
}


def icono(nombre, color="#263A58"):
    """Icono lineal de un solo color (SVG embebido; Dash no trae componentes SVG)."""
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%s" '
           'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">%s</svg>'
           % (color, _ICONOS[nombre]))
    return html.Img(src="data:image/svg+xml;utf8," + quote(svg), alt="")


def metrica(titulo, valor, clase=""):
    return html.Div([html.Small(titulo), html.Strong(f"{valor:,}".replace(",", "."))],
                    className="metrica " + clase)


def cabecera(titulo, subtitulo):
    return html.Div([html.Img(src=app.get_asset_url("icono.png"), alt=""),
                     html.Div([html.H1(titulo), html.P(subtitulo)])], className="cab")


def boton(texto, id_, primario=False, **kw):
    return html.Button(texto, id=id_, n_clicks=0,
                       className="btn" + (" primario" if primario else ""), **kw)


# --------------------------------------------------------------------------- diseno
panel_elegir = html.Div([
    html.Div([
        html.H2("¿Qué facturas quieres cargar?"),
        html.P("Elige una carpeta completa (incluye subcarpetas) o archivos PDF sueltos. "
               "Puedes sumar varias selecciones.", className="suave"),
        html.Div([
            html.Button([icono("carpeta", "#22B2DE"), "Elegir carpeta"], id="btn-carpeta",
                        n_clicks=0, className="btn"),
            html.Button([icono("archivo", "#22B2DE"), "Elegir archivos PDF"], id="btn-archivos",
                        n_clicks=0, className="btn"),
        ], className="elegir"),
        html.Details([
            html.Summary("¿No se abre el selector? Escribe la ruta"),
            html.Div([dcc.Input(id="in-ruta", type="text", placeholder=r"C:\Facturas\Mayo"),
                      boton("Agregar", "btn-ruta")], className="ruta-manual"),
        ]),
        html.Div(id="msg-seleccion"),
        html.Div(id="lista-seleccion"),
        html.Div([boton("Quitar todo", "btn-quitar"),
                  boton("Continuar", "btn-continuar", True, disabled=True)], className="acciones"),
    ], className="tarjeta"),
], id="panel-0")

panel_revisar = html.Div([
    html.Div([
        html.H2("Esto es lo que encontré"),
        dcc.Loading(html.Div(id="plan-contenido"), type="dot", color="#22B2DE"),
        dcc.Checklist(id="chk-forzar", value=[], className="suave", style={"marginTop": ".6rem"},
                      options=[{"label": " Volver a leer también las ya cargadas", "value": "si"}]),
        html.Div([boton("Cambiar selección", "btn-atras"),
                  boton("Procesar", "btn-procesar", True)], className="acciones"),
    ], className="tarjeta"),
], id="panel-1", style={"display": "none"})

panel_procesar = html.Div([
    html.Div([
        html.H2("Leyendo las facturas…"),
        html.Div(html.Div(id="barra-proc", style={"width": "0%"}), className="barra"),
        html.Div(id="texto-proc", className="suave pequeno"),
    ], className="tarjeta"),
], id="panel-2", style={"display": "none"})

panel_resultado = html.Div([
    html.Div([
        html.H2("Resultado de la lectura"),
        html.Div(id="res-contenido"),
    ], className="tarjeta"),
    html.Div([
        html.H2("Actualizar el archivo final"),
        html.P("Reúne todo lo cargado hasta hoy y actualiza Consumos_Consolidado.xlsx y el dashboard.",
               className="suave"),
        html.Div(html.Div(id="barra-act", style={"width": "0%"}), className="barra",
                 id="caja-barra-act", hidden=True),
        html.Div(id="texto-act", className="suave pequeno"),
        html.Div(id="final-contenido"),
        html.Div([boton("Actualizar el archivo", "btn-actualizar", True),
                  boton("Descargar Excel", "btn-descargar", disabled=True),
                  boton("Cargar más facturas", "btn-nuevo")], className="acciones"),
        dcc.Download(id="descarga"),
    ], className="tarjeta"),
], id="panel-3", style={"display": "none"})

vista_cargar = html.Div([
    cabecera("Cargar facturas",
             "Extrae los datos de las facturas de energía y acueducto y actualiza el archivo de consumos"),
    html.Div(id="pasos", className="pasos"),
    panel_elegir, panel_revisar, panel_procesar, panel_resultado,
], id="vista-cargar")

vista_dashboard = html.Div([
    cabecera("Dashboard", "Dashboard oficial: vistas Ejecutiva y Operativa. "
                          "Ingresa con tu correo y contraseña de acceso"),
    html.Div([
        html.Span("Los datos se actualizan al pulsar «Actualizar el archivo» en Cargar facturas.",
                  className="suave pequeno"),
        html.Button("Regenerar con los últimos datos", id="btn-regen", n_clicks=0, className="btn"),
    ], className="barra-sup"),
    dcc.Loading(html.Div(id="msg-regen"), type="dot", color="#22B2DE"),
    html.Iframe(id="marco", className="sitio", title="Dashboard de consumos"),
], id="vista-dash", style={"display": "none"})

app.layout = html.Div([
    dcc.Location(id="url"),
    dcc.Store(id="st-sel", data=[]), dcc.Store(id="st-paso", data=0), dcc.Store(id="st-plan"),
    dcc.Store(id="st-res"), dcc.Store(id="st-final"),
    dcc.Interval(id="reloj", interval=500),
    html.Div([
        html.Aside([
            html.Div([
                html.Img(src=app.get_asset_url("icono.png"), className="mini", alt="Monitor de Consumos"),
                html.Img(src=app.get_asset_url("logo_poli.png"), className="logo",
                         alt="Politécnico Grancolombiano"),
                html.Button(icono("menu"), id="btn-menu", n_clicks=0, className="menu-btn", title="Menú",
                            **{"aria-label": "Mostrar u ocultar el menú", "aria-expanded": "false"}),
            ], className="cab-lateral"),
            html.Nav([
                dcc.Link([icono("subir"), html.Span("Cargar facturas")], href="/", id="nav-cargar",
                         title="Cargar facturas"),
                dcc.Link([icono("tablero"), html.Span("Dashboard")], href="/dashboard", id="nav-dash",
                         title="Dashboard"),
            ], className="nav"),
            html.Div("Monitor de Consumos Ambientales · Politécnico Grancolombiano", className="pie"),
        ], className="lateral"),
        html.Main([vista_cargar, vista_dashboard], className="principal"),
    ], id="shell", className="app"),
])


# --------------------------------------------------------------------------- servidor
@server.route("/sitio/<path:ruta>")
def sitio(ruta):
    """Sirve la copia local del dashboard HTML oficial (site/)."""
    if not os.path.isfile(os.path.join(actualizacion.SITIO_LOCAL, "index.html")):
        actualizacion.copiar_dashboard_local()
    if not os.path.isdir(actualizacion.SITIO_LOCAL):
        abort(404)
    return send_from_directory(actualizacion.SITIO_LOCAL, ruta, max_age=0)


def _dialogo(tipo):
    """Selector nativo de Windows en un proceso aparte (tkinter exige el hilo principal)."""
    codigo = (
        "import json,sys,tkinter as tk\n"
        "from tkinter import filedialog as fd\n"
        "r=tk.Tk();r.withdraw();r.attributes('-topmost',True)\n"
        "if sys.argv[1]=='carpeta':\n"
        "    p=fd.askdirectory(title='Elige la carpeta con las facturas');o=[p] if p else []\n"
        "else:\n"
        "    o=list(fd.askopenfilenames(title='Elige las facturas (PDF)',"
        "filetypes=[('Facturas PDF','*.pdf')]))\n"
        "print(json.dumps(o))\n")
    r = subprocess.run([sys.executable, "-c", codigo, tipo], capture_output=True, text=True)
    try:
        return [os.path.normpath(x) for x in json.loads(r.stdout.strip().splitlines()[-1])]
    except (ValueError, IndexError):
        return []


# --------------------------------------------------------------------------- callbacks
@app.callback(Output("shell", "className"), Output("btn-menu", "aria-expanded"),
              Input("btn-menu", "n_clicks"), Input("url", "pathname"), State("shell", "className"))
def menu(_n, _ruta, clase):
    """El menu arranca plegado a iconos; el boton lo expande y elegir una pagina lo vuelve a plegar."""
    abierto = "abierto" in (clase or "")
    abierto = (not abierto) if ctx.triggered_id == "btn-menu" else False
    return ("app abierto" if abierto else "app"), str(abierto).lower()


@app.callback(Output("vista-cargar", "style"), Output("vista-dash", "style"),
              Output("nav-cargar", "className"), Output("nav-dash", "className"),
              Output("marco", "src"), Input("url", "pathname"))
def pagina(ruta):
    en_dash = (ruta or "").rstrip("/") == "/dashboard"
    mostrar, ocultar = {"display": "block"}, {"display": "none"}
    return (ocultar if en_dash else mostrar, mostrar if en_dash else ocultar,
            "" if en_dash else "activo", "activo" if en_dash else "",
            f"/sitio/index.html?t={int(time.time())}" if en_dash else no_update)


@app.callback(Output("st-sel", "data"), Output("msg-seleccion", "children"), Output("in-ruta", "value"),
              Input("btn-carpeta", "n_clicks"), Input("btn-archivos", "n_clicks"),
              Input("btn-ruta", "n_clicks"), Input("btn-quitar", "n_clicks"),
              State("in-ruta", "value"), State("st-sel", "data"), prevent_initial_call=True)
def seleccionar(_c, _a, _r, _q, ruta_manual, sel):
    sel = list(sel or [])
    quien = ctx.triggered_id
    if not ctx.triggered[0]["value"]:
        return no_update, no_update, no_update
    if quien == "btn-quitar":
        return [], None, ""
    if quien in ("btn-carpeta", "btn-archivos"):
        nuevos = _dialogo("carpeta" if quien == "btn-carpeta" else "archivos")
    elif quien == "btn-ruta" and (ruta_manual or "").strip():
        ruta = ruta_manual.strip().strip('"')
        if not os.path.exists(ruta):
            return sel, html.Div("Esa ruta no existe. Revisa que esté bien escrita.",
                                 className="aviso error"), no_update
        nuevos = [os.path.normpath(ruta)]
    else:
        return no_update, no_update, no_update
    return sel + [n for n in nuevos if n not in sel], None, ""


@app.callback(Output("lista-seleccion", "children"), Output("btn-continuar", "disabled"),
              Output("btn-quitar", "disabled"), Input("st-sel", "data"))
def lista(sel):
    sel = sel or []
    items = [html.Li([icono("carpeta" if os.path.isdir(r) else "archivo"), r]) for r in sel]
    return (html.Ul(items, className="seleccion") if items else
            html.P("Todavía no has elegido nada.", className="suave pequeno"), not sel, not sel)


@app.callback(Output("st-paso", "data"), Output("st-plan", "data"),
              Output("st-sel", "data", allow_duplicate=True),
              Output("st-res", "data", allow_duplicate=True), Output("st-final", "data", allow_duplicate=True),
              Input("btn-continuar", "n_clicks"), Input("btn-atras", "n_clicks"),
              Input("btn-procesar", "n_clicks"), Input("btn-nuevo", "n_clicks"),
              State("st-sel", "data"), State("chk-forzar", "value"), prevent_initial_call=True)
def flujo(_c, _a, _p, _n, sel, forzar):
    quien = ctx.triggered_id
    if not ctx.triggered[0]["value"]:
        return (no_update,) * 5
    if quien == "btn-continuar" and sel:
        plan = carga.planificar(sel)
        return 1, {k: len(v) for k, v in plan.items()}, no_update, no_update, no_update
    if quien == "btn-atras":
        return 0, no_update, no_update, no_update, no_update
    if quien == "btn-procesar":
        usar_forzar = bool(forzar)
        if _lanzar("procesar", lambda prog: carga.procesar(sel, progreso=prog, forzar=usar_forzar)):
            return 2, no_update, no_update, None, None
    if quien == "btn-nuevo":
        return 0, None, [], None, None
    return (no_update,) * 5


@app.callback(Output("st-paso", "data", allow_duplicate=True), Output("st-res", "data", allow_duplicate=True),
              Output("st-final", "data", allow_duplicate=True),
              Output("barra-proc", "style"), Output("texto-proc", "children"),
              Output("barra-act", "style"), Output("texto-act", "children"), Output("caja-barra-act", "hidden"),
              Input("reloj", "n_intervals"), prevent_initial_call=True)
def avance(_n):
    """Consulta el trabajo en hilo y mueve la pantalla cuando termina."""
    nada = (no_update,) * 8
    if JOB["estado"] not in ("corriendo", "terminado"):
        return nada
    pct = {"width": f"{100 * JOB['i'] / JOB['n']:.0f}%"}
    if JOB["tipo"] == "procesar":
        if JOB["estado"] == "terminado":
            res, JOB["estado"] = JOB["resultado"], "entregado"
            return 3, res, no_update, {"width": "100%"}, no_update, no_update, no_update, no_update
        return no_update, no_update, no_update, pct, f"{JOB['i']} de {JOB['n']}: {JOB['texto']}", \
            no_update, no_update, no_update
    if JOB["tipo"] == "actualizar":
        if JOB["estado"] == "terminado":
            fin, JOB["estado"] = JOB["resultado"], "entregado"
            return no_update, no_update, fin, no_update, no_update, {"width": "100%"}, "", False
        return no_update, no_update, no_update, no_update, no_update, pct, JOB["texto"], False
    return nada


@app.callback(Output("st-final", "data", allow_duplicate=True), Input("btn-actualizar", "n_clicks"),
              prevent_initial_call=True)
def actualizar(n):
    if n:
        _lanzar("actualizar", lambda prog: actualizacion.actualizar(prog))
    return None


@app.callback(Output("descarga", "data"), Input("btn-descargar", "n_clicks"), prevent_initial_call=True)
def descargar(n):
    if n and os.path.exists(actualizacion.LIBRO_FINAL):
        return dcc.send_file(actualizacion.LIBRO_FINAL)
    return no_update


@app.callback(Output("pasos", "children"),
              Output("panel-0", "style"), Output("panel-1", "style"), Output("panel-2", "style"),
              Output("panel-3", "style"),
              Output("plan-contenido", "children"), Output("btn-procesar", "disabled"),
              Output("res-contenido", "children"),
              Output("final-contenido", "children"), Output("btn-descargar", "disabled"),
              Input("st-paso", "data"), Input("st-plan", "data"), Input("st-res", "data"),
              Input("st-final", "data"), Input("chk-forzar", "value"))
def dibujar(paso, plan, res, final, forzar):
    paso = paso or 0
    partes = []
    for i, nombre in enumerate(PASOS):
        estado = "hecho" if i < paso else "actual" if i == paso else ""
        partes.append(html.Div([html.B("✓" if i < paso else str(i + 1)), html.Span(nombre)],
                               className="paso " + estado))
        if i < len(PASOS) - 1:
            partes.append(html.Div(className="linea" + (" hecho" if i < paso else "")))
    estilos = [{"display": "block" if i == paso else "none"} for i in range(4)]

    plan_ui, sin_nada = "", True
    if plan:
        sin_nada = not ((plan["nuevos"] + plan["reprocesar"]) > 0 or forzar)
        plan_ui = [html.Div([metrica("Nuevas", plan["nuevos"], "ok"),
                             metrica("Ya cargadas antes", plan["ya_cargados"], "neutro"),
                             metrica("Para volver a leer", plan["reprocesar"], "alerta")],
                            className="metricas")]
        if plan["repetidos_en_seleccion"]:
            plan_ui.append(html.Div(f"{plan['repetidos_en_seleccion']} archivo(s) son copias exactas de "
                                    "otros en tu selección y se leerán una sola vez.", className="aviso"))
        if plan["ignorados"]:
            plan_ui.append(html.Div(f"{plan['ignorados']} archivo(s) no son PDF y se ignoran.",
                                    className="aviso alerta"))
        if sin_nada:
            plan_ui.append(html.Div("No hay facturas nuevas: todo lo elegido ya estaba cargado.",
                                    className="aviso ok"))

    res_ui = ""
    if res:
        res_ui = [html.Div([metrica("Leídas bien", res["ok"], "ok"),
                            metrica("Necesitan revisión", res["pendientes"] + res["errores"], "alerta"),
                            metrica("Fuera de alcance", res["fuera_de_alcance"], "neutro")],
                           className="metricas")]
        problemas = [d for d in res["detalle"] if d["estado"] in ("PENDIENTE", "ERROR")]
        if problemas:
            res_ui.append(html.Div("Estas facturas no se pudieron leer solas. No se pierden: quedan en la "
                                   "hoja «Pendientes de lectura» del archivo final.",
                                   className="aviso alerta"))
            res_ui.append(html.Table([
                html.Thead(html.Tr([html.Th("Archivo"), html.Th("Origen"), html.Th("Motivo")])),
                html.Tbody([html.Tr([html.Td(d["archivo"]), html.Td(d["origen"]), html.Td(d["motivo"])])
                            for d in problemas])], className="tabla"))

    final_ui, descarga_off = "", True
    if final:
        if final.get("ok"):
            descarga_off = False
            final_ui = [html.Div(["Archivo actualizado. También queda guardado en: ", html.B(final["libro"])],
                                 className="aviso ok")]
            final_ui += [html.Div(a, className="aviso alerta") for a in final.get("avisos", [])]
        else:
            final_ui = [html.Div(f"No se pudo terminar en el paso «{final.get('etapa_fallida')}». "
                                 "Avisa al equipo técnico con este detalle:", className="aviso error"),
                        html.Pre(final.get("detalle", ""), className="detalle")]
    return partes, *estilos, plan_ui, sin_nada, res_ui, final_ui, descarga_off


@app.callback(Output("msg-regen", "children"), Input("btn-regen", "n_clicks"), prevent_initial_call=True)
def regenerar(n):
    if not n:
        return no_update
    r = subprocess.run([sys.executable, "scripts/publicar_dashboard.py"], cwd=BASE, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        return html.Div(actualizacion._aviso_dashboard((r.stderr or r.stdout)[-1200:]), className="aviso error")
    actualizacion.copiar_dashboard_local()
    return html.Div("Dashboard actualizado. Recarga la página para verlo.", className="aviso ok")


def main():
    if os.environ.get("NO_ABRIR_NAVEGADOR") != "1":
        threading.Timer(1.5, lambda: webbrowser.open(f"http://localhost:{PUERTO}")).start()
    app.run(host="127.0.0.1", port=PUERTO, debug=False)


if __name__ == "__main__":
    main()

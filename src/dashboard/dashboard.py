"""
PoliEcoConsumo - Dashboard de visualización de facturas
Proyecto de extracción masiva de facturas de Energía y Acueducto
"""

import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

import yaml
import pandas as pd
import dash
from dash import dcc, html, dash_table, Input, Output, callback_context
import plotly.express as px
import plotly.graph_objects as go

logger = logging.getLogger(__name__)

ASSETS_DIR = os.path.join(os.path.dirname(__file__), 'assets')

INDEX_STRING = '''
<!DOCTYPE html>
<html class="dark" lang="es">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
    <link href="https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet">
    <script>
      tailwind.config = {
        darkMode: "class",
        theme: {
          extend: {
            "colors": {
                "surface": "#0b1326",
                "surface-dim": "#0b1326",
                "surface-bright": "#31394d",
                "surface-container-lowest": "#060e20",
                "surface-container-low": "#131b2e",
                "surface-container": "#171f33",
                "surface-container-high": "#222a3d",
                "surface-container-highest": "#2d3449",
                "on-surface": "#dae2fd",
                "on-surface-variant": "#c2c6d6",
                "inverse-surface": "#dae2fd",
                "inverse-on-surface": "#283044",
                "outline": "#8c909f",
                "outline-variant": "#424754",
                "surface-tint": "#adc6ff",
                "primary": "#adc6ff",
                "on-primary": "#002e6a",
                "primary-container": "#4d8eff",
                "on-primary-container": "#00285d",
                "inverse-primary": "#005ac2",
                "secondary": "#b7c8e1",
                "on-secondary": "#213145",
                "secondary-container": "#3a4a5f",
                "on-secondary-container": "#a9bad3",
                "tertiary": "#ffb786",
                "on-tertiary": "#502400",
                "tertiary-container": "#df7412",
                "on-tertiary-container": "#461f00",
                "error": "#ffb4ab",
                "on-error": "#690005",
                "error-container": "#93000a",
                "on-error-container": "#ffdad6",
                "primary-fixed": "#d8e2ff",
                "primary-fixed-dim": "#adc6ff",
                "on-primary-fixed": "#001a42",
                "on-primary-fixed-variant": "#004395",
                "secondary-fixed": "#d3e4fe",
                "secondary-fixed-dim": "#b7c8e1",
                "on-secondary-fixed": "#0b1c30",
                "on-secondary-fixed-variant": "#38485d",
                "tertiary-fixed": "#ffdcc6",
                "tertiary-fixed-dim": "#ffb786",
                "on-tertiary-fixed": "#311400",
                "on-tertiary-fixed-variant": "#723600",
                "background": "#0b1326",
                "on-background": "#dae2fd",
                "surface-variant": "#2d3449"
            },
            "borderRadius": {
                "DEFAULT": "0.25rem",
                "lg": "0.5rem",
                "xl": "0.75rem",
                "full": "0.75rem"
            },
            "spacing": {
                "base": "4px",
                "xs": "0.25rem",
                "sm": "0.5rem",
                "md": "1rem",
                "lg": "1.5rem",
                "xl": "2rem",
                "2xl": "3rem",
                "gutter": "1.5rem",
                "margin-mobile": "1rem",
                "margin-desktop": "2.5rem"
            },
            "fontFamily": {
                "display": ["Hanken Grotesk"],
                "headline-lg": ["Hanken Grotesk"],
                "headline-md": ["Hanken Grotesk"],
                "body-lg": ["Inter"],
                "body-md": ["Inter"],
                "body-sm": ["Inter"],
                "label-md": ["JetBrains Mono"]
            },
            "fontSize": {
                "display": ["48px", {"lineHeight": "56px", "letterSpacing": "-0.02em", "fontWeight": "700"}],
                "headline-lg": ["32px", {"lineHeight": "40px", "letterSpacing": "-0.01em", "fontWeight": "600"}],
                "headline-md": ["24px", {"lineHeight": "32px", "fontWeight": "600"}],
                "body-lg": ["18px", {"lineHeight": "28px", "fontWeight": "400"}],
                "body-md": ["16px", {"lineHeight": "24px", "fontWeight": "400"}],
                "body-sm": ["14px", {"lineHeight": "20px", "fontWeight": "400"}],
                "label-md": ["12px", {"lineHeight": "16px", "letterSpacing": "0.05em", "fontWeight": "500"}],
                "data-metric": ["36px", {"lineHeight": "44px", "letterSpacing": "-0.01em", "fontWeight": "700"}]
            }
          }
        }
      }
    </script>
    {%metas%}
    <title>{%title%}</title>
    {%favicon%}
    {%css%}
</head>
    <body class="bg-background text-on-background">
        {%app_entry%}
    <footer>
        {%config%}
        {%scripts%}
        {%renderer%}
    </footer>
</body>
</html>
'''


class FacturaDashboard:
    """Dashboard para visualizar datos de facturas extraídas"""

    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = config_path
        self.config = self._cargar_config()
        self.dashboard_config = self.config.get('dashboard', {})

        self.app = dash.Dash(
            __name__,
            title=self.dashboard_config.get('titulo', 'PoliEcoConsumo - Dashboard'),
            assets_folder=ASSETS_DIR,
            suppress_callback_exceptions=True
        )
        self.app.index_string = INDEX_STRING

        self._configurar_layout()
        self._configurar_callbacks()

    def _cargar_config(self) -> Dict[str, Any]:
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error al cargar config.yaml: {str(e)}")
            return {}

    def _cargar_catalogo(self):
        """direccion_norm -> sede (confirmada si existe, si no sugerida)."""
        import glob as _glob
        carpeta = self.config.get('salida', {}).get('carpeta_salida', 'data/outputs')
        candidatos = sorted(_glob.glob(os.path.join(carpeta, "catalogo_sedes.csv")))
        if not candidatos:
            return {}, []
        cat = pd.read_csv(candidatos[-1], dtype=str).fillna("")
        sedes = []
        mapa = {}
        for _, r in cat.iterrows():
            sede = r["sede_confirmada"].strip() or r["sede_sugerida"].strip()
            if sede and sede != "SIN_MAPEO":
                mapa[r["direccion_norm"]] = sede
                if sede not in sedes:
                    sedes.append(sede)
        return mapa, sorted(sedes)

    def _cargar_base_unificada(self, patron: str) -> pd.DataFrame | None:
        import glob as _glob
        carpeta = self.config.get('salida', {}).get('carpeta_salida', 'data/outputs')
        candidatos = sorted(_glob.glob(os.path.join(carpeta, patron)))
        if not candidatos:
            return None
        df = pd.read_excel(candidatos[-1], sheet_name="Base")
        import re as _re
        direccion_norm = (df.get("direccion", "").astype(str)
                          .str.replace(r"\s*\|\s*\d+$", "", regex=True).str.strip())
        mapa_sedes, _ = self._cargar_catalogo()
        mapa = pd.DataFrame({
            "TIPO": df.get("servicio", "").astype(str).str.strip().str.replace(
                "^energia$", "Energía", regex=True).str.replace(
                "^acueducto$", "Acueducto", regex=True),
            "CIUDAD": df.get("sede", ""),
            "PROVEEDOR": df.get("prestador", ""),
            "No FACTURA": df.get("factura", ""),
            "CONSUMO Kwh": pd.to_numeric(df.get("consumo"), errors="coerce").where(
                df.get("unidad", "") == "kWh", 0.0),
            "CONSUMO M3": pd.to_numeric(df.get("consumo"), errors="coerce").where(
                df.get("unidad", "") == "m3", 0.0),
            "VALOR FACT.": df.get("valor", 0),
            "FECHA EXTRACCION": pd.to_datetime(
                df.get("periodo_fin", ""), errors="coerce"),
            "estado": df.get("estado", "OK"),
            "severidad": df.get("severidad", ""),
            "cuenta": df.get("cuenta", ""),
            "SEDE": direccion_norm.map(mapa_sedes).fillna("SIN_MAPEO"),
        })
        return mapa

    def _cargar_datos(self) -> pd.DataFrame:
        # Fuente primaria: validacion vigente = base + estado/severidad.
        # Si no existe, retrocede a base unificada y luego a lotes.
        for patron in ["validacion_*.xlsx", "base_unificada_*.xlsx"]:
            unificada = self._cargar_base_unificada(patron)
            if unificada is not None:
                return unificada
        carpeta_salida = self.config.get('salida', {}).get('carpeta_salida', 'data/outputs')
        archivos_excel = []
        if os.path.exists(carpeta_salida):
            for archivo in os.listdir(carpeta_salida):
                if archivo.endswith('.xlsx') and not archivo.startswith('~$'):
                    archivos_excel.append(os.path.join(carpeta_salida, archivo))
        dfs = []
        for archivo in archivos_excel:
            try:
                df = pd.read_excel(archivo)
                dfs.append(df)
            except Exception as e:
                logger.warning(f"Error al leer {archivo}: {str(e)}")
        if dfs:
            df = pd.concat(dfs, ignore_index=True)
            return self._normalizar_columnas(df)
        return pd.DataFrame()

    def _normalizar_columnas(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        # Normalizar TIPO: Energia -> Energía, Acueducto -> Acueducto
        if 'TIPO' in df.columns:
            df['TIPO'] = df['TIPO'].astype(str).str.strip().str.replace('Energia', 'Energía').str.replace('Acueducto', 'Acueducto')
        # Parsear CONSUMO (unidad) -> CONSUMO Kwh / CONSUMO M3
        if 'CONSUMO (unidad)' in df.columns:
            def _parse(val):
                if pd.isna(val): return (0.0, '')
                parts = str(val).strip().split()
                if len(parts) >= 2:
                    try: return (float(parts[0]), parts[1].lower())
                    except: pass
                return (0.0, '')
            parsed = df['CONSUMO (unidad)'].apply(_parse)
            vals = parsed.apply(lambda x: x[0])
            units = parsed.apply(lambda x: x[1])
            if 'CONSUMO Kwh' not in df.columns:
                df['CONSUMO Kwh'] = vals.where(units.isin(['kwh', 'kwh']), 0.0).astype(float)
            if 'CONSUMO M3' not in df.columns:
                df['CONSUMO M3'] = vals.where(units.isin(['m3', 'm3']), 0.0).astype(float)
        # Añadir FECHA EXTRACCION si no existe
        if 'FECHA EXTRACCION' not in df.columns:
            df['FECHA EXTRACCION'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # Eliminar filas duplicadas (misma No FACTURA + TIPO)
        id_cols = [c for c in ['No FACTURA', 'No.FACTURA', 'no_factura', 'TIPO'] if c in df.columns]
        if id_cols:
            before = len(df)
            df = df.drop_duplicates(subset=id_cols, keep='first')
            if len(df) < before:
                logger.info(f"Eliminados {before - len(df)} duplicados")
        return df

    def _get_proveedor_col(self, df):
        for col in ['PROVEEDOR', 'COMPAÑÍA', 'NOMBRE PRESTADOR']:
            if col in df.columns:
                return col
        return 'PROVEEDOR'

    def _get_valor_col(self, df):
        for col in ['VALOR FACT.', 'VALOR TOTAL', 'VALOR FACTURA', 'VALOR ACUEDUCTO', 'VLR FACT TOTAL', 'VAlOR FACT. CONSUMO']:
            if col in df.columns:
                return col
        return None

    def _filtrar_datos(self, df, ciudad, servicio, proveedor):
        if df.empty:
            return df
        if ciudad != 'todas':
            col = 'SEDE' if 'SEDE' in df.columns else 'CIUDAD'
            df = df[df.get(col, '') == ciudad]
        if servicio != 'todos':
            df = df[df.get('TIPO', '') == servicio]
        if proveedor != 'todos':
            col = self._get_proveedor_col(df)
            df = df[df.get(col, '') == proveedor]
        return df

    def _parse_valor(self, serie):
        try:
            s = serie.astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False).str.strip()
            s = s.replace('', '0').replace('nan', '0')
            return pd.to_numeric(s, errors='coerce')
        except Exception:
            return pd.Series([0])

    def _crear_figura_vacia(self):
        fig = go.Figure()
        self._aplicar_tema_oscuro(fig)
        return fig

    def _resumen_alertas(self, df):
        """Titulo + texto del panel de alertas a partir de la validacion real."""
        if df.empty or 'estado' not in df.columns:
            return ("Alertas de validación", "Sin datos de validación.")
        atip = df[df['estado'] == 'ATIPICO_REVISAR']
        if atip.empty:
            return ("Sin atípicos", "Todos los consumos dentro del rango esperado (±20%).")
        n_alta = int((atip.get('severidad', '') == 'ALTA').sum())
        return (f"{len(atip)} atípicos ({n_alta} ALTA)",
                f"{len(atip)} consumos fuera del ±20% requieren revisión del Analista SGA; "
                f"{n_alta} de severidad ALTA (>50%). Ver hoja Atipicos.")

    def _aplicar_tema_oscuro(self, fig):
        fig.update_layout(
            paper_bgcolor='#171f33',
            plot_bgcolor='#171f33',
            font=dict(family='Inter', color='#c2c6d6', size=12),
            title=dict(font=dict(family='Hanken Grotesk', color='#dae2fd', size=16)),
            xaxis=dict(
                gridcolor='rgba(66,71,84,0.4)',
                zeroline=False,
                tickfont=dict(color='#c2c6d6', size=11),
                title=dict(font=dict(color='#c2c6d6', size=12))
            ),
            yaxis=dict(
                gridcolor='rgba(66,71,84,0.4)',
                zeroline=False,
                tickfont=dict(color='#c2c6d6', size=11),
                title=dict(font=dict(color='#c2c6d6', size=12))
            ),
            margin=dict(l=10, r=10, t=40, b=10),
            legend=dict(font=dict(color='#c2c6d6', size=11), orientation='h', y=1.1),
            hovermode='x unified',
            hoverlabel=dict(
                bgcolor='#171f33',
                font=dict(color='#dae2fd', size=12),
                bordercolor='#424754'
            ),
            xaxis_rangeslider_visible=False,
        )
        return fig

    def _crear_header(self):
        return html.Header(
            className="sticky top-0 z-50 bg-surface/80 backdrop-blur-lg border-b border-outline-variant shadow-lg px-gutter h-20 flex justify-between items-center w-full",
            children=[
                html.Div(
                    className="flex items-center gap-lg",
                    children=[
                        html.Span("PoliEcoConsumo", className="font-display text-headline-md font-bold text-primary tracking-tight"),
                        html.Nav(
                            className="hidden md:flex gap-md items-end h-full pt-4",
                            children=[
                                html.A("Dashboard", id="nav-dashboard", href="/dashboard",
                                    className="text-primary font-bold border-b-2 border-primary pb-2 transition-colors duration-200"),
                                html.A("Consumo", id="nav-consumo", href="/consumo",
                                    className="text-on-surface-variant font-medium pb-2 hover:text-primary transition-colors duration-200"),
                                html.A("Costos", id="nav-costos", href="#",
                                    className="text-on-surface-variant font-medium pb-2 hover:text-primary transition-colors duration-200"),
                                html.A("Reportes", id="nav-reportes", href="#",
                                    className="text-on-surface-variant font-medium pb-2 hover:text-primary transition-colors duration-200"),
                                html.A("Alertas", id="nav-alertas", href="#",
                                    className="text-on-surface-variant font-medium pb-2 hover:text-primary transition-colors duration-200"),
                            ]
                        ),
                    ]
                ),
                html.Div(
                    className="flex items-center gap-md",
                    children=[
                        html.Button(
                            className="p-base rounded-full hover:bg-surface-container-highest transition-all",
                            children=[html.Span("notifications", className="material-symbols-outlined text-on-surface-variant")]
                        ),
                        html.Button(
                            className="p-base rounded-full hover:bg-surface-container-highest transition-all",
                            children=[html.Span("settings", className="material-symbols-outlined text-on-surface-variant")]
                        ),
                        html.Div(
                            className="flex items-center gap-sm border-l border-outline-variant pl-md",
                            children=[
                                html.Img(
                                    src="https://lh3.googleusercontent.com/aida-public/AB6AXuDPyMn3KnWA6Ogmn6RQpL6Ulc_02eEBA5SkYYrsxGHgaQ8oil-Zpa9McV3wxIoxksWmiZMdDFTXRuLRcGGhlzlsdu9eswAzWUr4Z-x8nms5Uaf5cI32Qey-CfxWgQ99uhWiVFEt3oeZ_KkPqfGxeoNx1KnwsioQmBgPtFonDTRSpZZryrunm6qnPdQdS3-xvNnGammgbCbeTpYOAH0JXEu1TcmsyPx8rLkXpCC9xFgJeM5ed0ZsnkoX7nvEkf4vQs5lq6kfNasb6mo",
                                    className="w-10 h-10 rounded-full bg-secondary-container object-cover"
                                ),
                                html.Div(
                                    className="hidden lg:block",
                                    children=[
                                        html.P("Admin Global", className="font-label-md text-label-md text-on-surface"),
                                        html.P("Planta Industrial A1", className="text-[10px] text-on-surface-variant"),
                                    ]
                                ),
                            ]
                        ),
                    ]
                ),
            ]
        )

    def _crear_filtros(self, prefix=''):
        suf = lambda s: f"{prefix}-{s}" if prefix else s
        _, sedes = self._cargar_catalogo()
        opciones_sede = [{'label': 'Todas', 'value': 'todas'}] + [
            {'label': s, 'value': s} for s in sedes]
        return html.Div(
            className="flex flex-wrap items-end gap-md mb-lg bg-surface-container p-md rounded-xl border border-outline-variant shadow-sm",
            children=[
                html.Div([
                    html.Label("Sede:", className="font-label-md text-label-md text-on-surface-variant block mb-xs"),
                    dcc.Dropdown(
                        id=suf('dropdown-ciudad'),
                        options=opciones_sede,
                        value='todas',
                        clearable=False,
                        className="text-sm min-w-[160px]"
                    )
                ], className="flex-1 min-w-[140px]"),
                html.Div([
                    html.Label("Servicio:", className="font-label-md text-label-md text-on-surface-variant block mb-xs"),
                    dcc.Dropdown(
                        id=suf('dropdown-servicio'),
                        options=[
                            {'label': 'Todos', 'value': 'todos'},
                            {'label': 'Energía', 'value': 'Energía'},
                            {'label': 'Acueducto', 'value': 'Acueducto'}
                        ],
                        value='todos',
                        clearable=False,
                        className="text-sm min-w-[160px]"
                    )
                ], className="flex-1 min-w-[140px]"),
                html.Div([
                    html.Label("Proveedor:", className="font-label-md text-label-md text-on-surface-variant block mb-xs"),
                    dcc.Dropdown(
                        id=suf('dropdown-proveedor'),
                        options=[{'label': 'Todos', 'value': 'todos'}],
                        value='todos',
                        clearable=False,
                        className="text-sm min-w-[160px]"
                    )
                ], className="flex-1 min-w-[140px]"),
            ]
        )

    def _crear_hero(self, titulo, subtitulo, page='dashboard'):
        return html.Div(
            className="flex flex-col md:flex-row justify-between items-start md:items-center gap-md mb-lg",
            children=[
                html.Div([
                    html.H1(titulo, className="font-headline-lg text-headline-lg text-primary"),
                    html.P(subtitulo, className="text-on-surface-variant font-body-md"),
                ]),
                html.Div(
                    className="flex items-center gap-sm",
                    children=[
                        html.Div(
                            className="flex items-center gap-sm bg-surface-container-low shadow-inner rounded-xl p-xs border border-outline-variant",
                            children=[
                                html.Button("Hoy", className="px-md py-sm rounded-lg bg-primary text-on-primary text-label-md font-label-md"),
                                html.Button("Semana", className="px-md py-sm rounded-lg text-on-surface-variant hover:bg-surface-container-highest text-label-md font-label-md transition-all"),
                                html.Button("Mes", className="px-md py-sm rounded-lg text-on-surface-variant hover:bg-surface-container-highest text-label-md font-label-md transition-all"),
                            ]
                        ),
                        html.Button(
                            className="py-sm px-md bg-primary text-on-primary font-label-md text-label-md rounded-xl flex items-center justify-center gap-sm hover:brightness-110 transition-all active:scale-95 shadow-lg shadow-primary/20",
                            children=[
                                html.Span("download", className="material-symbols-outlined text-sm"),
                                "Descargar Reporte"
                            ]
                        ),
                    ]
                ),
            ]
        )

    def _crear_kpi_energia(self):
        return html.Div(
            className="bg-surface-container p-md rounded-xl shadow-sm border border-outline-variant border-l-[3px] border-l-primary flex flex-col gap-sm relative overflow-hidden group hover:border-primary/50 transition-all",
            children=[
                html.Div(
                    className="flex justify-between items-center",
                    children=[
                        html.Span("Consumo Energía", className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider"),
                        html.Span("bolt", className="material-symbols-outlined text-primary bg-surface-container-high p-xs rounded-lg"),
                    ]
                ),
                html.Div(
                    className="flex items-baseline gap-xs",
                    children=[
                        html.Span(id="kpi-energia-valor", className="font-data-metric text-data-metric text-on-surface", children="—"),
                        html.Span("kWh", className="text-on-surface-variant font-label-md"),
                    ]
                ),
                html.Div(
                    className="flex items-center gap-xs text-[12px]",
                    children=[
                        html.Span(id="kpi-energia-trend-icon", className="material-symbols-outlined text-sm text-on-surface-variant"),
                        html.Span(id="kpi-energia-trend", className="font-bold text-on-surface-variant"),
                        html.Span("vs periodo anterior", className="text-on-surface-variant italic"),
                    ]
                ),
                html.Div(
                    className="absolute bottom-0 left-0 w-full h-1 bg-surface-container-highest",
                    children=[html.Div(id="kpi-energia-bar", className="h-full bg-primary", style={'width': '0%'})]
                ),
            ]
        )

    def _crear_kpi_agua(self):
        return html.Div(
            className="bg-surface-container p-md rounded-xl shadow-sm border border-outline-variant border-l-[3px] border-l-tertiary flex flex-col gap-sm relative overflow-hidden group hover:border-primary/50 transition-all",
            children=[
                html.Div(
                    className="flex justify-between items-center",
                    children=[
                        html.Span("Consumo Agua", className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider"),
                        html.Span("water_drop", className="material-symbols-outlined text-primary bg-surface-container-high p-xs rounded-lg"),
                    ]
                ),
                html.Div(
                    className="flex items-baseline gap-xs",
                    children=[
                        html.Span(id="kpi-agua-valor", className="font-data-metric text-data-metric text-on-surface", children="—"),
                        html.Span("m³", className="text-on-surface-variant font-label-md"),
                    ]
                ),
                html.Div(
                    className="flex items-center gap-xs text-[12px]",
                    children=[
                        html.Span(id="kpi-agua-trend-icon", className="material-symbols-outlined text-sm text-on-surface-variant"),
                        html.Span(id="kpi-agua-trend", className="font-bold text-on-surface-variant"),
                        html.Span("vs periodo anterior", className="text-on-surface-variant italic"),
                    ]
                ),
                html.Div(
                    className="absolute bottom-0 left-0 w-full h-1 bg-surface-container-highest",
                    children=[html.Div(id="kpi-agua-bar", className="h-full bg-tertiary", style={'width': '0%'})]
                ),
            ]
        )

    def _crear_kpi_costos(self):
        return html.Div(
            className="bg-surface-container p-md rounded-xl shadow-sm border border-outline-variant border-l-[3px] border-l-primary/50 flex flex-col gap-sm relative overflow-hidden group hover:border-primary/50 transition-all",
            children=[
                html.Div(
                    className="flex justify-between items-center",
                    children=[
                        html.Span("Costos Totales", className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider"),
                        html.Span("payments", className="material-symbols-outlined text-primary bg-surface-container-high p-xs rounded-lg"),
                    ]
                ),
                html.Div(
                    className="flex items-baseline gap-xs",
                    children=[
                        html.Span(id="kpi-costos-valor", className="font-data-metric text-data-metric text-on-surface", children="$0"),
                    ]
                ),
                html.Div(
                    className="flex items-center gap-xs text-[12px]",
                    children=[
                        html.Span(id="kpi-costos-icon", className="material-symbols-outlined text-sm"),
                        html.Span(id="kpi-costos-text", className="font-bold"),
                    ]
                ),
            ]
        )

    def _crear_kpi_ahorro(self):
        return html.Div(
            className="bg-primary-container/20 text-on-primary p-md rounded-xl shadow-lg border border-primary/20 flex flex-col gap-sm relative overflow-hidden",
            children=[
                html.Div(
                    className="flex justify-between items-center",
                    children=[
                        html.Span("Ahorro Mensual", className="font-label-md text-label-md text-on-surface-variant/80 uppercase tracking-wider"),
                        html.Span("eco", className="material-symbols-outlined text-primary"),
                    ]
                ),
                html.Div(
                    className="flex items-baseline gap-xs",
                    children=[
                        html.Span(id="kpi-ahorro-valor", className="font-data-metric text-data-metric text-primary", children="—"),
                    ]
                ),
                html.P("Meta de ahorro", className="text-on-surface-variant/80 font-body-sm"),
                html.Div(
                    className="absolute -right-4 -bottom-4 opacity-10",
                    children=[html.Span("energy_savings_leaf", className="material-symbols-outlined text-[80px] text-primary")]
                ),
            ]
        )

    def _crear_alerta(self):
        return html.Div(
            className="bg-error-container/50 p-md rounded-xl border border-error/20 flex flex-col gap-sm shadow-lg",
            children=[
                html.Div(
                    className="flex items-center gap-sm text-on-error-container",
                    children=[
                        html.Span("warning", className="material-symbols-outlined text-error"),
                        html.H4(id="alerta-titulo", className="font-headline-sm text-[16px] font-bold text-on-surface",
                                children="Alertas de validación"),
                    ]
                ),
                html.P(id="alerta-texto",
                       className="text-[13px] text-on-surface-variant",
                       children="Sin datos de validación."),
                html.Button("Ver detalles técnicos", className="text-left font-label-md text-[12px] text-primary underline hover:opacity-70 transition-opacity"),
            ]
        )

    def _crear_notificaciones(self):
        return html.Div(
            className="bg-surface-container p-md rounded-xl border border-outline-variant flex-1 shadow-sm",
            children=[
                html.Div(
                    className="flex justify-between items-center mb-base",
                    children=[
                        html.H4("Notificaciones Recientes", className="font-label-md text-label-md text-on-surface uppercase tracking-widest"),
                        html.Span("history", className="material-symbols-outlined text-on-surface-variant text-sm"),
                    ]
                ),
                html.Ul(
                    className="flex flex-col gap-sm",
                    children=[
                        html.Li(
                            className="flex gap-sm items-start border-b border-outline-variant pb-sm",
                            children=[
                                html.Span(className="w-2 h-2 rounded-full bg-primary mt-1.5 shrink-0"),
                                html.Div([
                                    html.P("Mantenimiento de sensores finalizado", className="text-body-sm font-medium text-on-surface"),
                                    html.P("Hace 2 horas • Sector A1", className="text-[10px] text-on-surface-variant"),
                                ]),
                            ]
                        ),
                        html.Li(
                            className="flex gap-sm items-start border-b border-outline-variant pb-sm",
                            children=[
                                html.Span(className="w-2 h-2 rounded-full bg-tertiary mt-1.5 shrink-0"),
                                html.Div([
                                    html.P("Fuga de agua mitigada", className="text-body-sm font-medium text-on-surface"),
                                    html.P("Hace 5 horas • Área de Carga", className="text-[10px] text-on-surface-variant"),
                                ]),
                            ]
                        ),
                        html.Li(
                            className="flex gap-sm items-start",
                            children=[
                                html.Span(className="w-2 h-2 rounded-full bg-outline mt-1.5 shrink-0"),
                                html.Div([
                                    html.P("Reporte mensual generado", className="text-body-sm font-medium text-on-surface"),
                                    html.P("Hace 8 horas • Sistema", className="text-[10px] text-on-surface-variant"),
                                ]),
                            ]
                        ),
                    ]
                ),
            ]
        )

    def _crear_pagina_dashboard(self):
        return html.Main(
            className="flex-1 p-gutter max-w-7xl mx-auto overflow-hidden pb-20 md:pb-6",
            children=[
                self._crear_hero(
                    "Resumen de Facturas",
                    "Datos actualizados en tiempo real para el periodo actual."
                ),
                self._crear_filtros(),
                # KPIs Grid
                html.Div(
                    className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-md mb-lg",
                    children=[
                        self._crear_kpi_energia(),
                        self._crear_kpi_agua(),
                        self._crear_kpi_costos(),
                        self._crear_kpi_ahorro(),
                    ]
                ),
                # Bento Grid: Charts + Alerts
                html.Div(
                    className="grid grid-cols-1 lg:grid-cols-12 gap-md mb-lg",
                    children=[
                        html.Div(
                            className="lg:col-span-8 bg-surface-container p-md rounded-xl shadow-sm border border-outline-variant flex flex-col gap-md",
                            children=[
                                html.Div(
                                    className="flex justify-between items-center",
                                    children=[
                                        html.H3("Facturas por Servicio", className="font-headline-sm text-[20px] text-on-surface"),
                                        html.Div(
                                            className="flex gap-md text-[10px] font-label-md uppercase tracking-tighter",
                                            children=[
                                                html.Div(className="flex items-center gap-xs", children=[html.Span(className="w-3 h-3 bg-primary rounded-full"), "Energía"]),
                                                html.Div(className="flex items-center gap-xs", children=[html.Span(className="w-3 h-3 bg-tertiary rounded-full"), "Agua"]),
                                            ]
                                        ),
                                    ]
                                ),
                                dcc.Graph(
                                    id='grafico-servicios',
                                    figure=self._crear_figura_vacia(),
                                    style={'height': '300px'},
                                    config={'displayModeBar': False, 'responsive': True}
                                ),
                            ]
                        ),
                        html.Div(
                            className="lg:col-span-4 flex flex-col gap-md",
                            children=[
                                self._crear_alerta(),
                                self._crear_notificaciones(),
                            ]
                        ),
                    ]
                ),
                # Line Chart
                html.Div(
                    className="grid grid-cols-1 lg:grid-cols-12 gap-md",
                    children=[
                        html.Div(
                            className="lg:col-span-12 bg-surface-container p-md rounded-xl shadow-sm border border-outline-variant overflow-hidden",
                            children=[
                                html.Div(
                                    className="flex justify-between items-center mb-lg",
                                    children=[
                                        html.Div([
                                            html.H3("Tendencia de Facturas por Día", className="font-headline-sm text-headline-sm text-on-surface"),
                                            html.P("Facturas procesadas a lo largo del tiempo", className="text-on-surface-variant font-body-sm"),
                                        ]),
                                    ]
                                ),
                                dcc.Graph(
                                    id='grafico-tiempo',
                                    figure=self._crear_figura_vacia(),
                                    style={'height': '250px'},
                                    config={'displayModeBar': False, 'responsive': True}
                                ),
                            ]
                        ),
                    ]
                ),
                # Data Table
                html.Div(
                    className="bg-surface-container p-md rounded-xl shadow-sm border border-outline-variant mt-lg",
                    children=[
                        html.H4("Últimas Facturas", className="font-headline-sm text-headline-sm text-on-surface mb-md"),
                        html.Div(id='dash-tabla'),
                    ]
                ),
            ]
        )

    def _crear_pagina_consumo(self):
        return html.Main(
            className="flex-1 p-gutter max-w-7xl mx-auto overflow-hidden pb-20 md:pb-6",
            children=[
                self._crear_hero(
                    "Consumo de Facturas",
                    "Exploración detallada de todas las facturas registradas."
                ),
                self._crear_filtros(prefix='con'),
                # Summary stats
                html.Div(
                    className="grid grid-cols-2 sm:grid-cols-4 gap-md mb-lg",
                    children=[
                        html.Div(
                            className="bg-surface-container p-md rounded-xl border border-outline-variant flex flex-col gap-xs",
                            children=[
                                html.Span("Total Registros", className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider"),
                                html.Span(id="con-total-registros", className="font-data-metric text-data-metric text-on-surface", children="—"),
                            ]
                        ),
                        html.Div(
                            className="bg-surface-container p-md rounded-xl border border-outline-variant flex flex-col gap-xs",
                            children=[
                                html.Span("Total Energía", className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider"),
                                html.Div(className="flex items-baseline gap-xs", children=[
                                    html.Span(id="con-total-energia", className="font-data-metric text-data-metric text-primary", children="—"),
                                    html.Span("kWh", className="text-on-surface-variant font-label-md"),
                                ]),
                            ]
                        ),
                        html.Div(
                            className="bg-surface-container p-md rounded-xl border border-outline-variant flex flex-col gap-xs",
                            children=[
                                html.Span("Total Agua", className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider"),
                                html.Div(className="flex items-baseline gap-xs", children=[
                                    html.Span(id="con-total-agua", className="font-data-metric text-data-metric text-primary", children="—"),
                                    html.Span("m³", className="text-on-surface-variant font-label-md"),
                                ]),
                            ]
                        ),
                        html.Div(
                            className="bg-surface-container p-md rounded-xl border border-outline-variant flex flex-col gap-xs",
                            children=[
                                html.Span("Costo Total", className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider"),
                                html.Span(id="con-costo-total", className="font-data-metric text-data-metric text-on-surface", children="$0"),
                            ]
                        ),
                    ]
                ),
                # Full data table
                html.Div(
                    className="bg-surface-container p-md rounded-xl shadow-sm border border-outline-variant",
                    children=[
                        html.H4("Todas las Facturas", className="font-headline-sm text-headline-sm text-on-surface mb-md"),
                        html.Div(id='con-tabla'),
                    ]
                ),
            ]
        )

    def _crear_mobile_nav(self):
        return html.Nav(
            className="md:hidden fixed bottom-0 left-0 w-full bg-surface-container border-t border-outline-variant flex justify-around items-center h-16 z-50",
            children=[
                html.A(
                    className="flex flex-col items-center gap-1 text-primary",
                    href="/dashboard",
                    children=[
                        html.Span("dashboard", className="material-symbols-outlined"),
                        html.Span("Resumen", className="text-[10px] font-bold"),
                    ]
                ),
                html.A(
                    className="flex flex-col items-center gap-1 text-on-surface-variant/90 hover:text-on-surface transition-colors",
                    href="/consumo",
                    children=[
                        html.Span("table", className="material-symbols-outlined"),
                        html.Span("Consumo", className="text-[10px]"),
                    ]
                ),
                html.A(
                    className="flex flex-col items-center gap-1 text-on-surface-variant/90 hover:text-on-surface transition-colors",
                    href="#",
                    children=[
                        html.Span("water_drop", className="material-symbols-outlined"),
                        html.Span("Agua", className="text-[10px]"),
                    ]
                ),
                html.A(
                    className="flex flex-col items-center gap-1 text-on-surface-variant/90 hover:text-on-surface transition-colors",
                    href="#",
                    children=[
                        html.Span("settings", className="material-symbols-outlined"),
                        html.Span("Config", className="text-[10px]"),
                    ]
                ),
            ]
        )

    def _configurar_layout(self):
        self.app.layout = html.Div(
            className="bg-background text-on-background min-h-screen",
            children=[
            dcc.Location(id='url', refresh=False),

            # Background decorations
            html.Div(
                className="fixed inset-0 pointer-events-none -z-10 overflow-hidden",
                children=[
                    html.Div(className="absolute top-[-10%] right-[-10%] w-[40%] h-[40%] bg-primary/5 rounded-full blur-[120px]"),
                    html.Div(className="absolute bottom-[-5%] left-[-5%] w-[30%] h-[30%] bg-primary/5 rounded-full blur-[100px]"),
                ]
            ),

            # TopAppBar
            self._crear_header(),

            # Page content — both pages always in DOM, toggle visibility
            html.Div(id='page-dashboard', className="bg-background", style={}, children=self._crear_pagina_dashboard()),
            html.Div(id='page-consumo', className="bg-background", style={'display': 'none'}, children=self._crear_pagina_consumo()),

            # Mobile nav
            self._crear_mobile_nav(),

            # Auto-refresh
            dcc.Interval(
                id='intervalo-actualizacion',
                interval=self.dashboard_config.get('auto_refresh', 30) * 1000,
                n_intervals=0
            ),
        ])

    def _configurar_callbacks(self):
        # --- Page routing — show/hide toggle ---
        @self.app.callback(
            [Output('page-dashboard', 'style'),
             Output('page-consumo', 'style')],
            [Input('url', 'pathname')]
        )
        def route_page(pathname):
            if pathname == '/consumo':
                return {'display': 'none'}, {}
            return {}, {'display': 'none'}

        # --- Nav link active states ---
        @self.app.callback(
            [Output('nav-dashboard', 'className'),
             Output('nav-consumo', 'className'),
             Output('nav-costos', 'className'),
             Output('nav-reportes', 'className'),
             Output('nav-alertas', 'className')],
            [Input('url', 'pathname')]
        )
        def update_nav(pathname):
            base = "font-medium pb-2 hover:text-primary transition-colors duration-200"
            active = "text-primary font-bold border-b-2 border-primary pb-2 transition-colors duration-200"
            if pathname == '/consumo':
                return base, active, base, base, base
            if pathname == '/costos':
                return base, base, active, base, base
            if pathname == '/reportes':
                return base, base, base, active, base
            if pathname == '/alertas':
                return base, base, base, base, active
            return active, base, base, base, base

        # --- Dashboard callback ---
        @self.app.callback(
            [
                Output('kpi-energia-valor', 'children'),
                Output('kpi-energia-trend', 'children'),
                Output('kpi-energia-trend-icon', 'children'),
                Output('kpi-energia-trend-icon', 'className'),
                Output('kpi-energia-trend', 'className'),
                Output('kpi-energia-bar', 'style'),
                Output('kpi-agua-valor', 'children'),
                Output('kpi-agua-trend', 'children'),
                Output('kpi-agua-trend-icon', 'children'),
                Output('kpi-agua-trend-icon', 'className'),
                Output('kpi-agua-trend', 'className'),
                Output('kpi-agua-bar', 'style'),
                Output('kpi-costos-valor', 'children'),
                Output('kpi-costos-icon', 'children'),
                Output('kpi-costos-text', 'children'),
                Output('kpi-ahorro-valor', 'children'),
                Output('dropdown-proveedor', 'options'),
                Output('grafico-servicios', 'figure'),
                Output('grafico-tiempo', 'figure'),
                Output('dash-tabla', 'children'),
                Output('alerta-titulo', 'children'),
                Output('alerta-texto', 'children'),
            ],
            [
                Input('dropdown-ciudad', 'value'),
                Input('dropdown-servicio', 'value'),
                Input('dropdown-proveedor', 'value'),
                Input('intervalo-actualizacion', 'n_intervals'),
            ]
        )
        def actualizar_dashboard(ciudad, servicio, proveedor, n):
            df = self._cargar_datos()
            df = self._filtrar_datos(df, ciudad, servicio, proveedor)

            if df.empty:
                empty_fig = go.Figure()
                self._aplicar_tema_oscuro(empty_fig)
                neutral_cls = "material-symbols-outlined text-sm text-on-surface-variant"
                trend_cls = "font-bold text-on-surface-variant"
                return ("—", "—", "trending_flat", neutral_cls, trend_cls, {'width': '0%'},
                        "—", "—", "trending_flat", neutral_cls, trend_cls, {'width': '0%'},
                        "$0", "info", "Sin datos", "—",
                        [{'label': 'Todos', 'value': 'todos'}],
                        empty_fig, empty_fig, "No hay datos disponibles",
                        "Alertas de validación", "Sin datos de validación.")

            # KPI Energía
            total_kwh = 0
            if 'CONSUMO Kwh' in df.columns:
                total_kwh = pd.to_numeric(df['CONSUMO Kwh'], errors='coerce').sum()
            kwh_val = f"{total_kwh:,.0f}" if total_kwh > 0 else "0"

            # KPI Agua
            total_m3 = 0
            if 'CONSUMO M3' in df.columns:
                total_m3 = pd.to_numeric(df['CONSUMO M3'], errors='coerce').sum()
            m3_val = f"{total_m3:,.0f}" if total_m3 > 0 else "0"

            # KPI Costos
            valor_col = self._get_valor_col(df)
            valor_numeric = 0
            if valor_col:
                vals = self._parse_valor(df[valor_col])
                valor_numeric = vals.sum()
            costo_val = f"${valor_numeric:,.0f}" if valor_numeric > 0 else "$0"
            costo_icon = "check_circle" if valor_numeric > 0 else "info"
            costo_text = "Dentro de presupuesto" if valor_numeric > 0 else "Sin datos"

            # KPI Ahorro
            ahorro = "—"
            if valor_numeric > 0:
                budget = valor_numeric * 1.15
                pct = ((budget - valor_numeric) / budget) * 100
                if pct > 0:
                    ahorro = f"{pct:.1f}%"

            # Trends
            en_trend, en_icon = "—", "trending_flat"
            ag_trend, ag_icon = "—", "trending_flat"
            en_icon_cls = "material-symbols-outlined text-sm text-on-surface-variant"
            en_trend_cls = "font-bold text-on-surface-variant"
            ag_icon_cls = "material-symbols-outlined text-sm text-on-surface-variant"
            ag_trend_cls = "font-bold text-on-surface-variant"

            df_en = df[df.get('TIPO', '') == 'Energía']
            df_ag = df[df.get('TIPO', '') == 'Acueducto']

            if not df_en.empty and 'CONSUMO Kwh' in df_en.columns:
                mid = max(1, len(df_en) // 2)
                r = pd.to_numeric(df_en['CONSUMO Kwh'].iloc[mid:], errors='coerce').sum()
                p = pd.to_numeric(df_en['CONSUMO Kwh'].iloc[:mid], errors='coerce').sum()
                if p > 0:
                    diff = ((r - p) / p) * 100
                    en_trend = f"{abs(diff):.1f}%"
                    en_icon = "trending_down" if diff < 0 else "trending_up"
                    en_icon_cls = "material-symbols-outlined text-sm text-tertiary" if diff < 0 else "material-symbols-outlined text-sm text-error"
                    en_trend_cls = "font-bold text-tertiary" if diff < 0 else "font-bold text-error"

            if not df_ag.empty and 'CONSUMO M3' in df_ag.columns:
                mid = max(1, len(df_ag) // 2)
                r = pd.to_numeric(df_ag['CONSUMO M3'].iloc[mid:], errors='coerce').sum()
                p = pd.to_numeric(df_ag['CONSUMO M3'].iloc[:mid], errors='coerce').sum()
                if p > 0:
                    diff = ((r - p) / p) * 100
                    ag_trend = f"{abs(diff):.1f}%"
                    ag_icon = "trending_down" if diff < 0 else "trending_up"
                    ag_icon_cls = "material-symbols-outlined text-sm text-tertiary" if diff < 0 else "material-symbols-outlined text-sm text-error"
                    ag_trend_cls = "font-bold text-tertiary" if diff < 0 else "font-bold text-error"

            # Progress bars
            max_kwh = max(total_kwh * 1.5, 1)
            max_m3 = max(total_m3 * 1.5, 1)
            en_bar = min(100, (total_kwh / max_kwh) * 100)
            ag_bar = min(100, (total_m3 / max_m3) * 100)

            # Provider dropdown
            proveedor_col = self._get_proveedor_col(df)
            opts = [{'label': 'Todos', 'value': 'todos'}]
            if proveedor_col in df.columns:
                for p in df[proveedor_col].unique():
                    if pd.notna(p) and str(p).strip():
                        opts.append({'label': p, 'value': p})

            # Bar chart
            fig_svc = go.Figure()
            col_tipo = 'TIPO' if 'TIPO' in df.columns else 'tipo'
            if col_tipo in df.columns:
                cnt = df[col_tipo].value_counts()
                colors = ['#adc6ff' if s == 'Energía' else '#ffb786' for s in cnt.index]
                fig_svc.add_trace(go.Bar(
                    x=cnt.index, y=cnt.values,
                    marker_color=colors,
                    text=cnt.values, textposition='outside',
                    textfont=dict(color='#dae2fd', size=13),
                    hovertemplate='<b>%{x}</b><br>Cantidad: %{y}<extra></extra>',
                ))
                fig_svc.update_layout(xaxis_title=None, yaxis_title="Cantidad")
            self._aplicar_tema_oscuro(fig_svc)

            # Line chart
            fig_t = go.Figure()
            if 'FECHA EXTRACCION' in df.columns:
                dft = df.copy()
                dft['FECHA EXTRACCION'] = pd.to_datetime(dft['FECHA EXTRACCION'], errors='coerce')
                dft = dft.dropna(subset=['FECHA EXTRACCION'])
                if not dft.empty:
                    grp = dft.groupby(dft['FECHA EXTRACCION'].dt.date).size().reset_index()
                    grp.columns = ['fecha', 'cantidad']
                    grp = grp.sort_values('fecha')
                    fig_t.add_trace(go.Scatter(
                        x=grp['fecha'], y=grp['cantidad'],
                        mode='lines+markers',
                        line=dict(color='#adc6ff', width=3),
                        marker=dict(color='#adc6ff', size=6, line=dict(color='#0b1326', width=2)),
                        fill='tozeroy',
                        fillcolor='rgba(173,198,255,0.25)',
                        hovertemplate='<b>%{x|%d %b %Y}</b><br>Facturas: %{y}<extra></extra>',
                    ))
                    fig_t.update_layout(xaxis_title=None, yaxis_title="Facturas")
            self._aplicar_tema_oscuro(fig_t)

            # Table
            tabla = dash_table.DataTable(
                data=df.head(10).to_dict('records'),
                columns=[{'name': i, 'id': i} for i in df.columns],
                style_table={'overflowX': 'auto', 'border': 'none'},
                style_cell={
                    'textAlign': 'left', 'padding': '10px 12px',
                    'backgroundColor': '#171f33', 'color': '#dae2fd',
                    'fontFamily': 'Inter, sans-serif', 'fontSize': '13px',
                    'border': 'none', 'borderBottom': '1px solid #424754',
                },
                style_header={
                    'backgroundColor': '#1e3a8a', 'color': '#dae2fd',
                    'fontWeight': '600', 'fontFamily': 'JetBrains Mono, monospace',
                    'fontSize': '11px', 'letterSpacing': '0.05em',
                    'textTransform': 'uppercase', 'border': 'none',
                },
                style_data_conditional=[
                    {'if': {'row_index': 'odd'}, 'backgroundColor': '#1a2236'},
                    {'if': {'state': 'active'}, 'backgroundColor': '#2d3449', 'border': '1px solid #adc6ff'},
                ],
            )

            return (kwh_val, en_trend, en_icon, en_icon_cls, en_trend_cls, {'width': f'{en_bar:.0f}%'},
                    m3_val, ag_trend, ag_icon, ag_icon_cls, ag_trend_cls, {'width': f'{ag_bar:.0f}%'},
                    costo_val, costo_icon, costo_text, ahorro,
                    opts, fig_svc, fig_t, tabla,
                    *self._resumen_alertas(df))

        # --- Consumo callback ---
        @self.app.callback(
            [
                Output('con-total-registros', 'children'),
                Output('con-total-energia', 'children'),
                Output('con-total-agua', 'children'),
                Output('con-costo-total', 'children'),
                Output('con-dropdown-proveedor', 'options'),
                Output('con-tabla', 'children'),
            ],
            [
                Input('con-dropdown-ciudad', 'value'),
                Input('con-dropdown-servicio', 'value'),
                Input('con-dropdown-proveedor', 'value'),
                Input('intervalo-actualizacion', 'n_intervals'),
            ]
        )
        def actualizar_consumo(ciudad, servicio, proveedor, n):
            df = self._cargar_datos()
            df = self._filtrar_datos(df, ciudad, servicio, proveedor)

            if df.empty:
                return ("—", "—", "—", "$0",
                        [{'label': 'Todos', 'value': 'todos'}],
                        "No hay datos disponibles")

            total = len(df)

            total_kwh = 0
            if 'CONSUMO Kwh' in df.columns:
                total_kwh = pd.to_numeric(df['CONSUMO Kwh'], errors='coerce').sum()
            en_val = f"{total_kwh:,.0f}" if total_kwh > 0 else "0"

            total_m3 = 0
            if 'CONSUMO M3' in df.columns:
                total_m3 = pd.to_numeric(df['CONSUMO M3'], errors='coerce').sum()
            ag_val = f"{total_m3:,.0f}" if total_m3 > 0 else "0"

            vcol = self._get_valor_col(df)
            vnum = 0
            if vcol:
                vnum = self._parse_valor(df[vcol]).sum()
            costo = f"${vnum:,.0f}" if vnum > 0 else "$0"

            proveedor_col = self._get_proveedor_col(df)
            opts = [{'label': 'Todos', 'value': 'todos'}]
            if proveedor_col in df.columns:
                for p in df[proveedor_col].unique():
                    if pd.notna(p) and str(p).strip():
                        opts.append({'label': p, 'value': p})

            tabla = dash_table.DataTable(
                data=df.to_dict('records'),
                columns=[{'name': i, 'id': i} for i in df.columns],
                page_size=25,
                style_table={'overflowX': 'auto', 'border': 'none'},
                style_cell={
                    'textAlign': 'left', 'padding': '10px 12px',
                    'backgroundColor': '#171f33', 'color': '#dae2fd',
                    'fontFamily': 'Inter, sans-serif', 'fontSize': '13px',
                    'border': 'none', 'borderBottom': '1px solid #424754',
                    'maxWidth': '200px',
                },
                style_header={
                    'backgroundColor': '#1e3a8a', 'color': '#dae2fd',
                    'fontWeight': '600', 'fontFamily': 'JetBrains Mono, monospace',
                    'fontSize': '11px', 'letterSpacing': '0.05em',
                    'textTransform': 'uppercase', 'border': 'none',
                },
                style_data_conditional=[
                    {'if': {'row_index': 'odd'}, 'backgroundColor': '#1a2236'},
                    {'if': {'state': 'active'}, 'backgroundColor': '#2d3449', 'border': '1px solid #adc6ff'},
                ],
                sort_action='native',
                filter_action='native',
                export_format='xlsx',
                export_headers='display',
            )

            return (str(total), en_val, ag_val, costo, opts, tabla)

    def ejecutar(self, host: str = '0.0.0.0', port: int = 8050, debug: bool = False):
        puerto = self.dashboard_config.get('puerto', port)
        logger.info(f"Iniciando dashboard en http://{host}:{puerto}")
        self.app.run(host=host, port=puerto, debug=debug)


def crear_dashboard(config_path: str = "config/config.yaml") -> FacturaDashboard:
    return FacturaDashboard(config_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    dashboard = crear_dashboard()
    dashboard.ejecutar(debug=True)

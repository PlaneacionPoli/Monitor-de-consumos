"""
Libro final legible: data/outputs/Consumos_Consolidado.xlsx

Toma la validacion vigente (03_validacion) y las alertas (04_alertas) y los presenta
con encabezados en español, sede identificada, formato de marca Poli y hojas:
Resumen, Base, Atipicos, Cola de revision, Faltantes.

Uso: python scripts/exportar_consolidado.py
"""
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
from src.utils import rutas  # noqa: E402
from src.utils.sedes import completar_sede_por_cuenta  # noqa: E402

AZUL, CIAN, CLARO = "263A58", "22B2DE", "EAF6FB"
ESTADOS = {
    "OK": "Sin hallazgos", "ATIPICO_REVISAR": "Atípico", "SIN_SERIE": "Sin medidor",
    "REVISION_BAJA_CONFIANZA": "Baja confianza", "REVISION_PERIODO_INFERIDO": "Periodo inferido",
    "REVISION_UNIDAD": "Unidad incoherente",
}
COLUMNAS = [  # (campo, encabezado, ancho, formato)
    ("sede_final", "Sede", 24, None), ("prestador", "Prestador", 14, None),
    ("servicio", "Servicio", 12, None), ("factura", "Factura", 18, None),
    ("periodo_inicio", "Periodo inicio", 13, "yyyy-mm-dd"), ("periodo_fin", "Periodo fin", 13, "yyyy-mm-dd"),
    ("consumo", "Consumo", 12, "#,##0"), ("unidad", "Unidad", 8, None),
    ("valor", "Valor facturado (COP)", 20, '"$" #,##0'), ("estado_txt", "Estado", 18, None),
    ("severidad", "Severidad", 11, None), ("sentido_txt", "Sentido", 10, None), ("detalle", "Detalle", 48, None),
    ("confianza", "Confianza", 11, "0%"), ("cuenta", "Cuenta / medidor", 20, None),
    ("direccion", "Dirección", 34, None), ("archivo", "Archivo origen", 44, None),
]


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


def preparar(base: pd.DataFrame) -> pd.DataFrame:
    base = base.copy()
    direccion = (base["direccion"].astype(str)
                 .str.replace(r"\s*\|\s*\d+$", "", regex=True).str.strip())
    base["sede_final"] = direccion.map(mapa_sedes()).fillna("Sin sede identificada")
    base = completar_sede_por_cuenta(base, "Sin sede identificada")
    base["sede_final"] = base["sede_final"].fillna("Sin sede identificada").astype(str)
    base["servicio"] = base["servicio"].astype(str).str.replace("^energia$", "Energía", regex=True) \
        .str.capitalize().str.replace("^Energ[ií]a$", "Energía", regex=True)
    base["unidad"] = base["unidad"].replace({"m3": "m³"})
    base["sentido_txt"] = base["sentido"].map({"AUMENTO": "Aumento", "CAIDA": "Caída"}).fillna("") \
        if "sentido" in base.columns else ""
    base["estado_txt"] = base["estado"].map(ESTADOS).fillna(base["estado"])
    for c in ("periodo_inicio", "periodo_fin"):
        base[c] = pd.to_datetime(base[c], errors="coerce")
    base["confianza"] = pd.to_numeric(base["confianza"], errors="coerce")
    return base


def dar_formato(ws, anchos, formatos, filas):
    cab = PatternFill("solid", fgColor=AZUL)
    for c in ws[1]:
        c.fill, c.font = cab, Font(bold=True, color="FFFFFF")
        c.alignment = Alignment(vertical="center", wrap_text=True)
    ws.row_dimensions[1].height = 30
    for i, (ancho, fmt) in enumerate(zip(anchos, formatos), start=1):
        ws.column_dimensions[get_column_letter(i)].width = ancho
        if fmt:
            for fila in range(2, filas + 2):
                ws.cell(row=fila, column=i).number_format = fmt
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    ws.sheet_properties.tabColor = CIAN


def hoja_tabla(escritor, nombre, df, vacio=None):
    if df.empty:
        pd.DataFrame({"Información": [vacio or "Sin registros."]}).to_excel(escritor, sheet_name=nombre, index=False)
        ws = escritor.sheets[nombre]
        dar_formato(ws, [60], [None], 1)
        return
    campos = [c for c in COLUMNAS if c[0] in df.columns]
    salida = df[[c[0] for c in campos]].copy()
    salida.columns = [c[1] for c in campos]
    salida.to_excel(escritor, sheet_name=nombre, index=False)
    dar_formato(escritor.sheets[nombre], [c[2] for c in campos], [c[3] for c in campos], len(salida))


def resumen(escritor, base, fuente, faltantes):
    ws = escritor.book.create_sheet("Resumen", 0)
    ws.sheet_properties.tabColor = AZUL
    ws.sheet_view.showGridLines = False
    total = len(base)
    ok = int((base["estado"] == "OK").sum())
    atip = int((base["estado"] == "ATIPICO_REVISAR").sum())
    altas = int(((base["estado"] == "ATIPICO_REVISAR") & (base["severidad"] == "ALTA")).sum())
    energia = base.loc[base["unidad"] == "kWh", "consumo"].sum()
    agua = base.loc[base["unidad"] == "m³", "consumo"].sum()
    ahora = datetime.now(ZoneInfo("America/Bogota")).strftime("%Y-%m-%d %H:%M")
    ws["A1"] = "Monitor de Consumos Ambientales"
    ws["A1"].font = Font(size=16, bold=True, color=AZUL)
    ws["A2"] = f"Generado {ahora} · fuente {fuente} · Politécnico Grancolombiano"
    ws["A2"].font = Font(italic=True, color="5A6A82")
    indicadores = [
        ("Facturas procesadas", total, "#,##0"),
        ("Sin revisión manual", ok / total if total else 0, "0%"),
        ("Energía consumida (kWh)", energia, "#,##0"),
        ("Agua consumida (m³)", agua, "#,##0"),
        ("Valor facturado (COP)", base["valor"].sum(), '"$" #,##0'),
        ("Atípicos por revisar", atip, "#,##0"),
        ("  de ellos, severidad alta", altas, "#,##0"),
        ("Posibles facturas faltantes", faltantes, "#,##0"),
    ]
    ws["A4"], ws["B4"] = "Indicador", "Valor"
    for i, (k, v, fmt) in enumerate(indicadores, start=5):
        ws.cell(row=i, column=1, value=k)
        c = ws.cell(row=i, column=2, value=float(v) if not isinstance(v, int) else v)
        c.number_format, c.alignment = fmt, Alignment(horizontal="right")
    fila = 5 + len(indicadores) + 1
    ws.cell(row=fila, column=1, value="Por sede")
    encabezados = ["Sede", "Facturas", "Energía (kWh)", "Agua (m³)", "Atípicos", "% sin hallazgos"]
    for j, h in enumerate(encabezados, start=1):
        ws.cell(row=fila + 1, column=j, value=h)
    def stats(nombre, g):
        return (nombre, len(g), g.loc[g["unidad"] == "kWh", "consumo"].sum(),
                g.loc[g["unidad"] == "m³", "consumo"].sum(),
                int((g["estado"] == "ATIPICO_REVISAR").sum()), (g["estado"] == "OK").mean())
    es_csu = base["sede_final"].str.startswith("CSU ")
    por = [stats(sede, g) for sede, g in base[~es_csu].groupby("sede_final")]
    if es_csu.any():       # los CSU se presentan como una sola sede, con sus centros debajo
        por.append(stats("CSU (todos los centros)", base[es_csu]))
    por.sort(key=lambda x: -x[2])
    detalle = []
    for fila_d in por:
        detalle.append((fila_d, True))
        if fila_d[0].startswith("CSU ("):
            hijos = sorted((stats("   " + sede, g) for sede, g in base[es_csu].groupby("sede_final")),
                           key=lambda x: -x[2])
            detalle.extend((h, False) for h in hijos)
    for i, (fila_d, principal) in enumerate(detalle, start=fila + 2):
        for j, v in enumerate(fila_d, start=1):
            c = ws.cell(row=i, column=j, value=float(v) if j > 1 and not isinstance(v, int) else v)
            c.number_format = {2: "#,##0", 3: "#,##0", 4: "#,##0", 5: "#,##0", 6: "0%"}.get(j, "General")
            if principal and fila_d[0].startswith("CSU ("):
                c.font = Font(bold=True)
                c.fill = PatternFill("solid", fgColor=CLARO)
    cabeceras = [(4, 1, 2), (fila + 1, 1, 6)]
    for f, c1, c2 in cabeceras:
        for c in range(c1, c2 + 1):
            celda = ws.cell(row=f, column=c)
            celda.fill, celda.font = PatternFill("solid", fgColor=AZUL), Font(bold=True, color="FFFFFF")
    for f in range(5, 5 + len(indicadores)):
        ws.cell(row=f, column=1).fill = PatternFill("solid", fgColor=CLARO)
        ws.cell(row=f, column=2).fill = PatternFill("solid", fgColor=CLARO)
    ws.cell(row=fila, column=1).font = Font(bold=True, size=12, color=AZUL)
    for col, ancho in zip("ABCDEF", (34, 16, 16, 14, 12, 16)):
        ws.column_dimensions[col].width = ancho


def main():
    ruta_val = rutas.ultimo("validacion_*.xlsx")
    if not ruta_val:
        print("Sin validacion. Ejecute validar_atipicos.py primero.")
        return 1
    libro = pd.read_excel(ruta_val, sheet_name=None)
    if libro["Base"].empty:
        print("ERROR: la validacion no tiene facturas (ninguna con periodo legible). "
              "Nada que exportar; revise los pendientes de lectura.")
        return 1
    base = preparar(libro["Base"])
    if "severidad" not in base.columns:      # cargas pequenas: validacion sin atipicos
        base["severidad"] = None
    atip = base[base["estado"] == "ATIPICO_REVISAR"].copy()
    atip["_o"] = atip["severidad"].map({"ALTA": 0, "MEDIA": 1}).fillna(2)
    atip = atip.sort_values(["_o", "sede_final", "periodo_fin"], ascending=[True, True, False])
    cola = libro.get("ColaRevision", pd.DataFrame())
    por_revisar = base[base["estado"].isin(
        ["SIN_SERIE", "REVISION_BAJA_CONFIANZA", "REVISION_PERIODO_INFERIDO", "REVISION_UNIDAD"])]

    faltantes = pd.DataFrame()
    ruta_al = rutas.ultimo("alertas_*.xlsx")
    if ruta_al:
        hojas = pd.read_excel(ruta_al, sheet_name=None)
        faltantes = hojas.get("Faltantes", pd.DataFrame())

    salida = os.path.join(rutas.SALIDAS, "Consumos_Consolidado.xlsx")
    with pd.ExcelWriter(salida, engine="openpyxl") as w:
        hoja_tabla(w, "Base", base.sort_values(["sede_final", "servicio", "periodo_fin"]))
        hoja_tabla(w, "Atipicos", atip, "Sin atípicos.")
        hoja_tabla(w, "Por revisar", por_revisar, "Sin facturas pendientes de revisión.")
        if cola is not None and not cola.empty:
            cola = cola.rename(columns={"archivo": "Archivo", "motivo": "Motivo", "estado": "Estado"})
            cola.to_excel(w, sheet_name="Pendientes de lectura", index=False)
            dar_formato(w.sheets["Pendientes de lectura"], [50, 50, 20], [None, None, None], len(cola))
        if not faltantes.empty:
            f = faltantes.rename(columns={
                "servicio": "Servicio", "medidor": "Medidor", "tipo": "Tipo", "cadencia": "Cadencia",
                "entre": "Entre", "periodo_esperado": "Periodo esperado", "dias": "Días", "estado": "Estado",
                "detalle": "Detalle"})
            f.to_excel(w, sheet_name="Faltantes", index=False)
            dar_formato(w.sheets["Faltantes"], [12, 24, 20, 12, 26, 16, 8, 16, 50], [None] * 9, len(f))
        resumen(w, base, os.path.basename(ruta_val), len(faltantes))
    print(f"Libro final: {salida}")
    print(f"Hojas: Resumen, Base ({len(base)}), Atipicos ({len(atip)}), Por revisar ({len(por_revisar)}), "
          f"Faltantes ({len(faltantes)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

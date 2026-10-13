"""
Consolida lotes Bogota/CSU en base unificada con dedup (Fase 2 del plan).

- Une los ultimos Excel bogota_*.xlsx y csu_*.xlsx (hojas Energia/Acueducto).
- Normaliza a esquema comun: prestador, servicio, sede, factura, periodo,
  consumo, unidad, valor, fecha_pago, archivo.
- Dedup en 2 niveles: (a) mismo archivo en 2 carpetas; (b) misma
  (factura, prestador). Los duplicados van a la hoja Duplicados.
- Salida: data/outputs/base_unificada_<fecha>.xlsx
Uso: python scripts/consolidar_base.py
"""
import glob
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
from src.utils import rutas  # noqa: E402
SALIDAS = os.path.join(BASE, "data", "outputs")


ultimo = rutas.ultimo   # busca en la carpeta de la etapa (data/outputs/<etapa>/)


def _primero(r, claves):
    """Primer valor no vacio de la fila para las columnas dadas (orden = prioridad)."""
    for clave in claves:
        valor = r.get(clave)
        if valor is None or (not isinstance(valor, str) and pd.isna(valor)):
            continue
        texto = str(valor).strip()
        if texto.endswith(".0") and texto[:-2].isdigit():   # Excel guarda ids como float
            texto = texto[:-2]
        if texto not in ("", "0"):
            return texto
    return None


def _numero(r, claves):
    """Primer valor numerico de la fila para las columnas dadas, o None."""
    for clave in claves:
        valor = pd.to_numeric(r.get(clave), errors="coerce")
        if pd.notna(valor):
            return float(valor)
    return None


# Prioridad de identificadores: factura = No. de factura o DOCUMENTO EQUIVALENTE
# ELECTRONICO No.; cuenta = cuenta / contrato / NIU / cliente segun el prestador.
CLAVES_FACTURA = ["no_factura", "No.FACTURA", "No. FACTURA", "documento_equivalente",
                  "factura_electronica", "documento"]
CLAVES_CUENTA = ["no_cuenta", "cuenta_contrato", "cuenta", "cuenta_poliza", "contrato",
                 "CONTRATO", "No.CUENTA CONTRATO", "No.CUENTA CONTRATO", "niu",
                 "cuenta_ruta", "codigo_interno"]


def normalizar(df: pd.DataFrame, servicio_por_defecto: str) -> pd.DataFrame:
    """Mapea columnas heterogeneas al esquema comun."""
    filas = []
    for _, r in df.iterrows():
        factura = _primero(r, CLAVES_FACTURA)
        consumo = _numero(r, ["consumo_kwh", "CONSUMO Kwh"])
        unidad = "kWh"
        if consumo is None:
            consumo = _numero(r, ["consumo_m3", "CONSUMO M3"])
            unidad = "m3"
        valor = _numero(r, ["valor_factura", "VALOR FACT.", "valor_total", "VALOR TOTAL"])
        # El aseo viaja dentro del recibo (EPM, Enel, Triple A): se separa del servicio.
        aseo = _numero(r, ["valor_aseo", "VALOR ASEO", "RECOLECCION BASURAS"]) or 0.0
        if r.get("PROVEEDOR") == "EPM" and "VALOR ASEO" in r.index and pd.notna(valor):
            valor = valor + aseo   # EPM energia: VALOR FACT. no incluye el aseo
        alumbrado = _numero(r, ["valor_alumbrado"]) or 0.0
        periodo_ini = r.get("periodo_inicio")
        if periodo_ini is None or (isinstance(periodo_ini, float) and pd.isna(periodo_ini)):
            periodo_ini = r.get("PERIODO INICIO")
        periodo_fin = r.get("periodo_fin")
        if periodo_fin is None or (isinstance(periodo_fin, float) and pd.isna(periodo_fin)):
            periodo_fin = r.get("PERIODO FINAL") or r.get("PERIODO FIN")
        ini = pd.to_datetime(periodo_ini, errors="coerce")
        fin = pd.to_datetime(periodo_fin, errors="coerce")
        dias = (fin - ini).days + 1 if pd.notna(ini) and pd.notna(fin) else None
        bimestral = bool((dias is not None and dias > 45)
                         or str(r.get("periodicidad")).lower() == "bimestral"
                         or (pd.notna(r.get("periodo_bimestral"))
                             and str(r.get("periodo_bimestral")).strip() != ""))
        meses = 2 if bimestral else 1
        filas.append({
            "prestador": (r.get("prestador") or r.get("PROVEEDOR")
                          or r.get("COMPAÑÍA") or r.get("COMPANIA")),
            "servicio": r.get("servicio") or servicio_por_defecto,
            "sede": r.get("sede_origen") or r.get("CIUDAD"),
            "cuenta": _primero(r, CLAVES_CUENTA),
            "factura": factura,
            "periodo_inicio": ini,
            "periodo_fin": fin,
            "dias": dias,
            "bimestral": bimestral,
            "consumo": consumo,
            "consumo_mensual": consumo / meses if consumo is not None else None,
            "unidad": unidad,
            "valor": valor,
            "valor_servicio": valor - aseo - alumbrado if valor is not None else None,
            "valor_aseo": aseo,
            "valor_alumbrado": alumbrado,
            "fecha_pago": pd.to_datetime(
                r.get("fecha_pago") or r.get("FECHA DE PAGO"), errors="coerce"),
            "archivo": r.get("archivo_origen") or r.get("ARCHIVO ORIGEN"),
            "direccion": r.get("direccion") or r.get("DIRECCION"),
            "periodo_fuente": r.get("PERIODO FUENTE") or r.get("periodo_fuente"),
        })
    return pd.DataFrame(filas)


def main():
    hojas = []
    for patron in ["bogota_*.xlsx", "csu_*.xlsx", "epm_*.xlsx"]:
        ruta = ultimo(patron)
        if not ruta:
            print(f"AVISO: sin archivos {patron}")
            continue
        print(f"Lote: {os.path.basename(ruta)}")
        libro = pd.read_excel(ruta, sheet_name=None)
        for hoja, servicio in (("Energia", "energia"), ("Acueducto", "acueducto")):
            if hoja in libro:
                hojas.append(normalizar(libro[hoja], servicio))

    base = pd.concat(hojas, ignore_index=True)
    base = base[base["archivo"].notna() & (base["archivo"].astype(str).str.strip() != "")]
    base = base.reset_index(drop=True)
    print(f"Filas totales: {len(base)}")

    base["clave_archivo"] = (base["sede"].astype(str).str.lower().str.strip()
                               + "||" + base["archivo"].astype(str).str.lower()
                               + "||" + base["servicio"].astype(str).str.lower())

    def _en_casa(fila):
        """True si la carpeta contiene el mes del nombre del archivo
        (las carpetas EPM solapan meses; se prefiere la fila 'en casa')."""
        import re as _re
        sede = str(fila["sede"]).upper()
        archivo = str(fila["archivo"]).upper()
        mes_sede = _re.search(r"EPM\s+([A-Z]+)\s+(\d{4})", sede)
        if not mes_sede:
            return True
        return mes_sede.group(1) in archivo and mes_sede.group(2) in archivo

    base["_en_casa"] = base.apply(_en_casa, axis=1)
    base = base.sort_values("_en_casa", ascending=False, kind="stable")
    base = base.reset_index(drop=True)
    dup_archivo = base.duplicated(subset=["clave_archivo"], keep="first")
    con_clave = base["factura"].notna() & (base["factura"].astype(str).str.strip() != "")
    base["clave_factura"] = (base["prestador"].astype(str).str.lower().str.strip()
                               + "|" + base["servicio"].astype(str).str.lower().str.strip()
                               + "|" + base["factura"].astype(str).str.strip())
    dup_factura = (base.duplicated(subset=["clave_factura"], keep="first")
                   & con_clave & ~dup_archivo)

    duplicados = base[dup_archivo | dup_factura].copy()
    duplicados["motivo"] = ["archivo_repetido" if a else "factura_repetida"
                            for a in dup_archivo[duplicados.index]]
    base = base[~(dup_archivo | dup_factura)].copy()
    print(f"Duplicados: {len(duplicados)} "
          f"(archivo: {dup_archivo.sum()}, factura: {dup_factura.sum()})")
    print(f"Base unificada: {len(base)} filas")

    fecha = datetime.now(ZoneInfo("America/Bogota")).strftime("%Y%m%d_%H%M%S")
    salida = rutas.ruta(f"base_unificada_{fecha}.xlsx")
    with pd.ExcelWriter(salida, engine="openpyxl") as writer:
        base.drop(columns=["clave_archivo", "clave_factura", "_en_casa"]).to_excel(
            writer, sheet_name="Base", index=False)
        if not duplicados.empty:
            duplicados.drop(columns=["clave_archivo", "clave_factura", "_en_casa"]).to_excel(
                writer, sheet_name="Duplicados", index=False)
    print(f"Salida: {salida}")


if __name__ == "__main__":
    sys.exit(main())

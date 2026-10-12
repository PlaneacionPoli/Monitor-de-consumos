"""
Prueba control: base generada vs. base manual del mes anterior (DoD Propuesta §12).

Compara facturas EPM de MARZO 2025 (hoja manual) contra la base unificada
por numero de factura: periodo, consumo y valor. Reporta tasa de
coincidencia exacta y diferencias.
Uso: python scripts/prueba_control.py
"""
import glob
import os
import sys

import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANUAL = os.path.join(BASE, "data", "EPM", "ENERGIA 2025.xlsx")
HOJA = "MARZO 2025 "


def main():
    manual = pd.read_excel(MANUAL, sheet_name=HOJA, header=2)
    manual = manual[manual["No.FACTURA"].notna()].copy()
    manual["No.FACTURA"] = manual["No.FACTURA"].astype(str).str.strip()
    print(f"Filas manual {HOJA.strip()}: {len(manual)}")

    ruta_base = sorted(glob.glob(os.path.join(
        BASE, "data", "outputs", "base_unificada_*.xlsx")))[-1]
    base = pd.read_excel(ruta_base, sheet_name="Base")
    auto = base[(base["prestador"] == "EPM") & (base["servicio"] == "energia")].copy()
    auto["factura"] = auto["factura"].astype(str).str.strip()
    print(f"Filas auto EPM energia: {len(auto)}")

    comparadas, exactas, difs = 0, 0, []
    for _, m in manual.iterrows():
        cand = auto[auto["factura"] == m["No.FACTURA"]]
        if cand.empty:
            continue
        a = cand.iloc[0]
        comparadas += 1
        ok_consumo = abs(float(a["consumo"]) - float(m["CONSUMO Kwh"])) < 0.01
        ok_valor = abs(float(a["valor"]) - float(m["VALOR  FACT."])) < 1.0
        ok_periodo = (pd.to_datetime(a["periodo_fin"]).date()
                      == pd.to_datetime(m["PERIODO FINAL"]).date())
        if ok_consumo and ok_valor and ok_periodo:
            exactas += 1
        else:
            difs.append((m["No.FACTURA"], ok_consumo, ok_valor, ok_periodo,
                         a["consumo"], m["CONSUMO Kwh"], a["valor"], m["VALOR  FACT."]))

    print(f"Comparadas: {comparadas}/{len(manual)} | Exactas: {exactas} "
          f"({exactas / comparadas * 100:.1f}%)" if comparadas else "sin cruces")
    faltantes = manual[~manual["No.FACTURA"].isin(
        auto["factura"].tolist())]["No.FACTURA"].tolist()
    print(f"Sin contraparte auto ({len(faltantes)}): {faltantes}")

    print("\n--- ACUEDUCTO (manual NOVIEMBRE 2025) ---")
    manual_ac = pd.read_excel(
        os.path.join(BASE, "data", "EPM", "ACUEDUCTO  2025.xlsx"),
        sheet_name="NOVIEMBRE 2025", header=2)
    manual_ac = manual_ac[manual_ac["No. FACTURA"].notna()].copy()
    manual_ac["No. FACTURA"] = manual_ac["No. FACTURA"].astype(str).str.strip()
    auto_ac = base[(base["prestador"] == "EPM") & (base["servicio"] == "acueducto")].copy()
    auto_ac["factura"] = auto_ac["factura"].astype(str).str.strip()
    print(f"Filas manual: {len(manual_ac)} | Filas auto: {len(auto_ac)}")
    comp, ex = 0, 0
    for _, m in manual_ac.iterrows():
        cand = auto_ac[auto_ac["factura"] == m["No. FACTURA"]]
        if cand.empty:
            continue
        a = cand.iloc[0]
        comp += 1
        ok_per = (pd.to_datetime(a["periodo_fin"]).date()
                  == pd.to_datetime(m["PERIODO FIN"]).date())
        ok_agua = abs(float(a["valor"]) - float(m["VALOR TOTAL"])) < 1.0
        ok_cons = (abs(float(a["consumo"]) - float(m["CONSUMO M3"])) < 0.01
                   if "CONSUMO M3" in manual_ac.columns
                   and pd.notna(m.get("CONSUMO M3")) else None)
        if ok_per and ok_agua and (ok_cons is not False):
            ex += 1
        else:
            print(f"  DIF {m['No. FACTURA']}: periodo={ok_per} valor={ok_agua} "
                  f"consumo={ok_cons} (auto {a['consumo']}/{a['valor']:,.0f} "
                  f"vs manual {m.get('CONSUMO M3')}/{m['VALOR TOTAL']:,.0f})")
    print(f"Comparadas: {comp}/{len(manual_ac)} | Exactas: {ex} "
          f"({ex / comp * 100:.1f}%)" if comp else "sin cruces")
    for d in difs[:15]:
        print(f"  DIF {d[0]}: consumo_ok={d[1]} valor_ok={d[2]} periodo_ok={d[3]} "
              f"(auto {d[4]}/{d[6]:,.0f} vs manual {d[5]}/{d[7]:,.0f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

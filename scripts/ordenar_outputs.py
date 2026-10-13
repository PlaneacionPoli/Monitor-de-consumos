"""
Ordena data/outputs: cada archivo a la carpeta de su etapa y las versiones
anteriores a _historico/ (no se borra nada). Regenera el LEEME.md del directorio.

Uso: python scripts/ordenar_outputs.py
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
from src.utils import rutas  # noqa: E402

LEEME = """# Salidas del Monitor de Consumos

**Empiece por `Consumos_Consolidado.xlsx`**: es el libro final, con hojas en español
(Resumen, Base, Atípicos, Cola de revisión, Faltantes). Se regenera en cada corrida
(`python scripts/exportar_consolidado.py`).

El resto son los pasos intermedios del pipeline, en el orden en que se generan.
En cada carpeta queda solo la versión más reciente; las anteriores están en `_historico/`.

| Carpeta | Qué contiene | Quién la genera |
|---|---|---|
| `01_extraccion/` | `bogota_*`, `csu_*`, `epm_*`: datos extraídos de los PDF, una hoja por servicio y una de pendientes | `procesar_lote_*.py` |
| `02_consolidado/` | `base_unificada_*`: todas las facturas en un esquema común, sin duplicados | `consolidar_base.py` |
| `03_validacion/` | `validacion_*`: la base con estado, severidad y confianza; hojas Base, Atipicos, ColaRevision | `validar_atipicos.py` |
| `04_alertas/` | `alertas_*`: atípicos, posibles facturas faltantes y resumen | `generar_alertas.py` |
| `05_oficial/` | `monitor.db` (almacén con ciclo EN_REVISION → CONFIRMADO → OFICIAL) y `base_oficial_*` (solo lo oficial) | `cargar_almacen.py` |
| `catalogos/` | `catalogo_sedes.csv` (dirección → sede; la columna `sede_confirmada` se edita a mano) e `inventario_pdfs.csv` | `catalogo_sedes.py`, `clasificar_pdfs.py` |
| `control/` | `auditoria.csv` (decisiones de revisión), `medicion_automatizacion.csv`, `accesos_dashboard.csv` (**no compartir ni versionar**) | varios |
| `_historico/` | versiones anteriores de cada etapa, por carpeta | `ordenar_outputs.py` |
| `_legado/` | salidas del diseño original (`Energia_*`, `Acueducto_*`, `facturas_*`); ya no las usa ningún script | — |

Nota: `data/` está excluido del repositorio (contiene facturas y datos reales).
"""


def main():
    r = rutas.ordenar()
    print(f"Movidos a su carpeta: {len(r['movidos'])}")
    print(f"Versiones anteriores archivadas: {r['archivadas']}")
    if r["bloqueados"]:
        print("No se pudieron mover (abiertos en otro programa o ya existían):")
        for n in r["bloqueados"]:
            print(f"  - {n}")
    with open(os.path.join(rutas.SALIDAS, "LEEME.md"), "w", encoding="utf-8") as f:
        f.write(LEEME)
    print("LEEME.md actualizado")
    return 0


if __name__ == "__main__":
    sys.exit(main())

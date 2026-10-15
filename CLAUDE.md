# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Qué es esto

PoliEcoConsumo / "Monitor de Consumos Ambientales": extrae por lote datos de facturas PDF de energía y acueducto (Enel, EAAB, EPM, Afinia, Air-e, Triple A, EmCali, etc.) de las sedes y CSUs del Politécnico Grancolombiano, las consolida, valida atípicos y alimenta un dashboard. Es un **prototipo** (ver `Plan_Primera_Revision.md`, que es la fuente de verdad del alcance, estado y decisiones pendientes; los documentos rectores son los `.docx` de Propuesta y Ficha de Iniciativa). Alcance de la primera revisión: carpetas de `data/raw` Acueducto sedes, Energía sedes, CSUs + `data/EPM`. Gas propano y combustibles están excluidos.

Este directorio es un subproyecto de un workspace de portafolio (ver `../AGENTS.md`): shell PowerShell, rutas con espacios entre comillas, Windows/OneDrive.

## Comandos

```powershell
pip install -r requirements.txt            # Tesseract (con idioma spa) se instala aparte
python scripts/pipeline.py                 # orquesta todo, en orden, midiendo tiempos
python -m pytest tests/ -q                 # suite (59 pruebas; la de Node se omite si no hay node)
python -m pytest tests/test_extractores.py::test_moneda_latina -q   # una prueba
python app/aplicacion.py        # app local unica en Dash (http://localhost:8050): Cargar facturas + Dashboard HTML oficial incrustado (o Iniciar_App.bat)
python scripts/procesar_archivos.py <carpeta|pdf> [--simular|--solo-extraer|--forzar]   # misma carga por consola
python -m src.dashboard.dashboard          # dashboard Dash en http://localhost:8050
python scripts/cargar_almacen.py [--publicar] [--exportar]   # almacen SQLite + compuerta de confirmacion
python scripts/publicar_dashboard.py       # sitio estatico CIFRADO en site/ para GitHub Pages
python scripts/exportar_consolidado.py     # libro final legible: data/outputs/Consumos_Consolidado.xlsx
python scripts/ordenar_outputs.py          # lleva cada salida a su carpeta y archiva versiones anteriores
```

Todos los scripts se ejecutan desde la raíz del proyecto (`python scripts/<x>.py`). Etapas del pipeline, en orden: `clasificar_pdfs` → `procesar_lote_bogota` → `procesar_lote_csu` → `procesar_lote_epm` → `consolidar_base` → `validar_atipicos` → `generar_alertas` → `almacen` → `prueba_control` → `exportar` → `ordenar` → pytest. `medir_automatizacion.py` mide el % de facturas sin revisión. `catalogo_sedes.py` y `verificar_extraccion_bogota.py` son utilidades fuera del pipeline.

## Arquitectura

El flujo real es una **cadena de archivos Excel/CSV en `data/outputs/`** con nombre `<etapa>_<YYYYMMDD_HHMMSS>.xlsx`, organizada en **una carpeta por etapa** (`01_extraccion/`, `02_consolidado/`, `03_validacion/`, `04_alertas/`, `05_oficial/`, más `catalogos/`, `control/`, `_historico/` y `_legado/`; en la raíz solo `Consumos_Consolidado.xlsx` y `LEEME.md`). Las rutas se piden siempre a `src/utils/rutas.py` (`ruta()`, `todos()`, `ultimo()`): ningún script arma rutas de `data/outputs` a mano. Cada etapa lee el *último* archivo (orden alfabético) de la carpeta de la etapa anterior; `scripts/ordenar_outputs.py` (última etapa del pipeline) mueve las versiones anteriores a `_historico/`, sin borrar nada:

`bogota_*` / `csu_*` / `epm_*` (lotes, hojas por servicio + Pendientes) → `base_unificada_*` (esquema común + dedup, hoja Duplicados) → `validacion_*` (columna `estado`/`severidad`/`confianza`; hojas Base, Atipicos, ColaRevision) → `alertas_*`. El dashboard lee el último `validacion_*.xlsx` (con `base_unificada_*` de respaldo) y `catalogo_sedes.csv`. Los archivos se acumulan; no se borran.

- `src/extractor/prestadores_bogota.py` (Enel, EAAB) y `prestadores_csu.py` (un `extraer_<prestador>` por formato de factura): funciones puras `(texto, nombre_archivo) -> dict` con regex por formato real. Se escribe un extractor nuevo por prestador y se enruta en el script de lote correspondiente (la detección de prestador es por palabras clave del texto).
- `src/processor/batch_epm.py`: EPM es una factura unificada (energía+acueducto+aseo) que se separa en filas por servicio; el periodo ISO se completa con la fecha de emisión del *cuerpo* de la factura (`resolver_periodo_epm`); solo si falta se usa la carpeta (mes de *recepción*) y la fila queda `periodo_fuente=carpeta` → `REVISION_PERIODO_INFERIDO`.
- `src/ocr/ocr_engine.py`: texto con PyMuPDF (`fitz`) para PDFs digitales; Tesseract solo cuando el PDF es imagen (<50 caracteres). Casi todo el corpus es digital (801/803).
- `src/utils/auditoria.py`: `registrar_revision` anexa a `control/auditoria.csv` (decisiones restringidas a APROBADO/CORREGIDO/RECHAZADO).
- `src/processor/validacion.py` (reglas puras, usadas por `scripts/validar_atipicos.py`) y `src/processor/faltantes.py` (cadencia mensual/bimensual inferida por medidor; corte por prestador). Catálogo de reglas con su prueba en `docs/Reglas_de_Negocio.md`.
- `src/storage/repositorio.py`: SQLite en `data/outputs/05_oficial/monitor.db` con ciclo `EN_REVISION → CONFIRMADO → OFICIAL`; solo lo OFICIAL se exporta; historial de revisiones con cadena de hash. Modelo en `docs/Modelo_de_Datos.md`.
- `src/dashboard_estatico/` + `scripts/publicar_dashboard.py`: dashboard HTML/JS (secciones Ejecutiva y Operativa, ECharts local en `vendor/`) cuyos datos se publican cifrados; ver `docs/Dashboard_GitHub_Pages.md`. No es el mismo dashboard que `src/dashboard/dashboard.py` (Dash).
- `scripts/validar_atipicos.py`: regla de >20% vs. mismo periodo del año anterior; sin 12 meses de histórico usa mediana de los 3 periodos previos como suplente (marcado). Confianza sobre periodo/consumo/valor; fila incompleta → `REVISION_BAJA_CONFIANZA`, nunca se rechaza.
- Reglas de negocio a respetar: el periodo sale del cuerpo de la factura (nunca de la fecha de recepción); factura sin número → "N factura no identificado" sin rechazar; Calle 84 factura bimensual (no es "faltante"); la clave de dedup incluye servicio.

- **Carga incremental (app)**: `src/processor/extraccion.py` detecta el prestador por contenido (no por carpeta) y `carga.py` registra cada PDF por hash en `control/registro_extracciones.db`; solo extrae lo nuevo o lo de una `VERSION_EXTRACTORES` anterior (subirla al cambiar un extractor). `exportar_extraccion` vuelca todo a `01_extraccion/extraccion_*.xlsx`, que `consolidar_base`/`validar_atipicos` prefieren sobre los `bogota_/csu_/epm_` sueltos. `actualizacion.py` encadena las etapas posteriores (incluye `publicar_dashboard.py` y copia `site/` a `app/static/dashboard/`, que la app Dash sirve en /sitio/ y muestra en la pagina Dashboard; el dashboard oficial es el HTML de `site/`, el Dash de `src/dashboard/` es el diseno original sin uso). El dashboard HTML trae un mapa de sedes (ECharts + `vendor/colombia.geojson`, contorno DANE; coordenadas por sede en `COORDS_SEDES` de `app.js`, a nivel de calle en Bogota). `exportar_extraccion` suma los lotes `bogota_/csu_/epm_` historicos al libro acumulado para no perder lo extraido antes de la app. Facturas de aseo (Emvarias) quedan `OMITIDA` (fuera de alcance).

## Ojo con

- **Código vs. documentación**: `README.md`, `config/config.yaml` y los ADRs describen un stack (FastAPI, Dagster, MySQL, Keycloak, watcher automático, plantillas YAML) que **no está implementado**: no hay imports de eso en `src/`. `src/extractor/field_extractor.py` (regex genéricos), `src/watcher/file_watcher.py` y `src/processor/excel_exporter.py` son del diseño original y no producen la salida real (el watcher no exporta). El esquema real de salida (26 cols heredadas vs. 13–15 de `config.yaml`) es una decisión abierta.
- `data/raw`, `data/EPM` y `data/outputs` contienen facturas reales y salidas; el `.gitignore` los excluye. Nunca versionar `config/accesos_dashboard.txt` ni `accesos_dashboard.csv` (correos y contraseñas del dashboard). `site/` sí se versiona: solo lleva el sitio y `data.enc.json` cifrado.
- Los 272 atípicos actuales usan la mediana de 3 periodos (ninguna serie tiene 12 meses): la rama anual de la regla está probada pero no se ha ejercido con datos reales.
- Los scripts usan `zoneinfo`/timestamps en hora de Bogotá y rutas relativas a `BASE`; no dependen del cwd para ubicar datos pero sí para `sys.path`/subprocesos del pipeline.
- Estilo: código y comentarios en español, docstring de módulo con propósito y "Uso:".

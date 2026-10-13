# Plan de Primera Revisión — Monitor de Consumos Ambientales (OCR Facturas)

> Decisión de alcance vigente: primera revisión cubre **carpetas 5, 6 y 7** (Acueducto sedes,
> Energía sedes, CSUs) + EPM-Medellín existente. **Fuera:** gas propano, combustibles y
> archivos zip (duplicados de facturas ya descomprimidas).
> Documentos rectores: *Propuesta – Monitor de Consumos Ambientales* (2026-09-01, prevalece) y
> *Ficha de Iniciativa* (2026-07-23). Evaluación base: 2026-10-06 + adenda `data/raw`.

---

## 1. Universo de trabajo

| Grupo | Volumen único | Formato verificado | Prestador / sede |
|---|---|---|---|
| 5. Recibos Acueducto sedes | 25 PDF | Digital con texto (7.065 chars/muestra) | Acueducto Bogotá: Campus (8), City Campus (12, 3 cuentas), Calle 84 (5, bimensual) |
| 6. RecibOS Energía sedes | 42 PDF | Digital con texto (5.273–7.731 chars/muestra) | Enel Bogotá: Campus (13), City (14), Calle 84 (15) |
| 7. Servicios públicos CSUs | 102 PDF | Digital con texto (6.722–9.575 chars/muestra) | 10 CSU: Zipaquirá, Chía, Soacha, Bosa, Portal 80, Cartagena, Barranquilla, Cali (EmCali), Bello (EPM), Villavicencio |
| EPM Medellín (base existente) | 634 PDF | Digital con texto | EPM unificada (agua + energía + aseo) |
| **Total primera revisión** | **~803 PDF** | — | — |
| Excluido fase posterior | 52 PDF + 1 xlsx (gas/combustibles) | Gas La Banca = imagen escaneada (0 chars, requiere OCR real de baja calidad verificada) | Decisión SGA pendiente: ¿gas/combustible entra al Monitor? |

## 2. Alcance funcional exigido (Propuesta)

1. Ingesta de PDF por carpeta compartida (correo: fase posterior).
2. Extracción: consumo (m³/kWh), valor facturado ($), **periodo de consumo del cuerpo
   de la factura (nunca fecha de recepción)**, No. factura, sede; con confianza por campo.
3. Separación EPM unificada en 3 componentes (Bello + EPM Medellín).
4. Validación automática: unidad↔componente; variación **>20% vs. mismo periodo año
   anterior** (requiere histórico ≥12 meses); confianza <90% → revisión obligatoria;
   No. factura siempre (ausente → "N factura no identificado", sin rechazar).
5. Consolidación a base unificada solo tras confirmación del Analista SGA.
6. Indicadores: kWh/m², m³/persona, huella de carbono, costo de sobreconsumo
   (requiere datos maestros de Infraestructura: m², población por sede).
7. Alertas de factura faltante (respetando **Calle 84 bimensual**) y consumo atípico,
   con SLA y escalamiento (pendiente definir con SGA).
8. Revisión humana con auditoría total (quién/cuándo/antes/después).
9. Salidas: base Excel unificada mensual + tablero HTML + insumos GreenMetric/GEI.

Metas: precisión ≥98% (mín. 95%) · auto sin revisión ≥80% (mín. 60%) ·
detección atípicos <1 día · tiempo ≤2 h/mes.

## 3. Estado actual vs. esperado (resumen)

| Dimensión | Estado | Cumpl. |
|---|---|---|
| Extracción EPM (`src/processor/batch_epm.py`) | Funciona parcial: 59 filas probadas; periodo sin año; fecha pago/contrato vacíos | 45% |
| Extracción Enel/Acueducto/CSU | Inexistente (regex genéricos de `field_extractor.py` incompatibles con formatos reales) | 0% |
| Watcher → Excel (`src/watcher/file_watcher.py:159-199`) | Roto: retorna dict en memoria, nunca exporta | 0% |
| Validación 20% / confianza / dedup | Inexistente (`validacion:` en yaml sin código) | 0% |
| Revisión humana + auditoría | Inexistente | 0% |
| Histórico 12 m | Sin cargar (energía Bogotá trae ~12 meses por sede: insumo listo) | 10% |
| Tablero (`src/dashboard/dashboard.py`) | Existe, KPIs genéricos, alerta "+22%" quemada en código | 30% |
| Stack declarado (FastAPI/Dagster/MySQL/Keycloak) | Solo en `requirements.txt`/README/ADRs; 0 imports en `src/` | 0% |
| Pruebas (`tests/`, `scripts/` vacíos) | Inexistente | 0% |
| Esquema salida | Deriva: xlsx de 26 cols ≠ `config.yaml` (13–15 cols); ningún código genera el de 26 | Brecha documental |

Madurez: **prototipo / prueba funcional parcial** (nivel 2–3 de 8). No piloto, no producción.

## 4. Roadmap primera revisión

### Fase 0 — Decisiones previas (con SGA/TI, 1 semana)
- [ ] Tratamiento de alumbrado público y aseo Emvarias en EPM (¿componente propio o se ignoran? $28.000/factura en muestra real).
- [ ] Esquema de salida único: ¿26 columnas heredadas o 13–15 de `config.yaml`?
- [ ] SLA de alertas: tiempo máximo de respuesta + escalamiento si no hay respuesta.
- [ ] Datos maestros: m² y población por sede (con Infraestructura).
- [ ] Validación TI de restricción "no cloud no autorizado" (el diseño local la favorece).
- [ ] Recortar README/ADRs a la realidad o calendarizar stack faltante.

### Fase 1 — Saneamiento y base (1–2 sem)
- [x] Clasificación masiva digital vs. imagen: `scripts/clasificar_pdfs.py` →
  `data/outputs/catalogos/inventario_pdfs.csv` (2026-10-06: **803 PDF, 801 DIGITAL, 2 IMAGEN** —
  ambas Enel City Campus DIC-2025 y FEB-2026, casos OCR reales dentro del alcance).
- [x] Extractor Enel Bogotá (`src/extractor/prestadores_bogota.py:extraer_enel`):
  12/12 campos en muestra Campus ENE-2026 (factura, periodo ISO, valor, pago,
  contrato, referencia, identificación, dirección, NIT, consumo kWh 50.967,38).
- [x] Lote EPM-Medellín (`scripts/procesar_lote_epm.py`, 2026-10-07): **634/634
  PDF, 0 fallos** → 571 energía + 60 acueducto. Periodo ISO inferido de la
  carpeta (`normalizar_periodo_epm` en `batch_epm.py`). Corrección 2026-10-07:
  las carpetas NO solapan (carpeta = mes de recepción, archivo = mes de
  facturación); los 58 "duplicados" EPM eran pares energía/acueducto del mismo
  PDF — la clave dedup ahora incluye servicio. 94 facturas traen dirección
  "Pendiente Planeación" (dato EPM, no error) → estado SIN_SERIE.
- [x] Prueba control acueducto (2026-10-07): manual NOVIEMBRE 2025 →
  **5/5 exactas (100%)** en periodo/valor; las 54 filas manuales en cero no
  tienen servicio (correcto: sin fila auto).
- [x] Base + validación global: **738 filas únicas, 715 evaluables, 243
  atípicos con severidad** (ALTA >50 %). Tasa alta por series de 11 meses con
  suplente mediana-3 (la regla anual exige 12+ meses); la cola se triagea
  por severidad. Salidas: `base_unificada_*.xlsx`, `validacion_*.xlsx`
  (Base + Atipicos + ColaRevision).
- [x] Dashboard con datos reales (`src/dashboard/dashboard.py`, 2026-10-07):
  lee `validacion_*.xlsx` (base + estado/severidad): 715 filas, KPIs y
  tendencia calculados sobre datos reales; alerta quemada "+22%" reemplazada
  por panel dinámico (243 atípicos, 124 ALTA). Filtros por sede.group_by
  pendientes (las sedes no son Bogotá/Medellín).
- [x] Motor de alertas (`scripts/generar_alertas.py`, 2026-10-07):
  `alertas_*.xlsx` (Atipicos + Faltantes + Resumen). Faltantes por huecos
  >62 días: **0** en este dataset (series continuas, incluye bimensuales).
- [x] Auditoría (`src/utils/auditoria.py`, 2026-10-07): `registrar_revision`
  anexa quién/cuándo/original/nuevo/decisión a `auditoria.csv`; decisiones
  restringidas a APROBADO/CORREGIDO/RECHAZADO.
- [x] Prueba control (`scripts/prueba_control.py`, 2026-10-07): base auto vs.
  hoja manual MARZO 2025 → **50/50 exactas (100.0%)** en periodo/consumo/valor,
  sobre la meta 98%. Hallazgos corregidos: valor EPM incluye alumbrado
  (+$28.000 constante), consumos con miles ("15.180 kWh") y bloque alterno
  "Energía 22 kwh". 5 facturas manuales sin PDF en `data/EPM` (hueco de
  fuente, no de extracción).
- [x] Confianza de extracción (`validar_atipicos.py`, 2026-10-07): columna
  `confianza` sobre los 3 campos clave del DoD (periodo/consumo/valor);
  fila incompleta → REVISION_BAJA_CONFIANZA sin rechazar (regla factura
  ausente). Resultado: **8/773 en revisión, todas Air-e sin consumo**
  (brecha visual ya registrada). Distribución: 399 OK, 272 atípicos,
  94 SIN_SERIE, 8 baja confianza, 1 pendiente manual.
- [x] Suite: **22/22 pruebas pasan**.
- [x] Catálogo sede←dirección (`scripts/catalogo_sedes.py`, 2026-10-07):
  `catalogo_sedes.csv` con 64 direcciones: **63 mapeadas** (carpeta primero,
  reglas por texto después; 2 correcciones aplicadas: KR 7 es Soacha no
  Portal 80, "Pendiente Planeación" queda SIN_MAPEO) + columna
  `sede_confirmada` vacía para validación del Analista SGA.

## 6. Estado DoD (Propuesta §12) tras la primera revisión

| Criterio DoD | Estado | Evidencia |
|---|---|---|
| ≥1 factura real por prestador activo | ✅ 11 prestadores/formatos | Enel ×3 formatos, EAAB, EPM, Afinia, Aguas Cartagena, Villavicencio, Zipaquirá, Triple A, Air-e, EmCali |
| Precisión ≥95% en consumo/periodo/valor | ✅ 100.0% (50/50) | `scripts/prueba_control.py` vs. base manual MARZO 2025 |
| Validación atípico 20% funcional | ✅ operativa | `scripts/validar_atipicos.py` + severidad; anual al completar 12 m |
| Base generada == base manual | ✅ mes control | prueba control; 5 facturas sin PDF en origen (hueco de fuente) |
| Lote autónomo Analista <2 h sin TI | ✅ 0:02:36 medido | `scripts/pipeline.py` (9 etapas, corrido 2026-10-07: clasificar 1:03 + lotes 1:10 + resto 0:23); falta corrida con el Analista |
| Tablero correcto mes prueba | ✅ datos reales | dashboard lee `validacion_*.xlsx`; alerta dinámica |

Pendiente no-técnico (Fase 0): SLA/escalamiento, maestros de sede (m², población),
validación TI de restricción cloud, KPIs per cápita/carbono y export GreenMetric/GEI.

## 7. Roadmap restante (detalle original en §§1–5)

### Fase 2 — Validación y control humano (2–4 sem)
- [ ] Regla atípicos >20% vs. histórico + calendario por sede (incluye bimensual Calle 84).
- [ ] Confianza por campo + umbral 90% + cola de revisión del Analista SGA con aprobación.
- [ ] Deduplicación (No. factura + proveedor) + fallback "N factura no identificado".
- [ ] Catálogo sede←dirección; log de auditoría de ediciones.
- [ ] Plantillas por prestador conectadas a `config.yaml` (hoy decorativo): Enel, Acueducto-Bogotá, EPM, EmCali + 1 CSU regional.

### Fase 3 — Calidad y DoD (2 sem)
- [ ] Protocolo de medición: precisión en consumo/periodo/valor vs. PDF original.
- [ ] Prueba control: Excel generado == base manual del mes anterior.
- [ ] DoD: ≥1 factura real por prestador (Enel, Acueducto, EPM, EmCali/Cartagena), precisión ≥95%, validación 20% funcional, lote autónomo Analista <2 h, tablero correcto del mes prueba.
- [ ] Suite mínima de pruebas en `tests/` (regex por prestador, validación, export).

### Fase 4 — Operación (2–3 sem)
- [ ] Ingesta por carpeta compartida + protocolo de envío con fecha límite (Gestión Adm. Bogotá / Coord. Medellín).
- [ ] Alertas faltantes/atípicos operativas + medición tiempo ≤2 h/mes y detección <1 día.
- [ ] Tablero validado + export GreenMetric/GEI.

### Fase 3B — Dashboard profesional y alertas (etapa explícita)
- [x] Dashboard lee datos reales (`validacion_*.xlsx`, 715 filas).
- [x] Alerta quemada "+22%" reemplazada por panel dinámico (atípicos/ALTA).
- [x] Motor de alertas (`alertas_*.xlsx`: Atipicos + Faltantes + Resumen).
- [x] Filtros por sede conectados al `catalogo_sedes.csv` (2026-10-07): dropdown
  de 13 sedes; serie EAAB recuperada (titular con fecha MMM/DD/AAAA).
- [ ] KPIs ambientales (kWh/m², m³/persona, huella) — bloqueado por maestros de sede (Fase 0).
- [ ] KPIs ambientales (kWh/m², m³/persona, huella) — bloqueado por maestros de sede (Fase 0).
- [ ] Validación del tablero del mes prueba con el Coordinador SGA.
- [ ] Export GreenMetric/GEI — bloqueado por Fase 0.

### Fase posterior (fuera de esta revisión)
Gas propano (OCR dedicado + revisión casi total), combustibles, correo como ingesta,
stack FastAPI/Dagster/MySQL/Keycloak (si se justifica), IoT y Propuestas 2–3 del canvas.

## 5. Criterios de aceptación de la primera revisión

1. DoD de la Propuesta §12 cumplido para Enel + Acueducto-Bogotá + EPM + 1 CSU regional.
2. Precisión medida ≥95% (meta 98%) en los 3 campos clave contra PDF original.
3. Cero ediciones sin registro de auditoría; ninguna fila marcada entra a la base oficial sin confirmación.
4. Calle 84 bimensual no genera falsas alertas de faltante.
5. Prueba control superada (Excel == base manual del mes anterior).

## 6. Riesgos principales

- Dato no validado propagado a GreenMetric/GEI (impacto 5/5 declarado en canvas).
- Cambio de formato de prestador sin aviso rompe regex (probabilidad alta, 8 formatos).
- Dependencia de terceros sin protocolo de envío ni fechas límite.
- Valores $ contractuales en xlsx locales sin control de acceso (validar con TI).
- Iniciativa sin aprobación formal (Ficha: sponsor/fechas/presupuesto "por definir").

## 7. Registro de decisiones

| Fecha | Decisión | Efecto |
|---|---|---|
| 2026-10-06 | Primera revisión = carpetas 5, 6, 7 + EPM | Gas/combustibles a fase posterior; métricas DoD solo sobre ~803 PDF |
| 2026-10-06 | Zip omitidos (duplicados) | Sin tarea de descompresión/dedup; universo = PDF únicos |
| Pendiente | §4 Fase 0 (6 decisiones SGA/TI) | Bloquean diseño de validación y esquema de salida |

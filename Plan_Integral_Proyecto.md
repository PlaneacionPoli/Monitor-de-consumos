# Plan Integral del Proyecto — Monitor de Consumos Ambientales

**Versión:** 1.0 · **Fecha base:** 2026-10-07
**Insumo:** `Auditoria_Requerimientos_Plan.md` (referenciada como **AUD**). El prompt nombraba `Plan_Primera_Revision_Auditoria.md`, que no existe; se usó la auditoría vigente.
**Trazabilidad:** hallazgo (`H1…H10`) → requerimiento (`REQ-*`, catálogo en AUD §2) → actividad (`F1-*`, `F2-*`) → entregable (`E1-*`, `E2-*`) → criterio de aceptación (§11). Lo que no viene de la auditoría se marca **[Mejora propuesta]**.
**Sin fechas:** las fuentes no dan duración. Se usan secuencia, dependencias, prioridad y esfuerzo relativo (S / M / L).

**Roles usados** (los nombres solo existen en la Ficha; el resto está por asignar):
`LÍDER` Juan Carlos Castro (Líder SGA, Director del Proyecto) · `SPONSOR` Camilo Coronel · `SGA-A` Analista SGA · `SGA-C` Coordinador SGA · `TI` Gerencia de TI · `INFRA` Infraestructura/Servicios Generales · `GAB` Gestión Administrativa Bogotá · `CAM` Coordinación Administrativa Medellín · `JUR` Jurídica · `DEV` equipo de desarrollo (por asignar).

---

## 1. Resumen ejecutivo

**Estado actual.** Hay un prototipo funcional de extracción: 11 formatos de prestador, 803 PDF procesados, base unificada, validación de atípicos, alertas en Excel, tablero Dash y 22 pruebas unitarias. Cubre el núcleo técnico, pero AUD muestra que **el 59% de los requerimientos está solo parcialmente cubierto y el 29% ausente**, y que varios "✅" del DoD no están demostrados (H5, H6). Hay defectos reales: el detector de faltantes no detecta un mes faltante (H1), la auditoría no está conectada (H3), se consolida antes de confirmar (H4) y la "confianza" no es la de OCR (H2).

**Estrategia.** Dos fases separadas por la regla del prompt: *¿se puede hacer correctamente con lo que hay hoy?*. Los PDF, los Excel de EPM, el código y los roles definidos ya están disponibles. Faltan los datos maestros, los históricos en Excel, la metodología GEI, los accesos de TI y las decisiones de gobierno. Por eso **casi todo el trabajo de construcción cabe en la Fase 1**, y la Fase 2 queda reservada a integrar, calibrar y validar con esas fuentes.

**Ejecutable hoy (Fase 1, 63 actividades):** corregir H1–H8; separar base "en revisión" de "oficial" con compuerta de confirmación; módulo de revisión con auditoría; modelo de datos y almacenamiento; motor de indicadores parametrizable (con datos simulados); notificaciones desacopladas; roles y seguridad base; prototipo de tablero por rol; protocolo de precisión y su primera medición sobre los PDF disponibles; documentación operativa en borrador.

**Condicionado (Fase 2, 18 actividades):** cargar maestros e históricos, calibrar el umbral de confianza con muestra verificada, integrar la ingesta y el canal de notificación reales, exportar en el formato oficial GreenMetric/GEI, correr el piloto cronometrado con el Analista, hacer UAT con SGA/Medellín y las validaciones de TI y Jurídica.

**Riesgos principales.** (1) Las decisiones de gobierno sin responsable ni fecha congelan la Fase 2. (2) Sin los 12 meses de histórico, el % sin revisión probablemente no alcance el mínimo de 60% (≈52% hoy). (3) Un cambio de formato de prestador rompe un extractor sin que nadie lo note. (4) Un dato no confirmado llega a GreenMetric/GEI (impacto 5/5).

---

## 2. Principio de división Fase 1 / Fase 2

Cada actividad se clasificó con una sola pregunta: **¿hay hoy información, archivos y decisiones suficientes para hacerla correctamente?**

| Clase | Criterio | Qué hacemos |
|---|---|---|
| 🟢 F1 ejecutable | Todo lo necesario está disponible. | Va a Fase 1 completa. |
| 🟡 F1 parcial | Se puede construir con un contrato, parámetro o dato simulado; la validación real depende de algo ausente. | Se construye ahora. En Fase 2 queda **solo** el tramo bloqueado, con su propio ID. |
| 🔴 F2 bloqueada | Requiere fuente, acceso, validación de un tercero o dato real que no existe hoy. | Va a Fase 2 con criterio de entrada. |
| 🔵 DEC / DEP | Es una decisión, acceso o definición, no trabajo técnico. | Va a §14 y a la matriz de dependencias, con responsable y qué bloquea. |

**Reglas aplicadas:**
- Un dato simulado se acepta solo cuando no condiciona una decisión que dependa del dato real. Todo lo calculado con simulados se marca *"validar con datos reales"*.
- Lo que depende de una decisión pendiente se construye **parametrizable** (p. ej. aseo en kg o $, esquema de salida, canal de notificación). La decisión se aplica después sin reescribir.
- Donde AUD no da información suficiente para definir una actividad, se indica expresamente (p. ej. fórmula de costo de sobreconsumo, formato oficial GreenMetric/GEI).

---

## 3. Fase 1 — Plan ejecutable actualmente

### 3.1 Objetivo y alcance

**Objetivo.** Llevar el prototipo a una solución base **correcta, segura, trazable y probada** con los recursos actuales, y dejar un paquete claro de entrada a la integración con datos reales.

**Alcance.** Corrección de los defectos H1–H8; diseño completo (funcional, arquitectura, datos, seguridad, UX); construcción de todo lo independiente de fuentes pendientes; calidad; documentación operativa en borrador; identificación de lo que Fase 2 necesita.

**Fuera de Fase 1:** integración con fuentes aún no entregadas, calibración con datos reales pendientes, validaciones de terceros, puesta en producción. Fuera del proyecto: gas propano/combustibles, IoT, Propuestas 2–3 (AUD REQ-GOB-004), salvo que **DEC-01** lo cambie.

### 3.2 Actividades

Columnas: *Esf.* = esfuerzo relativo. *Clase* = 🟢 o 🟡. Estado: **P** pendiente · **Pa** parcial (existe prototipo) · **H** ya hecho (se conserva).

#### Gestión (GES)

| ID | Actividad | Req. origen | Dep. | Resp. | Prio. | Clase | Esf. | Estado | Entregable |
|---|---|---|---|---|---|---|---|---|---|
| F1-G01 | Charter de alcance v1: objetivos, entregables, in/out de alcance, DoD corregido. Registra las contradicciones de las fuentes (kg vs $, CSU fuera de Bogotá, gas/combustibles) como decisiones abiertas. | GOB-004, D-005, H10; revisar casillas F§1 (GOB-005) | — | LÍDER + DEV | P0 | 🟢 | S | P | E1-01 |
| F1-G02 | Matriz RACI con los roles de las fuentes. Nombres sin asignar quedan "por asignar". | GOB-001 | — | LÍDER | P1 | 🟡 | S | P | E1-01 |
| F1-G03 | Sanear `Plan_Primera_Revision.md`: numeración, duplicados, sincronizar Fase 1/2, refrescar §3, corregir cifras (AUD §5). | AUD §5 | — | DEV | P1 | 🟢 | S | P | E1-01 |
| F1-G04 | Paquete de aprobación: estructura de presupuesto por los 6 rubros de F§8 (montos vacíos), solicitud de conceptos a JUR/TI/Talento Humano/GEV y fechas. | GOB-001, GOB-002 | DEC-11 | LÍDER | P1 | 🟡 | S | P | E1-02 |
| F1-G05 | Registro de riesgos y decisiones; tablero de trazabilidad vivo (esta matriz como CSV) y script de indicadores de avance (§13). | OPS-004, NF-006 | — | DEV | P1 | 🟢 | M | P | E1-02 |

#### Funcional (FUN)

| ID | Actividad | Req. origen | Dep. | Resp. | Prio. | Clase | Esf. | Estado | Entregable |
|---|---|---|---|---|---|---|---|---|---|
| F1-F01 | Casos de uso y flujos. Principal: lote mensual. Alternos: PDF imagen, factura sin nº, duplicado, atípico, bimensual, cambio de formato, factura que no llega. | F-001…F-016 | — | DEV + SGA-A | P0 | 🟢 | M | P | E1-03 |
| F1-F02 | Catálogo de reglas de negocio R-01…R-n con ID, condición, acción y prueba asociada (P§9). | F-003, F-006…F-009, F-013, F-015 | — | DEV | P0 | 🟢 | S | H | E1-03 |
| F1-F03 | Matriz de roles y permisos: SGA-A, SGA-C, CAM (solo su sede), Dirección (solo lectura), TI (admin). GAB sin acceso. | SEG-002 | — | DEV | P1 | 🟢 | S | P | E1-03 |
| F1-F04 | Requisitos no funcionales medibles: cada meta de P§7 con método de medición. | NF-001…NF-007 | — | DEV | P1 | 🟢 | S | P | E1-03 |

#### Datos (DAT)

| ID | Actividad | Req. origen | Dep. | Resp. | Prio. | Clase | Esf. | Estado | Entregable |
|---|---|---|---|---|---|---|---|---|---|
| F1-D01 | Modelo conceptual y lógico: Sede, Medidor/Cuenta, Prestador, Componente, Factura, Registro de consumo, Lote, Hallazgo, Revisión, Alerta, MaestroSede (m², población, vigencia), FactorEmisión, Usuario/Rol. Se separa **definitivo** de **pendiente de validar** (ver §3.5). | D-001, D-003, F-010, F-011 | — | DEV | P0 | 🟢 | M | P | E1-05 |
| F1-D02 | Diccionario de datos y **esquema de salida canónico** derivado de P§6, con mapeo desde las 26 columnas heredadas y las 13–15 de `config.yaml`. La elección final del esquema es DEC-02. | D-003, H (AUD §5.7) | DEC-02 (solo para cerrar) | DEV | P0 | 🟡 | M | P | E1-05 |
| F1-D03 | Almacenamiento local con migraciones y capa de repositorio, con **estados de ciclo de vida** de cada fila: `EXTRAIDO → EN_REVISION → CONFIRMADO → OFICIAL / RECHAZADO`. Carga inicial de las salidas existentes como datos de desarrollo. **[Mejora propuesta]**: SQLite por ser local, sin servidor y compatible con la restricción "no cloud"; la capa de repositorio permite cambiarlo si TI decide otra cosa (DEC-05). | F-010, SEG-001, D-007, H4 | — | DEV | P0 | 🟢 | L | H | E1-06 |
| F1-D04 | Reglas de calidad de datos como validaciones de esquema: obligatorios, tipos, rangos, unidades válidas por componente, unicidad. | F-006, F-009, D-003 | F1-D01 | DEV | P1 | 🟢 | M | P | E1-05 |
| F1-D05 | Catálogo de sedes: formalizar el `catalogo_sedes.csv` (63/64) como tabla maestra con ciudad, prestador y medidor. La columna `sede_confirmada` se completa en F2. | D-006, D-003 | — | DEV | P1 | 🟡 | S | Pa | E1-05 |
| F1-D06 | Calendario de periodicidad por medidor, **inferido** del histórico disponible (mensual / bimensual). Alimenta el detector de faltantes. La confirmación del SGA es F2-05. | F-013, F-007 | F1-D05 | DEV | P0 | 🟡 | M | P | E1-05 |
| F1-D07 | Histórico desde los PDF ya procesados (p. ej. energía Bogotá, ≈12 meses por sede) y medición de qué medidores ya tienen 12 meses y cuáles no. | D-002, F-007 | — | DEV | P1 | 🟡 | S | Pa | E1-13 |
| F1-D08 | Reglas de retención y versión "oficial": manifiesto por corrida (`run_id`), fin de la selección del "último archivo por orden alfabético". | D-007 | F1-D03 | DEV | P1 | 🟢 | M | P | E1-06 |

#### Arquitectura (ARQ)

| ID | Actividad | Req. origen | Dep. | Resp. | Prio. | Clase | Esf. | Estado | Entregable |
|---|---|---|---|---|---|---|---|---|---|
| F1-A01 | Arquitectura objetivo (§9) y ADRs vigentes. Se declara qué se adopta y qué no. | SEG-001, NF-008, ARQ-001 | — | DEV | P0 | 🟢 | M | P | E1-04 |
| F1-A02 | Contratos de integración (campos, formato, errores, reintento) para: ingesta, notificación, maestros de sede, factores de emisión, export GreenMetric/GEI. La implementación real es F2. | F-001, INT-001…003, D-001 | — | DEV | P0 | 🟡 | M | P | E1-04 |
| F1-A03 | Alinear `README.md`, `config.yaml` y ADRs con la realidad: eliminar o marcar como "no adoptado" FastAPI, Dagster, MySQL, Keycloak y el watcher roto. | AUD §5.7, H (README) | — | DEV | P1 | 🟢 | S | P | E1-04 |
| F1-A04 | Análisis de fallos de extracción sobre los PDF disponibles (p. ej. Air-e sin consumo, 8 filas) y criterio escrito para decidir si hace falta IA más allá de OCR y reglas. La decisión es DEC-04. | TEC-001 | — | DEV | P1 | 🟡 | M | P | E1-04 |

#### Desarrollo (DEV) y Calidad de datos

| ID | Actividad | Req. origen | Dep. | Resp. | Prio. | Clase | Esf. | Estado | Entregable |
|---|---|---|---|---|---|---|---|---|---|
| F1-V01 | **Detector de faltantes por calendario esperado**: periodo esperado por medidor vs. fecha de corte del lote. Prueba con serie mensual a la que se quita un mes, y con serie bimensual completa. | F-013, H1 | F1-D06 | DEV | P0 | 🟢 | M | H | E1-07 |
| F1-V02 | **Confianza por campo**: para PDF imagen, la confianza de Tesseract; para PDF digital, puntaje por validaciones cruzadas (formato, coherencia con desglose). Umbral 90% parametrizable. La calibración con muestra verificada es F2-06. | F-004, F-015, H2 | — | DEV | P0 | 🟡 | L | P | E1-07 |
| F1-V03 | Validación unidad↔componente (m³ agua, kWh energía, $/kg aseo). | F-006 | F1-D04 | DEV | P1 | 🟢 | S | H | E1-07 |
| F1-V04 | Etiqueta literal "N° factura no identificado" y control de duplicados por clave (factura, prestador, servicio). | F-008, F-009 | F1-D04 | DEV | P1 | 🟢 | S | H | E1-07 |
| F1-V05 | **Compuerta de confirmación**: la base oficial se alimenta solo de filas `CONFIRMADO`. Las marcadas (atípicas, baja confianza, SIN_SERIE) esperan decisión. | F-010, F-015, H4 | F1-D03 | DEV | P0 | 🟢 | M | H | E1-06 |
| F1-V06 | **Módulo de revisión**: lista la cola, muestra valor original, evidencia (archivo y página) y acepta APROBADO / CORREGIDO / RECHAZADO. Cada decisión llama a la auditoría. El revisor sale de la sesión autenticada, no de un parámetro. | F-015, F-016, SEG-003, H3 | F1-V05, F1-S02 | DEV | P0 | 🟢 | L | P | E1-08 |
| F1-V07 | Auditoría protegida: tabla append-only con hash encadenado para detectar alteración. **[Mejora propuesta]** (usa solo la biblioteca estándar). | SEG-003, F-016 | F1-D03 | DEV | P2 | 🟢 | S | H | E1-08 |
| F1-V08 | EPM: no completar año/mes con la carpeta. Si el texto no trae el año, marcar `REVISION` y registrar el motivo. | F-003, H8 | — | DEV | P0 | 🟢 | S | H | E1-07 |
| F1-V09 | Separar el aseo de EPM como componente propio y capturar el alumbrado público como campo aparte. Unidad del aseo y tratamiento del alumbrado **parametrizables** hasta DEC-03. | F-005, F-002, D-004 | DEC-03 (solo para fijar valor por defecto) | DEV | P1 | 🟡 | M | P | E1-07 |
| F1-V10 | Detección de cambio de formato: tasa de campos extraídos por prestador y lote vs. su línea base, con alerta si cae. **[Mejora propuesta]** | NF-010, NF-008 | F1-D03 | DEV | P2 | 🟢 | M | P | E1-07 |
| F1-V11 | Motor de indicadores parametrizable: kWh/m², m³/persona, huella. Los parámetros salen de las tablas MaestroSede y FactorEmisión. Se prueba con datos simulados, **marcados "validar con datos reales"**. | F-011, D-001 | F1-D01 | DEV | P1 | 🟡 | L | P | E1-09 |
| F1-V12 | Costo de sobreconsumo: AUD no define la fórmula. Se implementa una propuesta (exceso sobre la línea base × costo unitario de la propia factura), aislada y desactivada hasta DEC-12. | F-012 | DEC-12 | DEV | P3 | 🟡 | S | P | E1-09 |
| F1-V13 | Notificador desacoplado (interfaz + plantillas de mensaje para faltante y atípico). Implementación inicial a archivo/registro. El canal real es F2-08. | F-014, INT-001 | F1-A02 | DEV | P1 | 🟡 | M | P | E1-10 |
| F1-V14 | Ingesta: reemplazar el watcher roto por un detector de PDF nuevos sobre una carpeta configurable, idempotente, con registro de lote. La carpeta compartida institucional es F2-07. | F-001 | F1-D03 | DEV | P1 | 🟡 | M | Pa | E1-07 |
| F1-V15 | Export para GreenMetric/GEI con los campos que dan las fuentes. El formato oficial no está definido en AUD: se deja plantilla genérica y se completa en F2-09. | F-018, F-019, INT-003 | F1-V11 | DEV | P2 | 🟡 | M | P | E1-09 |
| F1-V16 | Resumen ejecutivo imprimible (vista de Dirección). El formato PDF se resuelve al implementar, sin fijar biblioteca ahora. | F-020 | F1-U03 | DEV | P2 | 🟡 | M | P | E1-11 |
| F1-V17 | Pipeline con `run_id`, tiempos por etapa y reintento de lote fallido; medición del tiempo de máquina (el tiempo humano es F2-11). | NF-001, NF-007, D-007 | F1-D08 | DEV | P1 | 🟢 | M | Pa | E1-07 |
| F1-V18 | Plantillas de extracción declarativas por prestador (regex y reglas en configuración, no en código). **[Mejora propuesta]**: dejar de depender de un desarrollador para ajustar un formato. | NF-008 | F1-A01 | DEV | P2 | 🟢 | L | P | E1-07 |
| F1-V19 | Resolver Air-e sin consumo (8 filas) o documentar la causa si es de imagen. | F-002, H (AUD §3, REQ-F-002) | F1-A04 | DEV | P2 | 🟡 | S | P | E1-07 |

#### Seguridad (SEG)

| ID | Actividad | Req. origen | Dep. | Resp. | Prio. | Clase | Esf. | Estado | Entregable |
|---|---|---|---|---|---|---|---|---|---|
| F1-S01 | Clasificación de datos (contractuales, personales) y modelo de amenazas ligero. | SEG-001, SEG-004 | — | DEV | P0 | 🟢 | S | P | E1-12 |
| F1-S02 | RBAC con proveedor de identidad **enchufable**; implementación inicial con cuentas locales. Roles de F1-F03. El proveedor definitivo es DEC-06. | SEG-002, SEG-003 | F1-F03 | DEV | P0 | 🟡 | L | P | E1-12 |
| F1-S03 | Gestión de secretos y configuración fuera del código; `.gitignore` de `data/` y `.env`; verificación de que no haya datos personales versionados. | SEG-001, SEG-004 | — | DEV | P0 | 🟢 | S | P | E1-12 |
| F1-S04 | Backup y recuperación de la base oficial y de la auditoría: script, procedimiento y prueba de restauración. El destino institucional es F2-17. | D-007, SEG-001 | F1-D03 | DEV | P1 | 🟡 | M | P | E1-12 |
| F1-S05 | Datos de prueba anonimizados (sin NIT, identificación ni dirección reales). **[Mejora propuesta]** | SEG-004 | — | DEV | P1 | 🟢 | S | P | E1-12 |
| F1-S06 | Pruebas de seguridad iniciales: autorización por rol, intento de edición sin registro, revisión de dependencias. | SEG-002, F-016 | F1-S02 | DEV | P1 | 🟢 | M | P | E1-13 |

#### UX/UI

| ID | Actividad | Req. origen | Dep. | Resp. | Prio. | Clase | Esf. | Estado | Entregable |
|---|---|---|---|---|---|---|---|---|---|
| F1-U01 | Arquitectura de información y navegación por rol. | F-017, F-019, F-020 | F1-F03 | DEV | P1 | 🟢 | S | P | E1-11 |
| F1-U02 | Wireframes: tablero, detalle de sede/medidor, cola de revisión, alertas, histórico, exportaciones, vista Medellín, vista Dirección. | F-017 | F1-U01 | DEV | P1 | 🟢 | M | P | E1-11 |
| F1-U03 | Prototipo en el tablero actual con datos reales ya disponibles: semáforo, comparativo sede/ciudad, filtro por rol. Los KPIs per cápita usan simulados rotulados. | F-017, F-019 | F1-U02, F1-D05 | DEV | P1 | 🟡 | L | Pa | E1-11 |

#### Infraestructura (INF) y Calidad (CAL)

| ID | Actividad | Req. origen | Dep. | Resp. | Prio. | Clase | Esf. | Estado | Entregable |
|---|---|---|---|---|---|---|---|---|---|
| F1-I01 | Entorno reproducible: versión de Python fijada, dependencias separadas en ejecución/desarrollo, retirar las no usadas (Dagster, MySQL, Keycloak, FastAPI). **[Mejora propuesta]** | INT-002, AUD §5.7 | F1-A01 | DEV | P1 | 🟢 | S | P | E1-04 |
| F1-I02 | Estructura del repositorio y comandos de verificación únicos (pruebas, estilo). | INT-002 | — | DEV | P2 | 🟢 | S | P | E1-04 |
| F1-C01 | Pruebas unitarias nuevas: faltantes, compuerta, auditoría, unidad↔componente, N° factura, periodo EPM, consolidación, validación, indicadores, RBAC. Hoy las 22 cubren solo extracción. | NF-002, H1–H8 | cada F1-V | DEV | P0 | 🟢 | L | Pa | E1-13 |
| F1-C02 | Protocolo de medición de precisión: muestra estratificada por formato, hoja de verificación contra el PDF original, métricas por campo. Tamaño propuesto: 5 facturas por formato (11 formatos ≈ 55), a confirmar. | NF-002, NF-009, H5 | — | DEV + SGA-A | P0 | 🟢 | M | P | E1-13 |
| F1-C03 | Ejecutar el protocolo sobre los PDF disponibles (cotejo humano con el original). La aceptación formal por el SGA es F2-06. | NF-002, H5 | F1-C02 | DEV | P0 | 🟡 | L | P | E1-13 |
| F1-C04 | Medir el % sin revisión actual (hoy ≈52%) y desglosarlo por causa (serie corta, baja confianza, SIN_SERIE). Define la línea base de precisión (GOB-003). | NF-003, H7, GOB-003 | — | DEV | P0 | 🟢 | S | H | E1-13 |
| F1-C05 | Prueba de rendimiento con datos sintéticos (p. ej. 5× el volumen actual) y de resiliencia ante PDF corrupto o vacío. | NF-001 | — | DEV | P2 | 🟢 | S | P | E1-13 |
| F1-C06 | Pruebas de regresión por formato con **textos anonimizados** (no los PDF reales). | NF-008, OPS-003 | F1-S05 | DEV | P1 | 🟢 | M | Pa | E1-13 |

#### Documentación y Operación (DOC / OPS)

| ID | Actividad | Req. origen | Dep. | Resp. | Prio. | Clase | Esf. | Estado | Entregable |
|---|---|---|---|---|---|---|---|---|---|
| F1-O01 | Manual de operación del Analista (borrador): lote mensual, revisión, errores frecuentes, primer uso por prestador (REQ-F-021). | NF-007, OPS-005, F-021 | F1-V06 | DEV | P1 | 🟡 | M | P | E1-14 |
| F1-O02 | Borrador del protocolo de envío de facturas (formato, canal, responsable). La fecha límite es DEC-09. | OPS-001 | DEC-09 | DEV + LÍDER | P1 | 🟡 | S | P | E1-14 |
| F1-O03 | Borrador de SLA y escalamiento con opciones. La decisión es DEC-07. | OPS-002, NF-006 | DEC-07 | DEV + LÍDER | P1 | 🟡 | S | P | E1-14 |
| F1-O04 | Plan de contingencia: lote fallido, cambio de formato, pérdida de la base. **[Mejora propuesta]** | OPS-006 | F1-V10, F1-S04 | DEV | P2 | 🟢 | S | P | E1-14 |
| F1-O05 | Plan de capacitación al Analista y al Coordinador SGA (contenido y secuencia, sin fechas). **[Mejora propuesta]** | OPS-005 | F1-O01 | DEV | P2 | 🟢 | S | P | E1-14 |
| F1-O06 | **Paquete de entrada a Fase 2**: solicitudes redactadas por fuente y por decisión, con responsable, qué se pide y qué bloquea. | AUD §6 (todas) | — | DEV + LÍDER | P0 | 🟢 | S | P | E1-15 |

**Ya hecho y se conserva (no se repite):** relevamiento de formatos y extractores de 11 prestadores (OPS-003), dedup con servicio, clasificación digital/imagen, catálogo de sedes (63/64), prueba control EPM marzo 2025, alertas de atípicos, tablero con datos reales.

### 3.3 Dependencias internas de Fase 1 (orden obligatorio)

`F1-D01 → F1-D03 → F1-V05 → F1-V06` · `F1-D05 → F1-D06 → F1-V01` · `F1-F03 → F1-S02 → F1-V06` · `F1-C02 → F1-C03`. Todo lo demás es independiente.

### 3.4 Trabajo paralelo

| Carril | Contenido | Puede correr junto a |
|---|---|---|
| A. Definición | F1-G01…G05, F1-F01…F04 | Todos |
| B. Datos | F1-D01…D08 | A, D, E |
| C. Arquitectura y seguridad | F1-A01…A04, F1-S01…S05 | A, B, E |
| D. Correcciones de pipeline | F1-V01, V03, V04, V08, V17, F1-C04 | B (tras D01), C. Son independientes entre sí |
| E. UX | F1-U01…U02 | B, C, D |
| F. Construcción dependiente | F1-V05, V06, V11, V13, U03 | Tras B y C |
| G. Calidad y documentación | F1-C01…C06, F1-O01…O06 | Se alimenta de D y F |

Las combinaciones recomendadas son: **datos + seguridad**, **arquitectura + UX**, **correcciones de pipeline + protocolo de precisión**, y **documentación + desarrollo**.

### 3.5 Modelo: definitivo vs. pendiente de validar con datos reales

| Elemento | Estado |
|---|---|
| Entidades Factura, Lote, Hallazgo, Revisión, Alerta, ciclo de vida de la fila | **Definitivo** |
| Identificadores (factura + prestador + servicio), periodo (inicio/fin ISO), unidades por componente | **Definitivo** |
| Sede, Medidor, catálogo | Definitivo en estructura; contenido pendiente de confirmar por SGA-A (F2-04) |
| MaestroSede (m², población, vigencia) | Estructura definitiva; **valores pendientes** (F2-02) |
| FactorEmisión | Estructura definitiva; **fuente y valores pendientes** (F2-03) |
| Componente aseo (unidad kg o $) y alumbrado público | **Pendiente** de DEC-03 (campos parametrizables) |
| Calendario de periodicidad por medidor | Inferido; **pendiente** de confirmar (F2-05) |
| Esquema de salida | Canónico propuesto; **pendiente** de DEC-02 |

### 3.6 Entregables de Fase 1 y criterios de aceptación

Ver §11 (tabla única de criterios para ambas fases).

### 3.7 Riesgos de Fase 1

| Riesgo | Mitigación |
|---|---|
| Se reescribe el pipeline y se rompe lo que ya funciona | Congelar las salidas actuales como referencia; F1-C01 antes de refactorizar |
| La compuerta de confirmación frena al Analista | Las filas sin hallazgos pasan a `CONFIRMADO` automáticamente según una regla explícita (DEC-13); solo las marcadas esperan |
| Datos simulados que se confunden con reales | Etiquetado obligatorio y fuente visible en el tablero |
| El alcance crece por las 10 CSU o gas | Charter F1-G01 con DEC-01 abierta; no se agrega nada fuera de la lista |

---

## 4. Fase 2 — Actividades condicionadas

### 4.1 Objetivo

Integrar las fuentes reales, calibrar y validar con datos reales, y aceptar funcionalmente. Termina con la solución operable y reconciliada.

### 4.2 Actividades

*Entrada* es el criterio que debe cumplirse antes de arrancar. *Resultado / aceptación* resume lo que se espera; el detalle verificable está en §11.

| ID | Frente | Actividad | Info. requerida (fuente) | Resp. de entregarla | Req. origen | Entrada | Resultado / aceptación | Prio. | Esf. | Entregable |
|---|---|---|---|---|---|---|---|---|---|---|
| F2-01 | Datos | Cargar el histórico ≥12 meses desde los Excel manuales (Bogotá, CSU, agua, Medellín) y reconciliar con lo extraído de PDF | S05 | SGA-A | D-002, F-007 | S05 entregada; F1-D03 operativo | Cada medidor con ≥12 meses o con la brecha documentada; atípicos recalculados con la regla anual | P0 | M | E2-01 |
| F2-02 | Datos | Cargar maestros m² y población por sede; calcular KPIs per cápita reales | S06 | INFRA | D-001, F-011 | S06 entregada y validada por INFRA; F1-V11 | KPIs reales por sede; diferencias con los simulados explicadas | P0 | M | E2-02 |
| F2-03 | Datos | Cargar factores de emisión y metodología GEI; calcular huella | S07 | SGA-C | F-011 | DEC de metodología; F1-V11 | Huella reproduce un cálculo previo del inventario GEI dentro de la tolerancia que fije SGA-C | P1 | M | E2-02 |
| F2-04 | Datos | Confirmar el catálogo de sedes (`sede_confirmada`) | S14 | SGA-A | D-006 | F1-D05 | 100% de los medidores confirmados o marcados SIN_MAPEO con motivo | P0 | S | E2-01 |
| F2-05 | Datos | Confirmar periodicidad por medidor (mensual / bimensual) | S14 | SGA-A | F-013 | F1-D06 | Calendario aprobado; el detector da 0 falsas alertas en bimensuales | P0 | S | E2-01 |
| F2-06 | Calidad | Calibrar el umbral de confianza 90% y emitir el informe formal de precisión con el SGA | muestra verificada (F1-C03) | SGA-A | NF-002, F-004 | F1-C03; F2-04 | Precisión ≥95% por campo y prestador (meta 98%); umbral calibrado con tasa de falsos negativos medida | P0 | M | E2-03 |
| F2-07 | Integración | Ingesta real por carpeta compartida (o correo) | S11 | TI | F-001, OPS-001 | Acceso concedido; DEC-09 | Un PDF depositado en la carpeta real se procesa y deja traza; los rechazados quedan reprocesables | P1 | M | E2-04 |
| F2-08 | Integración | Canal real de notificaciones | S11, DEC-10 | TI | F-014, INT-001 | DEC-10; F1-V13 | Alertas de faltante y atípico llegan al SGA-A por el canal definido | P1 | S | E2-04 |
| F2-09 | Integración | Export en el formato oficial GreenMetric/GEI | S10 | SGA-C | F-018, INT-003 | S10 definido; F1-V15; F2-02, F2-03 | El SGA-C acepta el archivo sin retrabajo manual de estructura | P2 | M | E2-05 |
| F2-10 | Calidad | Prueba de control mensual (base automática vs. manual del mes anterior) para Bogotá, CSU y agua | S05 | SGA-A | NF-009 | F2-01 | Coincidencia ≥98% en periodo, consumo y valor por cada familia | P0 | M | E2-03 |
| F2-11 | Operación | Piloto cronometrado de un mes con el Analista, sin ayuda de TI | facturas reales del mes (S08) | GAB, CAM | NF-001, NF-003, NF-007 | F2-06, F2-07; F1-O01 | ≤2 h de trabajo humano (mínimo <4 h); % sin revisión medido contra la meta | P0 | M | E2-06 |
| F2-12 | Calidad | UAT del tablero con SGA-C, vista Medellín con CAM, vista Dirección | personas disponibles | SGA-C, CAM | F-017, F-019, F-020 | F2-02; F1-U03 | Actas firmadas por rol con defectos cerrados | P1 | M | E2-06 |
| F2-13 | Calidad | Primer uso supervisado por cada prestador activo | facturas reales | SGA-A | F-021 | F2-06 | Checklist completo por prestador | P1 | M | E2-06 |
| F2-14 | Seguridad | Validación con TI (ubicación, nube, identidad) y JUR (datos personales y contractuales) | conceptos | TI, JUR | SEG-001, SEG-004, GOB-002 | F1-S01…S05 | Conceptos escritos de TI y JUR; observaciones cerradas | P0 | M | E2-07 |
| F2-15 | Operación | Medir KPIs 6–8 semanas y aplicar NPS | operación real | SGA-A, SGA-C | NF-001…NF-006, OPS-004 | F2-11 en operación | Informe de KPIs contra meta y mínimo; NPS ≥6 (meta ≥8) | P1 | M | E2-08 |
| F2-16 | Datos | Muestras adicionales de PDF escaneados (Acueducto) y confirmación de que los lotes futuros mantendrán el formato | S09 | GAB | H9, F-004 | solicitud enviada (F1-O06) | OCR probado sobre ≥N muestras reales de imagen (N lo fija el SGA) | P1 | S | E2-03 |
| F2-17 | Infraestructura | Despliegue en ambiente institucional, backups en destino institucional, restauración probada | ambiente (TI) | TI | SEG-001, D-007 | F2-14; DEC-05 | Restauración exitosa desde el backup institucional | P1 | M | E2-09 |
| F2-18 | Operación | Capacitación y entrega operativa | personal | LÍDER | OPS-005 | F2-11 | Analista y Coordinador ejecutan el flujo completo según el manual | P2 | S | E2-09 |

### 4.3 Criterios de entrada de la Fase 2 (generales)

No se inicia una actividad de Fase 2 hasta cumplir su columna *Entrada*. Además, para abrir la fase se exige el **Gate 1** (§10).

### 4.4 Riesgos de transición

Ver §12.2.

---

## 5. Matriz completa de requerimientos → actividades

Ningún requerimiento queda sin acción. *Cobertura AUD* es el estado de la auditoría antes de este plan.

| REQ | Cobertura AUD | Fase 1 | Fase 2 | Decisión |
|---|---|---|---|---|
| F-001 Ingesta | 🟡 | F1-V14, F1-A02 | F2-07 | DEC-09 |
| F-002 Campos | 🟡 | F1-V09, F1-V19 | F2-16 | DEC-03 |
| F-003 Periodo del cuerpo | 🟡 | F1-V08, F1-F02 | — | — |
| F-004 OCR y confianza | 🟡 | F1-V02 | F2-06, F2-16 | — |
| F-005 Separar EPM | 🟡 | F1-V09 | — | DEC-03 |
| F-006 Unidad↔componente | 🔴 | F1-V03, F1-D04 | — | — |
| F-007 Atípico 20% | 🟡 | F1-D07, F1-C04 | F2-01 | — |
| F-008 N° factura | 🟡 | F1-V04 | — | — |
| F-009 Duplicados | 🟢 | F1-V04, F1-D04 | — | — |
| F-010 Consolidar tras confirmar | 🟡 | F1-V05, F1-D03 | — | DEC-13 |
| F-011 Indicadores | 🟡 | F1-V11, F1-D01 | F2-02, F2-03 | — |
| F-012 Costo sobreconsumo | 🟡 | F1-V12 | — | DEC-12 |
| F-013 Faltantes | 🟡 | F1-V01, F1-D06 | F2-05 | — |
| F-014 Alerta atípico | 🟡 | F1-V13 | F2-08 | DEC-10 |
| F-015 Revisión (<90%) | 🟡 | F1-V06, F1-V05, F1-V02 | F2-06 | — |
| F-016 Auditoría | 🟡 | F1-V06, F1-V07 | — | — |
| F-017 Tablero | 🟡 | F1-U01…U03 | F2-12 | DEC-08 |
| F-018 Export GreenMetric/GEI | 🟡 | F1-V15 | F2-09 | — |
| F-019 Descarga Coordinador | 🔴 | F1-V15, F1-U03 | F2-12 | — |
| F-020 PDF ejecutivo | 🔴 | F1-V16 | F2-12 | — |
| F-021 Primer uso por prestador | 🔴 | F1-O01 | F2-13 | — |
| D-001 Maestros de sede | 🟡 | F1-D01, F1-V11 | F2-02 | — |
| D-002 Histórico 12 m | 🟡 | F1-D07 | F2-01 | — |
| D-003 Trazabilidad | 🟡 | F1-D01, F1-D02 | — | DEC-02 |
| D-004 Aseo kg/$ | ⚠️ | F1-V09 | — | DEC-03 |
| D-005 Cobertura | ➕ | F1-G01 | — | DEC-01 |
| D-006 Catálogo de sedes | 🟡 | F1-D05 | F2-04 | — |
| D-007 Versionado y retención | 🔴 | F1-D08, F1-S04, F1-V17 | F2-17 | — |
| NF-001 ≤2 h | 🟡 | F1-V17, F1-F04 | F2-11, F2-15 | — |
| NF-002 Precisión | 🟡 | F1-C02, F1-C03 | F2-06 | DEC-14 |
| NF-003 % sin revisión | 🔴 | F1-C04 | F2-11, F2-15 | DEC-13 |
| NF-004 Detección <1 día | 🟡 | F1-C05, F1-V01 | F2-15 | — |
| NF-005 NPS | 🔴 | F1-G05 | F2-15 | — |
| NF-006 Alertas atendidas | 🔴 | F1-G05, F1-V13 | F2-15 | DEC-07 |
| NF-007 Autonomía | 🟡 | F1-O01, F1-V17 | F2-11 | — |
| NF-008 Plantillas actualizables | 🟡 | F1-V18, F1-A01 | — | — |
| NF-009 Prueba de control | 🟡 | F1-C02 | F2-10 | — |
| NF-010 Detección de drift | 🔴 | F1-V10 | — | — |
| SEG-001 Local / no cloud | 🟡 | F1-S01, F1-A01 | F2-14, F2-17 | DEC-05 |
| SEG-002 Acceso por rol | 🔴 | F1-S02, F1-F03 | — | DEC-06 |
| SEG-003 Revisor autenticado | 🔴 | F1-V06, F1-V07, F1-S02 | — | DEC-06 |
| SEG-004 Datos personales | 🔴 | F1-S01, F1-S05 | F2-14 | — |
| INT-001 Notificación | 🔴 | F1-V13, F1-A02 | F2-08 | DEC-10 |
| INT-002 Soporte TI | 🟡 | F1-A02, F1-I01 | F2-14, F2-17 | — |
| INT-003 GreenMetric/GEI | 🟡 | F1-A02, F1-V15 | F2-09 | — |
| TEC-001 OCR + IA | ⚠️ | F1-A04 | — | DEC-04 |
| ARQ-001 Tablero HTML | 🟡 | F1-V16, F1-U03 | — | DEC-08 |
| OPS-001 Protocolo de envío | 🟡 | F1-O02 | F2-07 | DEC-09 |
| OPS-002 SLA | 🟡 | F1-O03 | — | DEC-07 |
| OPS-003 Formatos | 🟢 | F1-C06 | — | — |
| OPS-004 Medir KPIs | 🟡 | F1-G05 | F2-15 | — |
| OPS-005 Capacitación | 🔴 | F1-O01, F1-O05 | F2-18 | — |
| OPS-006 Contingencia | 🔴 | F1-O04 | — | — |
| GOB-001 Sponsor, fechas, presupuesto | 🟡 | F1-G02, F1-G04 | — | DEC-11 |
| GOB-002 Conceptos de áreas | 🔴 | F1-G04 | F2-14 | DEC-11 |
| GOB-003 Línea base de precisión | 🔴 | F1-C04 | — | DEC-14 |
| GOB-004 Fuera de alcance | 🟢 | F1-G01 | — | — |
| GOB-005 Casillas de la Ficha | ⚠️ | F1-G01 | — | — |

---

## 6. Matriz de fuentes de datos

Solo se listan fuentes que aparecen en las fuentes del proyecto o en el repositorio. Cuando AUD no dice quién es el responsable, se indica.

| ID | Fuente | Tipo | Disponible | Responsable | Datos requeridos | Periodicidad | Dependencia | Fase |
|---|---|---|---|---|---|---|---|---|
| S01 | PDF Enel y Acueducto de Bogotá, 3 sedes (`data/raw`: 25 + 42) | Archivos | **Disponible** | GAB | Consumo, valor, periodo, factura | Mensual (Calle 84 bimensual) | — | F1 |
| S02 | PDF de CSU (102, 10 sedes) | Archivos | **Disponible**; alcance **requiere definición** | Por confirmar (P§4 solo menciona GAB para Bogotá) | Ídem | Mensual | DEC-01 | F1 (alcance en F2 si DEC-01 lo cambia) |
| S03 | PDF EPM Medellín (634) | Archivos | **Disponible** | CAM | Ídem, 3 componentes | Mensual | DEC-03 (aseo, alumbrado) | F1 |
| S04 | Excel manual EPM 2025 (`data/EPM`) | Archivos | **Disponible** | CAM | Control manual | Anual (consolidado) | — | F1 (control EPM) |
| S05 | Excel históricos manuales de Bogotá, CSU, agua y Medellín | Archivos | **Requiere validación**: P§4 dice que existen; no hay evidencia en el repositorio de los de Bogotá y CSU | SGA-A | ≥12 meses de consumo por medidor | Única vez | — | **F2-01, F2-10** |
| S06 | Datos maestros de sede: m², población | Archivo a definir | **No disponible** | INFRA | m², colaboradores/estudiantes por sede | Estática, actualizable | — | **F2-02** |
| S07 | Factores de emisión y metodología GEI | Documento | **Requiere definición** (AUD no dice la fuente) | SGA-C | Factor por energía y agua | Anual (a confirmar) | — | **F2-03** |
| S08 | Facturas futuras de meses nuevos | Archivos | **Requiere acceso** | GAB, CAM | Facturas del mes | Mensual | DEC-09 | **F2-07, F2-11** |
| S09 | Muestras de PDF escaneado (Acueducto) | Archivos | **Disponible parcialmente**: 2 de 803 son imagen | GAB | Escaneados representativos | Única vez | — | **F2-16** |
| S10 | Formato oficial del reporte GreenMetric/GEI | Plantilla | **Requiere definición** | SGA-C | Estructura de entrega | Semestral / anual | — | **F2-09** |
| S11 | Carpeta compartida o correo, y canal de notificación | Acceso | **Requiere acceso** | TI | Ruta, permisos, cuenta de envío | Continuo | DEC-10 | **F2-07, F2-08** |
| S12 | Proveedor de identidad institucional | Acceso | **Requiere definición** | TI | Autenticación | Continuo | DEC-06 | F2 (F1 usa proveedor local) |
| S13 | Catálogo de sedes confirmado | Archivo | **Disponible parcialmente** (63/64 propuestas, sin confirmar) | SGA-A | `sede_confirmada` | Estática | — | **F2-04, F2-05** |
| S14 | Gas propano y combustibles (`data/raw`) | Archivos | Disponible; **fuera de alcance** | Por definir | — | — | DEC-01 | Fuera |

**Resumen (14 fuentes):** 3 disponibles (S01, S03, S04); 3 disponibles solo en parte (S02 por alcance, S09, S13); 1 disponible pero fuera de alcance (S14); 6 requieren acceso, validación o definición (S05, S07, S08, S10, S11, S12); 1 no disponible (S06).

---

## 7. Matriz de dependencias

| ID | Dependencia | Tipo | Bloquea | Responsable | Fase objetivo | Estado |
|---|---|---|---|---|---|---|
| DEP-01 | Datos maestros de sede (S06) | Datos | F2-02; cálculo real de F-011 | INFRA | F2 | Abierta |
| DEP-02 | Excel históricos (S05) | Datos | F2-01, F2-10; cumplimiento de NF-003 | SGA-A | F2 | Abierta, hay que validar que existan |
| DEP-03 | Metodología y factores GEI (S07) | Datos / Funcional | F2-03 | SGA-C | F2 | Abierta |
| DEP-04 | Formato oficial de reporte (S10) | Funcional | F2-09 | SGA-C | F2 | Abierta |
| DEP-05 | Acceso a carpeta/correo y canal de envío (S11) | Acceso | F2-07, F2-08 | TI | F2 | Abierta |
| DEP-06 | Proveedor de identidad (S12) | Seguridad / Técnico | Cierre de F1-S02 en producción | TI | F2 | Abierta |
| DEP-07 | Facturas de meses nuevos (S08) | Datos / Tercero | F2-11, F2-15 | GAB, CAM | F2 | Abierta |
| DEP-08 | Conceptos de TI, JUR, Talento Humano, GEV | Tercero / Decisión | F2-14, producción | SPONSOR / LÍDER | Gate 2 | Abierta |
| DEP-09 | Disponibilidad del Analista y del Coordinador para pruebas | Operativo | F2-06, F2-10…F2-13 | LÍDER | F2 | Abierta |
| DEP-10 | Disponibilidad de personal de verificación para el cotejo de F1-C03 | Operativo | F1-C03 | LÍDER | F1 | Abierta |
| DEP-11 | Decisiones DEC-01…14 | Decisión | Ver §14 | LÍDER / SPONSOR | F1/F2 | Abiertas |
| DEP-12 | Equipo de desarrollo asignado | Técnico / Operativo | Toda la Fase 1 | LÍDER | Antes de F1 | **Por confirmar** |

Ninguna dependencia bloquea las actividades de Fase 1 salvo DEP-12 y DEP-10.

---

## 8. Backlog priorizado

*Esfuerzo y detalle completos en §3.2 y §4.2.* Las **P0** son las que se atacan primero.

**P0 — Crítica**
F1-G01 · F1-F01 · F1-F02 · F1-D01 · F1-D02 · F1-D03 · F1-D06 · F1-A01 · F1-A02 · F1-V01 · F1-V02 · F1-V05 · F1-V06 · F1-V08 · F1-S01 · F1-S02 · F1-S03 · F1-C01 · F1-C02 · F1-C03 · F1-C04 · F1-O06 · F2-01 · F2-02 · F2-04 · F2-05 · F2-06 · F2-10 · F2-11 · F2-14

**P1 — Alta**
F1-G02 · F1-G03 · F1-G04 · F1-G05 · F1-F03 · F1-F04 · F1-D04 · F1-D05 · F1-D07 · F1-D08 · F1-A03 · F1-A04 · F1-V03 · F1-V04 · F1-V09 · F1-V11 · F1-V13 · F1-V14 · F1-V17 · F1-S04 · F1-S05 · F1-S06 · F1-U01 · F1-U02 · F1-U03 · F1-I01 · F1-C06 · F1-O01 · F1-O02 · F1-O03 · F2-03 · F2-07 · F2-08 · F2-12 · F2-13 · F2-15 · F2-16 · F2-17

**P2 — Media**
F1-V07 · F1-V10 · F1-V15 · F1-V16 · F1-V18 · F1-V19 · F1-I02 · F1-C05 · F1-O04 · F1-O05 · F2-09 · F2-18

**P3 — Evolutiva**
F1-V12 (costo de sobreconsumo, con DEC-12) · evaluación de API HTTP, servidor de base de datos o motor de flujos si TI lo exige (Gate 2) · ampliaciones fuera de alcance (gas, combustibles, IoT, Propuestas 2–3).

---

## 9. Arquitectura objetivo

**Criterio:** conservar lo que ya funciona (Python, PyMuPDF, Tesseract, pandas, openpyxl, Dash) y añadir solo lo que un requerimiento justifica. FastAPI, Dagster, MySQL y Keycloak **no se adoptan** porque ninguna fuente los exige; se reevalúan en Gate 2 si TI lo pide.

```
Fuentes ─► Ingesta ─► Extracción ─► Validación ─► Transformación ─► Almacenamiento
 PDF         lote,       texto/OCR,   unidad,       esquema común,    SQLite local
 (carpeta)   run_id,     plantilla    duplicado,    separar EPM,      (staging, revisión,
             registro    por          confianza,    catálogo sede     oficial, auditoría)
                         prestador    atípico 20%,
                                      calendario
                                                         │
Alertas ◄─ Procesamiento ◄──────────────────────────────┘
(Notificador) indicadores, faltantes     Aplicación (Dash, con roles)
                                         revisión · tablero · exportes
```

| Capa | Responsabilidad | Estado hoy | Tecnología (justificación) |
|---|---|---|---|
| Fuentes / Ingesta | Detectar PDF nuevos, registrar el lote, clasificar digital/imagen | Parcial (lotes por script; watcher roto) | Python (existente) |
| Extracción | Texto con PyMuPDF; OCR solo si es imagen; extractor por prestador con plantilla | Hecho para 11 formatos | PyMuPDF, Tesseract (existentes) |
| Validación | Reglas R-xx (unidad, duplicado, confianza, atípico, calendario) | Parcial | Python |
| Transformación | Esquema común, separar EPM, mapear sede | Parcial | pandas (existente) |
| Almacenamiento | Estados `EXTRAIDO → OFICIAL`, auditoría append-only, histórico, maestros | **No existe** | SQLite **[Mejora propuesta]**, cambiable por la capa de repositorio (DEC-05) |
| Procesamiento | Indicadores, alertas, cálculo de faltantes | Parcial | Python |
| Servicios | Capa de servicios internos que usan la aplicación y el pipeline. Sin API HTTP en Fase 1 | No existe | Python |
| Aplicación | Revisión, tablero, descargas, con RBAC | Tablero parcial | Dash (existente) |
| Alertas | Notificador con interfaz; canal definido por TI | No existe | Interfaz propia |
| Seguridad transversal | RBAC, secretos fuera del código, auditoría, backup | No existe | Python, biblioteca estándar |

**Salidas:** Excel unificado mensual (export desde la base oficial), tablero, insumos GreenMetric/GEI, resumen ejecutivo.

---

## 10. Roadmap

```
FASE 1 — Preparación + Diseño + Construcción
  Carril A  Definición ───────────────┐
  Carril B  Datos ────────────────────┤
  Carril C  Arquitectura/Seguridad ───┤
  Carril D  Correcciones de pipeline ─┼──► GATE 1
  Carril E  UX ───────────────────────┤
  Carril F  Construcción ─────────────┤
  Carril G  Calidad/Documentación ────┘
                    │
                    ▼
FASE 2 — Datos + Integración + Validación
  (cada actividad arranca al cumplir su criterio de entrada)
  Datos: F2-01 F2-02 F2-03 F2-04 F2-05 F2-16
  Integración: F2-07 F2-08 F2-09
  Calidad: F2-06 F2-10 F2-12 F2-13
  Operación: F2-11 F2-15 F2-18        Seguridad/Infra: F2-14 F2-17
                    │
                    ▼
                 GATE 2
                    │
                    ▼
        Puesta en producción / Operación
```

### Gate 1 — salida de Fase 1 (todas las condiciones)

1. Arquitectura, modelo de datos y reglas aprobados por el LÍDER.
2. E1-06 a E1-10 construidos y con pruebas pasando.
3. H1–H8 cerradas, cada una con su prueba automatizada.
4. Seguridad base (RBAC, secretos, backup probado) implementada.
5. Informe preliminar de precisión por campo y prestador, y % sin revisión medido.
6. Matriz de fuentes, dependencias y decisiones publicada, con solicitudes enviadas (F1-O06).
7. Nada simulado sin etiquetar.

### Gate 2 — salida de Fase 2

Integrada, validada con datos reales, probada, reconciliada, aceptada funcionalmente y lista para operar: precisión ≥95%, prueba de control superada, piloto ≤2 h, conceptos de TI y JUR emitidos y, si aplica, aprobación formal de la Ficha (DEC-11).

### 10.1 Hitos

Sin fechas: los hitos se ordenan por dependencia. Un hito se cierra cuando **todos** sus entregables están aceptados según §11. *Depende de* indica qué hito debe estar cerrado antes (un hito puede empezar antes, pero no cerrarse).

| Hito | Nombre | Fase | Entregables | Depende de | Se cierra cuando | Responsable de aceptar |
|---|---|---|---|---|---|---|
| **M1** | Fundamentos definidos | 1 | E1-01, E1-02, E1-03, E1-04 | — | Charter, RACI, reglas R-xx, casos de uso y arquitectura aprobados; contradicciones de las fuentes convertidas en DEC con responsable | LÍDER |
| **M2** | Datos y pipeline corregidos | 1 | E1-05, E1-06, E1-07 | M1 (modelo y reglas) | H1–H4 y H8 cerradas con prueba automatizada; la base oficial solo recibe filas confirmadas | LÍDER |
| **M3** | Control humano y seguridad operativos | 1 | E1-08, E1-12 | M2 (E1-06) | Una decisión de revisión queda auditada con revisor autenticado; RBAC, secretos y backup probados | LÍDER + TI (consulta) |
| **M4** | Producto funcional con datos disponibles | 1 | E1-09, E1-10, E1-11 | M2, M3 | Indicadores, notificaciones y tablero por rol funcionan de extremo a extremo con datos reales disponibles y simulados rotulados | SGA-C (revisión del prototipo) |
| **M5 — GATE 1** | Calidad medida y paquete de entrada a Fase 2 | 1 | E1-13, E1-14, E1-15 | M2, M3, M4 | Ver condiciones del Gate 1 (§10) | LÍDER |
| **M6** | Datos reales cargados y confirmados | 2 | E2-01, E2-02 | M5; DEP-01, 02, 03 | Histórico, maestros, catálogo y calendario cargados y aprobados por sus dueños | SGA-A, INFRA, SGA-C |
| **M7** | Integraciones reales operando | 2 | E2-04, E2-05 | M5; DEP-04, 05 | Ingesta y canal reales funcionando; export aceptado por SGA-C | TI, SGA-C |
| **M8** | Validación con datos reales | 2 | E2-03, E2-07 | M6 | Precisión y prueba de control cumplen los umbrales; conceptos de TI y JUR emitidos | SGA-A, TI, JUR |
| **M9 — GATE 2** | Piloto y aceptación funcional | 2 | E2-06 | M6, M7, M8 | Piloto de un mes ≤2 h con el Analista; actas de UAT por rol | LÍDER + SPONSOR |
| **M10** | Operación y medición | Operación | E2-08, E2-09 | M9 | Ambiente institucional con backup probado; KPIs medidos de 6 a 8 semanas contra meta y mínimo | LÍDER |

```
M1 ─► M2 ─► M3 ─► M4 ─► M5 (Gate 1) ─┬─► M6 ─► M8 ─┐
                                      └─► M7 ────────┴─► M9 (Gate 2) ─► M10
```

M6 y M7 corren en paralelo; M8 necesita M6 pero no M7.

### 10.2 Catálogo de entregables

Cada entregable es un producto verificable. El criterio de aceptación está en §11 bajo el mismo ID. *Actividades* son las que lo producen; el entregable se acepta cuando todas terminan.

#### Fase 1

| ID | Entregable | Formato / ubicación sugerida | Actividades | Hito | Resp. | Hallazgos / REQ que cierra |
|---|---|---|---|---|---|---|
| E1-01 | Charter de alcance, RACI y plan saneado | Documento en el repositorio | F1-G01, G02, G03 | M1 | LÍDER | D-005, GOB-001, GOB-004, GOB-005 · H10 |
| E1-02 | Registro de riesgos y decisiones; paquete de aprobación (rubros de presupuesto y solicitudes de conceptos) | Documento + tablero de trazabilidad (CSV) | F1-G04, G05 | M1 | LÍDER | GOB-001, GOB-002, OPS-004 |
| E1-03 | Especificación funcional: casos de uso, catálogo de reglas R-xx, matriz de roles, RNF medibles | Documento | F1-F01…F04 | M1 | DEV + SGA-A | F-001…F-016, SEG-002, NF-001…007 |
| E1-04 | Arquitectura objetivo, ADRs vigentes, contratos de integración, entorno reproducible, README y configuración alineados | Documento + código de entorno | F1-A01…A04, F1-I01, I02 | M1 | DEV | TEC-001, INT-001…003, NF-008 · AUD §5.7 |
| E1-05 | Modelo de datos (conceptual y lógico), diccionario, esquema canónico, catálogo de sedes y calendario de periodicidad | Documento + tablas | F1-D01, D02, D04, D05, D06 | M2 | DEV | D-001, D-003, D-006, F-013 |
| E1-06 | Almacenamiento con ciclo de vida de fila (`EXTRAIDO → OFICIAL`), compuerta de confirmación y versión oficial por `run_id` | Código + base local | F1-D03, D08, V05 | M2 | DEV | F-010, D-007 · **H4** |
| E1-07 | Pipeline corregido: faltantes por calendario, unidad↔componente, N° factura, periodo EPM, confianza por campo, aseo/alumbrado, detección de cambio de formato, ingesta, plantillas declarativas | Código + pruebas | F1-V01…V04, V08…V10, V14, V17…V19 | M2 | DEV | F-002…F-009, F-013, NF-008, NF-010 · **H1, H2, H8** |
| E1-08 | Módulo de revisión con auditoría protegida y revisor autenticado | Código + pruebas | F1-V06, V07 | M3 | DEV | F-015, F-016, SEG-003 · **H3** |
| E1-09 | Motor de indicadores parametrizable (con datos simulados rotulados), export genérico, costo de sobreconsumo inactivo | Código + pruebas | F1-V11, V12, V15 | M4 | DEV | F-011, F-012, F-018, F-019 |
| E1-10 | Notificador desacoplado con plantillas de faltante y atípico | Código + pruebas | F1-V13 | M4 | DEV | F-014, INT-001 |
| E1-11 | Prototipo de tablero por rol: arquitectura de información, wireframes, vistas, resumen ejecutivo imprimible | Aplicación + wireframes | F1-U01…U03, V16 | M4 | DEV | F-017, F-019, F-020, ARQ-001 |
| E1-12 | Seguridad base: clasificación de datos, modelo de amenazas, RBAC, secretos, `.gitignore`, backup con restauración probada, datos anonimizados | Código + procedimiento | F1-S01…S05 | M3 | DEV | SEG-001…004, D-007 |
| E1-13 | Informe de calidad: suite de pruebas, protocolo y resultado de precisión por campo y prestador, % sin revisión con desglose, histórico disponible, pruebas de seguridad y rendimiento | Informe + pruebas | F1-C01…C06, F1-S06, F1-D07 | M5 | DEV | NF-001…004, NF-009, GOB-003 · **H5, H6, H7** |
| E1-14 | Documentación operativa en borrador: manual del Analista, protocolo de envío, SLA y escalamiento (opciones), contingencia, plan de capacitación | Documentos | F1-O01…O05 | M5 | DEV + LÍDER | OPS-001, OPS-002, OPS-005, OPS-006, F-021 |
| E1-15 | Paquete de entrada a Fase 2: solicitud por fuente (S05–S13) y por decisión abierta, con responsable y consecuencia de no recibirla | Documento | F1-O06 | M5 | DEV + LÍDER | AUD §6 completo |

#### Fase 2

| ID | Entregable | Formato / ubicación sugerida | Actividades | Hito | Resp. | REQ que cierra |
|---|---|---|---|---|---|---|
| E2-01 | Histórico ≥12 meses cargado, catálogo de sedes confirmado, calendario de periodicidad aprobado | Datos + acta | F2-01, F2-04, F2-05 | M6 | SGA-A | D-002, D-006, F-007, F-013 |
| E2-02 | Maestros de sede e indicadores calculados con valores reales (kWh/m², m³/persona, huella) | Datos + informe | F2-02, F2-03 | M6 | INFRA, SGA-C | D-001, F-011 |
| E2-03 | Informe formal de precisión, prueba de control mensual y umbral de confianza calibrado | Informe | F2-06, F2-10, F2-16 | M8 | SGA-A | NF-002, NF-009, F-004 |
| E2-04 | Ingesta real y canal de notificación real | Configuración + evidencia | F2-07, F2-08 | M7 | TI | F-001, F-014, INT-001, OPS-001 |
| E2-05 | Export en el formato oficial GreenMetric/GEI | Archivo + acta | F2-09 | M7 | SGA-C | F-018, INT-003 |
| E2-06 | Informe del piloto cronometrado, actas de UAT por rol y checklist de primer uso por prestador | Informe + actas | F2-11, F2-12, F2-13 | M9 | LÍDER | NF-001, NF-003, NF-007, F-017, F-019…021 |
| E2-07 | Conceptos escritos de TI y JUR | Documentos | F2-14 | M8 | TI, JUR | SEG-001, SEG-004, GOB-002 |
| E2-08 | Informe de KPIs de 6 a 8 semanas y resultado del NPS | Informe | F2-15 | M10 | SGA-A, SGA-C | NF-001…006, OPS-004 |
| E2-09 | Ambiente institucional desplegado con backup y restauración probados; capacitación realizada | Ambiente + acta | F2-17, F2-18 | M10 | TI, LÍDER | SEG-001, D-007, OPS-005 |

#### Cobertura

- Las **63** actividades de Fase 1 y las **18** de Fase 2 producen al menos un entregable. Ninguna queda sin destino. Los entregables E1-13 y E1-12 absorben las actividades transversales (F1-S06, F1-D07) para no multiplicar productos.
- Los hallazgos **H1 a H8** de la auditoría quedan cerrados por E1-06, E1-07, E1-08 y E1-13. **H9** por E2-03 (F2-16) y **H10** por E1-01 junto con DEC-01.

---

## 11. Criterios de aceptación

### Fase 1

| Entregable | Descripción | Criterio de aceptación (verificable) |
|---|---|---|
| E1-01 Charter y gobierno base | Alcance, RACI, DoD, plan saneado | El documento lista cada contradicción de las fuentes con un ID de decisión; el plan no tiene secciones duplicadas ni estados contradictorios; cada rol de la Ficha aparece en el RACI |
| E1-02 Registro de riesgos, decisiones y paquete de aprobación | Riesgos, DEC-xx, rubros de presupuesto | Cada DEC tiene responsable y bloqueo declarado; el paquete cubre los 6 rubros de F§8 |
| E1-03 Especificación funcional | Casos de uso, reglas R-xx, roles, RNF | Cada regla de P§9 tiene un ID R-xx y al menos una prueba automatizada asociada; cada RNF tiene un método de medición |
| E1-04 Arquitectura y ADRs | Arquitectura objetivo, contratos, entorno | README, `config.yaml` y ADRs no mencionan componentes que no existan en el código; cada contrato define campos, formato, error y reintento |
| E1-05 Modelo de datos | Conceptual, lógico, diccionario, esquema canónico, calendario | Las 8 entidades clave están documentadas con claves; el mapeo desde las 26 columnas heredadas no deja ninguna sin destino o sin descarte justificado |
| E1-06 Almacenamiento y ciclo de vida | Base, estados, versión oficial | Una fila `EN_REVISION` no aparece en la exportación "oficial"; dos corridas generan `run_id` distintos y la oficial refiere a uno; restaurar desde backup reproduce los conteos |
| E1-07 Pipeline corregido | Faltantes, unidad, N° factura, periodo EPM, confianza, drift, ingesta | (a) Serie mensual sin un mes → exactamente 1 `ALERTA_FALTANTE` con medidor y periodo esperado; serie bimensual completa → 0; (b) unidad incoherente → rechazo con motivo; (c) factura sin número → fila con "N° factura no identificado", no rechazada; (d) EPM: el periodo se completa con la fecha de emisión del cuerpo; si el cuerpo no la trae, `periodo_fuente=carpeta` y la fila queda en `REVISION_PERIODO_INFERIDO`; (e) caída de campos extraídos >umbral configurable en un lote → alerta de formato |
| E1-08 Revisión y auditoría | Módulo de revisión, auditoría protegida | Toda decisión escribe una fila con revisor autenticado, fecha, valor original y nuevo; un intento de decisión sin sesión es rechazado; alterar una fila del log es detectado por la verificación del hash |
| E1-09 Indicadores y exportes | Motor parametrizable, export genérico, costo (inactivo) | Con maestros simulados, kWh/m² y m³/persona coinciden con un cálculo manual en ≥3 sedes de prueba; cada valor simulado está rotulado; el export contiene los campos de P§6 |
| E1-10 Notificaciones | Interfaz y plantillas | Un faltante y un atípico generan cada uno un mensaje con medidor, periodo y enlace a la evidencia; al cambiar la implementación del canal no cambia el código del motor |
| E1-11 Prototipo de tablero | Vistas por rol | Un usuario CAM solo ve la sede de Medellín; Dirección no ve la cola de revisión; el semáforo cambia al marcar un atípico en datos de prueba |
| E1-12 Seguridad base | RBAC, secretos, backup, modelo de amenazas | `git ls-files` no contiene `.env` ni PDF/Excel de `data/`; pruebas de autorización pasan para los 5 roles; restauración probada |
| E1-13 Calidad | Pruebas, protocolo, medición | Pruebas nuevas por cada H1–H8; informe con precisión por campo y por prestador sobre la muestra del protocolo; % sin revisión con desglose por causa; ningún caso sin cotejar |
| E1-14 Documentación operativa | Manual, protocolo, SLA, contingencia, capacitación | Un tercero sigue el manual con datos de prueba y completa un lote sin consultar al desarrollador |
| E1-15 Paquete de entrada a Fase 2 | Solicitudes por fuente y decisión | Cada fuente S05–S13 y cada DEC abierta tiene solicitud redactada, responsable y consecuencia de no recibirla |

### Fase 2

| Entregable | Criterio de aceptación (verificable) |
|---|---|
| E2-01 Histórico y catálogos confirmados | Todo medidor con ≥12 meses o brecha documentada; catálogo 100% confirmado o SIN_MAPEO con motivo; calendario aprobado y 0 falsas alertas en bimensuales |
| E2-02 Maestros e indicadores reales | KPIs por sede calculados con valores reales; huella reproduce un cálculo previo del inventario GEI dentro de la tolerancia de SGA-C |
| E2-03 Precisión y reconciliación | Precisión ≥95% (meta 98%) por campo y prestador contra el PDF original; prueba de control ≥98% en periodo, consumo y valor para Bogotá, CSU y agua; umbral de confianza calibrado |
| E2-04 Ingesta y notificación reales | Un PDF depositado en la carpeta real se procesa de extremo a extremo; los rechazados quedan en cola reprocesable; una alerta real llega por el canal definido |
| E2-05 Export oficial | El SGA-C acepta el archivo sin modificar su estructura |
| E2-06 Piloto y UAT | Piloto de un mes real ≤2 h de trabajo humano (mínimo <4 h) con % sin revisión medido contra la meta; actas de UAT por rol; checklist de primer uso por prestador |
| E2-07 Conceptos de seguridad y legal | Conceptos escritos de TI y JUR; observaciones cerradas |
| E2-08 Informe de KPIs | KPIs de P§7 medidos contra meta y mínimo durante 6–8 semanas; NPS ≥6 (meta ≥8) |
| E2-09 Operación | Ambiente institucional con backup y restauración probados; Analista y Coordinador ejecutan el flujo completo según el manual |

---

## 12. Riesgos

### 12.1 Riesgos del proyecto

| Riesgo | Impacto | Mitigación | Origen |
|---|---|---|---|
| Dato no confirmado llega a GreenMetric/GEI | Crítico (5/5) | Compuerta F1-V05; export solo desde la base oficial | H4 |
| Cambio de formato rompe un extractor sin aviso | Alto | F1-V10 (detección), F1-V18 (plantillas), F1-C06 (regresión) | NF-008, NF-010 |
| El % sin revisión no alcanza el mínimo de 60% | Alto | F1-C04 (medir y desglosar), F2-01 (histórico) | H7 |
| Detector de faltantes da falsa tranquilidad | Alto | F1-V01 con pruebas de serie sin un mes | H1 |
| Fallas de OCR en escaneados | Alto | F1-V02, F2-16 | H2, H9 |
| Datos contractuales y personales en archivos sin control | Medio | F1-S01…S05, F2-14 | SEG-001, SEG-004 |
| Dependencia de terceros para el envío | Medio | F1-O02, DEC-09, F2-07 | OPS-001 |
| Alcance creciente (CSU, gas) | Medio | F1-G01, DEC-01 | H10 |
| Iniciativa sin aprobación formal | Medio | F1-G04, DEC-11 | GOB-001 |

### 12.2 Riesgos de transición Fase 1 → Fase 2

| Riesgo | Causa | Impacto | Mitigación | Responsable | Punto de control |
|---|---|---|---|---|---|
| Fase 2 no arranca por falta de maestros | INFRA no entrega m² ni población | KPIs per cápita sin validar; REQ-F-011 incumplido | Solicitud formal en F1-O06; escalar al LÍDER si no hay respuesta | LÍDER | Gate 1 |
| No existen los Excel históricos de Bogotá/CSU | S05 no confirmado | Sin regla anual; atípicos siguen inflados | Verificar existencia en F1-D07; si no existen, acordar usar solo PDF disponibles y documentar el límite | SGA-A | Gate 1 |
| Decisiones sin responsable ni fecha | Hoy no hay dueño de Fase 0 | Parámetros sin cerrar; retrabajo | Cada DEC con responsable en F1-G05 | LÍDER | Gate 1 |
| Dato simulado tomado por real | Falta de etiquetado | Decisiones sobre cifras falsas | Rotular y mostrar la fuente | DEV | Gate 1 |
| Disponibilidad del Analista para pruebas | Carga operativa | Piloto y UAT se atrasan | Reservar su tiempo antes de Gate 1 (DEP-09) | LÍDER | Gate 1 |
| TI no valida la ubicación o la identidad | Sin concepto | No se puede pasar a producción | Entregar F1-S01 y los contratos de F1-A02 a TI durante Fase 1, no al final | TI | Gate 1 / Gate 2 |
| Los defectos corregidos cambian las cifras históricas | H1, H4, H8 | Desconfianza | Comparar antes/después y documentar diferencias | DEV | Gate 1 |

---

## 13. Indicadores de seguimiento

Todos se calculan desde el tablero de trazabilidad (F1-G05). Cada uno tiene numerador y denominador explícitos.

| Indicador | Fórmula | Meta de referencia |
|---|---|---|
| % requerimientos cubiertos | REQ con actividad terminada y criterio cumplido ÷ 58 | 100% al Gate 2; línea base: 3 🟢 de 58 (5%) |
| % actividades Fase 1 completadas | F1 con aceptación ÷ 63 | 100% en Gate 1 |
| % actividades Fase 2 preparadas | F2 con criterio de entrada cumplido ÷ 18 | Medición continua |
| % fuentes disponibles | S (disponibles) ÷ S (totales en alcance) | — |
| % fuentes integradas | S integradas y validadas ÷ S en alcance | 100% en Gate 2 |
| % componentes desarrollados | E1-06…E1-12 con aceptación ÷ 7 | 100% en Gate 1 |
| % pruebas ejecutadas / aprobadas | Pruebas corridas ÷ planificadas · aprobadas ÷ corridas | 100% / 100% de las críticas |
| % riesgos críticos gestionados | Críticos con mitigación activa ÷ críticos | 100% |
| % dependencias resueltas | DEP cerradas ÷ 12 | — |
| Indicadores del producto | Tiempo del Analista, precisión, % sin revisión, detección de atípicos, NPS, alertas atendidas (P§7) | Según meta y mínimo |

---

## 14. Decisiones requeridas

Solo decisiones que corresponden a los responsables del proyecto.

| ID | Decisión | Opciones / recomendación | Responsable | Bloquea |
|---|---|---|---|---|
| DEC-01 | ¿Entran las CSU fuera de Bogotá y el gas/combustibles? | Recomendado: mantener las CSU ya procesadas como alcance explícito y dejar gas/combustibles fuera. Las fuentes no respaldan ni lo uno ni lo otro | LÍDER + SGA-C | F1-G01; S02, S14 |
| DEC-02 | Esquema de salida único | Canónico de F1-D02, o las 26 columnas heredadas | SGA-A + SGA-C | Cierre de E1-05 |
| DEC-03 | Aseo: kg o $; tratamiento del alumbrado público | Las fuentes se contradicen (kg en la Ficha, $ en la Propuesta) | SGA-C | Valor por defecto de F1-V09 |
| DEC-04 | ¿Se requiere IA además de OCR y reglas? | Criterio a partir de F1-A04. Si se elige IA, debe ser local por la restricción cloud | LÍDER + TI | TEC-001 |
| DEC-05 | Almacenamiento y despliegue | SQLite local (propuesto) o un servidor institucional | TI | F2-17 |
| DEC-06 | Proveedor de identidad | Cuentas locales o el proveedor institucional | TI | F2 (producción) |
| DEC-07 | SLA de respuesta y escalamiento | — | LÍDER | NF-006, F1-O03 |
| DEC-08 | Formato del tablero: aplicación con servidor o archivo HTML estático | P§6 dice "HTML interactivo" | SGA-C + TI | F1-V16, ARQ-001 |
| DEC-09 | Fecha límite de envío y responsable de cada envío | — | GAB, CAM + SGA-A | F1-O02, F2-07 |
| DEC-10 | Canal de notificación | Correo (P§6) u otro | SGA-A + TI | F2-08 |
| DEC-11 | Sponsor, fechas, presupuesto, equipo y conceptos de áreas | F§1, §8–10 | SPONSOR | Gate 2 |
| DEC-12 | Definición del costo de sobreconsumo | Sin definición en las fuentes | SGA-C | F1-V12 (P3) |
| DEC-13 | ¿Qué filas pasan solas a `CONFIRMADO`? | Solo las sin hallazgos, o también las atípicas con serie corta | SGA-C | F1-V05, NF-003 |
| DEC-14 | Línea base de precisión | F§3 la deja pendiente; se propone la que mida F1-C03 | SGA-C | GOB-003 |

---

## 15. Próximas acciones inmediatas

Orden de ejecución:

1. **Asignar el equipo de desarrollo y a quien verifique el cotejo manual** (DEP-12, DEP-10). Sin esto, nada de Fase 1 avanza. *LÍDER.*
2. **F1-C04: medir el % sin revisión actual** y desglosarlo por causa. Es una consulta sobre las salidas ya generadas y fija la línea base (H7).
3. **F1-V01: corregir el detector de faltantes** y su prueba con la serie sin un mes (H1). Es el defecto de más riesgo y se arregla con lo que hay.
4. **F1-F02 + F1-D01: fijar el catálogo de reglas R-xx y el modelo de datos.** Desbloquean D03, V05, V06.
5. **F1-D03 + F1-V05: almacenamiento y compuerta de confirmación** (H4).
6. **F1-V08: dejar de inferir el periodo EPM desde la carpeta** (H8). Cambio pequeño, riesgo alto para el DoD.
7. **F1-C02: escribir el protocolo de precisión y elegir la muestra** (H5).
8. **F1-S01 + F1-S03: clasificación de datos, `.gitignore` y secretos** antes de seguir cargando datos reales.
9. **F1-G01: charter con las contradicciones como decisiones abiertas**, y envío de DEC-01, DEC-03, DEC-07 y DEC-11 a sus responsables.
10. **F1-O06 (arranque): redactar y enviar las solicitudes de S05, S06, S07, S10 y S11.** Su tiempo de respuesta es el que fija cuándo puede empezar la Fase 2, así que conviene que corran en paralelo desde el primer día.

---

## Anexo — Avance de implementación

| Fecha | Actividad | Resultado |
|---|---|---|
| 2026-10-08 | F1-V01 Faltantes | `src/processor/faltantes.py`: cadencia inferida por medidor, corte por prestador. 7 pruebas nuevas. Sobre los datos reales: 5 huecos en serie (EPM, abril 2025 en 5 medidores, coherente con las 5 facturas sin PDF en origen) y 5 series que terminan antes que el resto de su prestador. Antes: 0 |
| 2026-10-08 | F1-V08 Periodo EPM | `resolver_periodo_epm`: el año sale del cuerpo ("Fecha de generación", "facturación <mes> de <año>"). 573 de 573 facturas con periodo resolvieron por cuerpo; 0 por carpeta; fechas idénticas a las anteriores. Columna `periodo_fuente` en la base. 3 pruebas nuevas |
| 2026-10-08 | F1-C04 % sin revisión | `scripts/medir_automatizacion.py`: **51,6 %** (399/773), bajo el mínimo de 60 %. Atípicos 35,2 %, SIN_SERIE 12,2 %, baja confianza 1,0 %. **Los 272 atípicos usan mediana de 3 periodos; ninguno usa la regla anual**, que por tanto no se ha ejercido nunca con estos datos |

| 2026-10-08 | F1-D03, F1-V05, F1-V07 Almacén y compuerta | `src/storage/repositorio.py` (SQLite) + `scripts/cargar_almacen.py` + etapa `almacen` en el pipeline. Ciclo `EN_REVISION → CONFIRMADO → OFICIAL`; historial con cadena de hash que detecta alteración. 10 pruebas nuevas. Datos reales: 773 filas cargadas, **399 oficiales, 374 en revisión**. Cierra el núcleo de H4; H3 queda pendiente de interfaz y de autenticación (F1-V06, F1-S02) |
| 2026-10-08 | F1-F02, F1-D01 (parcial) | `docs/Reglas_de_Negocio.md` (13 reglas, cada una con su prueba) y `docs/Modelo_de_Datos.md` (implementado vs. pendiente) |

| 2026-10-08 | F1-V03, F1-V04, F1-C01 (parcial) | `src/processor/validacion.py`: reglas R-02, R-03, R-04, R-06, R-12 extraídas de `main()` a funciones puras, con 11 pruebas (incluida la rama anual). Comportamiento preservado: 773 filas, 272 atípicos, 399 OK. Nuevo: 43 facturas etiquetadas "N° factura no identificado"; 0 inconsistencias de unidad |

Suite: 53 pruebas pasan (eran 22). Cobertura pendiente de F1-C01: consolidación (`consolidar_base.py`) y extractores de los 6 formatos CSU restantes.

---

## Anexo — Limitaciones de este plan

- Los responsables son los roles de las fuentes. Solo el LÍDER y el SPONSOR tienen nombre; el equipo de desarrollo y los demás roles están **por asignar**.
- Los esfuerzos son relativos (S/M/L), no horas. Ninguna fecha está estimada.
- **[Mejora propuesta]** no está respaldada por las fuentes: SQLite (F1-D03), auditoría con hash (F1-V07), detección de drift (F1-V10), plantillas declarativas (F1-V18), datos anonimizados (F1-S05), entorno reproducible (F1-I01), contingencia y capacitación (F1-O04, F1-O05). Se pueden descartar sin romper ningún requerimiento explícito, salvo que se reemplacen por otra solución para H3 y H4.
- Los conteos (63 actividades de Fase 1, 18 de Fase 2, 58 requerimientos) se refieren a este documento. Las cifras de AUD y del plan original (≈52% sin revisión, 803 PDF, 22 pruebas) no se re-verificaron ejecutando el pipeline.
- La Ficha no deja leer las casillas Sí/No; F1-G01 incluye revisarlas a mano.

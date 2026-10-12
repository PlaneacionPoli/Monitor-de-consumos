# Auditoría de requerimientos — Monitor de Consumos Ambientales

**Fecha:** 2026-10-07 · **Objeto evaluado:** `Plan_Primera_Revision.md`
**Fuentes de referencia:** *Propuesta* (P) y *Ficha de Iniciativa* (F). Se citan por sección: `P§5` = Propuesta, sección 5; `F§3` = Ficha, sección 3.
**Contraste adicional:** el plan se verificó contra el código (`scripts/`, `src/`, `tests/`) para saber si lo que declara hecho existe. Donde difieren, se indica.

Estados: 🟢 Completo · 🟡 Parcial · 🔴 Ausente · ⚠️ Ambiguo · ➕ En el plan sin respaldo en las fuentes.
(Nota: el prompt original se cortó en la definición de ⚠️; se asumió "referencia que no permite determinar el alcance o la intención".)

---

## 1. Veredicto

El plan **cubre bien el núcleo técnico de extracción** (Enel, EAAB, EPM y CSU, con pruebas) y es honesto sobre los bloqueos de Fase 0. **No representa de forma suficiente el alcance completo** de las fuentes. Hay cuatro brechas estructurales:

1. **Gobierno de la iniciativa.** F§1, §8, §9 y §10 tienen sponsor, fechas, presupuesto, equipo y concepto de Jurídica, Tecnología, Talento Humano y GEV en "por definir" o vacíos. El plan lo reconoce como riesgo, pero no tiene ninguna actividad para resolverlo.
2. **Mitad de las entregas al usuario.** Faltan los KPIs ambientales (kWh/m², m³/persona, huella), el reporte GreenMetric/GEI, el PDF ejecutivo, la notificación por correo o mensaje y el control de acceso por rol. Los tres primeros están bloqueados por datos maestros que nadie tiene asignados; los dos últimos no tienen tarea.
3. **El estado "✅" del DoD está sobredeclarado.** Ver §4. Varias evidencias no prueban lo que el criterio exige (precisión contra el PDF original, lote operado por el Analista, confirmación previa a la consolidación).
4. **El plan no es consistente consigo mismo.** Tiene secciones numeradas dos veces, tareas hechas en Fase 1 que siguen abiertas en Fase 2, cifras que cambian (738/243 → 773/272) y una línea duplicada.

**Hallazgos de mayor riesgo, verificados en código:**

| # | Hallazgo | Evidencia |
|---|---|---|
| H1 | **El detector de faltantes no detecta un mes faltante.** Mide el hueco entre `periodo_fin` consecutivos y alerta solo si es > 62 días. Una factura mensual ausente deja un hueco de 59–61 días, así que **nunca alerta**. El "0 faltantes" del plan no prueba que la serie esté completa, sino que la regla no puede disparar. Tampoco compara contra una "fecha esperada" (hoy), así que la factura del mes en curso que no llegó es invisible. | `scripts/generar_alertas.py:20,38-41` |
| H2 | **La "confianza" no es la confianza de OCR de P§9.4.** Es un indicador de completitud (periodo, consumo y valor no nulos). Un valor mal leído pero presente tiene confianza "alta". El umbral de 90% no se puede aplicar. | `scripts/validar_atipicos.py:43-49` |
| H3 | **La auditoría de ediciones no está conectada a nada.** `registrar_revision` solo la llama la prueba unitaria. No hay interfaz de revisión ni de edición, `revisor` es un texto libre sin autenticación, y el CSV es editable. P§9.6 exige "ninguna modificación sin registro"; hoy se cumple solo porque no existe forma de modificar. | `grep registrar_revision`; `src/utils/auditoria.py` |
| H4 | **Se consolida antes de confirmar.** El orden es consolidar → validar, y la base oficial incluye filas marcadas. P§5 exige consolidar "solo tras la confirmación del Analista SGA". Hoy la "base oficial" y la "base por revisar" son el mismo archivo con una columna `estado`. | `pipeline.py`, orden de etapas |
| H5 | **La prueba de control no valida lo que dice el DoD.** El 100% (50/50) compara **solo EPM energía, marzo 2025**, contra la hoja manual, no contra el PDF original (P§12 exige "verificada contra el PDF original en consumo, período y valor"). Enel, EAAB y las CSU no tienen medición de precisión. El protocolo de Fase 3 sigue sin marcar. | `scripts/prueba_control.py:1-15` |
| H6 | **El "lote < 2 h" mide el tiempo de máquina (2 min 36 s), no el tiempo del Analista.** El propio plan admite que falta la corrida con el Analista, pero el DoD aparece como ✅. | Plan §6 |
| H7 | **El % de facturas sin revisión no se calcula, y las cifras del plan sugieren que no llega al mínimo.** Con 399 OK de 773 filas son ≈52%, frente a una meta de ≥80% y un mínimo de ≥60%. La causa principal son las series de 11 meses sin comparación anual. | Plan §Fase 1, "Confianza de extracción" |
| H8 | **El periodo EPM se infiere de la carpeta.** P§9.1 prohíbe usar la fecha de recepción. El plan mismo documenta que la carpeta es el mes de recepción. El año y mes de carpeta se usan como respaldo cuando el texto no trae año, lo que viola la regla en los casos más difíciles. | `batch_epm.py:28-49`; plan, corrección del 2026-10-07 |
| H9 | **Premisa de fuente contradicha.** P§4 y F§3 dicen que Acueducto Bogotá tiene "alta proporción de imagen escaneada". La muestra tiene 801 de 803 PDF digitales. Es una buena noticia, pero conviene confirmar con el SGA si los lotes futuros seguirán así antes de dar el OCR por resuelto. | Plan §1 |
| H10 | **Alcance geográfico y de servicios ampliado sin decisión registrada.** F habla de "Bogotá y Medellín"; P§4 lista "CSU propias (Bogotá)". El plan procesa 10 CSU en 8 ciudades. Además introduce gas propano y combustibles, que no están en las fuentes (P§8 solo excluye "combustible consumido" y "papel" como KPI). Es posible que la ampliación sea correcta, pero no hay una decisión de alcance que la respalde. | Plan §1, §4 |

---

## 2. Catálogo de requerimientos

Todos son **explícitos** (se citan con sección) salvo los marcados 💡 *recomendado*. Los 💡 son mi propuesta: no están en las fuentes y se justifican en la columna "Evidencia / justificación".

### 2.1 Funcionales

| ID | Requerimiento | Fuente | Evidencia / justificación | Prioridad |
|---|---|---|---|---|
| REQ-F-001 | Ingestar PDF de Enel, EPM, Acueducto y CSU por correo **o** carpeta compartida | P§5.1; P§4 | "por correo o carpeta compartida" | Alta |
| REQ-F-002 | Extraer consumo (m³/kWh/kg), valor facturado, periodo, nº de factura y sede | P§5.2; F§2-3 | Lista explícita de campos | Alta |
| REQ-F-003 | El periodo se toma del cuerpo de la factura, nunca de la fecha de recepción | P§5.2; P§9.1 | "nunca" | Alta |
| REQ-F-004 | Aplicar OCR a PDF imagen y registrar la confianza por campo | P§5.2; P§9.4 | "registra el nivel de confianza de cada campo" | Alta |
| REQ-F-005 | Separar la factura unificada de EPM en 3 componentes (agua, energía, aseo) como registros independientes | P§5.3; P§9.2; F§3 | Explícito | Alta |
| REQ-F-006 | Validar que la unidad corresponda al componente (m³ agua, kWh energía, $/kg aseo) | P§5.4 | Primera regla de validación | Media |
| REQ-F-007 | Marcar "dato atípico — verificar" toda variación > 20% frente al mismo periodo del año anterior | P§5.4; P§9.3; F§3 | Explícito | Alta |
| REQ-F-008 | Registrar siempre el nº de factura; si falta, marcar "N° factura no identificado" sin rechazar | P§5.4; P§9.5 | Explícito | Alta |
| REQ-F-009 | Control de duplicados con el nº de factura como identificador único | P§9.5 | "control de duplicados" | Media |
| REQ-F-010 | Consolidar en base unificada por componente, sede, **ciudad** y periodo, **solo tras confirmación del Analista SGA** | P§5.5; F§3 | Explícito | Alta |
| REQ-F-011 | Calcular kWh/m², m³/persona, variación y huella de carbono | P§5.6; P§8; F§3 | Requiere datos maestros | Alta |
| REQ-F-012 | Calcular el costo asociado a sobreconsumo | P§8 | Marcado "KPI adicional recomendado" en la propia Propuesta | Baja |
| REQ-F-013 | Alertar factura faltante en la fecha esperada, respetando la periodicidad mensual/bimensual por sede | P§5.7; P§9.7 | Explícito | Alta |
| REQ-F-014 | Alertar consumo atípico | P§5.7; F§3 | Explícito | Alta |
| REQ-F-015 | Enrutar a revisión humana todo dato atípico o con confianza OCR < 90% antes de entrar a la base oficial | P§5.8; P§9.4 | Explícito | Alta |
| REQ-F-016 | Auditar toda modificación manual: quién, cuándo, valor original vs. nuevo | P§5.8; P§9.6; F§3 | Explícito | Alta |
| REQ-F-017 | Tablero HTML interactivo: KPIs, tendencias, semáforo de alertas, comparativo por sede/ciudad | P§6; P§5.9 | Explícito | Alta |
| REQ-F-018 | Exportar los insumos para el reporte GreenMetric y el inventario GEI | P§5.9; P§6; F§3 | La propia P§14 lo ubica en "fase posterior" | Media |
| REQ-F-019 | El Coordinador SGA descarga la base validada y exporta reportes | P§3 | Tabla de actores | Media |
| REQ-F-020 | La Dirección/Gerencia consulta el resumen ejecutivo y descarga el PDF ejecutivo | P§3 | Tabla de actores | Media |
| REQ-F-021 | Revisión manual del primer uso por prestador | P§11 (fila "error de OCR en un dígito") | Mitigación explícita | Media |

### 2.2 Datos

| ID | Requerimiento | Fuente | Evidencia / justificación | Prioridad |
|---|---|---|---|---|
| REQ-D-001 | Datos maestros por sede: m² y población (colaboradores/estudiantes) | P§4 | "entrada adicional necesaria", "a definir con Infraestructura" | Alta |
| REQ-D-002 | Histórico ≥ 12 meses cargado **antes del MVP**, desde las bases Excel manuales | P§4; P§11; P§14 sem. 2; F§7 | Explícito | Alta |
| REQ-D-003 | Trazabilidad de cada factura en la base (nº de factura, archivo, sede, periodo) | P§6 | "con trazabilidad de cada factura" | Alta |
| REQ-D-004 | Definir la unidad y el tratamiento del componente aseo: kg (F§2) o $ (P§6, P§5.4 "$/kg") | F§2; P§5.4; P§6 | **Contradicción entre las fuentes** | Alta |
| REQ-D-005 | Cobertura: sedes y CSU de Bogotá y Medellín | F§3; P§4 | P§4 "CSU propias (Bogotá)" | Alta |
| REQ-D-006 | 💡 Catálogo oficial sede ↔ dirección ↔ cuenta/contrato, validado por el SGA | Recomendado | Sin él no hay "por sede", ni calendario por sede, ni datos maestros | Alta |
| REQ-D-007 | 💡 Versionado y retención de la base oficial y de los PDF de origen | Recomendado | Hoy los Excel se acumulan por timestamp y se toma "el último" por orden alfabético | Media |

### 2.3 No funcionales y metas

| ID | Requerimiento | Fuente | Evidencia / justificación | Prioridad |
|---|---|---|---|---|
| REQ-NF-001 | Tiempo mensual del Analista ≤ 2 h (mínimo < 4 h) | F§2; P§7; P§12 | Meta y mínimo | Alta |
| REQ-NF-002 | Precisión de extracción ≥ 98% de campos correctos (mínimo ≥ 95%), verificada contra el PDF original en consumo, periodo y valor | P§7; P§12; F§3 | Explícito | Alta |
| REQ-NF-003 | ≥ 80% de facturas procesadas sin revisión manual (mínimo ≥ 60%) | P§7; F§3 | Explícito | Alta |
| REQ-NF-004 | Detección de variación atípica < 1 día (mínimo < 3 días) | P§7; F§7 | Explícito | Media |
| REQ-NF-005 | Satisfacción del equipo SGA (NPS) ≥ 8 (mínimo ≥ 6) | P§7; P§14 sem. 6-8 | Explícito | Baja |
| REQ-NF-006 | Precisión de consolidación > 98% y alertas atendidas > 90% | P§7 | "Meta institucional original" | Media |
| REQ-NF-007 | Operación autónoma: el Analista procesa un lote sin ayuda de TI en < 2 h | P§12 | DoD | Alta |
| REQ-NF-008 | Plantilla de extracción por prestador, **actualizable**, porque el formato puede cambiar sin aviso | P§11 | Mitigación explícita | Alta |
| REQ-NF-009 | La base generada coincide con la base manual del mes anterior (prueba de control) | P§12 | DoD | Alta |
| REQ-NF-010 | 💡 Detección automática de cambio de formato por prestador (caída de campos extraídos) | Recomendado | El riesgo de F§7 es "sin previo aviso"; sin detección el fallo es silencioso | Media |

### 2.4 Seguridad, integración, arquitectura y tecnología

| ID | Requerimiento | Fuente | Evidencia / justificación | Prioridad |
|---|---|---|---|---|
| REQ-SEG-001 | Solución local/institucional; no cargar facturas en servicios cloud no autorizados; validar con TI | F§7; P§11 | Explícito | Alta |
| REQ-SEG-002 | Acceso por rol: el tablero de Medellín solo ve su sede; Gestión Administrativa no accede al sistema; Dirección solo consulta | P§3 | Implícito en la tabla de actores | Media |
| REQ-SEG-003 | 💡 Revisor identificado y autenticado en el log de auditoría; log protegido contra edición | Recomendado | "Quién" no tiene valor probatorio si es texto libre | Alta |
| REQ-SEG-004 | 💡 Protección de datos personales de las facturas (identificación, dirección, NIT) | Recomendado | El extractor los captura. Aplica Ley 1581/2012. Validar con Jurídica | Media |
| REQ-INT-001 | Canal de notificación (correo/mensaje) para alertas, con tiempo "inmediato" | P§6 | "Correo / mensaje · Inmediata" | Alta |
| REQ-INT-002 | Soporte e infraestructura de TI para la herramienta OCR/IA | F§9 | Rol "Gerencia de TI" | Media |
| REQ-INT-003 | Insumos para GreenMetric/GEI | P§5.9 | Ver REQ-F-018 | Media |
| REQ-TEC-001 | Extracción con OCR **e inteligencia artificial**; elegir la herramienta (proveedor por definir) | F§2, F§8; P§14 sem. 2 | La Ficha lo declara en el objetivo | Alta |
| REQ-ARQ-001 | El tablero es HTML interactivo | P§6 | Formato explícito | Media |

### 2.5 Operativos, gobierno y evolución

| ID | Requerimiento | Fuente | Evidencia / justificación | Prioridad |
|---|---|---|---|---|
| REQ-OPS-001 | Protocolo de envío con fecha límite para Gestión Administrativa (Bogotá) y Coordinación (Medellín) | P§11; P§14 sem. 1; P§1 | Explícito | Alta |
| REQ-OPS-002 | Definir SLA de respuesta ante un hallazgo y el escalamiento automático | P§10 | "Pendiente de definir" | Alta |
| REQ-OPS-003 | Relevar el formato de cada prestador | P§14 sem. 1 | Explícito | Media |
| REQ-OPS-004 | Medir KPIs de impacto y NPS en las semanas 6-8 | P§14 | Explícito | Media |
| REQ-OPS-005 | 💡 Capacitación y manual de operación para el Analista SGA | Recomendado | REQ-NF-007 exige autonomía; sin capacitación no es verificable | Media |
| REQ-OPS-006 | 💡 Plan de contingencia si un lote falla o un prestador cambia de formato | Recomendado | Riesgo "Alto" en P§11 sin responsable | Baja |
| REQ-GOB-001 | Definir sponsor, fechas, presupuesto (6 rubros), equipo y dedicaciones | F§1, §8, §9 | "Por definir" | Alta |
| REQ-GOB-002 | Obtener concepto de Jurídica, Tecnología, Talento Humano y GEV | F§10 | Casillas vacías | Alta |
| REQ-GOB-003 | Línea base de precisión (F la deja "pendiente por definir") | F§3 | Explícito | Media |
| REQ-GOB-004 | Dejar fuera de alcance: IoT, captura operativa (Propuestas 2 y 3), combustible y papel | P§8; P§13 | Explícito | Media |
| REQ-GOB-005 | Confirmar las condiciones de F§1 (exigencia legal, desarrollo tecnológico, plan de mejoramiento) | F§1 | Las casillas Sí/No **no son legibles en la extracción**; hay que revisarlas a mano en el .docx | Baja |

---

## 3. Matriz de trazabilidad

| ID | Evidencia en el plan | Cobertura | Observación |
|---|---|---|---|
| REQ-F-001 | Fase 4 "ingesta por carpeta compartida" (sin marcar); correo → fase posterior; el watcher existe pero no exporta | 🟡 | Hoy los lotes leen carpetas fijas de `data/raw`. P§5.1 admite "carpeta compartida" como alternativa válida, pero no hay diseño |
| REQ-F-002 | Extractores por prestador (11 formatos), Fase 1 | 🟡 | Cubre consumo kWh/m³, valor, periodo, factura. **No hay consumo en kg ni componente aseo** (ver REQ-D-004). Air-e sin consumo (8 filas) |
| REQ-F-003 | Reglas del plan §2; corrección EPM 2026-10-07 | 🟡 | Se cumple en Enel/EAAB/CSU. En EPM el mes/año se completa con la **carpeta** (H8) |
| REQ-F-004 | OCR para 2 PDF imagen; `confianza` en `validar_atipicos.py` | 🟡 | La confianza es completitud, no confianza de OCR (H2). No hay confianza por campo ni umbral 90% real |
| REQ-F-005 | 571 energía + 60 acueducto EPM | 🟡 | **Aseo no se separa**; la decisión de alumbrado/aseo sigue en Fase 0. El "valor" EPM incluye alumbrado (+$28.000) |
| REQ-F-006 | — | 🔴 | Sin tarea ni código. Es una regla barata y evitaría errores de componente |
| REQ-F-007 | Fase 1: 243→272 atípicos con severidad; Fase 2: regla sin marcar | 🟡 | Operativa, pero con mediana-3 como suplente en las series de 11 meses. Esto infla los atípicos (≈35% de las filas) y es la razón de H7 |
| REQ-F-008 | Fase 2 "fallback N factura no identificado" (sin marcar) | 🟡 | En el código solo existe un comentario; **no hay etiqueta literal** en la base |
| REQ-F-009 | Dedup (factura + prestador); luego + servicio | 🟢 | Ajuste justificado (pares energía/acueducto de EPM). La Propuesta debería actualizarse |
| REQ-F-010 | Criterio de aceptación 3; `ColaRevision` | 🟡 | H4: la base se consolida antes de confirmar. Falta un estado "confirmado" y una compuerta |
| REQ-F-011 | Plan §2 pto. 6; Fase 3B bloqueada | 🟡 | Identificado y bloqueado, pero sin diseño ni responsable. Faltan factores de emisión para huella |
| REQ-F-012 | Solo mencionado en §2 | 🟡 | Sin tarea. Es de baja prioridad, pero está en la tabla de metas |
| REQ-F-013 | `generar_alertas.py`; Calle 84 | 🟡 | **H1**: no detecta un mes faltante ni compara contra fecha esperada. No hay calendario por sede |
| REQ-F-014 | `alertas_*.xlsx` hoja Atipicos | 🟡 | Se genera un archivo; no hay notificación (REQ-INT-001) |
| REQ-F-015 | Cola de revisión (hoja de Excel) | 🟡 | Sin interfaz de aprobación. Depende de H2 para el umbral de 90% |
| REQ-F-016 | `auditoria.py` + prueba unitaria | 🟡 | H3: función aislada, sin punto de uso ni autenticación |
| REQ-F-017 | Dashboard Dash con datos reales, filtro por sede | 🟡 | Dash necesita servidor; P pide "HTML interactivo" (entregable de una pieza). Sin comparativo ciudad, sin semáforo documentado, KPIs ambientales pendientes |
| REQ-F-018 | Fase 3B / Fase 4, "bloqueado por Fase 0" | 🟡 | P§14 lo ubica en fase posterior, así que es una prioridad legítimamente baja. Aun así debería tener una fecha |
| REQ-F-019 | — | 🔴 | El Excel existe; falta definir cómo lo descarga el Coordinador |
| REQ-F-020 | — | 🔴 | No hay mención de PDF ejecutivo ni vista de Dirección |
| REQ-F-021 | — | 🔴 | No está contemplado el primer uso supervisado por prestador. Hay 11 formatos nuevos que lo necesitan |
| REQ-D-001 | Fase 0 (sin responsable ni fecha) | 🟡 | Es el bloqueo crítico de F-011, F-012 y F-018 |
| REQ-D-002 | §3 "histórico: 10%"; energía Bogotá trae ~12 meses | 🟡 | No hay tarea para cargar los Excel históricos de Bogotá/CSU/agua. Es prerrequisito del MVP según P§4 |
| REQ-D-003 | Columnas `factura`, `archivo`, `periodo`, `sede` en `base_unificada` | 🟡 | No hay columna `ciudad` ni `confianza` en la base consolidada. Esquema de salida pendiente (Fase 0) |
| REQ-D-004 | Fase 0: "alumbrado público y aseo Emvarias" | ⚠️ | El plan trata el aseo como un detalle de EPM. Las fuentes se contradicen en kg vs. $, y nadie lo ha escalado |
| REQ-D-005 | §1: 10 CSU, 8 ciudades | ➕ | H10. Ampliación no respaldada. Hay que registrar la decisión |
| REQ-D-006 | `catalogo_sedes.py`: 63/64 mapeadas | 🟡 | Buen avance. Falta la confirmación del Analista (`sede_confirmada` vacía) |
| REQ-D-007 | — | 🔴 | Los archivos se acumulan y `ultimo()` toma el mayor nombre. No hay versión "oficial" ni retención |
| REQ-NF-001 | §6: 2 min 36 s de máquina | 🟡 | H6. Falta medir el tiempo humano |
| REQ-NF-002 | §6: 100% (50/50) | 🟡 | H5. Solo EPM, solo contra el manual |
| REQ-NF-003 | — | 🔴 | Sin métrica. Con las cifras del plan sería ≈52% (H7) |
| REQ-NF-004 | Fase 4 "medición" (sin marcar) | 🟡 | Sin medición |
| REQ-NF-005 | — | 🔴 | Sin encuesta NPS |
| REQ-NF-006 | — | 🔴 | "Alertas atendidas" depende del SLA (REQ-OPS-002), que está pendiente |
| REQ-NF-007 | DoD "lote autónomo" | 🟡 | H6 |
| REQ-NF-008 | Fase 2 "plantillas conectadas a `config.yaml` (hoy decorativo)" | 🟡 | Los extractores son regex en Python. Actualizar requiere un desarrollador, no una plantilla |
| REQ-NF-009 | Prueba de control marzo 2025 | 🟡 | Solo EPM energía (H5). Falta la prueba mensual repetible |
| REQ-NF-010 | — | 🔴 | 💡 Recomendado |
| REQ-SEG-001 | Fase 0 "validación TI"; riesgo en §6 | 🟡 | El diseño local lo favorece, pero falta el visto bueno de TI. Si la herramienta de IA fuera externa, el requisito cambia (ver REQ-TEC-001) |
| REQ-SEG-002 | ADR-004 / README (Keycloak) | 🔴 | **Documentado, no implementado** (0 imports). El plan no lo trata |
| REQ-SEG-003 | — | 🔴 | H3 |
| REQ-SEG-004 | — | 🔴 | 💡 Recomendado. Riesgo del plan: "xlsx locales sin control de acceso" lo menciona sin mitigación |
| REQ-INT-001 | — | 🔴 | No hay canal de notificación; las "alertas" son hojas de Excel |
| REQ-INT-002 | Menciona "TI" en Fase 0 solo para la restricción cloud | 🟡 | Sin soporte de infraestructura ni responsable |
| REQ-INT-003 | Ver REQ-F-018 | 🟡 | |
| REQ-TEC-001 | Tesseract + regex | ⚠️ | F§2 promete OCR **e IA**. El plan usa solo OCR y reglas, y nunca decide si eso basta. ADR-002 existe, pero el plan no lo cita |
| REQ-ARQ-001 | Dash | 🟡 | Ver REQ-F-017 |
| REQ-OPS-001 | Fase 4 (sin marcar) | 🟡 | Sin borrador de protocolo ni fecha |
| REQ-OPS-002 | Fase 0 | 🟡 | Pendiente. Bloquea REQ-NF-006 |
| REQ-OPS-003 | Fase 1, completada | 🟢 | |
| REQ-OPS-004 | Fase 4 | 🟡 | |
| REQ-OPS-005 | — | 🔴 | 💡 |
| REQ-OPS-006 | — | 🔴 | 💡 |
| REQ-GOB-001 | Solo en el riesgo "Iniciativa sin aprobación formal" | 🟡 | Se reconoce, pero no hay actividad ni responsable |
| REQ-GOB-002 | — | 🔴 | Jurídica y TI son bloqueantes de SEG-001 y SEG-004 |
| REQ-GOB-003 | — | 🔴 | |
| REQ-GOB-004 | "Fase posterior", registro de decisiones | 🟢 | Bien documentado. Aclarar que **gas propano no es un requisito de las fuentes** |
| REQ-GOB-005 | — | ⚠️ | Verificar en el .docx |

### Resumen de cobertura

| Estado | Cantidad | % |
|---|---|---|
| 🟢 Completo | 3 | 5% |
| 🟡 Parcial | 34 | 59% |
| 🔴 Ausente | 17 | 29% |
| ⚠️ Ambiguo | 3 | 5% |
| ➕ Sin respaldo en fuentes (REQ-D-005) | 1 | 2% |

*(58 requerimientos, 7 de ellos recomendados. Seis de los 7 recomendados caen en 🔴: es esperable, porque nacen de huecos que el plan no vio.)*

---

## 4. Estado del DoD (P§12): lo que el plan declara frente a lo que prueba la evidencia

| Criterio | Plan | Evaluación | Qué falta para que sea cierto |
|---|---|---|---|
| ≥ 1 factura real por prestador | ✅ | 🟢 **Cierto** | — |
| Precisión ≥ 95% en consumo, periodo y valor, contra el PDF original | ✅ 100% | 🟡 **Sobredeclarado** (H5) | Muestra estratificada por prestador (≥ 30 facturas), cotejo con el PDF, y informe por campo |
| Validación ±20% con el histórico cargado | ✅ | 🟡 **Parcial** | El histórico de 12 meses no está completo. Hoy se usa la mediana-3 como suplente |
| Base generada == base manual del mes anterior | ✅ | 🟡 **Parcial** | Solo EPM energía de marzo 2025. Falta Bogotá/CSU/agua, y un mes "anterior" real |
| Lote autónomo < 2 h sin TI | ✅ | 🔴 **No demostrado** (H6) | Corrida cronometrada con el Analista, incluyendo la revisión |
| Tablero correcto del mes de prueba | ✅ | 🟡 **Parcial** | Validación con el Coordinador SGA (el propio plan la deja sin marcar) |

**Criterios de aceptación del plan (§5):** el criterio 3 ("ninguna fila marcada entra a la base oficial sin confirmación") **no se cumple hoy** (H4). El criterio 4 (Calle 84 sin falsas alertas) se cumple trivialmente, porque el detector tampoco alerta ante faltantes reales (H1).

---

## 5. Problemas internos del plan

1. **Numeración duplicada.** Las secciones §5, §6 y §7 aparecen dos veces (DoD / Criterios / Roadmap / Riesgos / Decisiones).
2. **Estado contradictorio.** Marcado como hecho en Fase 1 y abierto en Fase 2: regla de atípicos, confianza y umbral, deduplicación, catálogo sede←dirección y log de auditoría. No se sabe qué falta realmente.
3. **Línea duplicada** en Fase 3B: "KPIs ambientales … bloqueado por maestros de sede" aparece dos veces.
4. **Cifras que cambian sin explicación.** 738 filas / 715 evaluables / 243 atípicos (Fase 1) frente a 773 filas / 272 atípicos (confianza). La suma de la distribución final (399+272+94+8+1) da 774, no 773.
5. **§3 es una foto del 2026-10-06** (extracción Enel/CSU "0%", pruebas "inexistentes") y quedó superada por Fase 1. Un lector que mire solo esa tabla se lleva una imagen falsa.
6. **Fase 0 sin dueño ni fecha.** Seis decisiones que bloquean el diseño, ninguna con responsable. El registro de decisiones dice "Pendiente".
7. **README, `config.yaml` y los ADR** describen FastAPI, Dagster, MySQL, Keycloak y plantillas YAML que no existen. El plan sugiere "recortar o calendarizar", pero no lo hace; es una deuda de documentación que un auditor externo leería como incumplimiento.
8. **Typo:** "RecibOS Energía sedes" (§1).

---

## 6. Recomendaciones priorizadas

### Crítico: corregir antes de declarar cumplido el DoD

| # | Acción | Cierra |
|---|---|---|
| 1 | **Arreglar el detector de faltantes.** Calcular el periodo esperado por medidor (mensual o bimensual, tomado del catálogo) y comparar contra la fecha de corte del lote. Agregar una prueba con una serie a la que se le quita un mes y verificar que alerta | H1, REQ-F-013 |
| 2 | **Separar "base por revisar" de "base oficial".** Agregar la compuerta de confirmación: solo las filas con `decision` en `auditoria.csv` pasan a la oficial | H4, REQ-F-010 |
| 3 | **Conectar la auditoría a una interfaz de revisión** (aunque sea una hoja de cálculo con validación de datos y un script que aplica las decisiones), con identidad del revisor tomada del sistema operativo o del login | H3, REQ-F-015/016, SEG-003 |
| 4 | **Medir la precisión como la define P§12**: muestra por prestador, cotejo con el PDF original, tabla por campo. Reemplazar el "100% (50/50)" por esa medición | H5, REQ-NF-002 |
| 5 | **Calcular el % sin revisión y reportarlo.** Si es ≈52%, decirlo y documentar el plan para llegar a ≥ 60% (cargar los 12 meses de histórico es la palanca principal) | H7, REQ-NF-003 |
| 6 | **Cronometrar una corrida con el Analista SGA** y cambiar el DoD de ✅ a "pendiente" hasta entonces | H6 |

### Alto: decisiones que desbloquean el trabajo (Fase 0 con dueño y fecha)

7. Asignar responsable y fecha a cada decisión de Fase 0. La más urgente es **datos maestros** (m² y población), porque bloquea 3 requerimientos.
8. Resolver la contradicción **kg vs. $** del aseo (REQ-D-004) con el SGA y registrar la decisión.
9. Registrar una **decisión de alcance** sobre las 10 CSU fuera de Bogotá y sobre gas/combustibles (H10), o reducir el alcance a lo que dicen las fuentes.
10. Decidir qué se entiende por "IA" (REQ-TEC-001). Si bastan OCR y reglas, actualizar la Ficha; si no, definir el componente de IA y volver a evaluar la restricción cloud.
11. Convertir el riesgo "iniciativa sin aprobación formal" en un entregable: sponsor, fechas, presupuesto y conceptos de Jurídica y TI (REQ-GOB-001/002).

### Medio

12. Implementar la validación unidad↔componente (REQ-F-006): es barata.
13. Poner una etiqueta literal "N° factura no identificado" en la base (REQ-F-008).
14. Agregar canal de notificación por correo (REQ-INT-001). Es lo mínimo para que "alerta inmediata" sea cierta.
15. Cargar el histórico de 12 meses de todas las sedes, no solo EPM (REQ-D-002).
16. Dejar de inferir el periodo de EPM desde la carpeta; si el texto no trae año, marcar `REVISION` (H8).
17. Definir control de acceso por rol, o retirar Keycloak del README y documentarlo como fase posterior (REQ-SEG-002).
18. Agregar pruebas de `consolidar_base`, `validar_atipicos` y `generar_alertas`: hoy las 22 pruebas cubren solo funciones puras de extracción.

### Higiene del plan

19. Reordenar la numeración, eliminar la duplicación, sincronizar Fase 1 y Fase 2, y refrescar la tabla de §3.
20. Añadir al plan **esta matriz de trazabilidad** (o un enlace a ella), de modo que cada tarea cite un `REQ-*`.

---

## 7. Limitaciones de esta auditoría

- Las casillas Sí/No de F§1, F§5 y F§6 no son legibles en la extracción del .docx. No se evaluaron los grupos de interés ni los sistemas de gestión impactados.
- No se ejecutó el pipeline ni las pruebas. Las cifras del plan se tomaron tal cual y solo se verificó que el código respalde la lógica, no que reproduzca los números.
- El prompt original llegaba cortado en la definición de ⚠️ y no incluía las etapas posteriores a la matriz (que probablemente pedían hallazgos, riesgos y recomendaciones). Se cubrieron en §1, §5 y §6; si había secciones adicionales, conviene enviarlas.
- Las prioridades son criterio mío, aplicado sobre la importancia que le dan las fuentes. Los ítems 💡 son propuestas y no deben tratarse como requisitos contractuales hasta que el SGA los acepte.

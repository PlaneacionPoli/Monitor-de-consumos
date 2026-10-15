# Catálogo de reglas de negocio (F1-F02)

Fuente: Propuesta (P) y Ficha (F). **Estado** indica si la regla está implementada, y **Prueba** qué la verifica. Una regla sin prueba automatizada se marca ❌: es deuda de F1-C01.

| ID | Regla | Origen | Implementación | Prueba | Estado |
|---|---|---|---|---|---|
| R-01 | El periodo sale del cuerpo de la factura, nunca de la fecha de recepción. En EPM el año sale de "Fecha de generación" / "facturación <mes> de <año>"; si falta, se usa la carpeta y la fila se marca `REVISION_PERIODO_INFERIDO` | P§5.2, P§9.1 | `batch_epm.resolver_periodo_epm`, `validacion.validar_base` | `test_epm_periodo_*`, `test_periodo_inferido_*` | ✅ |
| R-02 | Unidad coherente con el componente (m³ agua, kWh energía, $/kg aseo) | P§5.4 | `validacion.marcar_unidad` → `REVISION_UNIDAD` | `test_unidad_incoherente_*` | ✅ el aseo ($/kg) espera DEC-03; 0 inconsistencias en los datos reales |
| R-03 | Atípico = variación > 20 % **y** > 3 desviaciones robustas (MAD). Con el mismo mes del año anterior se compara contra él (`anual`); sin él, el consumo **por día** se compara contra la mediana de la serie (`mad`) o, con ≥ 5 contratos comparables ese mes, contra la serie normalizada por los pares (`mad_pares`, descuenta la estacionalidad común). Los atípicos se omiten de la referencia; un salto sostenido de ≥ 3 periodos (cambio de nivel) no repite la alerta; series de < 6 periodos se marcan `serie corta`. Severidad ALTA si > 50 % | P§9.3, F§3 | `validacion.marcar_atipicos` | `test_atipico_*`, `test_variacion_*`, `test_el_umbral_*`, `test_consumo_cero_*`, `test_serie_por_medidor_*`, `test_cambio_de_nivel_*`, `test_estacionalidad_*`, `test_pico_solo_*`, `test_serie_corta_*` | ✅ la rama anual está probada con datos sintéticos, pero **no se ha ejercido con datos reales** (no hay 12 meses de histórico) |
| R-04 | Sin nº de factura → "N° factura no identificado", sin rechazar. La clave de unicidad lo trata como ausente | P§5.4 | `validacion.etiquetar_factura` | `test_factura_ausente_*` | ✅ 43 filas reales etiquetadas |
| R-05 | Identificador único = (prestador, servicio, factura); sin factura, (prestador, servicio, sede, archivo). El servicio forma parte de la clave porque una factura unificada EPM produce una fila por servicio | P§9.5 | `repositorio.clave_registro`, `consolidar_base.py` | `test_clave_incluye_servicio_y_cae_a_archivo` | ✅ |
| R-06 | Confianza < 90 % o campo clave ausente (periodo, consumo, valor) → revisión obligatoria. **Hoy "confianza" mide completitud, no confianza de OCR** | P§9.4 | `validacion.validar_base` | `test_confianza_*` | 🟡 F1-V02 |
| R-07 | Facturación bimensual (Calle 84) no genera alerta en los meses sin factura. La cadencia se infiere por medidor y se alerta si un hueco supera 1,5 cadencias o la serie termina antes del corte de su prestador | P§9.7 | `processor/faltantes.py` | `test_faltantes_*` (7) | ✅ cadencia pendiente de confirmar por SGA (F2-05) |
| R-08 | Solo las filas confirmadas entran a la base oficial. Las marcadas esperan al Analista | P§5.5 | `storage/repositorio.publicar_oficial` | `test_compuerta_*`, `test_aprobar_*`, `test_rechazar_*` | ✅ política de auto-confirmación = DEC-13 |
| R-09 | Toda modificación manual deja revisor, fecha, valor original y nuevo; el historial detecta alteración | P§5.8, P§9.6, F§3 | `repositorio.revisar`, cadena de hash | `test_correccion_*`, `test_auditoria_detecta_alteracion` | ✅ el revisor aún es texto libre (F1-S02) |
| R-10 | Un registro OFICIAL no se modifica; un RECHAZADO no se reabre | P§9.6 (derivada) | `repositorio.revisar` | `test_registro_oficial_no_se_modifica` | ✅ [Mejora propuesta] |
| R-11 | Factura unificada EPM → un registro por componente (energía, acueducto, aseo) | P§5.3 | `batch_epm.py` | `test_epm_valor_incluye_alumbrado` | 🟡 aseo no se separa (DEC-03, F1-V09) |
| R-12 | Facturas sin sede identificable (`SIN_SERIE`) no se comparan contra histórico | (derivada de R-03) | `validacion.validar_base` | `test_sin_medidor_*` | ✅ |
| R-13 | Cargas repetidas son idempotentes: no pisan una revisión ya hecha | (derivada de R-09) | `repositorio.cargar_validacion` | `test_recarga_es_idempotente_*` | ✅ [Mejora propuesta] |

## Casos de uso principales (F1-F01)

1. **Procesar el lote mensual.** Entrada: PDF nuevos. Flujo: clasificar → extraer → consolidar → validar → alertas → `cargar_almacen.py`. Salida: filas `CONFIRMADO` (sin hallazgos) y `EN_REVISION`.
2. **Revisar un hallazgo.** El Analista abre la cola, ve valor original y evidencia (archivo), y decide APROBADO / CORREGIDO / RECHAZADO. Alternos: corrige el valor; rechaza.
3. **Publicar la base oficial.** `--publicar` mueve lo confirmado a `OFICIAL`; `--exportar` genera el Excel. Alterno: filas pendientes → no entran.
4. **Atender una alerta de faltante.** Alerta por medidor y periodo esperado → el Analista pide la factura a Gestión Administrativa; llega y se reprocesa (R-13).
5. **Cambio de formato de un prestador.** Pendiente de diseño (F1-V10).

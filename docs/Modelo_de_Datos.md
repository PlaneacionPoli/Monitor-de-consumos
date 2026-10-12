# Modelo de datos (F1-D01)

Almacén local SQLite (`data/outputs/monitor.db`), definido en `src/storage/repositorio.py`.
**Definitivo** = implementado y probado. **Pendiente** = depende de datos o decisiones externas.

## Entidades implementadas (definitivo)

| Entidad | Clave | Contenido | Notas |
|---|---|---|---|
| `lote` | `run_id` (marca de tiempo de la validación) | origen, fecha de carga | Trazabilidad de qué corrida produjo cada fila |
| `registro` | `id`; único `clave` (R-05) | factura, prestador, servicio, sede, cuenta, periodo inicio/fin, consumo, unidad, valor, archivo, `periodo_fuente`, `confianza`, `estado_validacion`, `severidad`, `detalle` | |
| `registro.estado` | — | `EN_REVISION → CONFIRMADO → OFICIAL`; `RECHAZADO` | Ciclo de vida; `confirmado_por` = "AUTO" o el revisor |
| `revision` | `id` | revisor, fecha, `registro_id`, campo, valor original/nuevo, decisión, observación, `hash_prev`, `hash` | Append-only encadenada; `verificar_auditoria()` detecta alteración |

Periodos en ISO `AAAA-MM-DD`. Fechas y horas en hora de Bogotá.

## Entidades pendientes

| Entidad | Por qué falta | Depende de |
|---|---|---|
| `sede`, `medidor` | Hoy `sede` y `cuenta` son texto en `registro`. El catálogo `catalogo_sedes.csv` (63/64) aún no está confirmado | F1-D05, F2-04 |
| `maestro_sede` (m², población, vigencia) | No hay datos | S06 / INFRA (F2-02) |
| `factor_emision` | No hay fuente ni metodología | S07 / SGA-C (F2-03) |
| `alerta` | Las alertas hoy son hojas de Excel | F1-V13 |
| `usuario`, `rol` | Sin autenticación | F1-S02, DEC-06 |
| `ciudad` en `registro` | Se derivará del catálogo de sedes | F1-D05 |

## Pendiente de validar con datos reales

- Qué filas pasan solas a `CONFIRMADO`: hoy solo las de estado `OK` (`AUTOCONFIRMAR`, DEC-13).
- Unidad y tratamiento del aseo y del alumbrado público (DEC-03).
- Esquema de salida único (DEC-02): hoy la exportación oficial es el esquema de `registro`.

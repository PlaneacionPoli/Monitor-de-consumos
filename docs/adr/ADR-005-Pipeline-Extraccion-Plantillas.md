# ADR-005: Pipeline de Extracción y Gestión de Plantillas

## Estado
**Aceptado**

## Fecha
2026-05-05

## Contexto
El sistema debe procesar facturas de múltiples proveedores con diferentes formatos. Se requiere un mecanismo flexible para manejar variaciones.

## Decisión
Se implementa un pipeline de extracción basado en plantillas configurables:

### Flujo de Procesamiento
1. **Watcher** detecta nuevo archivo en `data/invoices_inbox`
2. **OCR Engine** extrae texto del archivo
3. **Field Extractor** identifica servicio (Energía/Acueducco) y ciudad
4. Se aplican **plantillas específicas** del proveedor en `config.yaml`
5. **Excel Exporter** genera archivos de salida
6. **Dashboard** se actualiza automáticamente

### Gestión de Plantillas
- **config.yaml** contiene todas las plantillas por proveedor
- Cada plantilla define:
  - Sinonimos de campos (ej: "No. FACTURA", "Factura No.")
  - Patrones regex para validación
  - Tipos de datos y formatos de fecha
- **Fallback** a plantilla genérica si no hay plantilla específica

### Formato de Salida
- Dos libros Excel separados (Energía / Acueducco)
- Columnas estandarizadas según configuración
- Metadatos: archivo origen, fecha extracción, ciudad, proveedor

## Consecuencias

### Positivas
- Flexibilidad para agregar nuevos proveedores
- Centralización de configuración
- Facilidad de mantenimiento

### Negativas
- Requiere mantener config.yaml actualizado
- Posibles conflictos si hay cambios en formatos de facturas

## Alternativas consideradas
- Plantillas en base de datos: más complejo, mismo resultado
- UI para gestión de plantillas: feature para versión futura

## Notas
Se alinea con las decisiones del plan:
- 4C: Dos libros separados (uno por servicio)
- 21A: Config.yaml por proveedor/plantilla
- 1A: Ambos servicios desde el inicio
- 2A: Bogotá y Medellín
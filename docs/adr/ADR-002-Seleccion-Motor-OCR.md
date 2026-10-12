# ADR-002: Selección del Motor OCR

## Estado
**Aceptado**

## Fecha
2026-05-05

## Contexto
El sistema requiere extraer texto de facturas en formato PDF e imágenes (JPG, PNG, TIFF). Se evaluaron opciones gratuitas y de pago.

## Decisión
Se selecciona **Tesseract OCR** como motor principal de OCR por las siguientes razones:

1. **Gratuito y open-source**: Sin costos de licenciamiento
2. **Comunidad activa**: Amplio soporte y documentación
3. **Multiidioma**: Soporte para español
4. **Flexible**: Configurable via parámetros

### Configuración adoptada:
- Idioma: Español (spa)
- PSM: 6 (assume a single uniform block of text)
- OEM: 3 (default, uses whatever is available)
- Preprocesamiento: Escalado 1.5x, threshold binario, dilatación

## Consecuencias

### Positivas
- Sin costos de licenciamiento
- Instalación simple en Windows, Linux y macOS
- Compatible con pipeline de Python

### Negativas
- Menor precisión que servicios cloud (Google Vision, AWS Textract)
- Requiere preprocesamiento de imágenes para mejores resultados

## Alternativas consideradas
- Google Cloud Vision: costos por uso, mayor precisión
- AWS Textract: costos por uso, integración AWS
- Azure Form Recognizer: costos por uso
- EasyOCR: alternativa open-source, más lenta

## Notas
- Se deja abierta la posibilidad de migrar a servicios cloud si se requieren mayores tasas de precisión
- La configuración de plantillas en config.yaml permite compensar limitaciones del OCR
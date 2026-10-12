# ADR-001: Arquitectura General del Sistema

## Estado
**Aceptado**

## Fecha
2026-05-05

## Contexto
PoliEcoConsumo es un sistema de extracción masiva de facturas de Energía y Acueducco para Bogotá y Medellín. Se requiere una arquitectura que permita procesar PDFs e imágenes, extraer datos estructurados, generar archivos Excel y mostrar un dashboard en tiempo real.

## Decisión
Se adopta una arquitectura modular con los siguientes componentes:

1. **Capa de Ingesta**: Watcher que monitorea la carpeta `data/invoices_inbox`
2. **Capa de OCR**: Motor Tesseract para extracción de texto de PDFs e imágenes
3. **Capa de Extracción**: Field Extractor que parsea el texto según plantillas configuradas
4. **Capa de Exportación**: Generador de archivos Excel
5. **Capa de Visualización**: Dashboard con Dash/Plotly

## Consecuencias

### Positivas
- Modularidad permite reemplazar componentes individualmente
- Fácil de testear cada componente de forma aislada
- Escalabilidad horizontal adicionando más workers de procesamiento

### Negativas
- Mayor complejidad en operación y monitoreo
- Requiere gestión de dependencias entre componentes

## Alternativas consideradas
- Arquitectura monolítica: rechazada por menor flexibilidad
- Serverless: considerada pero rechazada por requisitos de procesamiento continuo

## Notas
Esta arquitectura se alinea con las decisiones del plan:
- Backend: Python con FastAPI
- OCR: Tesseract (opción gratuita)
- Dashboard: Dash/Plotly
- Almacenamiento: Local/dual
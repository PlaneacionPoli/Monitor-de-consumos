# ADR-003: Selección del Stack Tecnológico

## Estado
**Aceptado**

## Fecha
2026-05-05

## Contexto
Se requiere definir el stack tecnológico completo para el proyecto PoliEcoConsumo considerando las decisiones del plan.

## Decisión
Se selecciona el siguiente stack tecnológico:

| Componente | Tecnología | Justificación |
|------------|-------------|---------------|
| Backend | Python + FastAPI | Ecosistema rico para OCR y datos |
| OCR | Tesseract | Gratuito, open-source, soporte español |
| Dashboard | Dash/Plotly | Visualización interactiva, integración Python |
| Orquestación | Dagster | Pipeline de datos, gestión de activos |
| Base de datos | MySQL | Robustez, soporte transacciones |
| Almacenamiento | Local/Dual | Flexibilidad, costos reducidos |
| Monitorización | Prometheus + Grafana | Estándar industria, open-source |
| CI/CD | GitHub Actions | Integración con repositorio |

## Consecuencias

### Positivas
- stack cohesivo basado en Python
- Componentes open-source sin costos de licenciamiento
- Comunidad activa y soporte disponible

### Negativas
- Curva de aprendizaje para Dagster
- MySQL puede requerir migración a PostgreSQL si hay escalabilidad

## Alternativas consideradas
- Node.js para backend: rechazado por mejor soporte de Python para datos
- Airflow para orquestación: alternativa, pero Dagster ofrece mejor DX
- PostgreSQL vs MySQL: MySQL seleccionado por familiarity

## Notas
Este ADR se alinea con las respuestas del plan:
- 6A: Python con FastAPI
- 7B: Dash/Plotly
- 8B: Dagster
- 9B: MySQL
- 12B: Dash/Plotly
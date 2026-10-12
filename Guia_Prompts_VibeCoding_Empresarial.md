## Guia Prompts VibeCoding Empresarial (Adaptado al Proyecto)

Objetivo: proporcionar prompts adaptados para planificar, diseñar y desplegar un sistema de extracción masiva de facturas de Energía y Acueducto/Alcantarillado (PDF/imágenes) con generación de Excel y un dashboard en tiempo real. Soporta dos ciudades: Bogotá y Medellín.

Proyecto: FacturasEnergia_Acueducto_BogMed

Campos clave de salida: ver secciones específicas.

-----------------------------------------------------------------------
01. PROMPT DE PLANIFICACIÓN Y DEFINICIÓN DEL PROYECTO
 CONTEXTO DEL PROYECTO:
- Objetivo principal: Automatizar OCR y extracción de datos de facturas (Energía y Acueducto/Alcantarillado) en PDF o imágenes; generar un Excel estructurado y un dashboard en tiempo real; ingesta automática de archivos desde data/.
- Usuarios objetivo: Equipo de Facturación, Analistas de Datos, Operaciones, IT Soporte.
- NOMBRE_PROYECTO: FacturasEnergia_Acueducto_BogMed
- INDUSTRIA: Servicios Públicos (Energía y Agua)
- PRESUPUESTO: TBD
- TIEMPO_ESTIMADO: TBD
- COMPOSICIÓN_EQUIPO: 1 Data Engineer, 1 ML/OCR Specialist, 1 Backend Dev, 1 Frontend/BI Dev, 1 DevOps
- Alcance: Ingesta de PDFs/imágenes; extracción de campos por servicio; normalización; exportación a Excel; dashboard; watcher; logs y auditoría.
- Entregables: pipeline OCR + extracción + exportación a Excel; dashboard en tiempo real; config.yaml de plantillas; README y ADRs.

ANÁLISIS DE REQUERIMIENTOS
- Requerimientos funcionales (mínimo 15): Ingesta de facturas; extracción de campos por servicio; manejo de múltiples plantillas; normalización de fechas y montos; deduplicación; validación de consistencia; exportación a Excel; generación de outputs/outputs; dashboard en tiempo real; watcher de data en data/; logs estructurados; gestión de errores; pruebas con muestras; soporte para dos ciudades; seguridad de datos; trazabilidad y auditoría.
- Requerimientos no funcionales: rendimiento (OCR paralelo), escalabilidad, disponibilidad, observabilidad, seguridad de datos PII, cumplimiento, mantenimiento, documentación, pruebas.
- Requerimientos de negocio: cumplimiento regulatorio, entrega de datos para facturación, dashboards para monitoreo.
- Restricciones técnicas: tolerancia a plantillas diversas, calidad de escaneo, tamaño de PDFs, latencia aceptable.

DEFINICIÓN DE ALCANCE
- MVP: ingestión de PDFs/imágenes para Energía y Acueducto; extracción de campos principales; exportación a Excel; dashboard básico; watcher.
- Roadmap: plantillas adicionales, más ciudades y proveedores, mejoras de UI/UX, dashboards avanzados.
- Criterios de aceptación: precisión de extracción, ausencia de duplicados, salida de Excel con columnas normalizadas, dashboard funcional.
- Out of scope: procesamiento de facturas con escaneo irrecuperable, datos fuera de alcance legal.

ANÁLISIS DE RIESGOS
- Riesgos técnicos: OCR con baja precisión; variabilidad de plantillas; mitigaciones: plantillas mapeables, validaciones y fallback.
- Riesgos de negocio: cambios en proveedores, cambios regulatorios.
- Riesgos de equipo: dependencia de expertos OCR; mitigaciones: документация, pruebas robustas.

ESTRUCTURA DE TRABAJO (WBS)
- Fase 1: Ingesta y extracción
- Fase 2: Normalización y exportación a Excel
- Fase 3: Dashboard en tiempo real
- Fase 4: Automatización watcher y orquestación
- Fase 5: Pruebas y validaciones
- Fase 6: Documentación y despliegue

MÉTRICAS DE ÉXITO
- Exactitud de extracción, tasa de procesamiento, latencia de dashboard, disponibilidad del watcher, cobertura de pruebas.

CONSIDERACIONES DE ESCALABILIDAD
- Escalar ingesta, manejar más facturas, particionar datos por ciudad, escalar dashboard.

PLAN DE SEGURIDAD Y COMPLIANCE
- Manejo de datos sensibles; cifrado; control de acceso; auditoría; cumplimiento.

PLAN DE DESPLIEGUE Y MUESTRAS DE ENTREGABLES
- Roadmap y entregables; cronograma; criterios de aceptación.

RECOMENDACIONES DE MANTENIMIENTO Y SOPORTE
- Guía de actualización de plantillas; documentación de ADRs; procedimientos de rollback.

-----------------------------------------------------------------------
02. PROMPT DE DISEÑO UX/UI
 CONTEXTO: dashboard en tiempo real para Energía y Agua; dos tabs (Energia, Agua) con filtros por ciudad, proveedor, periodo; exportación de datos y detalle de factura. Requisitos de accesibilidad y mobile-friendly.
PROMPT COMPLETO: Actúa como diseñador UX/UI para FacturasEnergia_Acueducto_BogMed. Genera un design system, wireframes y guías de interacción para un dashboard que presenta dos dominios (Energia y Agua), con navegación clara, filtros, y exportación de datos. Incluye prototipos y criterios de aceptación de diseño.

03. PROMPT DE MODELO DE DATOS
 CONTEXTO: Dos entidades principales; campos comunes y específicos; relaciones con Proveedor, Ciudad, ArchivoFuente. Normalizar y diseñar índices. 
PROMPT COMPLETO: Diseña el modelo de datos para facturas Energía y Acueducto con tablas InvoiceEnergy, InvoiceWater, Proveedor, Ciudad, ArchivoFuente; define campos, tipos, constraints, índices y relaciones. Incluye migraciones y ORM mappings.

04. PROMPT DE ARQUITECTURA DEL SISTEMA
 CONTEXTO: pipeline OCR -> extracción -> exportación -> dashboard; watcher; multi-city; seguridad; observabilidad. 
PROMPT COMPLETO: Diseña la arquitectura en capas para FacturasEnergia_Acueducto_BogMed: Presentación, Aplicación, Datos, Infraestructura; define flujos de datos, eventos, API contracts, y estrategias de escalabilidad y resiliencia.

05. PROMPT DE STACK TECNOLÓGICO
 CONTEXTO: stack recomendado para OCR + data pipeline + dashboard; consideraciones de coste y mantenimiento.
PROMPT COMPLETO: Define el stack técnico óptimo para FacturasEnergia_Acueducto_BogMed (Frontend, Backend, OCR, Data, Infraestructura). Justifica cada elección y proporciona configuraciones iniciales y ejemplo de código de integración básica.

06. PROMPT DE AUTENTICACIÓN Y AUTORIZACIÓN
 CONTEXTO: acceso al dashboard y API internos.
PROMPT COMPLETO: Especifica un modelo RBAC + MFA para usuarios internos; soporte OIDC/OAuth2; gestión de sesiones; auditoría.

07. PROMPT DE SEGURIDAD DE LA INFORMACIÓN
 CONTEXTO: datos sensibles en facturas; cumplimiento; incident response.
PROMPT COMPLETO: Define la estrategia de seguridad (clasificación de datos, cifrado, controles de acceso, secretos, logging seguro, respuesta a incidentes, cumplimiento).

08. PROMPT DE ESTRUCTURA DE ARCHIVOS DEL PROYECTO
 CONTEXTO: organización de código y artifacts.
PROMPT COMPLETO: Define la estructura de directorios para el proyecto, convención de nombres, y separación de módulos (frontend, backend, libs, data, infra, docs).

09. PROMPT DE DOCUMENTACIÓN
 CONTEXTO: documentación viva y ADRs.
PROMPT COMPLETO: Genera README, ADRs, OpenAPI (si aplica), guías de contribución, runbooks y changelog. Estructura de docs basada en Docs-as-Code.

10. PROMPT DE TESTING INTEGRAL
 CONTEXTO: pipelines OCR, extracción, exportación y dashboard. 
PROMPT COMPLETO: Diseña la estrategia de testing (unitario, integración, E2E, performance, seguridad, chaos). Incluye ejemplos de pruebas para OCR, validación de datos y flujos completos.

11. PROMPT DE DESPLIEGUE Y CI/CD
 CONTEXTO: pipelines de CI/CD, entornos, rollback.
PROMPT COMPLETO: Define el pipeline CI/CD (CI y CD), entornos, políticas de rollout (blue/green/canary), monitorización post-despliegue y rollback automático. Incluye archivos YAML de ejemplo y playbooks de recuperación.

-----------------------------------------------------------------------
Notas:
- Reemplaza los placeholders [NOMBRE_PROYECTO], [INDUSTRIA], etc., con los valores del proyecto real cuando ejecutes.
- Si necesitas, puedo generar contenido de ejemplo para config.yaml, OpenAPI y ADRs basados en este marco.

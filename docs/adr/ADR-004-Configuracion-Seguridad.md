# ADR-004: Configuración de Seguridad e IAM

## Estado
**Aceptado**

## Fecha
2026-05-05

## Contexto
El sistema procesa datos de facturas que pueden contener información sensible. Se requiere un sistema de seguridad robusto.

## Decisión
Se implementa la siguiente estrategia de seguridad:

### Autenticación y Autorización
- **Keycloak** como proveedor de identidad (IAM)
- Protocolo **OIDC/OAuth2** para SSO
- **RBAC** (Control de Acceso Basado en Roles) para gestión de permisos
- **MFA** (Autenticación Multi-Factor) obligatorio para usuarios

### Seguridad de Datos
- Cifrado en reposo para archivos sensibles
- Logs de auditoría con trazabilidad completa
- Manejo de secretos via environment variables o Vault

### Seguridad en Pipeline CI/CD
- SAST (Static Application Security Testing) en CI
- DAST (Dynamic Application Security Testing) en staging
- Scanning de dependencias vulnerables

## Consecuencias

### Positivas
- Integración con sistemas corporativos via SSO
- Cumplimiento de estándares de seguridad
- Trazabilidad completa de operaciones

### Negativas
- Complejidad adicional en configuración inicial
- Requiere infraestructura adicional (Keycloak)

## Alternativas consideradas
- Auth0: costo adicional, menor control
- Firebase Auth: limitado para casos empresariales
- Sin IAM: rechazado por riesgos de seguridad

## Notas
Se alinea con las decisiones del plan:
- 14: Keycloak
- 15: F (ninguna regulación por ahora, pero preparación para GDPR/SOC2)
- 28: SAST/DAST y scanning de dependencias
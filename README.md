# PoliEcoConsumo

<p align="center">
  <img src="https://img.shields.io/badge/Status-En%20Desarrollo-yellow" alt="Estado">
  <img src="https://img.shields.io/badge/Python-3.10+-blue" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="Licencia">
</p>

## Descripción

**PoliEcoConsumo** es un sistema de extracción masiva de información de facturas de **Energía** y **Acueducco/Alcantarillado** para las ciudades de Bogotá y Medellín.

El sistema procesa facturas en formato PDF e imágenes, extrae los datos relevantes mediante OCR y genera archivos Excel estructurados junto con un dashboard en tiempo real.

## Características

- **Procesamiento automático**: Detecta nuevos archivos y los procesa automáticamente
- **OCR con Tesseract**: Extracción de texto de PDFs e imágenes
- **Múltiples proveedores**: Plantillas configurables por proveedor y ciudad
- **Dashboard en tiempo real**: Visualización de métricas y datos extraídos
- **Exportación a Excel**: Archivos separados por servicio (Energía / Acueducco)
- **Escalable**: Arquitectura modular basada en Python

## Estructura del Proyecto

```
PoliEcoConsumo/
├── config/
│   └── config.yaml              # Configuración de plantillas y proveedores
├── data/
│   ├── invoices_inbox/         # Carpeta de entrada para nuevas facturas
│   ├── processed/               # Facturas procesadas (movidas aquí)
│   └── outputs/                 # Archivos Excel generados
├── src/
│   ├── ocr/                     # Motor OCR (Tesseract)
│   ├── extractor/              # Extracción de campos
│   ├── processor/               # Procesamiento y exportación
│   ├── dashboard/              # Dashboard con Dash/Plotly
│   ├── watcher/                 # Monitor de carpeta de entrada
│   └── utils/                   # Utilidades
├── docs/
│   └── adr/                    # Architecture Decision Records
├── tests/                      # Pruebas unitarias y de integración
├── requirements.txt            # Dependencias del proyecto
└── README.md                   # Este archivo
```

## Requisitos

- Python 3.10+
- Tesseract OCR instalado en el sistema
- Windows / Linux / macOS

### Instalación de Tesseract

**Windows:**
Descargar e instalar desde: https://github.com/UB-Mannheim/tesseract/wiki

**Linux:**
```bash
sudo apt-get install tesseract-ocr tesseract-ocr-spa
```

**macOS:**
```bash
brew install tesseract tesseract-lang
```

## Instalación

1. Clonar el repositorio:
```bash
git clone <repositorio>
cd PoliEcoConsumo
```

2. Crear entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

4. Configurar variables de entorno:
```bash
copy .env.example .env
# Editar .env con la configuración desired
```

## Uso

### Modo Watcher (Automático)
```bash
python -m src.watcher.file_watcher
```
El watcher monitorea la carpeta `data/invoices_inbox` y procesa automáticamente cualquier nuevo archivo.

### Dashboard
```bash
python -m src.dashboard.dashboard
```
Acceder a: http://localhost:8050

### Procesamiento Manual
```python
from src.ocr.ocr_engine import crear_engine_ocr
from src.extractor.field_extractor import crear_extractor
from src.processor.excel_exporter import crear_exporter

# Configuración
config_ocr = {'idioma': 'spa', 'config_tesseract': '--psm 6 --oem 3'}

# Procesar archivo
ocr = crear_engine_ocr(config_ocr)
extractor = crear_extractor()
exporter = crear_exporter()

# Extraer texto
datos = ocr.extraer_datos('factura.pdf')
datos_factura = extractor.extraer_datos_factura(datos['texto'], datos['archivo'])

# Exportar
exporter.exportar_datos([datos_factura])
```

## Configuración

Editar `config/config.yaml` para:
- Agregar/modificar proveedores
- Ajustar plantillas de extracción
- Configurar columnas de salida
- Modificar parámetros de OCR

### Ejemplo de estructura de proveedores:

```yaml
proveedores_energia:
  bogota:
    - nombre: "Codensa"
      codigo: "CODENSA"
      campos:
        no_factura:
          sinonimos: ["No. FACTURA", "Factura No."]
```

## Dashboard

El dashboard incluye:
- KPIs: Total facturas, valor total, ciudad/proveedor principal
- Gráficos: Distribución por servicio, ciudad, tiempo
- Tabla: Últimas facturas procesadas
- Auto-refresh cada 30 segundos

## Métricas del Proyecto

| Métrica | Valor Objetivo |
|---------|----------------|
| Precisión OCR | >= 90% |
| Tiempo promedio por factura | < 30 segundos |
| Disponibilidad del sistema | >= 99% |
| Cobertura de pruebas | >= 80% |

## Stack Tecnológico

| Componente | Tecnología |
|------------|------------|
| Backend | Python + FastAPI |
| OCR | Tesseract |
| Dashboard | Dash/Plotly |
| Orquestación | Dagster |
| Base de datos | MySQL |
| Seguridad | Keycloak (OIDC) |

## Documentación ADRs

Ver `docs/adr/` para las decisiones de arquitectura:
- ADR-001: Arquitectura General
- ADR-002: Motor OCR
- ADR-003: Stack Tecnológico
- ADR-004: Seguridad
- ADR-005: Pipeline de Extracción

## Contribución

1. Fork del repositorio
2. Crear branch (`git checkout -b feature/nueva-caracteristica`)
3. Commit de cambios (`git commit -am 'Agregar nueva característica'`)
4. Push al branch (`git push origin feature/nueva-caracteristica`)
5. Crear Pull Request

## Licencia

MIT License - ver archivo LICENSE para más detalles.

## Autores

Equipo de desarrollo PoliEcoConsumo

---

<p align="center">Desarrollado con ❤️ para la gestión eficiente de facturas</p>
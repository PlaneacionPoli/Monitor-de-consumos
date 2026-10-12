"""
PoliEcoConsumo - Exportador de datos a Excel
Proyecto de extracción masiva de facturas de Energía y Acueducto
"""

import os
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

BOGOTA_TZ = ZoneInfo('America/Bogota')
from typing import List, Dict, Any, Optional

import pandas as pd
import yaml

logger = logging.getLogger(__name__)


class ExcelExporter:
    """Exportador de facturas a archivos Excel"""

    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = config_path
        self.config = self._cargar_config()
        self.salida_config = self.config.get('salida', {})

    def _cargar_config(self) -> Dict[str, Any]:
        """Carga la configuración del archivo YAML"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error al cargar config.yaml: {str(e)}")
            raise

    def _normalizar_datos_energia(self, datos: Dict[str, Any]) -> Dict[str, str]:
        """Normaliza los datos de Energía al formato de salida"""
        columnas = self.salida_config.get('columnas_salida', {}).get('energia', [])

        return {
            'No.FACTURA': datos.get('no_factura', ''),
            'PERIODO INICIO': datos.get('periodo_inicio', ''),
            'PERIODO FINAL': datos.get('periodo_fin', ''),
            'DIRECCION': datos.get('direccion', ''),
            'PROVEEDOR': datos.get('proveedor', ''),
            'VALOR FACT.': datos.get('valor_factura', ''),
            'FECHA DE PAGO': datos.get('fecha_pago', ''),
            'No.CUENTA CONTRATO': datos.get('no_cuenta_contrato', ''),
            'CONSUMO Kwh': datos.get('consumo_kwh', ''),
            'CIUDAD': datos.get('ciudad', ''),
            'TIPO': 'Energía',
            'ARCHIVO ORIGEN': datos.get('archivo_origen', ''),
            'FECHA EXTRACCION': datos.get('fecha_extraccion', '')
        }

    def _normalizar_datos_acueducco(self, datos: Dict[str, Any]) -> Dict[str, str]:
        """Normaliza los datos de Acueducco al formato de salida"""
        columnas = self.salida_config.get('columnas_salida', {}).get('acueducto', [])

        return {
            'No. FACTURA': datos.get('no_factura', ''),
            'PERIODO INICIO': datos.get('periodo_inicio', ''),
            'PERIODO FIN': datos.get('periodo_fin', ''),
            'DIRECCION': datos.get('direccion', ''),
            'COMPAÑÍA': datos.get('compania', ''),
            'VALOR ACUEDUCTO': datos.get('valor_acueducto', ''),
            'RECOLECCION BASURAS': datos.get('recoleccion_basuras', ''),
            'VALOR TOTAL': datos.get('valor_total', ''),
            'FECHA DE PAGO': datos.get('fecha_pago', ''),
            'CONTRATO': datos.get('contrato', ''),
            'CONSUMO M3': datos.get('consumo_m3', ''),
            'CIUDAD': datos.get('ciudad', ''),
            'TIPO': 'Acueducto',
            'ARCHIVO ORIGEN': datos.get('archivo_origen', ''),
            'FECHA EXTRACCION': datos.get('fecha_extraccion', '')
        }

    def exportar_datos(
        self,
        lista_datos: List[Dict[str, Any]],
        carpeta_salida: Optional[str] = None,
        nombre_archivo: Optional[str] = None
    ) -> str:
        """
        Exporta los datos a archivos Excel

        Args:
            lista_datos: Lista de diccionarios con datos de facturas
            carpeta_salida: Carpeta de salida (opcional)
            nombre_archivo: Nombre del archivo (opcional)

        Returns:
            Ruta del archivo Excel generado
        """
        if carpeta_salida is None:
            carpeta_salida = self.salida_config.get('carpeta_salida', 'data/outputs')

        if nombre_archivo is None:
            fecha = datetime.now(BOGOTA_TZ).strftime('%Y%m%d_%H%M%S')
            nombre_base = self.salida_config.get('nombre_archivo', 'facturas_{fecha}.xlsx')
            nombre_archivo = nombre_base.format(fecha=fecha)

        os.makedirs(carpeta_salida, exist_ok=True)
        ruta_salida = os.path.join(carpeta_salida, nombre_archivo)

        datos_energia = []
        datos_acueducco = []

        for dato in lista_datos:
            servicio = dato.get('servicio')

            if servicio == 'energia':
                datos_energia.append(self._normalizar_datos_energia(dato))
            elif servicio == 'acueducto':
                datos_acueducco.append(self._normalizar_datos_acueducco(dato))

        with pd.ExcelWriter(ruta_salida, engine='openpyxl') as writer:
            if datos_energia:
                df_energia = pd.DataFrame(datos_energia)
                df_energia.to_excel(writer, sheet_name='Energia', index=False)
                logger.info(f"Exportadas {len(datos_energia)} facturas de Energía")

            if datos_acueducco:
                df_acueducco = pd.DataFrame(datos_acueducco)
                df_acueducco.to_excel(writer, sheet_name='Acueducto', index=False)
                logger.info(f"Exportadas {len(datos_acueducco)} facturas de Acueducco")

        logger.info(f"Excel generado: {ruta_salida}")
        return ruta_salida

    def exportar_datos_separados(
        self,
        lista_datos: List[Dict[str, Any]],
        carpeta_salida: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Exporta los datos a dos archivos Excel separados (uno por servicio)

        Args:
            lista_datos: Lista de diccionarios con datos de facturas
            carpeta_salida: Carpeta de salida (opcional)

        Returns:
            Diccionario con las rutas de los archivos generados
        """
        if carpeta_salida is None:
            carpeta_salida = self.salida_config.get('carpeta_salida', 'data/outputs')

        separador = self.salida_config.get('separador_libros', {})
        energia_nombre = separador.get('energia', 'Energia')
        acueducco_nombre = separador.get('acueducto', 'Acueducto')

        fecha = datetime.now(BOGOTA_TZ).strftime('%Y%m%d_%H%M%S')

        energia_path = os.path.join(carpeta_salida, f"{energia_nombre}_{fecha}.xlsx")
        acueducco_path = os.path.join(carpeta_salida, f"{acueducco_nombre}_{fecha}.xlsx")

        os.makedirs(carpeta_salida, exist_ok=True)

        datos_energia = []
        datos_acueducco = []

        for dato in lista_datos:
            servicio = dato.get('servicio')

            if servicio == 'energia':
                datos_energia.append(self._normalizar_datos_energia(dato))
            elif servicio == 'acueducto':
                datos_acueducco.append(self._normalizar_datos_acueducco(dato))

        resultados = {}

        if datos_energia:
            df_energia = pd.DataFrame(datos_energia)
            df_energia.to_excel(energia_path, sheet_name='Energia', index=False)
            logger.info(f"Excel Energía generado: {energia_path}")
            resultados['energia'] = energia_path

        if datos_acueducco:
            df_acueducco = pd.DataFrame(datos_acueducco)
            df_acueducco.to_excel(acueducco_path, sheet_name='Acueducto', index=False)
            logger.info(f"Excel Acueducco generado: {acueducco_path}")
            resultados['acueducto'] = acueducco_path

        return resultados


def crear_exporter(config_path: str = "config/config.yaml") -> ExcelExporter:
    """Factory para crear una instancia del exportador"""
    return ExcelExporter(config_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    exporter = crear_exporter()

    datos_ejemplo = [
        {
            'servicio': 'energia',
            'no_factura': '1234567890',
            'periodo_inicio': '01/01/2024',
            'periodo_fin': '31/01/2024',
            'direccion': 'Carrera 10 # 20-30',
            'proveedor': 'Codensa',
            'valor_factura': '$150.000',
            'fecha_pago': '20/02/2024',
            'no_cuenta_contrato': 'CON123456',
            'consumo_kwh': '250',
            'ciudad': 'Bogotá',
            'archivo_origen': 'factura_ejemplo.pdf',
            'fecha_extraccion': '2024-02-01 10:00:00'
        }
    ]

    exporter.exportar_datos(datos_ejemplo)
    logger.info("Exportador de Excel inicializado y funcionando")
"""
PoliEcoConsumo - Extraktor de campos de facturas
Proyecto de extracción masiva de facturas de Energía y Acueducto
"""

import os
import re
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

import yaml
import pandas as pd

logger = logging.getLogger(__name__)


class FieldExtractor:
    """Extractor de campos específicos de facturas"""

    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = config_path
        self.config = self._cargar_config()
        self.servicios = self.config.get('servicios', {})
        self.proveedores_energia = self.config.get('proveedores_energia', {})
        self.proveedores_acueducto = self.config.get('proveedores_acueducto', {})

    def _cargar_config(self) -> Dict[str, Any]:
        """Carga la configuración del archivo YAML"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error al cargar config.yaml: {str(e)}")
            raise

    def detectar_servicio(self, texto: str) -> Optional[str]:
        """
        Detecta si la factura es de Energía o Acueducco

        Args:
            texto: Texto extraído del OCR

        Returns:
            'energia', 'acueducto' o None
        """
        texto_lower = texto.lower()

        indicadores_energia = [
            'kwh', 'kilovatio', 'consumo energía', 'enero', 'febrero',
            'cargo por energía', 'tarifa', 'potencia', 'codensa', 'enel', 'epm'
        ]

        indicadores_acueducto = [
            'm3', 'metro cúbico', 'acueducto', 'alcantarillado',
            'recolección basuras', 'aseo', 'consumo agua', 'eaab', 'epm aguas'
        ]

        score_energia = sum(1 for ind in indicadores_energia if ind in texto_lower)
        score_acueducto = sum(1 for ind in indicadores_acueducto if ind in texto_lower)

        if score_energia > score_acueducco:
            return 'energia'
        elif score_acueducto > score_energia:
            return 'acueducto'

        return None

    def detectar_ciudad(self, texto: str) -> Optional[str]:
        """Detecta la ciudad basándose en el texto"""
        texto_lower = texto.lower()

        indicadores_bogota = ['bogotá', 'bogota', 'codensa', 'eaab', ' Empresa de Acueducco de Bogotá']
        indicadores_medellin = ['medellín', 'medellin', 'epm']

        for ind in indicadores_bogota:
            if ind in texto_lower:
                return 'Bogotá'

        for ind in indicadores_medellin:
            if ind in texto_lower:
                return 'Medellín'

        return None

    def detectar_proveedor(self, texto: str, servicio: str) -> Optional[str]:
        """Detecta el proveedor basándose en el servicio"""
        texto_lower = texto.lower()

        if servicio == 'energia':
            proveedores = self.proveedores_energia
        else:
            proveedores = self.proveedores_acueducto

        for ciudad, lista_proveedores in proveedores.items():
            for proveedor in lista_proveedores:
                nombre_proveedor = proveedor.get('nombre', '').lower()
                codigo = proveedor.get('codigo', '').lower()

                if nombre_proveedor in texto_lower or codigo in texto_lower:
                    return proveedor.get('nombre')

        return None

    def extraer_campos_energia(self, texto: str) -> Dict[str, Any]:
        """Extrae campos específicos de facturas de Energía"""
        campos = {}

        patrones = {
            'no_factura': [
                r'No\.?\s*FACTURA[:\s]*([A-Z0-9\-]+)',
                r'Factura\s*No\.?\s*([A-Z0-9\-]+)',
                r'Número\s*de\s*Factura[:\s]*([A-Z0-9\-]+)'
            ],
            'periodo_inicio': [
                r'Período\s*Inicio[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'Desde[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
            ],
            'periodo_fin': [
                r'Período\s*Final[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'Hasta[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
            ],
            'direccion': [
                r'Dirección[:\s]*([A-Za-z0-9\s\.,\-#]+)',
                r'Direccion[:\s]*([A-Za-z0-9\s\.,\-#]+)'
            ],
            'valor_factura': [
                r'Valor\s*Total[:\s]*\$?\s*([\d\.,]+)',
                r'Total\s*a\s*Pagar[:\s]*\$?\s*([\d\.,]+)',
                r'\$\s*([\d\.,]+)'
            ],
            'fecha_pago': [
                r'Fecha\s*de\s*Pago[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'Vencimiento[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
            ],
            'no_cuenta_contrato': [
                r'No\.?\s*Contrato[:\s]*([A-Z0-9\-]+)',
                r'Cuenta[:\s]*([A-Z0-9\-]+)'
            ],
            'consumo_kwh': [
                r'Consumo[:\s]*(\d+)\s*kWh',
                r'(\d+)\s*kWh'
            ]
        }

        for campo, lista_patrones in patrones.items():
            for patron in lista_patrones:
                match = re.search(patron, texto, re.IGNORECASE)
                if match:
                    campos[campo] = match.group(1).strip()
                    break

        return campos

    def extraer_campos_acueducto(self, texto: str) -> Dict[str, Any]:
        """Extrae campos específicos de facturas de Acueducco"""
        campos = {}

        patrones = {
            'no_factura': [
                r'No\.?\s*FACTURA[:\s]*([A-Z0-9\-]+)',
                r'Factura[:\s]*([A-Z0-9\-]+)'
            ],
            'periodo_inicio': [
                r'Período\s*Inicio[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'Desde[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
            ],
            'periodo_fin': [
                r'Período\s*Fin[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'Hasta[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
            ],
            'direccion': [
                r'Dirección[:\s]*([A-Za-z0-9\s\.,\-#]+)',
                r'Direccion[:\s]*([A-Za-z0-9\s\.,\-#]+)'
            ],
            'compania': [
                r'Empresa[:\s]*([A-Za-z\s]+)',
                r'Compañía[:\s]*([A-Za-z\s]+)'
            ],
            'valor_acueducto': [
                r'Acueducto[:\s]*\$?\s*([\d\.,]+)',
                r'Consumo[:\s]*\$?\s*([\d\.,]+)'
            ],
            'recoleccion_basuras': [
                r'Recolección\s*Basuras[:\s]*\$?\s*([\d\.,]+)',
                r'Aseo[:\s]*\$?\s*([\d\.,]+)'
            ],
            'valor_total': [
                r'Valor\s*Total[:\s]*\$?\s*([\d\.,]+)',
                r'Total[:\s]*\$?\s*([\d\.,]+)'
            ],
            'fecha_pago': [
                r'Fecha\s*de\s*Pago[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'Vencimiento[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
            ],
            'contrato': [
                r'Contrato[:\s]*([A-Z0-9\-]+)',
                r'No\.?\s*Contrato[:\s]*([A-Z0-9\-]+)'
            ],
            'consumo_m3': [
                r'Consumo[:\s]*(\d+)\s*m3',
                r'(\d+)\s*m3'
            ]
        }

        for campo, lista_patrones in patrones.items():
            for patron in lista_patrones:
                match = re.search(patron, texto, re.IGNORECASE)
                if match:
                    campos[campo] = match.group(1).strip()
                    break

        return campos

    def extraer_datos_factura(self, texto: str, nombre_archivo: str) -> Dict[str, Any]:
        """
        Extrae todos los datos de una factura

        Args:
            texto: Texto extraído del OCR
            nombre_archivo: Nombre del archivo procesado

        Returns:
            Diccionario con todos los campos extraídos
        """
        servicio = self.detectar_servicio(texto)
        ciudad = self.detectar_ciudad(texto)
        proveedor = self.detectar_proveedor(texto, servicio) if servicio else None

        if servicio == 'energia':
            datos = self.extraer_campos_energia(texto)
            datos['tipo'] = 'Energía'
        elif servicio == 'acueducto':
            datos = self.extraer_campos_acueducto(texto)
            datos['tipo'] = 'Acueducto'
        else:
            datos = {}
            logger.warning(f"No se pudo detectar el tipo de servicio para: {nombre_archivo}")

        datos['servicio'] = servicio
        datos['ciudad'] = ciudad
        datos['proveedor'] = proveedor
        datos['archivo_origen'] = nombre_archivo
        datos['fecha_extraccion'] = datetime.now(ZoneInfo('America/Bogota')).strftime('%Y-%m-%d %H:%M:%S')

        return datos


def crear_extractor(config_path: str = "config/config.yaml") -> FieldExtractor:
    """Factory para crear una instancia del extractor"""
    return FieldExtractor(config_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    extractor = crear_extractor()
    logger.info("Extractor de campos inicializado correctamente")
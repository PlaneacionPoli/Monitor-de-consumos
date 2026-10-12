"""
PoliEcoConsumo - Motor OCR para extracción de texto de facturas
Proyecto de extracción masiva de facturas de Energía y Acueducto
"""

import os
import io
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path

import pytesseract
from PIL import Image
import cv2
import numpy as np

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


class OCREngine:
    """Motor de OCR para procesar facturas en PDF e imágenes"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.idioma = self.config.get('idioma', 'spa')
        self.config_tesseract = self.config.get('config_tesseract', '--psm 6 --oem 3')
        self.preprocesamiento = self.config.get('preprocesamiento', {})

        # Configurar ruta de Tesseract si es necesario (Windows)
        if os.name == 'nt' and 'TESSERACT_PATH' in os.environ:
            pytesseract.pytesseract.tesseract_cmd = os.environ['TESSERACT_PATH']

    def procesar_archivo(self, ruta_archivo: str) -> str:
        """
        Procesa un archivo (PDF o imagen) y retorna el texto extraído

        Args:
            ruta_archivo: Ruta al archivo a procesar

        Returns:
            Texto extraído del archivo
        """
        extension = Path(ruta_archivo).suffix.lower()

        logger.info(f"Procesando archivo: {ruta_archivo}")

        try:
            if extension == '.pdf':
                return self._procesar_pdf(ruta_archivo)
            else:
                return self._procesar_imagen(ruta_archivo)
        except Exception as e:
            logger.error(f"Error al procesar {ruta_archivo}: {str(e)}")
            raise

    def _procesar_pdf(self, ruta_pdf: str) -> str:
        """Procesa un PDF: extrae texto directo si es digital, o usa OCR si es imagen"""
        logger.info(f"Leyendo PDF: {ruta_pdf}")

        try:
            doc = fitz.open(ruta_pdf)
            texto_completo = []

            for i in range(len(doc)):
                pagina = doc[i]
                texto_directo = pagina.get_text().strip()
                tiene_texto = len(texto_directo) > 50

                if tiene_texto:
                    logger.info(f"Página {i + 1}: texto directo ({len(texto_directo)} chars)")
                    texto_completo.append(texto_directo)
                else:
                    logger.info(f"Página {i + 1}: sin texto directo, usando OCR")
                    mat = fitz.Matrix(2.0, 2.0)
                    pix = pagina.get_pixmap(matrix=mat)
                    img_bytes = pix.tobytes("png")
                    imagen = Image.open(io.BytesIO(img_bytes))
                    texto_pagina = self._procesar_imagen_pil(imagen)
                    texto_completo.append(texto_pagina)

            doc.close()
            return "\n\n--- PAGINA ---\n\n".join(texto_completo)

        except Exception as e:
            logger.error(f"Error al procesar PDF: {str(e)}")
            raise

    def _procesar_imagen(self, ruta_imagen: str) -> str:
        """Procesa una imagen directamente"""
        try:
            imagen = Image.open(ruta_imagen)
            return self._procesar_imagen_pil(imagen)
        except Exception as e:
            logger.error(f"Error al abrir imagen: {str(e)}")
            raise

    def _procesar_imagen_pil(self, imagen: Image.Image) -> str:
        """Procesa una imagen PIL"""
        imagen_preprocesada = self._preprocesar_imagen(imagen)

        texto = pytesseract.image_to_string(
            imagen_preprocesada,
            lang=self.idioma,
            config=self.config_tesseract
        )

        return texto

    def _preprocesar_imagen(self, imagen: Image.Image) -> Image.Image:
        """Preprocesa la imagen para mejorar el OCR"""
        escala = self.preprocesamiento.get('escala', 1.5)
        threshold = self.preprocesamiento.get('threshold_gris', 128)

        ancho, alto = imagen.size
        nuevo_ancho = int(ancho * escala)
        nuevo_alto = int(alto * escala)
        imagen = imagen.resize((nuevo_ancho, nuevo_alto), Image.Resampling.LANCZOS)

        if imagen.mode != 'L':
            imagen = imagen.convert('L')

        img_array = np.array(imagen)
        _, imagen_bin = cv2.threshold(img_array, threshold, 255, cv2.THRESH_BINARY)

        kernel_size = self.preprocesamiento.get('kernel_size', [3, 3])
        kernel = np.ones(kernel_size, np.uint8)
        imagen_bin = cv2.dilate(imagen_bin, kernel, iterations=1)

        return Image.fromarray(imagen_bin)

    def extraer_datos(self, ruta_archivo: str) -> Dict[str, Any]:
        """
        Extrae texto y metadatos de un archivo

        Args:
            ruta_archivo: Ruta al archivo

        Returns:
            Diccionario con texto y metadatos
        """
        texto = self.procesar_archivo(ruta_archivo)

        return {
            'texto': texto,
            'archivo': os.path.basename(ruta_archivo),
            'ruta': ruta_archivo,
            'exito': True,
            'error': None
        }


def crear_engine_ocr(config: Optional[Dict[str, Any]] = None) -> OCREngine:
    """Factory para crear una instancia del motor OCR"""
    return OCREngine(config)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    config = {
        'idioma': 'spa',
        'config_tesseract': '--psm 6 --oem 3',
        'preprocesamiento': {
            'escala': 1.5,
            'threshold_gris': 128,
            'kernel_size': [3, 3]
        }
    }

    engine = crear_engine_ocr(config)
    logger.info("Motor OCR inicializado correctamente")
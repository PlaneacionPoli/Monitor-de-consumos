"""
PoliEcoConsumo - Watcher para monitorear carpeta de facturas
Proyecto de extracción masiva de facturas de Energía y Acueducto
"""

import os
import time
import logging
import shutil
from pathlib import Path
from typing import Callable, List, Optional

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

logger = logging.getLogger(__name__)


class FacturaEventHandler(FileSystemEventHandler):
    """Manejador de eventos del sistema de archivos"""

    def __init__(
        self,
        callback: Callable[[str], None],
        extensiones_permitidas: List[str],
        carpeta_procesados: Optional[str] = None
    ):
        super().__init__()
        self.callback = callback
        self.extensiones_permitidas = [ext.lower() for ext in extensiones_permitidas]
        self.carpeta_procesados = carpeta_procesados
        self.archivos_procesados = set()

    def on_created(self, event: FileSystemEvent):
        """Se ejecuta cuando se crea un nuevo archivo"""
        if event.is_directory:
            return

        archivo = event.src_path
        extension = Path(archivo).suffix.lower()

        if extension in self.extensiones_permitidas:
            logger.info(f"Nuevo archivo detectado: {archivo}")

            time.sleep(1)

            if self._esperar_archivo_listo(archivo):
                try:
                    self.callback(archivo)

                    if self.carpeta_procesados:
                        self._mover_a_procesados(archivo)

                    self.archivos_procesados.add(archivo)
                    logger.info(f"Archivo procesado exitosamente: {archivo}")

                except Exception as e:
                    logger.error(f"Error al procesar archivo {archivo}: {str(e)}")
            else:
                logger.warning(f"Archivo no está listo para procesar: {archivo}")

    def _esperar_archivo_listo(self, archivo: str, max_intentos: int = 10) -> bool:
        """Espera a que el archivo esté completamente escrito"""
        tamaño_anterior = 0

        for _ in range(max_intentos):
            try:
                tamaño_actual = os.path.getsize(archivo)
                if tamaño_actual > 0 and tamaño_actual == tamaño_anterior:
                    return True
                tamaño_anterior = tamaño_actual
                time.sleep(0.5)
            except OSError:
                return False

        return False

    def _mover_a_procesados(self, archivo: str):
        """Mueve el archivo a la carpeta de procesados"""
        if not self.carpeta_procesados:
            return

        os.makedirs(self.carpeta_procesados, exist_ok=True)

        nombre_archivo = Path(archivo).name
        destino = os.path.join(self.carpeta_procesados, nombre_archivo)

        contador = 1
        while os.path.exists(destino):
            nombre_nuevo = f"{Path(archivo).stem}_{contador}{Path(archivo).suffix}"
            destino = os.path.join(self.carpeta_procesados, nombre_nuevo)
            contador += 1

        shutil.move(archivo, destino)
        logger.info(f"Archivo movido a procesados: {destino}")


class FileWatcher:
    """Watchers para monitorear carpetas de facturas"""

    def __init__(
        self,
        carpeta_entrada: str,
        callback: Callable[[str], None],
        extensiones_permitidas: List[str] = None,
        intervalo: int = 5,
        carpeta_procesados: Optional[str] = None
    ):
        self.carpeta_entrada = carpeta_entrada
        self.callback = callback
        self.extensiones_permitidas = extensiones_permitidas or ['.pdf', '.jpg', '.jpeg', '.png']
        self.intervalo = intervalo
        self.carpeta_procesados = carpeta_procesados

        self.observer = None
        self.event_handler = None

    def iniciar(self):
        """Inicia el watcher"""
        logger.info(f"Iniciando watcher en: {self.carpeta_entrada}")

        os.makedirs(self.carpeta_entrada, exist_ok=True)

        if self.carpeta_procesados:
            os.makedirs(self.carpeta_procesados, exist_ok=True)

        self.event_handler = FacturaEventHandler(
            callback=self.callback,
            extensiones_permitidas=self.extensiones_permitidas,
            carpeta_procesados=self.carpeta_procesados
        )

        self.observer = Observer()
        self.observer.schedule(
            self.event_handler,
            self.carpeta_entrada,
            recursive=False
        )

        self.observer.start()
        logger.info("Watcher iniciado correctamente")

    def detener(self):
        """Detiene el watcher"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            logger.info("Watcher detenido")

    def esperar(self):
        """Mantiene el watcher activo"""
        try:
            while True:
                time.sleep(self.intervalo)
        except KeyboardInterrupt:
            self.detener()


def procesar_archivo(ruta_archivo: str):
    """
    Callback para procesar un archivo detectado

    Args:
        ruta_archivo: Ruta al archivo a procesar
    """
    from src.ocr.ocr_engine import crear_engine_ocr
    from src.extractor.field_extractor import crear_extractor

    logger.info(f"Iniciando procesamiento de: {ruta_archivo}")

    config_ocr = {
        'idioma': 'spa',
        'config_tesseract': '--psm 6 --oem 3',
        'preprocesamiento': {
            'escala': 1.5,
            'threshold_gris': 128,
            'kernel_size': [3, 3]
        }
    }

    ocr_engine = crear_engine_ocr(config_ocr)
    extractor = crear_extractor()

    try:
        datos_ocr = ocr_engine.extraer_datos(ruta_archivo)

        if datos_ocr.get('exito'):
            texto = datos_ocr.get('texto', '')
            nombre_archivo = datos_ocr.get('archivo', '')

            datos_factura = extractor.extraer_datos_factura(texto, nombre_archivo)

            logger.info(f"Datos extraídos: {datos_factura.get('servicio')} - {datos_factura.get('ciudad')}")

            return datos_factura

    except Exception as e:
        logger.error(f"Error en procesamiento: {str(e)}")
        raise


def iniciar_watcher(
    carpeta_entrada: str = "data/invoices_inbox",
    carpeta_procesados: str = "data/processed",
    extensiones: List[str] = None
):
    """Función de conveniencia para iniciar el watcher"""

    if extensiones is None:
        extensiones = ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.bmp']

    watcher = FileWatcher(
        carpeta_entrada=carpeta_entrada,
        callback=procesar_archivo,
        extensiones_permitidas=extensiones,
        carpeta_procesados=carpeta_procesados
    )

    watcher.iniciar()
    return watcher


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    watcher = iniciar_watcher()
    watcher.esperar()
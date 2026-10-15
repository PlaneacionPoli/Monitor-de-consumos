@echo off
rem Abre el Monitor de Consumos (carga de facturas + dashboard) en el navegador.
cd /d "%~dp0"
python app\aplicacion.py
pause

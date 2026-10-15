@echo off
rem Instalacion unica del Monitor de Consumos en un equipo nuevo.
rem Requisito: Python 3.11 o superior ya instalado (marcar "Add Python to PATH").
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo  Instalando el Monitor de Consumos
echo ============================================

python --version >nul 2>&1
if errorlevel 1 (
  echo [X] No se encontro Python. Instalalo desde https://www.python.org/downloads/
  echo     Marca la casilla "Add Python to PATH" y vuelve a ejecutar este archivo.
  pause & exit /b 1
)

echo.
echo [1/3] Instalando librerias de Python...
python -m pip install --upgrade pip >nul
python -m pip install -r requirements-app.txt
if errorlevel 1 ( echo [X] Fallo la instalacion de librerias. & pause & exit /b 1 )

echo.
echo [2/3] Verificando Tesseract (lector de facturas escaneadas)...
if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
  echo     Tesseract ya esta instalado.
) else (
  winget install --id UB-Mannheim.TesseractOCR -e --accept-source-agreements --accept-package-agreements
  if errorlevel 1 echo [!] No se pudo instalar Tesseract solo ^(puede faltar permiso de administrador^). Descargalo de https://github.com/UB-Mannheim/tesseract/wiki o pidelo al equipo tecnico. Solo hace falta para facturas escaneadas.
)
if not exist "config\tessdata\spa.traineddata" (
  echo [!] Falta config\tessdata\spa.traineddata ^(idioma espanol^). Pidelo al equipo tecnico.
)

echo.
echo [3/3] Creando acceso directo en el Escritorio...
powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\Monitor de Consumos.lnk'); $s.TargetPath='%~dp0Iniciar_App.bat'; $s.WorkingDirectory='%~dp0'; $s.IconLocation='%~dp0Assets\icono.ico'; $s.Save()"

echo.
echo ============================================
echo  Listo. Abre "Monitor de Consumos" desde el Escritorio.
echo ============================================
pause

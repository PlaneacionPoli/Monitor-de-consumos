@echo off
rem Abre el Monitor de Consumos (carga de facturas + dashboard) en el navegador.
rem Al cerrar la app, git es OPCIONAL: se configura en config\git_opcional.txt (preguntar / automatico / nunca).
cd /d "%~dp0"
python app\aplicacion.py

set "GIT_MODO=preguntar"
if exist "config\git_opcional.txt" (
  for /f "usebackq eol=# tokens=1,* delims==" %%a in ("config\git_opcional.txt") do (
    if /i "%%a"=="modo" set "GIT_MODO=%%b"
  )
)
if /i "%GIT_MODO%"=="nunca" goto fin
if /i not "%GIT_MODO%"=="automatico" (
  echo.
  choice /c SN /n /m "Subir los cambios a GitHub ahora? (S/N): "
  if errorlevel 2 goto fin
)
python scripts\subir_a_git.py

:fin
pause

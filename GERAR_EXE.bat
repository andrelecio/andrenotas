@echo off
setlocal
cd /d "%~dp0"
title AndreNotas v1.0 - Gerar EXE
if not exist "AndreNotas.py" (echo ERRO: AndreNotas.py nao encontrado & pause & exit /b 1)
if not exist "andrenote.ico" (echo ERRO: andrenote.ico nao encontrado & pause & exit /b 1)
where py >nul 2>&1
if not errorlevel 1 (set "PY=py -3") else (set "PY=python")
%PY% -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
  %PY% -m pip install pyinstaller
  if errorlevel 1 (pause & exit /b 1)
)
%PY% -m PyInstaller --noconfirm --clean --onefile --windowed --icon "andrenote.ico" --add-data "icons;icons" --add-data "andrenote.ico;." --name "AndreNotas" "AndreNotas.py"
if errorlevel 1 (echo ERRO NA COMPILACAO & pause & exit /b 1)
echo.
echo EXE GERADO: dist\AndreNotas.exe
echo Agora execute GERAR_INSTALADOR.bat para montar a instalacao.
pause

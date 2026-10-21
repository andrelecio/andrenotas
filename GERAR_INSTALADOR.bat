@echo off
setlocal
cd /d "%~dp0"
if not exist "dist\AndreNotas.exe" (
 echo Primeiro execute GERAR_EXE.bat
 pause
 exit /b 1
)
set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
 echo Instale o Inno Setup 6 em https://jrsoftware.org/isinfo.php
 echo Depois execute este BAT novamente.
 pause
 exit /b 1
)
"%ISCC%" "AndreNotas_Instalador.iss"
if errorlevel 1 (echo Falha ao gerar instalador & pause & exit /b 1)
echo Instalador criado na pasta instalador.
pause

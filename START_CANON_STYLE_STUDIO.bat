@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Canon Style Studio Public Alpha

echo ============================================================
echo Canon Style Studio Public Alpha 1.0.0-alpha.1
echo ============================================================
echo.

set "PYTHON_EXE="
for /f "delims=" %%P in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do set "PYTHON_EXE=%%P"

if not defined PYTHON_EXE (
    for /f "delims=" %%P in ('python -c "import sys; print(sys.executable)" 2^>nul') do set "PYTHON_EXE=%%P"
)

if not defined PYTHON_EXE (
    echo [ERROR] Python 3 nao foi encontrado.
    echo.
    echo Esta janela NAO vai fechar automaticamente.
    pause
    exit /b 1
)

echo Python: "%PYTHON_EXE%"
echo.
echo [1/2] A verificar dependencias...
"%PYTHON_EXE%" -u bootstrap.py
set "BOOT_RC=%ERRORLEVEL%"

if not "%BOOT_RC%"=="0" (
    echo.
    echo [ERROR] Bootstrap falhou com codigo %BOOT_RC%.
    echo Envia o Test Report da aplicacao, o startup.log, ou uma fotografia desta janela.
    echo.
    pause
    exit /b %BOOT_RC%
)

echo.
echo [2/2] A iniciar a aplicacao...
echo.
"%PYTHON_EXE%" -u -X faulthandler launch_guard.py
set "APP_RC=%ERRORLEVEL%"

echo.
echo ============================================================
echo Canon Style Studio terminou com codigo %APP_RC%.
echo Log: "%LOCALAPPDATA%\CanonStyleStudio\logs\startup.log"
echo ============================================================
echo.
echo Esta janela fica aberta de proposito.
pause
exit /b %APP_RC%

@echo off
setlocal

set "ROOT=%~dp0"
set "SCRIPT=%ROOT%scripts\start-looplens.ps1"

if not exist "%SCRIPT%" (
    echo Missing startup script:
    echo %SCRIPT%
    echo.
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%" %*
if errorlevel 1 (
    echo.
    echo LoopLens failed to start.
    pause
    exit /b 1
)

exit /b 0

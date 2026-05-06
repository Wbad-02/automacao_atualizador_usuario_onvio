@echo off
chcp 65001 > nul
title Automacao Gestta v1.2

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                   AUTOMACAO GESTTA v1.2                       ║
echo ║                  © 2024 Wbad-02 - RH ^& Folha                 ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

echo Escolha o modo de execucao:
echo.
echo   [1] Interface Desktop  (recomendado)
echo   [2] CLI - com navegador visivel
echo   [3] CLI - headless (sem navegador)
echo   [4] Configurar credenciais
echo   [5] Sair
echo.
set /p opcao="Digite sua opcao (1/2/3/4/5): "

if "%opcao%"=="1" goto desktop
if "%opcao%"=="2" goto visivel
if "%opcao%"=="3" goto headless
if "%opcao%"=="4" goto credenciais
if "%opcao%"=="5" goto fim

:desktop
echo.
echo Iniciando interface desktop...
echo.
python -m src.desktop_app
goto fim

:visivel
echo.
echo Iniciando com navegador visivel...
echo.
python -m src.main --no-headless
goto resultado

:headless
echo.
echo Iniciando em modo headless (sem navegador)...
echo.
python -m src.main
goto resultado

:credenciais
echo.
python -m src.main --setup-credentials
echo.
pause
goto fim

:resultado
echo.
if %errorlevel%==0 (
    echo Automacao finalizada com SUCESSO!
) else (
    echo Automacao finalizada com ERROS. Verifique a pasta logs\
)
echo.
pause

:fim
exit

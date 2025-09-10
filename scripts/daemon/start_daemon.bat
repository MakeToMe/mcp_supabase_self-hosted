@echo off
REM Script para iniciar o servidor MCP Supabase em segundo plano no Windows
REM Uso: start_daemon.bat [start|stop|restart|status]

setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set VENV_PATH=%SCRIPT_DIR%venv
set PID_FILE=%SCRIPT_DIR%mcp_server.pid
set LOG_FILE=%SCRIPT_DIR%mcp_server.log
set ERROR_LOG=%SCRIPT_DIR%mcp_server_error.log

REM Carrega variáveis de ambiente se existir .env
if exist "%SCRIPT_DIR%.env" (
    for /f "tokens=1,2 delims==" %%a in ('type "%SCRIPT_DIR%.env" ^| findstr /v "^#"') do (
        set %%a=%%b
    )
)

if "%1"=="start" goto start_server
if "%1"=="stop" goto stop_server
if "%1"=="restart" goto restart_server
if "%1"=="status" goto status_server
goto usage

:start_server
if exist "%PID_FILE%" (
    set /p PID=<"%PID_FILE%"
    tasklist /FI "PID eq !PID!" 2>nul | find /I "!PID!" >nul
    if !errorlevel! equ 0 (
        echo Servidor já está rodando (PID: !PID!)
        goto end
    ) else (
        echo Removendo PID file obsoleto...
        del "%PID_FILE%" >nul 2>&1
    )
)

echo Iniciando servidor MCP Supabase em segundo plano...

REM Ativa o ambiente virtual
call "%VENV_PATH%\Scripts\activate.bat"

REM Inicia o servidor em background usando start
start /B "" python -m supabase_mcp_server --host 0.0.0.0 --port 8001 > "%LOG_FILE%" 2> "%ERROR_LOG%"

REM Captura o PID do último processo iniciado
for /f "tokens=2" %%i in ('tasklist /FI "IMAGENAME eq python.exe" /FO CSV ^| find /V "PID" ^| sort /R ^| head -1') do (
    set SERVER_PID=%%i
    set SERVER_PID=!SERVER_PID:"=!
)

echo !SERVER_PID! > "%PID_FILE%"

REM Aguarda um pouco para verificar se o servidor iniciou
timeout /t 3 /nobreak >nul

tasklist /FI "PID eq !SERVER_PID!" 2>nul | find /I "!SERVER_PID!" >nul
if !errorlevel! equ 0 (
    echo ✅ Servidor iniciado com sucesso!
    echo    PID: !SERVER_PID!
    echo    Logs: %LOG_FILE%
    echo    Erros: %ERROR_LOG%
    echo    URL: http://0.0.0.0:8001
) else (
    echo ❌ Falha ao iniciar o servidor
    echo Verifique os logs em: %ERROR_LOG%
    del "%PID_FILE%" >nul 2>&1
)
goto end

:stop_server
if not exist "%PID_FILE%" (
    echo Servidor não está rodando (PID file não encontrado)
    goto end
)

set /p PID=<"%PID_FILE%"

tasklist /FI "PID eq !PID!" 2>nul | find /I "!PID!" >nul
if !errorlevel! equ 0 (
    echo Parando servidor (PID: !PID!)...
    taskkill /PID !PID! /F >nul 2>&1
    del "%PID_FILE%" >nul 2>&1
    echo ✅ Servidor parado com sucesso
) else (
    echo Processo não encontrado, removendo PID file...
    del "%PID_FILE%" >nul 2>&1
)
goto end

:restart_server
call :stop_server
timeout /t 2 /nobreak >nul
call :start_server
goto end

:status_server
if not exist "%PID_FILE%" (
    echo ❌ Servidor não está rodando
    goto end
)

set /p PID=<"%PID_FILE%"

tasklist /FI "PID eq !PID!" 2>nul | find /I "!PID!" >nul
if !errorlevel! equ 0 (
    echo ✅ Servidor está rodando (PID: !PID!)
    echo    URL: http://0.0.0.0:8001
    echo    Logs: %LOG_FILE%
    
    if exist "%LOG_FILE%" (
        echo.
        echo Últimas linhas do log:
        powershell "Get-Content '%LOG_FILE%' | Select-Object -Last 5"
    )
) else (
    echo ❌ Servidor não está rodando (processo não encontrado)
    del "%PID_FILE%" >nul 2>&1
)
goto end

:usage
echo Uso: %0 {start^|stop^|restart^|status}
echo.
echo Comandos:
echo   start   - Inicia o servidor em segundo plano
echo   stop    - Para o servidor
echo   restart - Reinicia o servidor
echo   status  - Mostra status do servidor

:end
endlocal
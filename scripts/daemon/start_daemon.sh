#!/bin/bash

# Script para iniciar o servidor MCP Supabase em segundo plano (daemon)
# Uso: ./start_daemon.sh [start|stop|restart|status]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$SCRIPT_DIR/venv"
PID_FILE="$SCRIPT_DIR/mcp_server.pid"
LOG_FILE="$SCRIPT_DIR/mcp_server.log"
ERROR_LOG="$SCRIPT_DIR/mcp_server_error.log"

# Carrega variáveis de ambiente
if [ -f "$SCRIPT_DIR/.env" ]; then
    source "$SCRIPT_DIR/.env"
fi

start_server() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            echo "Servidor já está rodando (PID: $PID)"
            return 1
        else
            echo "Removendo PID file obsoleto..."
            rm -f "$PID_FILE"
        fi
    fi

    echo "Iniciando servidor MCP Supabase em segundo plano..."
    
    # Ativa o ambiente virtual
    source "$VENV_PATH/bin/activate"
    
    # Inicia o servidor em background
    nohup python -m supabase_mcp_server \
        --host 0.0.0.0 \
        --port 8001 \
        > "$LOG_FILE" 2> "$ERROR_LOG" &
    
    SERVER_PID=$!
    echo $SERVER_PID > "$PID_FILE"
    
    # Aguarda um pouco para verificar se o servidor iniciou corretamente
    sleep 3
    
    if ps -p $SERVER_PID > /dev/null 2>&1; then
        echo "✅ Servidor iniciado com sucesso!"
        echo "   PID: $SERVER_PID"
        echo "   Logs: $LOG_FILE"
        echo "   Erros: $ERROR_LOG"
        echo "   URL: http://0.0.0.0:8001"
    else
        echo "❌ Falha ao iniciar o servidor"
        echo "Verifique os logs em: $ERROR_LOG"
        rm -f "$PID_FILE"
        return 1
    fi
}

stop_server() {
    if [ ! -f "$PID_FILE" ]; then
        echo "Servidor não está rodando (PID file não encontrado)"
        return 1
    fi
    
    PID=$(cat "$PID_FILE")
    
    if ps -p $PID > /dev/null 2>&1; then
        echo "Parando servidor (PID: $PID)..."
        kill $PID
        
        # Aguarda o processo terminar
        for i in {1..10}; do
            if ! ps -p $PID > /dev/null 2>&1; then
                break
            fi
            sleep 1
        done
        
        # Force kill se necessário
        if ps -p $PID > /dev/null 2>&1; then
            echo "Forçando parada do servidor..."
            kill -9 $PID
        fi
        
        rm -f "$PID_FILE"
        echo "✅ Servidor parado com sucesso"
    else
        echo "Processo não encontrado, removendo PID file..."
        rm -f "$PID_FILE"
    fi
}

status_server() {
    if [ ! -f "$PID_FILE" ]; then
        echo "❌ Servidor não está rodando"
        return 1
    fi
    
    PID=$(cat "$PID_FILE")
    
    if ps -p $PID > /dev/null 2>&1; then
        echo "✅ Servidor está rodando (PID: $PID)"
        echo "   URL: http://0.0.0.0:8001"
        echo "   Logs: $LOG_FILE"
        
        # Mostra últimas linhas do log
        if [ -f "$LOG_FILE" ]; then
            echo ""
            echo "Últimas linhas do log:"
            tail -5 "$LOG_FILE"
        fi
    else
        echo "❌ Servidor não está rodando (processo não encontrado)"
        rm -f "$PID_FILE"
        return 1
    fi
}

case "$1" in
    start)
        start_server
        ;;
    stop)
        stop_server
        ;;
    restart)
        stop_server
        sleep 2
        start_server
        ;;
    status)
        status_server
        ;;
    *)
        echo "Uso: $0 {start|stop|restart|status}"
        echo ""
        echo "Comandos:"
        echo "  start   - Inicia o servidor em segundo plano"
        echo "  stop    - Para o servidor"
        echo "  restart - Reinicia o servidor"
        echo "  status  - Mostra status do servidor"
        exit 1
        ;;
esac
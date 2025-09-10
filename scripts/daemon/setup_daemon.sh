#!/bin/bash

# Script para configurar o servidor MCP Supabase como daemon
# Detecta o sistema operacional e configura automaticamente

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SERVICE_NAME="mcp-supabase"

echo "🚀 Configurando Supabase MCP Server como daemon..."

# Detecta o sistema operacional
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command -v systemctl >/dev/null 2>&1; then
            echo "systemd"
        else
            echo "linux"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

# Configura systemd (Linux)
setup_systemd() {
    echo "📋 Configurando serviço systemd..."
    
    # Atualiza o arquivo de serviço com o caminho correto
    sed "s|/opt/mcp-supabase|$PROJECT_ROOT|g" "$PROJECT_ROOT/systemd/mcp-supabase.service" > /tmp/mcp-supabase.service
    
    # Copia o arquivo de serviço
    sudo cp /tmp/mcp-supabase.service /etc/systemd/system/
    sudo chmod 644 /etc/systemd/system/mcp-supabase.service
    
    # Recarrega systemd
    sudo systemctl daemon-reload
    
    # Habilita o serviço
    sudo systemctl enable mcp-supabase
    
    echo "✅ Serviço systemd configurado!"
    echo "   Para iniciar: sudo systemctl start mcp-supabase"
    echo "   Para parar: sudo systemctl stop mcp-supabase"
    echo "   Para status: sudo systemctl status mcp-supabase"
    echo "   Para logs: sudo journalctl -u mcp-supabase -f"
}

# Configura launchd (macOS)
setup_launchd() {
    echo "📋 Configurando serviço launchd (macOS)..."
    
    PLIST_FILE="$HOME/Library/LaunchAgents/com.supabase.mcp.plist"
    
    cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.supabase.mcp</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PROJECT_ROOT/venv/bin/python</string>
        <string>-m</string>
        <string>supabase_mcp_server</string>
        <string>--host</string>
        <string>0.0.0.0</string>
        <string>--port</string>
        <string>8001</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$PROJECT_ROOT</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>$PROJECT_ROOT/venv/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$PROJECT_ROOT/mcp_server.log</string>
    <key>StandardErrorPath</key>
    <string>$PROJECT_ROOT/mcp_server_error.log</string>
</dict>
</plist>
EOF
    
    # Carrega o serviço
    launchctl load "$PLIST_FILE"
    
    echo "✅ Serviço launchd configurado!"
    echo "   Para iniciar: launchctl start com.supabase.mcp"
    echo "   Para parar: launchctl stop com.supabase.mcp"
    echo "   Para descarregar: launchctl unload $PLIST_FILE"
}

# Configura scripts daemon
setup_daemon_scripts() {
    echo "📋 Configurando scripts daemon..."
    
    # Torna os scripts executáveis
    chmod +x "$SCRIPT_DIR/start_daemon.sh"
    
    echo "✅ Scripts daemon configurados!"
    echo "   Para iniciar: ./start_daemon.sh start"
    echo "   Para parar: ./start_daemon.sh stop"
    echo "   Para status: ./start_daemon.sh status"
}

# Verifica se o ambiente virtual existe
check_venv() {
    if [ ! -d "$PROJECT_ROOT/venv" ]; then
        echo "❌ Ambiente virtual não encontrado!"
        echo "   Execute primeiro: python -m venv venv && source venv/bin/activate && pip install -e ."
        exit 1
    fi
}

# Verifica se o arquivo .env existe
check_env() {
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        echo "⚠️  Arquivo .env não encontrado!"
        echo "   Copie .env.example para .env e configure suas variáveis"
        cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
        echo "   Arquivo .env criado a partir do exemplo"
    fi
}

# Função principal
main() {
    echo "🔍 Detectando sistema operacional..."
    OS=$(detect_os)
    echo "   Sistema detectado: $OS"
    
    # Verificações básicas
    check_venv
    check_env
    
    case $OS in
        "systemd")
            setup_systemd
            ;;
        "macos")
            setup_launchd
            ;;
        "linux"|"windows"|"unknown")
            setup_daemon_scripts
            ;;
    esac
    
    echo ""
    echo "🎉 Configuração concluída!"
    echo ""
    echo "📝 Próximos passos:"
    echo "   1. Configure suas variáveis no arquivo .env"
    echo "   2. Inicie o serviço usando os comandos mostrados acima"
    echo "   3. Teste a conexão: curl http://localhost:8001/health"
    echo ""
    echo "📚 Para mais informações, consulte o QUICK_START.md"
}

# Executa se chamado diretamente
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
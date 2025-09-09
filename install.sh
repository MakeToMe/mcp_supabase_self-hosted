#!/bin/bash
set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Instalando Supabase MCP Server...${NC}"

# Verificar se está rodando como root
if [[ $EUID -eq 0 ]]; then
   echo -e "${RED}❌ Este script não deve ser executado como root${NC}"
   exit 1
fi

# Detectar sistema operacional
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if [ -f /etc/debian_version ]; then
        OS="debian"
        echo -e "${GREEN}✅ Sistema detectado: Debian/Ubuntu${NC}"
    elif [ -f /etc/redhat-release ]; then
        OS="redhat"
        echo -e "${GREEN}✅ Sistema detectado: RedHat/CentOS${NC}"
    else
        echo -e "${RED}❌ Sistema Linux não suportado${NC}"
        exit 1
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    echo -e "${GREEN}✅ Sistema detectado: macOS${NC}"
else
    echo -e "${RED}❌ Sistema operacional não suportado${NC}"
    exit 1
fi

# Função para instalar dependências no Ubuntu/Debian
install_debian() {
    echo -e "${YELLOW}📦 Atualizando sistema...${NC}"
    sudo apt update && sudo apt upgrade -y
    
    echo -e "${YELLOW}📦 Instalando dependências...${NC}"
    sudo apt install -y python3.11 python3.11-pip python3.11-venv git curl nginx software-properties-common
    
    # Verificar se python3.11 está disponível
    if ! command -v python3.11 &> /dev/null; then
        echo -e "${YELLOW}📦 Adicionando repositório Python 3.11...${NC}"
        sudo add-apt-repository ppa:deadsnakes/ppa -y
        sudo apt update
        sudo apt install -y python3.11 python3.11-pip python3.11-venv python3.11-dev
    fi
}

# Função para instalar dependências no RedHat/CentOS
install_redhat() {
    echo -e "${YELLOW}📦 Atualizando sistema...${NC}"
    sudo yum update -y
    
    echo -e "${YELLOW}📦 Instalando dependências...${NC}"
    sudo yum install -y python3.11 python3.11-pip git curl nginx
}

# Função para instalar dependências no macOS
install_macos() {
    echo -e "${YELLOW}📦 Verificando Homebrew...${NC}"
    if ! command -v brew &> /dev/null; then
        echo -e "${YELLOW}📦 Instalando Homebrew...${NC}"
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    
    echo -e "${YELLOW}📦 Instalando dependências...${NC}"
    brew install python@3.11 git curl nginx
}

# Instalar dependências baseado no OS
case $OS in
    "debian")
        install_debian
        ;;
    "redhat")
        install_redhat
        ;;
    "macos")
        install_macos
        ;;
esac

# Instalar Poetry
echo -e "${YELLOW}📦 Instalando Poetry...${NC}"
if ! command -v poetry &> /dev/null; then
    curl -sSL https://install.python-poetry.org | python3 -
    
    # Adicionar Poetry ao PATH
    export PATH="$HOME/.local/bin:$PATH"
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
    
    # Para zsh users
    if [ -f ~/.zshrc ]; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
    fi
else
    echo -e "${GREEN}✅ Poetry já está instalado${NC}"
fi

# Verificar se estamos no diretório correto
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}❌ Arquivo pyproject.toml não encontrado. Execute este script no diretório do projeto.${NC}"
    exit 1
fi

# Instalar dependências do projeto
echo -e "${YELLOW}📦 Instalando dependências do projeto...${NC}"
$HOME/.local/bin/poetry install

# Criar arquivo .env se não existir
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}📝 Criando arquivo .env...${NC}"
    cp .env.example .env
    echo -e "${BLUE}📝 Configure o arquivo .env com suas credenciais Supabase${NC}"
fi

# Criar script de inicialização
echo -e "${YELLOW}📝 Criando script de inicialização...${NC}"
cat > start_server.sh << 'EOF'
#!/bin/bash
export PATH="$HOME/.local/bin:$PATH"
cd "$(dirname "$0")"
poetry run python -m supabase_mcp_server.main
EOF

chmod +x start_server.sh

# Criar arquivo de serviço systemd (opcional)
echo -e "${YELLOW}📝 Criando arquivo de serviço systemd...${NC}"
cat > supabase-mcp.service << EOF
[Unit]
Description=Supabase MCP Server
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment=PATH=$HOME/.local/bin
ExecStart=$HOME/.local/bin/poetry run python -m supabase_mcp_server.main
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✅ Instalação concluída!${NC}"
echo ""
echo -e "${BLUE}📋 Próximos passos:${NC}"
echo -e "${YELLOW}1.${NC} Configure o arquivo .env com suas credenciais:"
echo -e "   ${BLUE}nano .env${NC}"
echo ""
echo -e "${YELLOW}2.${NC} Inicie o servidor:"
echo -e "   ${BLUE}./start_server.sh${NC}"
echo ""
echo -e "${YELLOW}3.${NC} Para instalar como serviço systemd (opcional):"
echo -e "   ${BLUE}sudo cp supabase-mcp.service /etc/systemd/system/${NC}"
echo -e "   ${BLUE}sudo systemctl daemon-reload${NC}"
echo -e "   ${BLUE}sudo systemctl enable supabase-mcp.service${NC}"
echo -e "   ${BLUE}sudo systemctl start supabase-mcp.service${NC}"
echo ""
echo -e "${YELLOW}4.${NC} Teste a instalação:"
echo -e "   ${BLUE}curl http://localhost:8001/health${NC}"
echo ""
echo -e "${GREEN}🎉 Servidor MCP Supabase pronto para uso!${NC}"
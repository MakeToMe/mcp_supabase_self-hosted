#!/bin/bash
set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Instalação Supabase MCP Server - Ubuntu 20.04${NC}"

# Verificar se está rodando como root
if [[ $EUID -eq 0 ]]; then
   echo -e "${YELLOW}⚠️  Executando como root. Recomendamos usar um usuário não-root.${NC}"
   echo -e "${YELLOW}⚠️  Continuando em 5 segundos... (Ctrl+C para cancelar)${NC}"
   sleep 5
fi

# Detectar versão do Ubuntu
if [ -f /etc/lsb-release ]; then
    . /etc/lsb-release
    UBUNTU_VERSION=$DISTRIB_RELEASE
    echo -e "${GREEN}✅ Ubuntu ${UBUNTU_VERSION} detectado${NC}"
else
    echo -e "${RED}❌ Não foi possível detectar a versão do Ubuntu${NC}"
    exit 1
fi

# Atualizar sistema
echo -e "${YELLOW}📦 Atualizando sistema...${NC}"
sudo apt update && sudo apt upgrade -y

# Instalar dependências básicas
echo -e "${YELLOW}📦 Instalando dependências básicas...${NC}"
sudo apt install -y git curl nginx software-properties-common python3-pip lsb-release

# Para Ubuntu 20.04, usar Python 3.8 (nativo) ou instalar 3.10
if [[ "$UBUNTU_VERSION" == "20.04" ]]; then
    echo -e "${YELLOW}📦 Configurando Python para Ubuntu 20.04...${NC}"
    
    # Tentar instalar Python 3.10 do repositório deadsnakes
    echo -e "${YELLOW}📦 Adicionando repositório deadsnakes...${NC}"
    sudo add-apt-repository ppa:deadsnakes/ppa -y
    sudo apt update
    
    # Instalar Python 3.10 (mais compatível que 3.11 no Ubuntu 20.04)
    echo -e "${YELLOW}📦 Instalando Python 3.10...${NC}"
    sudo apt install -y python3.10 python3.10-pip python3.10-venv python3.10-dev python3.10-distutils
    
    # Verificar instalação
    if command -v python3.10 &> /dev/null; then
        PYTHON_CMD="python3.10"
        echo -e "${GREEN}✅ Python 3.10 instalado com sucesso${NC}"
    else
        # Fallback para Python 3.8 (nativo do Ubuntu 20.04)
        PYTHON_CMD="python3.8"
        sudo apt install -y python3.8 python3.8-pip python3.8-venv python3.8-dev
        echo -e "${YELLOW}⚠️  Usando Python 3.8 (nativo do Ubuntu 20.04)${NC}"
    fi
else
    # Para outras versões do Ubuntu
    sudo apt install -y python3.11 python3.11-pip python3.11-venv python3.11-dev
    PYTHON_CMD="python3.11"
fi

# Instalar pip para a versão do Python escolhida
echo -e "${YELLOW}📦 Configurando pip...${NC}"
curl -sS https://bootstrap.pypa.io/get-pip.py | sudo $PYTHON_CMD

# Instalar Poetry
echo -e "${YELLOW}📦 Instalando Poetry...${NC}"
if ! command -v poetry &> /dev/null; then
    curl -sSL https://install.python-poetry.org | $PYTHON_CMD -
    
    # Adicionar Poetry ao PATH
    export PATH="$HOME/.local/bin:$PATH"
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
    
    # Para zsh users
    if [ -f ~/.zshrc ]; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
    fi
    
    echo -e "${GREEN}✅ Poetry instalado${NC}"
else
    echo -e "${GREEN}✅ Poetry já está instalado${NC}"
fi

# Clonar o repositório se necessário
if [ ! -f "pyproject.toml" ]; then
    echo -e "${YELLOW}📦 Clonando repositório...${NC}"
    git clone https://github.com/MakeToMe/mcp_supabase_self-hosted.git
    cd mcp_supabase_self-hosted
fi

# Configurar Poetry para usar a versão correta do Python
echo -e "${YELLOW}📦 Configurando Poetry...${NC}"
export PATH="$HOME/.local/bin:$PATH"
$HOME/.local/bin/poetry env use $PYTHON_CMD

# Instalar dependências do projeto
echo -e "${YELLOW}📦 Instalando dependências do projeto...${NC}"
$HOME/.local/bin/poetry install

# Criar arquivo .env se não existir
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}📝 Criando arquivo .env...${NC}"
    if [ -f ".env.example" ]; then
        cp .env.example .env
    else
        cat > .env << 'EOF'
# Supabase Configuration
SUPABASE_URL=https://studio.rardevops.com
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.ewogICJyb2xlIjogImFub24iLAogICJpc3MiOiAic3VwYWJhc2UiLAogICJpYXQiOiAxNzM0ODM2NDAwLAogICJleHAiOiAxODkyNjAyODAwCn0.a1mpboOHE9IMJbhsGquPv72W0iaDnM3kHYRKaZ2t3kA
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.ewogICJyb2xlIjogInNlcnZpY2Vfcm9sZSIsCiAgImlzcyI6ICJzdXBhYmFzZSIsCiAgImlhdCI6IDE3MzQ4MzY0MDAsCiAgImV4cCI6IDE4OTI2MDI4MDAKfQ.VmlSWOEpE77ZfOcQSjoP-1Ty4eWUgybz_K9AUvdsY70

# Database Configuration
DATABASE_URL=postgresql://postgres:Aha517_Rar-PGRS_U2a59w@studio.rardevops.com:4202/postgres

# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8001
LOG_LEVEL=INFO

# Security Configuration
MCP_API_KEY=mcp-test-key-2024-rardevops
EOF
    fi
    echo -e "${BLUE}📝 Arquivo .env criado com configurações padrão${NC}"
fi

# Criar script de inicialização
echo -e "${YELLOW}📝 Criando script de inicialização...${NC}"
cat > start_server.sh << EOF
#!/bin/bash
export PATH="\$HOME/.local/bin:\$PATH"
cd "\$(dirname "\$0")"
poetry run python -m supabase_mcp_server.main
EOF

chmod +x start_server.sh

# Criar arquivo de serviço systemd
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
echo -e "${BLUE}📋 Informações da instalação:${NC}"
echo -e "${YELLOW}Python usado:${NC} $PYTHON_CMD"
echo -e "${YELLOW}Versão:${NC} $($PYTHON_CMD --version)"
echo -e "${YELLOW}Poetry:${NC} $($HOME/.local/bin/poetry --version)"
echo ""
echo -e "${BLUE}📋 Próximos passos:${NC}"
echo -e "${YELLOW}1.${NC} Inicie o servidor:"
echo -e "   ${BLUE}./start_server.sh${NC}"
echo ""
echo -e "${YELLOW}2.${NC} Teste a instalação:"
echo -e "   ${BLUE}curl http://localhost:8001/health${NC}"
echo ""
echo -e "${YELLOW}3.${NC} Para instalar como serviço (opcional):"
echo -e "   ${BLUE}sudo cp supabase-mcp.service /etc/systemd/system/${NC}"
echo -e "   ${BLUE}sudo systemctl daemon-reload${NC}"
echo -e "   ${BLUE}sudo systemctl enable supabase-mcp.service${NC}"
echo -e "   ${BLUE}sudo systemctl start supabase-mcp.service${NC}"
echo ""
echo -e "${GREEN}🎉 Servidor MCP Supabase pronto para uso!${NC}"
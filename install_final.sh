#!/bin/bash
set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Instalação Final - Supabase MCP Server${NC}"

# Verificar se está rodando como root
if [[ $EUID -eq 0 ]]; then
   echo -e "${YELLOW}⚠️  Executando como root. Continuando em 3 segundos...${NC}"
   sleep 3
fi

# Atualizar sistema
echo -e "${YELLOW}📦 Atualizando sistema...${NC}"
sudo apt update

# Instalar dependências básicas
echo -e "${YELLOW}📦 Instalando dependências básicas...${NC}"
sudo apt install -y git curl nginx software-properties-common python3-pip python3-venv python3-dev build-essential

# Detectar versão do Python disponível
if command -v python3.10 &> /dev/null; then
    PYTHON_CMD="python3.10"
    echo -e "${GREEN}✅ Usando Python 3.10${NC}"
elif command -v python3.8 &> /dev/null; then
    PYTHON_CMD="python3.8"
    echo -e "${GREEN}✅ Usando Python 3.8${NC}"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    echo -e "${GREEN}✅ Usando Python 3 padrão${NC}"
else
    echo -e "${RED}❌ Python 3 não encontrado${NC}"
    exit 1
fi

# Verificar versão do Python
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
echo -e "${BLUE}📋 Versão do Python: ${PYTHON_VERSION}${NC}"

# Atualizar pip
echo -e "${YELLOW}📦 Atualizando pip...${NC}"
$PYTHON_CMD -m pip install --upgrade pip

# Instalar Poetry com método mais seguro
echo -e "${YELLOW}📦 Instalando Poetry...${NC}"
if ! command -v poetry &> /dev/null; then
    # Instalar Poetry via pip com --user para evitar conflitos
    echo -e "${YELLOW}📦 Instalando Poetry via pip (método seguro)...${NC}"
    $PYTHON_CMD -m pip install --user poetry --break-system-packages 2>/dev/null || $PYTHON_CMD -m pip install --user poetry
    
    # Adicionar Poetry ao PATH
    export PATH="$HOME/.local/bin:$PATH"
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
    
    echo -e "${GREEN}✅ Poetry instalado via pip${NC}"
else
    echo -e "${GREEN}✅ Poetry já está instalado${NC}"
fi

# Verificar se Poetry funciona
echo -e "${YELLOW}📦 Verificando Poetry...${NC}"
export PATH="$HOME/.local/bin:$PATH"
if command -v poetry &> /dev/null; then
    POETRY_CMD="poetry"
elif $PYTHON_CMD -m poetry --version &> /dev/null; then
    POETRY_CMD="$PYTHON_CMD -m poetry"
else
    echo -e "${RED}❌ Poetry não está funcionando corretamente${NC}"
    echo -e "${YELLOW}💡 Tentando criar ambiente virtual manualmente...${NC}"
    
    # Fallback: usar venv diretamente
    echo -e "${YELLOW}📦 Criando ambiente virtual...${NC}"
    $PYTHON_CMD -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    
    # Clonar repositório primeiro
    if [ ! -f "pyproject.toml" ]; then
        echo -e "${YELLOW}📦 Clonando repositório...${NC}"
        git clone https://github.com/MakeToMe/mcp_supabase_self-hosted.git
        cd mcp_supabase_self-hosted
    fi
    
    # Instalar dependências diretamente via pip
    echo -e "${YELLOW}📦 Instalando dependências via pip...${NC}"
    pip install fastapi uvicorn pydantic pydantic-settings asyncpg supabase redis prometheus-client structlog python-jose python-multipart httpx tenacity
    
    # Criar script de inicialização para venv
    cat > start_server.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python -m supabase_mcp_server.main
EOF
    chmod +x start_server.sh
    
    echo -e "${GREEN}✅ Instalação via venv concluída${NC}"
    VENV_MODE=true
fi

if [ "$VENV_MODE" != "true" ]; then
    echo -e "${GREEN}✅ Poetry funcionando: $($POETRY_CMD --version)${NC}"
    
    # Clonar o repositório se necessário
    if [ ! -f "pyproject.toml" ]; then
        echo -e "${YELLOW}📦 Clonando repositório...${NC}"
        git clone https://github.com/MakeToMe/mcp_supabase_self-hosted.git
        cd mcp_supabase_self-hosted
    fi
    
    # Configurar Poetry
    echo -e "${YELLOW}📦 Configurando Poetry...${NC}"
    $POETRY_CMD config virtualenvs.create true
    $POETRY_CMD config virtualenvs.in-project false
    $POETRY_CMD env use $PYTHON_CMD
    
    # Instalar dependências do projeto
    echo -e "${YELLOW}📦 Instalando dependências do projeto...${NC}"
    $POETRY_CMD install
    
    # Criar script de inicialização para Poetry
    cat > start_server.sh << 'EOF'
#!/bin/bash
export PATH="$HOME/.local/bin:$PATH"
cd "$(dirname "$0")"
poetry run python -m supabase_mcp_server.main
EOF
    chmod +x start_server.sh
fi

# Criar arquivo .env se não existir
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}📝 Criando arquivo .env...${NC}"
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
    echo -e "${BLUE}📝 Arquivo .env criado${NC}"
fi

# Criar script de teste
echo -e "${YELLOW}📝 Criando script de teste...${NC}"
cat > test_server.sh << 'EOF'
#!/bin/bash
echo "🧪 Testando servidor..."
sleep 2
echo "1. Verificando se o servidor responde..."
curl -f http://localhost:8001/health && echo " ✅ Health check OK" || echo " ❌ Health check falhou"

echo "2. Testando autenticação..."
curl -f -H "Authorization: Bearer mcp-test-key-2024-rardevops" \
     http://localhost:8001/mcp/tools && echo " ✅ Auth OK" || echo " ❌ Auth falhou"

echo "✅ Teste concluído"
EOF

chmod +x test_server.sh

echo -e "${GREEN}✅ Instalação concluída!${NC}"
echo ""
echo -e "${BLUE}📋 Informações:${NC}"
echo -e "${YELLOW}Python:${NC} $PYTHON_CMD ($PYTHON_VERSION)"
if [ "$VENV_MODE" = "true" ]; then
    echo -e "${YELLOW}Ambiente:${NC} venv (ambiente virtual Python)"
else
    echo -e "${YELLOW}Poetry:${NC} $($POETRY_CMD --version 2>/dev/null || echo 'Instalado')"
fi
echo ""
echo -e "${BLUE}📋 Para iniciar o servidor:${NC}"
echo -e "   ${GREEN}./start_server.sh${NC}"
echo ""
echo -e "${BLUE}📋 Para testar (em outro terminal):${NC}"
echo -e "   ${GREEN}./test_server.sh${NC}"
echo ""
echo -e "${BLUE}📋 Para parar o servidor:${NC}"
echo -e "   ${GREEN}Ctrl+C${NC}"
echo ""
echo -e "${GREEN}🎉 Pronto para uso!${NC}"
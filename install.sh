#!/bin/bash
set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Instalação Definitiva - Supabase MCP Server${NC}"

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

# Clonar o repositório se necessário
if [ ! -f "pyproject.toml" ]; then
    echo -e "${YELLOW}📦 Clonando repositório...${NC}"
    git clone https://github.com/MakeToMe/mcp_supabase_self-hosted.git
    cd mcp_supabase_self-hosted
fi

# Criar ambiente virtual
echo -e "${YELLOW}📦 Criando ambiente virtual...${NC}"
$PYTHON_CMD -m venv venv
source venv/bin/activate

# Atualizar pip no ambiente virtual
echo -e "${YELLOW}📦 Atualizando pip...${NC}"
pip install --upgrade pip

# Instalar dependências em ordem inteligente
echo -e "${YELLOW}📦 Instalando dependências principais...${NC}"
pip install fastapi uvicorn pydantic pydantic-settings

echo -e "${YELLOW}📦 Instalando Supabase (com dependências compatíveis)...${NC}"
pip install supabase

echo -e "${YELLOW}📦 Instalando dependências adicionais...${NC}"
pip install asyncpg redis prometheus-client structlog tenacity python-multipart

echo -e "${YELLOW}📦 Instalando python-jose...${NC}"
pip install "python-jose[cryptography]"

echo -e "${GREEN}✅ Todas as dependências instaladas${NC}"

# Instalar o projeto em modo desenvolvimento
echo -e "${YELLOW}📦 Instalando o projeto supabase_mcp_server...${NC}"
pip install -e .

# Verificar se tudo foi instalado corretamente
echo -e "${YELLOW}📦 Verificando instalação...${NC}"
python -c "import fastapi, uvicorn, supabase, asyncpg; print('✅ Dependências principais OK')"
python -c "import supabase_mcp_server; print('✅ Projeto supabase_mcp_server OK')"

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

# Criar script de inicialização robusto
echo -e "${YELLOW}📝 Criando script de inicialização...${NC}"
cat > start_server.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate

# Verificar se o módulo existe
if ! python -c "import supabase_mcp_server" 2>/dev/null; then
    echo "❌ Módulo supabase_mcp_server não encontrado. Instalando..."
    pip install -e .
fi

# Adicionar src ao PYTHONPATH como backup
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

echo "🚀 Iniciando servidor MCP Supabase..."
echo "📡 Servidor será acessível em: http://0.0.0.0:8001"
echo "🔑 API Key: mcp-test-key-2024-rardevops"
echo "⏹️  Para parar: Ctrl+C"
echo ""

python -m supabase_mcp_server.main
EOF

chmod +x start_server.sh

# Criar script de teste
echo -e "${YELLOW}📝 Criando script de teste...${NC}"
cat > test_server.sh << 'EOF'
#!/bin/bash
echo "🧪 Testando servidor MCP Supabase..."
echo "=================================="
sleep 2

echo "1. 🏥 Health Check..."
if curl -f -s http://localhost:8001/health > /dev/null; then
    echo "   ✅ Servidor respondendo"
else
    echo "   ❌ Servidor não responde"
    exit 1
fi

echo "2. 🔐 Testando autenticação..."
if curl -f -s -H "Authorization: Bearer mcp-test-key-2024-rardevops" \
     http://localhost:8001/mcp/tools > /dev/null; then
    echo "   ✅ Autenticação OK"
else
    echo "   ❌ Falha na autenticação"
fi

echo "3. 🛠️  Listando ferramentas disponíveis..."
curl -s -H "Authorization: Bearer mcp-test-key-2024-rardevops" \
     http://localhost:8001/mcp/tools | python -m json.tool 2>/dev/null || echo "   ❌ Erro ao listar ferramentas"

echo ""
echo "✅ Teste concluído!"
EOF

chmod +x test_server.sh

# Criar script de status
echo -e "${YELLOW}📝 Criando script de status...${NC}"
cat > status.sh << 'EOF'
#!/bin/bash
echo "📊 Status do Servidor MCP Supabase"
echo "=================================="
echo "🐍 Python: $(source venv/bin/activate && python --version)"
echo "📦 Ambiente: venv ativo"
echo ""
echo "🔧 Dependências principais:"
source venv/bin/activate
python -c "
try:
    import supabase_mcp_server
    print('   ✅ supabase_mcp_server')
except ImportError:
    print('   ❌ supabase_mcp_server')

try:
    import fastapi, uvicorn, supabase
    print('   ✅ fastapi, uvicorn, supabase')
except ImportError:
    print('   ❌ fastapi, uvicorn, supabase')
"
echo ""
echo "🌐 Conectividade:"
if curl -s http://localhost:8001/health > /dev/null; then
    echo "   ✅ Servidor respondendo em http://localhost:8001"
else
    echo "   ❌ Servidor não responde"
fi
echo ""
echo "📁 Arquivos de configuração:"
[ -f .env ] && echo "   ✅ .env" || echo "   ❌ .env"
[ -f start_server.sh ] && echo "   ✅ start_server.sh" || echo "   ❌ start_server.sh"
[ -f test_server.sh ] && echo "   ✅ test_server.sh" || echo "   ❌ test_server.sh"
EOF

chmod +x status.sh

echo -e "${GREEN}✅ Instalação concluída com sucesso!${NC}"
echo ""
echo -e "${BLUE}📋 Informações:${NC}"
echo -e "${YELLOW}Python:${NC} $PYTHON_CMD ($PYTHON_VERSION)"
echo -e "${YELLOW}Ambiente:${NC} venv (ambiente virtual Python)"
echo -e "${YELLOW}Projeto:${NC} Instalado em modo desenvolvimento"
echo ""
echo -e "${BLUE}📋 Comandos disponíveis:${NC}"
echo -e "   ${GREEN}./start_server.sh${NC}  - Iniciar servidor"
echo -e "   ${GREEN}./test_server.sh${NC}   - Testar servidor"
echo -e "   ${GREEN}./status.sh${NC}        - Ver status"
echo ""
echo -e "${BLUE}📡 Acesso externo:${NC}"
echo -e "   ${GREEN}http://SEU_IP:8001/health${NC}"
echo -e "   ${GREEN}http://SEU_IP:8001/mcp/tools${NC}"
echo ""
echo -e "${GREEN}🎉 Servidor MCP Supabase pronto para uso!${NC}"
#!/bin/bash
set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Instalação Produção - Supabase MCP Server${NC}"

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

# Instalar apenas dependências de produção (sem dev)
echo -e "${YELLOW}📦 Instalando dependências de produção...${NC}"
pip install \
    fastapi==0.104.1 \
    "uvicorn[standard]==0.24.0" \
    pydantic==2.5.0 \
    pydantic-settings==2.1.0 \
    asyncpg==0.29.0 \
    supabase==2.3.0 \
    redis==5.0.1 \
    prometheus-client==0.19.0 \
    structlog==23.2.0 \
    "python-jose[cryptography]==3.3.0" \
    python-multipart==0.0.6 \
    "httpx>=0.24.0,<0.25.0" \
    tenacity==8.2.3

echo -e "${GREEN}✅ Dependências instaladas${NC}"

# Instalar o projeto
echo -e "${YELLOW}📦 Instalando o projeto supabase_mcp_server...${NC}"
pip install -e .

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

# Criar script de inicialização
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
python -m supabase_mcp_server.main
EOF

chmod +x start_server.sh

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

# Criar serviço systemd
echo -e "${YELLOW}📝 Criando serviço systemd...${NC}"
cat > supabase-mcp.service << EOF
[Unit]
Description=Supabase MCP Server
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/venv/bin/python -m supabase_mcp_server.main
Restart=always
RestartSec=3
Environment=PATH=$(pwd)/venv/bin

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✅ Instalação concluída!${NC}"
echo ""
echo -e "${BLUE}📋 Informações:${NC}"
echo -e "${YELLOW}Python:${NC} $PYTHON_CMD ($PYTHON_VERSION)"
echo -e "${YELLOW}Ambiente:${NC} venv (ambiente virtual Python)"
echo -e "${YELLOW}Dependências:${NC} Apenas produção (sem ferramentas dev)"
echo ""
echo -e "${BLUE}📋 Para iniciar o servidor:${NC}"
echo -e "   ${GREEN}./start_server.sh${NC}"
echo ""
echo -e "${BLUE}📋 Para testar (em outro terminal):${NC}"
echo -e "   ${GREEN}./test_server.sh${NC}"
echo ""
echo -e "${BLUE}📋 Para instalar como serviço:${NC}"
echo -e "   ${GREEN}sudo cp supabase-mcp.service /etc/systemd/system/${NC}"
echo -e "   ${GREEN}sudo systemctl daemon-reload${NC}"
echo -e "   ${GREEN}sudo systemctl enable supabase-mcp.service${NC}"
echo -e "   ${GREEN}sudo systemctl start supabase-mcp.service${NC}"
echo ""
echo -e "${GREEN}🎉 Servidor pronto para produção!${NC}"
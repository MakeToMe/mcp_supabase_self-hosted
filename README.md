# Supabase MCP Server

A Model Context Protocol (MCP) server for Supabase self-hosted instances, enabling AI assistants to interact directly with your PostgreSQL database and Supabase services.

## 🚀 Quick Deploy

### One-Line Installation
```bash
curl -sSL https://raw.githubusercontent.com/MakeToMe/mcp_supabase_self-hosted/main/install.sh | bash
```

### Manual Installation
```bash
git clone https://github.com/MakeToMe/mcp_supabase_self-hosted.git
cd mcp_supabase_self-hosted
chmod +x install.sh && ./install.sh
```

## 📋 Passo a Passo Completo

### 1. Subir para GitHub
```bash
git init
git add .
git commit -m "Initial commit: Supabase MCP Server"
git branch -M main
git remote add origin https://github.com/MakeToMe/mcp_supabase_self-hosted.git
git push -u origin main
```

### 2. Deploy em VPS
```bash
# Conectar ao VPS
ssh user@seu-vps.com

# Clonar e instalar
git clone https://github.com/MakeToMe/mcp_supabase_self-hosted.git
cd mcp_supabase_self-hosted
chmod +x install.sh && ./install.sh
```

### 3. Configurar Variáveis Supabase
```bash
# Copiar template
cp .env.example .env

# Editar configurações
nano .env
```

**Template .env:**
```env
# Supabase Configuration
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_ANON_KEY=sua-chave-anonima
SUPABASE_SERVICE_ROLE_KEY=sua-chave-service-role

# Database Configuration  
DATABASE_URL=postgresql://postgres:senha@host:5432/postgres

# Security Configuration
MCP_API_KEY=sua-chave-api-segura
SERVER_PORT=8001
```

### 4. Iniciar Servidor

#### Desenvolvimento (Primeiro Plano)
```bash
# Ativar ambiente virtual
source venv/bin/activate

# Iniciar servidor
python -m supabase_mcp_server --host 0.0.0.0 --port 8001
```

#### Produção (Segundo Plano)
```bash
# Scripts daemon multiplataforma
chmod +x scripts/daemon/start_daemon.sh
./scripts/daemon/start_daemon.sh start

# Windows
scripts\daemon\start_daemon.bat start

# Docker (recomendado)
docker-compose -f docker-daemon.yml up -d

# Systemd (Linux)
sudo cp systemd/mcp-supabase.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable mcp-supabase
sudo systemctl start mcp-supabase
```

### 5. Configurações para IAs

#### Claude Desktop
```json
{
  "mcpServers": {
    "supabase": {
      "command": "curl",
      "args": ["-H", "Authorization: Bearer SUA_CHAVE_API", "http://seu-servidor:8001/mcp/tools"],
      "env": {
        "MCP_SERVER_URL": "http://seu-servidor:8001",
        "MCP_API_KEY": "sua-chave-api-segura"
      }
    }
  }
}
```

#### OpenAI GPTs
Use o arquivo `configs/openai-gpt.json` como schema OpenAPI.

#### Uso Genérico HTTP
```bash
# Listar ferramentas
curl -H "Authorization: Bearer SUA_CHAVE_API" http://seu-servidor:8001/mcp/tools

# Executar query
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer SUA_CHAVE_API" \
  -d '{"tool": "query_database", "parameters": {"query": "SELECT * FROM users LIMIT 5"}}' \
  http://seu-servidor:8001/mcp/execute
```

## 🛠️ Ferramentas Disponíveis

- **`query_database`**: Executar queries SQL no PostgreSQL
- **`get_schema`**: Obter informações do schema do banco
- **`crud_operations`**: Operações CRUD via API Supabase
- **`storage_operations`**: Gerenciar arquivos no Supabase Storage
- **`get_metrics`**: Obter métricas de performance

## 🔄 Execução em Background

### Scripts Daemon
Execução multiplataforma em segundo plano:
```bash
# Iniciar
./scripts/daemon/start_daemon.sh start

# Status
./scripts/daemon/start_daemon.sh status

# Parar
./scripts/daemon/start_daemon.sh stop
```

### Docker (Recomendado)
```bash
# Iniciar em background
docker-compose -f docker-daemon.yml up -d

# Ver logs
docker-compose -f docker-daemon.yml logs -f

# Parar
docker-compose -f docker-daemon.yml down
```

### Systemd (Linux)
```bash
# Configurar serviço
sudo cp systemd/mcp-supabase.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable mcp-supabase
sudo systemctl start mcp-supabase
```

## 🔧 Configuração Avançada

### Nginx Proxy
```nginx
server {
    listen 80;
    server_name mcp.seu-dominio.com;
    
    location / {
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### SSL com Let's Encrypt
```bash
sudo certbot --nginx -d mcp.seu-dominio.com
```

### Firewall
```bash
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

## 📊 Monitoramento

### Health Check
```bash
curl http://seu-servidor:8001/health
```

### Logs
```bash
# Logs do serviço
sudo journalctl -u supabase-mcp.service -f

# Status
systemctl status supabase-mcp.service
```

### Métricas
```bash
curl http://seu-servidor:9090/metrics
```

## 🔒 Segurança

- ✅ Autenticação via API Key
- ✅ Rate limiting configurável
- ✅ Validação de queries SQL
- ✅ Logs de auditoria
- ✅ Isolamento de rede

## 📁 Estrutura do Projeto

```
├── src/supabase_mcp_server/    # Código fonte
├── scripts/
│   ├── daemon/                 # Scripts para execução em background
│   │   ├── start_daemon.sh     # Linux/macOS daemon
│   │   ├── start_daemon.bat    # Windows daemon
│   │   └── setup_daemon.sh     # Configuração automática
│   └── ...                     # Outros scripts
├── systemd/                    # Arquivos de serviço systemd
├── configs/                    # Configurações para IAs
├── docker-daemon.yml           # Docker Compose para produção
├── install.sh                  # Script de instalação
├── DEPLOY_GUIDE.md            # Guia completo de deploy
└── README.md                  # Este arquivo
```

## 🚨 Troubleshooting

### Problemas Comuns
- **Porta em uso**: Alterar `SERVER_PORT` no .env
- **Conexão com banco**: Verificar `DATABASE_URL`
- **Permissões**: Verificar usuário do systemd

### Comandos Úteis
```bash
# Verificar status
systemctl status supabase-mcp.service

# Reiniciar serviço
sudo systemctl restart supabase-mcp.service

# Ver logs em tempo real
sudo journalctl -u supabase-mcp.service -f
```

## 📚 Documentação

- 📖 [Guia Completo de Deploy](DEPLOY_GUIDE.md)
- 🔧 [Configurações para IAs](configs/)
- 🐛 [Issues](https://github.com/MakeToMe/mcp_supabase_self-hosted/issues)

## 🎉 Pronto para Usar!

Após seguir os passos acima, seu servidor MCP estará rodando e pronto para conectar com qualquer IA compatível!

**Teste rápido:**
```bash
curl http://localhost:8001/health
```

Se retornar status 200, está funcionando! 🚀
# Guia de Deploy - Supabase MCP Server

Este guia fornece instruções completas para fazer deploy do servidor MCP Supabase em qualquer VPS.

## 1. Preparação do Repositório GitHub

### 1.1 Criar repositório no GitHub
1. Acesse [GitHub](https://github.com) e crie um novo repositório
2. Nome sugerido: `supabase-mcp-server`
3. Marque como público ou privado conforme necessário

### 1.2 Subir o projeto
```bash
# No diretório do projeto
git init
git add .
git commit -m "Initial commit: Supabase MCP Server"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/supabase-mcp-server.git
git push -u origin main
```

## 2. Deploy em VPS

### 2.1 Requisitos do Sistema
- Ubuntu 20.04+ ou CentOS 8+
- Python 3.11+
- Git
- Acesso root ou sudo

### 2.2 Script de Instalação Automática

Crie o arquivo `install.sh`:

```bash
#!/bin/bash
set -e

echo "🚀 Instalando Supabase MCP Server..."

# Atualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar dependências
sudo apt install -y python3.11 python3.11-pip python3.11-venv git curl nginx

# Instalar Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Adicionar Poetry ao PATH
export PATH="$HOME/.local/bin:$PATH"
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc

# Clonar repositório
git clone https://github.com/SEU_USUARIO/supabase-mcp-server.git
cd supabase-mcp-server

# Instalar dependências
poetry install

echo "✅ Instalação concluída!"
echo "📝 Configure o arquivo .env antes de iniciar o servidor"
```

### 2.3 Configuração do Ambiente

```bash
# Tornar o script executável
chmod +x install.sh

# Executar instalação
./install.sh
```

## 3. Configuração das Variáveis Supabase

### 3.1 Copiar arquivo de exemplo
```bash
cp .env.example .env
```

### 3.2 Editar configurações
```bash
nano .env
```

### 3.3 Template de configuração
```env
# Supabase Configuration
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_ANON_KEY=sua-chave-anonima-aqui
SUPABASE_SERVICE_ROLE_KEY=sua-chave-service-role-aqui

# Database Configuration
DATABASE_URL=postgresql://postgres:sua-senha@seu-host:5432/postgres
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
DATABASE_TIMEOUT=30

# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8001
LOG_LEVEL=INFO
ENABLE_CORS=true

# Security Configuration
MCP_API_KEY=sua-chave-api-segura-aqui
RATE_LIMIT_PER_MINUTE=100
ENABLE_QUERY_VALIDATION=true
MAX_QUERY_EXECUTION_TIME=30

# Redis Configuration (opcional)
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=

# Monitoring Configuration
ENABLE_METRICS=true
METRICS_PORT=9090
```

## 4. Iniciar o Servidor MCP

### 4.1 Modo Desenvolvimento
```bash
poetry run python -m supabase_mcp_server.main
```

### 4.2 Modo Produção com Systemd

Criar arquivo de serviço:
```bash
sudo nano /etc/systemd/system/supabase-mcp.service
```

Conteúdo do arquivo:
```ini
[Unit]
Description=Supabase MCP Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/supabase-mcp-server
Environment=PATH=/home/ubuntu/.local/bin
ExecStart=/home/ubuntu/.local/bin/poetry run python -m supabase_mcp_server.main
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Ativar e iniciar serviço:
```bash
sudo systemctl daemon-reload
sudo systemctl enable supabase-mcp.service
sudo systemctl start supabase-mcp.service
sudo systemctl status supabase-mcp.service
```

### 4.3 Configurar Nginx (Opcional)

```bash
sudo nano /etc/nginx/sites-available/supabase-mcp
```

```nginx
server {
    listen 80;
    server_name seu-dominio.com;

    location / {
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_cache_bypass $http_upgrade;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/supabase-mcp /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 5. Configuração JSON para IAs

### 5.1 Para Claude Desktop (MCP)
```json
{
  "mcpServers": {
    "supabase": {
      "command": "curl",
      "args": [
        "-X", "POST",
        "-H", "Content-Type: application/json",
        "-H", "Authorization: Bearer SUA_CHAVE_API",
        "http://seu-servidor:8001/mcp"
      ],
      "env": {
        "MCP_SERVER_URL": "http://seu-servidor:8001",
        "MCP_API_KEY": "sua-chave-api-segura-aqui"
      }
    }
  }
}
```

### 5.2 Para OpenAI GPTs (Webhook)
```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Supabase MCP Server",
    "version": "1.0.0"
  },
  "servers": [
    {
      "url": "http://seu-servidor:8001"
    }
  ],
  "paths": {
    "/mcp/tools": {
      "get": {
        "summary": "List available tools",
        "security": [{"ApiKeyAuth": []}]
      }
    }
  },
  "components": {
    "securitySchemes": {
      "ApiKeyAuth": {
        "type": "apiKey",
        "in": "header",
        "name": "Authorization"
      }
    }
  }
}
```

### 5.3 Para uso genérico via HTTP
```bash
# Listar ferramentas disponíveis
curl -H "Authorization: Bearer SUA_CHAVE_API" \
     http://seu-servidor:8001/mcp/tools

# Executar query no banco
curl -X POST \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer SUA_CHAVE_API" \
     -d '{"tool": "query_database", "parameters": {"query": "SELECT * FROM users LIMIT 5"}}' \
     http://seu-servidor:8001/mcp/execute
```

## 6. Verificação e Testes

### 6.1 Health Check
```bash
curl http://seu-servidor:8001/health
```

### 6.2 Verificar logs
```bash
sudo journalctl -u supabase-mcp.service -f
```

### 6.3 Testar ferramentas
```bash
curl -H "Authorization: Bearer SUA_CHAVE_API" \
     http://seu-servidor:8001/mcp/tools
```

## 7. Segurança e Manutenção

### 7.1 Firewall
```bash
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

### 7.2 SSL com Let's Encrypt
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d seu-dominio.com
```

### 7.3 Backup automático
```bash
# Adicionar ao crontab
0 2 * * * /usr/bin/pg_dump -h seu-host -U postgres -d postgres > /backup/supabase_$(date +\%Y\%m\%d).sql
```

## 8. Troubleshooting

### 8.1 Problemas comuns
- **Porta em uso**: Alterar `SERVER_PORT` no .env
- **Conexão com banco**: Verificar `DATABASE_URL`
- **Permissões**: Verificar usuário do serviço systemd

### 8.2 Logs úteis
```bash
# Logs do serviço
sudo journalctl -u supabase-mcp.service

# Logs do Nginx
sudo tail -f /var/log/nginx/error.log

# Status do sistema
systemctl status supabase-mcp.service
```

---

## Resumo dos Comandos

```bash
# 1. Clonar e instalar
git clone https://github.com/SEU_USUARIO/supabase-mcp-server.git
cd supabase-mcp-server
chmod +x install.sh && ./install.sh

# 2. Configurar
cp .env.example .env
nano .env

# 3. Iniciar
poetry run python -m supabase_mcp_server.main

# 4. Testar
curl http://localhost:8001/health
```

🎉 **Servidor MCP Supabase pronto para uso!**
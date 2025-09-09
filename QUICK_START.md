# 🚀 Quick Start - Supabase MCP Server

## Resumo dos 5 Passos

### 1. 📤 Subir para GitHub
```bash
# No diretório do projeto
git push origin main
```
✅ **Feito!** Projeto já está no GitHub

### 2. 🖥️ Deploy em VPS
```bash
# Conectar ao VPS
ssh user@seu-vps.com

# Instalar automaticamente
curl -sSL https://raw.githubusercontent.com/SEU_USUARIO/supabase-mcp-server/main/install.sh | bash
```

### 3. ⚙️ Configurar Variáveis Supabase
```bash
# Editar configurações
nano .env
```

**Preencher com suas credenciais:**
```env
SUPABASE_URL=https://studio.rardevops.com
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
DATABASE_URL=postgresql://postgres:Aha517_Rar-PGRS_U2a59w@studio.rardevops.com:4202/postgres
MCP_API_KEY=mcp-test-key-2024-rardevops
```

### 4. 🚀 Iniciar Servidor
```bash
# Desenvolvimento
./start_server.sh

# Produção (recomendado)
sudo cp supabase-mcp.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable supabase-mcp.service
sudo systemctl start supabase-mcp.service
```

### 5. 🤖 Configurar IA

#### Para Claude Desktop
```json
{
  "mcpServers": {
    "supabase": {
      "command": "node",
      "args": ["-e", "/* código de conexão */"],
      "env": {
        "MCP_SERVER_URL": "http://seu-vps:8001",
        "MCP_API_KEY": "mcp-test-key-2024-rardevops"
      }
    }
  }
}
```

#### Para qualquer IA via HTTP
```bash
# Testar conexão
curl -H "Authorization: Bearer mcp-test-key-2024-rardevops" \
     http://seu-vps:8001/mcp/tools

# Executar query
curl -X POST \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer mcp-test-key-2024-rardevops" \
     -d '{"tool": "query_database", "parameters": {"query": "SELECT * FROM users LIMIT 5"}}' \
     http://seu-vps:8001/mcp/execute
```

## ✅ Verificação Final

### Health Check
```bash
curl http://seu-vps:8001/health
```

**Resposta esperada:**
```json
{
  "status": "healthy",
  "service": "supabase-mcp-server",
  "version": "0.1.0"
}
```

### Listar Ferramentas
```bash
curl -H "Authorization: Bearer mcp-test-key-2024-rardevops" \
     http://seu-vps:8001/mcp/tools
```

**Ferramentas disponíveis:**
- ✅ `query_database` - Executar SQL
- ✅ `get_schema` - Schema do banco
- ✅ `crud_operations` - CRUD via Supabase
- ✅ `storage_operations` - Gerenciar arquivos
- ✅ `get_metrics` - Métricas do servidor

## 🔧 Comandos Úteis

```bash
# Ver status do serviço
systemctl status supabase-mcp.service

# Ver logs em tempo real
sudo journalctl -u supabase-mcp.service -f

# Reiniciar serviço
sudo systemctl restart supabase-mcp.service

# Parar serviço
sudo systemctl stop supabase-mcp.service
```

## 🎯 URLs Importantes

- **Health Check**: `http://seu-vps:8001/health`
- **Server Info**: `http://seu-vps:8001/info`
- **List Tools**: `http://seu-vps:8001/mcp/tools`
- **Execute Tool**: `http://seu-vps:8001/mcp/execute`
- **Metrics**: `http://seu-vps:9090/metrics`

## 🔒 Segurança

- ✅ API Key obrigatória
- ✅ Rate limiting ativo
- ✅ Validação de queries SQL
- ✅ Logs de auditoria
- ✅ CORS configurado

---

## 🎉 Pronto!

Seu servidor MCP Supabase está rodando e pronto para conectar com qualquer IA!

**Próximos passos:**
1. Configure SSL com Let's Encrypt
2. Configure domínio personalizado
3. Configure backup automático
4. Configure monitoramento avançado

📚 **Documentação completa**: [DEPLOY_GUIDE.md](DEPLOY_GUIDE.md)
# Configuração Kiro IDE - Supabase MCP Server

Este guia mostra como configurar o Kiro IDE para usar o servidor MCP Supabase self-hosted.

## 🚀 Configuração Rápida

### 1. Obter o IP da VM
```bash
# Na sua VM, execute:
curl ifconfig.me
# ou
hostname -I | awk '{print $1}'
```

### 2. Configurar o Kiro IDE

Copie o conteúdo do arquivo `kiro-ide-config.json` e substitua `SEU_IP_DA_VM` pelo IP real:

```json
{
  "mcpServers": {
    "supabase-self-hosted": {
      "command": "python3",
      "args": ["configs/mcp_client.py"],
      "env": {
        "MCP_SERVER_URL": "http://192.168.1.100:8001",
        "MCP_API_KEY": "mcp-test-key-2024-rardevops"
      }
    }
  }
}
```

### 3. Testar a Conexão

Execute o script de teste:
```bash
# Na sua máquina local ou VM
python3 test_mcp_connection.py http://SEU_IP:8001 mcp-test-key-2024-rardevops
```

## 📁 Arquivos de Configuração

- `kiro-ide-config.json` - Configuração principal (recomendada)
- `mcp_client.py` - Cliente Python para comunicação MCP
- `kiro-mcp-simple.json` - Versão simplificada inline
- `test_mcp_connection.py` - Script de teste

## 🔧 Configuração no Kiro IDE

### Método 1: Via Interface (Recomendado)
1. Abra o Kiro IDE
2. Vá em Settings → MCP Servers
3. Adicione um novo servidor:
   - **Nome**: `supabase-self-hosted`
   - **Command**: `python3`
   - **Args**: `["configs/mcp_client.py"]`
   - **Env Variables**:
     - `MCP_SERVER_URL`: `http://SEU_IP:8001`
     - `MCP_API_KEY`: `mcp-test-key-2024-rardevops`

### Método 2: Via Arquivo de Configuração
1. Localize o arquivo de configuração do Kiro IDE
2. Adicione a configuração do `kiro-ide-config.json`
3. Reinicie o Kiro IDE

## 🛠️ Ferramentas Disponíveis

Após a configuração, você terá acesso às seguintes ferramentas MCP:

### 🗄️ Database Operations
- `query_database` - Executar queries SQL
- `get_schema` - Obter schema do banco
- `get_table_info` - Informações de tabelas

### 🔧 Supabase Operations
- `crud_operations` - Operações CRUD via API
- `storage_operations` - Gerenciar arquivos
- `auth_operations` - Operações de autenticação

### 📊 Monitoring
- `get_metrics` - Métricas do servidor
- `get_server_info` - Informações do servidor
- `health_check` - Verificação de saúde

## 🔍 Troubleshooting

### Problema: Conexão recusada
```bash
# Verificar se o servidor está rodando
curl http://SEU_IP:8001/health

# Verificar logs do servidor
tail -f mcp_server.log
```

### Problema: Autenticação falhou
- Verifique se a `MCP_API_KEY` está correta
- Confirme que a chave no `.env` da VM é a mesma

### Problema: Timeout
- Verifique firewall da VM
- Teste conectividade: `telnet SEU_IP 8001`

## 📋 Comandos de Teste

```bash
# Teste básico de conectividade
curl -H "Authorization: Bearer mcp-test-key-2024-rardevops" \
     http://SEU_IP:8001/health

# Listar ferramentas MCP
curl -H "Authorization: Bearer mcp-test-key-2024-rardevops" \
     http://SEU_IP:8001/mcp/tools

# Executar query de teste
curl -X POST \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer mcp-test-key-2024-rardevops" \
     -d '{"tool": "query_database", "parameters": {"query": "SELECT version();"}}' \
     http://SEU_IP:8001/mcp/execute
```

## 🎯 Exemplo de Uso no Kiro IDE

Após configurar, você pode usar comandos como:

```
@supabase-self-hosted query_database {"query": "SELECT * FROM users LIMIT 5"}
@supabase-self-hosted get_schema {"table_name": "users"}
@supabase-self-hosted crud_operations {"operation": "select", "table": "posts", "limit": 10}
```

## 🔒 Segurança

- ✅ API Key obrigatória
- ✅ Rate limiting ativo
- ✅ Validação de queries
- ✅ Logs de auditoria

Para produção, considere:
- Usar HTTPS com certificado SSL
- Configurar firewall restritivo
- Rotacionar API keys regularmente
- Monitorar logs de acesso

## 📚 Recursos Adicionais

- [Documentação MCP](https://modelcontextprotocol.io/)
- [Kiro IDE MCP Guide](https://docs.kiro.ai/mcp)
- [Supabase Documentation](https://supabase.com/docs)

---

🎉 **Configuração concluída!** Seu Kiro IDE agora pode interagir diretamente com seu banco Supabase via MCP!
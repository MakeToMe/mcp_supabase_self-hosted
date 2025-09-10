# Scripts Daemon - Supabase MCP Server

Scripts para executar o servidor MCP Supabase em segundo plano (daemon) em diferentes sistemas operacionais.

## 📁 Arquivos

- `start_daemon.sh` - Script para Linux/macOS
- `start_daemon.bat` - Script para Windows
- `setup_daemon.sh` - Configuração automática de serviços do sistema

## 🚀 Uso Rápido

### Linux/macOS
```bash
# Tornar executável
chmod +x scripts/daemon/start_daemon.sh

# Iniciar servidor
./scripts/daemon/start_daemon.sh start

# Verificar status
./scripts/daemon/start_daemon.sh status

# Parar servidor
./scripts/daemon/start_daemon.sh stop

# Reiniciar servidor
./scripts/daemon/start_daemon.sh restart
```

### Windows
```cmd
# Iniciar servidor
scripts\daemon\start_daemon.bat start

# Verificar status
scripts\daemon\start_daemon.bat status

# Parar servidor
scripts\daemon\start_daemon.bat stop

# Reiniciar servidor
scripts\daemon\start_daemon.bat restart
```

## ⚙️ Configuração Automática de Serviços

Para configurar automaticamente como serviço do sistema:

```bash
# Linux/macOS
chmod +x scripts/daemon/setup_daemon.sh
./scripts/daemon/setup_daemon.sh
```

Este script detecta automaticamente o sistema operacional e configura:
- **Linux com systemd**: Cria serviço systemd
- **macOS**: Configura launchd
- **Outros sistemas**: Configura scripts daemon

## 📋 Funcionalidades

### Scripts Daemon
- ✅ Execução em segundo plano
- ✅ Gerenciamento de PID
- ✅ Logs separados (stdout/stderr)
- ✅ Verificação de status
- ✅ Reinicialização automática em caso de falha
- ✅ Compatibilidade multiplataforma

### Configuração de Serviços
- ✅ Detecção automática do SO
- ✅ Configuração de systemd (Linux)
- ✅ Configuração de launchd (macOS)
- ✅ Inicialização automática no boot
- ✅ Logs centralizados

## 📊 Arquivos Gerados

Quando executados, os scripts criam:
- `mcp_server.pid` - Arquivo com PID do processo
- `mcp_server.log` - Log de saída padrão
- `mcp_server_error.log` - Log de erros

## 🔧 Configuração Avançada

### Variáveis de Ambiente
Os scripts respeitam as configurações do arquivo `.env` na raiz do projeto.

### Personalização
Você pode modificar os scripts para:
- Alterar porta padrão
- Configurar logs personalizados
- Adicionar parâmetros específicos
- Configurar monitoramento

## 🚨 Troubleshooting

### Problemas Comuns

**Script não executa:**
```bash
# Linux/macOS - verificar permissões
chmod +x scripts/daemon/start_daemon.sh
```

**Servidor não inicia:**
```bash
# Verificar logs
cat mcp_server_error.log

# Verificar se a porta está em uso
netstat -tulpn | grep 8001
```

**PID file obsoleto:**
```bash
# Os scripts limpam automaticamente PIDs obsoletos
# Mas você pode remover manualmente se necessário
rm -f mcp_server.pid
```

### Comandos de Diagnóstico

```bash
# Verificar se o processo está rodando
ps aux | grep supabase_mcp_server

# Verificar porta
netstat -tulpn | grep 8001

# Testar conexão
curl http://localhost:8001/health
```

## 🎯 Integração com CI/CD

Os scripts podem ser integrados em pipelines de CI/CD:

```yaml
# Exemplo GitHub Actions
- name: Start MCP Server
  run: ./scripts/daemon/start_daemon.sh start

- name: Wait for server
  run: sleep 5

- name: Test server
  run: curl -f http://localhost:8001/health

- name: Stop server
  run: ./scripts/daemon/start_daemon.sh stop
```

## 📚 Referências

- [systemd Documentation](https://systemd.io/)
- [launchd Documentation](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html)
- [Windows Services](https://docs.microsoft.com/en-us/windows/win32/services/services)
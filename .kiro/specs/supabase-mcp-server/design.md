# Design Document

## Overview

O Supabase MCP Server é uma solução containerizada que atua como ponte entre editores de código com IA e instâncias Supabase self-hosted. Desenvolvido em Python usando FastAPI, o servidor implementa o protocolo MCP para fornecer acesso seguro e estruturado ao PostgreSQL e APIs do Supabase.

## Architecture

### Deployment Architecture

```mermaid
graph TB
    subgraph "VPS com Supabase"
        subgraph "Docker Network"
            SB[Supabase Stack]
            PG[(PostgreSQL)]
            MCP[MCP Server Container]
        end
        
        NGINX[Nginx Proxy]
        SSL[SSL Certificate]
    end
    
    subgraph "Cliente Local"
        IDE[Editor com IA]
        CONFIG[mcp.json]
    end
    
    IDE --> |HTTPS/WSS| NGINX
    NGINX --> |SSL Termination| MCP
    MCP --> |Direct Connection| PG
    MCP --> |REST API| SB
    
    style MCP fill:#e1f5fe
    style PG fill:#f3e5f5
    style SB fill:#e8f5e8
```

### Component Architecture

```mermaid
graph TB
    subgraph "MCP Server"
        API[FastAPI Application]
        MCP_HANDLER[MCP Protocol Handler]
        AUTH[Authentication Layer]
        RATE[Rate Limiter]
        
        subgraph "Services"
            DB_SVC[Database Service]
            SB_SVC[Supabase Service]
            STORAGE_SVC[Storage Service]
            SCHEMA_SVC[Schema Service]
        end
        
        subgraph "Utilities"
            LOGGER[Structured Logger]
            METRICS[Metrics Collector]
            HEALTH[Health Checker]
        end
    end
    
    API --> MCP_HANDLER
    MCP_HANDLER --> AUTH
    AUTH --> RATE
    RATE --> DB_SVC
    RATE --> SB_SVC
    RATE --> STORAGE_SVC
    RATE --> SCHEMA_SVC
    
    DB_SVC --> LOGGER
    SB_SVC --> METRICS
    STORAGE_SVC --> HEALTH
```

## Components and Interfaces

### 1. MCP Protocol Handler
**Responsabilidade:** Implementar o protocolo MCP padrão
**Interface:**
```python
class MCPHandler:
    async def handle_request(self, request: MCPRequest) -> MCPResponse
    async def list_tools(self) -> List[Tool]
    async def call_tool(self, name: str, arguments: Dict) -> ToolResult
```

**Ferramentas Expostas:**
- `query_database`: Executa queries SQL
- `get_schema`: Retorna estrutura do banco
- `crud_operations`: Operações CRUD via Supabase API
- `storage_operations`: Gerenciamento de arquivos
- `get_metrics`: Métricas de performance

### 2. Database Service
**Responsabilidade:** Gerenciar conexões e queries PostgreSQL
```python
class DatabaseService:
    async def execute_query(self, query: str, params: List) -> QueryResult
    async def get_schema_info(self) -> SchemaInfo
    async def validate_query(self, query: str) -> ValidationResult
```

### 3. Supabase Service
**Responsabilidade:** Integração com APIs do Supabase
```python
class SupabaseService:
    async def crud_operation(self, table: str, operation: str, data: Dict) -> Result
    async def call_edge_function(self, name: str, payload: Dict) -> Result
    async def manage_auth(self, operation: str, data: Dict) -> AuthResult
```

### 4. Security Layer
**Componentes:**
- JWT validation para requests
- Rate limiting por IP/usuário
- Query sanitization
- SQL injection prevention
- Audit logging

## Data Models

### Configuration Model
```python
@dataclass
class ServerConfig:
    supabase_url: str
    supabase_anon_key: str
    supabase_service_key: str
    database_url: str
    server_port: int = 8000
    log_level: str = "INFO"
    rate_limit_per_minute: int = 100
    enable_query_validation: bool = True
```

### MCP Tool Models
```python
@dataclass
class QueryTool:
    name: str = "query_database"
    description: str = "Execute SQL queries on PostgreSQL"
    parameters: Dict = field(default_factory=lambda: {
        "query": {"type": "string", "required": True},
        "params": {"type": "array", "required": False}
    })

@dataclass
class SchemaTool:
    name: str = "get_schema"
    description: str = "Get database schema information"
    parameters: Dict = field(default_factory=dict)
```

## Error Handling

### Error Categories
1. **Connection Errors:** Falhas de conexão com PostgreSQL/Supabase
2. **Authentication Errors:** Credenciais inválidas ou expiradas
3. **Query Errors:** SQL inválido ou violações de constraints
4. **Rate Limit Errors:** Excesso de requisições
5. **Validation Errors:** Dados de entrada inválidos

### Error Response Format
```python
@dataclass
class ErrorResponse:
    error_code: str
    message: str
    details: Optional[Dict] = None
    timestamp: datetime = field(default_factory=datetime.now)
    request_id: str = field(default_factory=lambda: str(uuid4()))
```

### Recovery Strategies
- **Connection Pool:** Reconexão automática com backoff exponencial
- **Circuit Breaker:** Proteção contra cascata de falhas
- **Graceful Degradation:** Funcionalidade limitada quando serviços estão indisponíveis
- **Health Checks:** Monitoramento contínuo de dependências

## Testing Strategy

### Unit Tests
- Testes para cada service isoladamente
- Mocks para dependências externas (PostgreSQL, Supabase API)
- Cobertura mínima de 90%

### Integration Tests
- Testes com banco PostgreSQL real (usando testcontainers)
- Validação de fluxos completos MCP
- Testes de autenticação e autorização

### Load Tests
- Simulação de múltiplas conexões simultâneas
- Teste de rate limiting
- Validação de performance sob carga

### Security Tests
- Testes de SQL injection
- Validação de sanitização de inputs
- Testes de bypass de autenticação

## Deployment Strategy

### Docker Setup
**Base Image:** `python:3.11-slim`
**Multi-stage build:**
1. Build stage: Instalar dependências e compilar
2. Runtime stage: Imagem mínima com apenas necessário

### Environment Configuration
```bash
# Supabase Configuration
SUPABASE_URL=https://your-instance.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-key

# Database Configuration
DATABASE_URL=postgresql://postgres:password@localhost:5432/postgres
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# Server Configuration
SERVER_PORT=8000
SERVER_HOST=0.0.0.0
LOG_LEVEL=INFO
ENABLE_CORS=true

# Security Configuration
RATE_LIMIT_PER_MINUTE=100
ENABLE_QUERY_VALIDATION=true
MAX_QUERY_EXECUTION_TIME=30

# SSL Configuration (for production)
SSL_CERT_PATH=/certs/cert.pem
SSL_KEY_PATH=/certs/key.pem
```

### Docker Compose Integration
O servidor será integrado ao stack Supabase existente através de docker-compose.override.yml:

```yaml
version: '3.8'
services:
  mcp-server:
    build: ./supabase-mcp-server
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@db:5432/postgres
      - SUPABASE_URL=http://kong:8000
    depends_on:
      - db
      - kong
    networks:
      - default
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### SSL/TLS Configuration
Baseado na configuração existente do Nginx, será criado um novo server block para o MCP:

```nginx
# Novo server block para MCP (adicionar ao nginx.conf)
server {
    server_name mcp.rardevops.com;  # Subdomínio dedicado para MCP
    client_max_body_size 100M;
    
    location / {
        proxy_pass http://170.205.37.204:8000;  # Porta do MCP server
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
    }
    
    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/studio.rardevops.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/studio.rardevops.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
}

server {
    if ($host = mcp.rardevops.com) {
        return 301 https://$host$request_uri;
    }
    listen 80;
    server_name mcp.rardevops.com;
    return 404;
}
```

**Configuração do Cliente MCP:**
```json
{
  "mcpServers": {
    "supabase": {
      "command": "uvx",
      "args": ["supabase-mcp-server-client@latest"],
      "env": {
        "MCP_SERVER_URL": "https://mcp.rardevops.com",
        "MCP_API_KEY": "your-generated-api-key"
      }
    }
  }
}
```

**Alternativa usando location no server existente:**
Se preferir não criar subdomínio, pode adicionar location no server do studio:

```nginx
# Adicionar dentro do server block existente de studio.rardevops.com
location /mcp {
    proxy_pass http://170.205.37.204:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
    
    # Remove /mcp prefix when forwarding
    rewrite ^/mcp/(.*) /$1 break;
}
```

## Performance Considerations

### Database Connection Management
- Pool de conexões configurável
- Connection timeout e retry logic
- Prepared statements para queries frequentes

### Caching Strategy
- Cache de schema information (TTL: 5 minutos)
- Cache de resultados para queries read-only
- Redis opcional para cache distribuído

### Monitoring and Observability
- Métricas Prometheus expostas em `/metrics`
- Logs estruturados em JSON
- Tracing distribuído com OpenTelemetry
- Dashboard Grafana para visualização
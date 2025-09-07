# Supabase MCP Server

A Model Context Protocol (MCP) server for Supabase self-hosted instances, enabling AI assistants to interact directly with your PostgreSQL database and Supabase services.

## Features

- 🔌 **MCP Protocol Support**: Full implementation of the Model Context Protocol
- 🐘 **PostgreSQL Integration**: Direct database access with connection pooling
- 🚀 **Supabase API Integration**: CRUD operations, Storage, and Edge Functions
- 🔒 **Security First**: JWT authentication, rate limiting, and query validation
- 📊 **Monitoring**: Structured logging, Prometheus metrics, and health checks
- 🐳 **Docker Ready**: Containerized deployment with Docker Compose
- 🔧 **Easy Setup**: Simple configuration with environment variables

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Supabase self-hosted instance
- Python 3.11+ (for development)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/supabase-mcp-server.git
   cd supabase-mcp-server
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your Supabase credentials
   ```

3. **Deploy with Docker Compose**
   ```bash
   # For standalone deployment
   docker-compose up -d
   
   # For integration with existing Supabase stack
   docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d
   ```

4. **Verify deployment**
   ```bash
   curl http://localhost:8000/health
   ```

### Configuration

Create a `.env` file with your Supabase configuration:

```env
# Supabase Configuration
SUPABASE_URL=https://your-instance.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here

# Database Configuration
DATABASE_URL=postgresql://postgres:your-password@localhost:5432/postgres

# Security Configuration
MCP_API_KEY=your-generated-api-key-here
```

### Client Configuration

Configure your AI editor to connect to the MCP server:

```json
{
  "mcpServers": {
    "supabase": {
      "command": "uvx",
      "args": ["supabase-mcp-server-client@latest"],
      "env": {
        "MCP_SERVER_URL": "https://mcp.yourdomain.com",
        "MCP_API_KEY": "your-generated-api-key"
      }
    }
  }
}
```

## Available MCP Tools

- **`query_database`**: Execute SQL queries on PostgreSQL
- **`get_schema`**: Retrieve database schema information
- **`crud_operations`**: Perform CRUD operations via Supabase API
- **`storage_operations`**: Manage files in Supabase Storage
- **`get_metrics`**: Retrieve server performance metrics

## Development

### Setup Development Environment

1. **Install Poetry**
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. **Install dependencies**
   ```bash
   poetry install
   ```

3. **Setup pre-commit hooks**
   ```bash
   poetry run pre-commit install
   ```

4. **Run tests**
   ```bash
   poetry run pytest
   ```

5. **Start development server**
   ```bash
   poetry run python -m supabase_mcp_server.main
   ```

### Project Structure

```
src/supabase_mcp_server/
├── __init__.py
├── main.py              # Application entry point
├── config.py            # Configuration management
├── core/                # Core utilities
│   ├── logging.py       # Structured logging
│   └── ...
├── mcp/                 # MCP protocol implementation
├── services/            # Business logic services
├── models/              # Data models
└── utils/               # Utility functions
```

## Deployment

### Nginx Configuration

Add this configuration to your existing Nginx setup:

```nginx
# For subdomain deployment
server {
    server_name mcp.yourdomain.com;
    client_max_body_size 100M;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
    }
    
    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
}
```

### SSL Certificate

The server integrates with your existing SSL setup. No additional certificate configuration needed.

## Security

- **Authentication**: API key-based authentication for MCP clients
- **Rate Limiting**: Configurable rate limits per IP address
- **Query Validation**: SQL injection prevention and dangerous query detection
- **Audit Logging**: Complete audit trail of all database operations
- **Network Security**: Runs in isolated Docker network

## Monitoring

- **Health Checks**: `/health` endpoint for load balancer integration
- **Metrics**: Prometheus metrics at `/metrics` endpoint
- **Structured Logs**: JSON-formatted logs with correlation IDs
- **Performance Tracking**: Query execution time and resource usage

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

- 📖 [Documentation](https://github.com/your-username/supabase-mcp-server/wiki)
- 🐛 [Issue Tracker](https://github.com/your-username/supabase-mcp-server/issues)
- 💬 [Discussions](https://github.com/your-username/supabase-mcp-server/discussions)
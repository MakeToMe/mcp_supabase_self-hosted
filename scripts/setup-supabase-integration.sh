#!/bin/bash

# Setup script for integrating Supabase MCP Server with existing Supabase installation

set -e

echo "🚀 Setting up Supabase MCP Server integration..."

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
NGINX_CONFIG_DIR="/etc/nginx/sites-available"
NGINX_ENABLED_DIR="/etc/nginx/sites-enabled"
BACKUP_DIR="/tmp/supabase-mcp-backup-$(date +%Y%m%d-%H%M%S)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root for nginx configuration
check_permissions() {
    if [[ $EUID -eq 0 ]]; then
        log_warning "Running as root. This is required for nginx configuration."
    else
        log_error "This script needs to be run with sudo for nginx configuration."
        echo "Usage: sudo $0"
        exit 1
    fi
}

# Backup existing configuration
backup_config() {
    log_info "Creating backup directory: $BACKUP_DIR"
    mkdir -p "$BACKUP_DIR"
    
    # Backup nginx configuration if it exists
    if [ -f "$NGINX_CONFIG_DIR/default" ]; then
        cp "$NGINX_CONFIG_DIR/default" "$BACKUP_DIR/nginx-default.backup"
        log_success "Backed up nginx default configuration"
    fi
    
    # Backup any existing MCP configuration
    if [ -f "$NGINX_CONFIG_DIR/supabase-mcp" ]; then
        cp "$NGINX_CONFIG_DIR/supabase-mcp" "$BACKUP_DIR/supabase-mcp.backup"
        log_success "Backed up existing MCP configuration"
    fi
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if nginx is installed
    if ! command -v nginx &> /dev/null; then
        log_error "Nginx is not installed. Please install Nginx first."
        exit 1
    fi
    
    # Check if .env file exists
    if [ ! -f "$PROJECT_DIR/.env" ]; then
        log_error ".env file not found. Please create it from .env.example"
        exit 1
    fi
    
    log_success "All prerequisites met"
}

# Detect existing Supabase installation
detect_supabase() {
    log_info "Detecting existing Supabase installation..."
    
    # Look for common Supabase directories
    SUPABASE_DIRS=(
        "/opt/supabase"
        "/home/supabase"
        "$HOME/supabase"
        "./supabase"
    )
    
    for dir in "${SUPABASE_DIRS[@]}"; do
        if [ -d "$dir" ] && [ -f "$dir/docker-compose.yml" ]; then
            SUPABASE_DIR="$dir"
            log_success "Found Supabase installation at: $SUPABASE_DIR"
            return 0
        fi
    done
    
    log_warning "Could not automatically detect Supabase installation"
    read -p "Please enter the path to your Supabase installation: " SUPABASE_DIR
    
    if [ ! -d "$SUPABASE_DIR" ] || [ ! -f "$SUPABASE_DIR/docker-compose.yml" ]; then
        log_error "Invalid Supabase directory: $SUPABASE_DIR"
        exit 1
    fi
    
    log_success "Using Supabase installation at: $SUPABASE_DIR"
}

# Configure nginx for MCP server
configure_nginx() {
    log_info "Configuring nginx for MCP server..."
    
    # Read domain from user or use default
    read -p "Enter your domain (e.g., studio.rardevops.com): " DOMAIN
    if [ -z "$DOMAIN" ]; then
        DOMAIN="localhost"
        log_warning "Using localhost as domain"
    fi
    
    # Ask for MCP subdomain or path
    echo "Choose MCP server access method:"
    echo "1) Subdomain (e.g., mcp.yourdomain.com)"
    echo "2) Path (e.g., yourdomain.com/mcp)"
    read -p "Enter choice (1 or 2): " ACCESS_METHOD
    
    if [ "$ACCESS_METHOD" = "1" ]; then
        # Subdomain configuration
        MCP_DOMAIN="mcp.$DOMAIN"
        create_subdomain_config
    else
        # Path configuration
        MCP_DOMAIN="$DOMAIN"
        create_path_config
    fi
}

create_subdomain_config() {
    log_info "Creating subdomain configuration for $MCP_DOMAIN"
    
    cat > "$NGINX_CONFIG_DIR/supabase-mcp" << EOF
# Supabase MCP Server Configuration
server {
    server_name $MCP_DOMAIN;
    client_max_body_size 100M;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_cache_bypass \$http_upgrade;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Health check endpoint
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
    
    # Metrics endpoint (restrict access)
    location /metrics {
        proxy_pass http://127.0.0.1:8000/metrics;
        allow 127.0.0.1;
        allow ::1;
        deny all;
    }
    
    listen 80;
}
EOF
    
    # Enable the site
    ln -sf "$NGINX_CONFIG_DIR/supabase-mcp" "$NGINX_ENABLED_DIR/supabase-mcp"
    
    log_success "Created subdomain configuration"
    log_info "You can now run 'sudo certbot --nginx -d $MCP_DOMAIN' to enable SSL"
}

create_path_config() {
    log_info "Creating path-based configuration for $MCP_DOMAIN/mcp"
    
    # Check if there's an existing server block for the domain
    EXISTING_CONFIG=""
    for config in "$NGINX_CONFIG_DIR"/*; do
        if [ -f "$config" ] && grep -q "server_name.*$DOMAIN" "$config"; then
            EXISTING_CONFIG="$config"
            break
        fi
    done
    
    if [ -n "$EXISTING_CONFIG" ]; then
        log_info "Found existing configuration: $EXISTING_CONFIG"
        log_info "Adding MCP location block to existing configuration"
        
        # Backup existing config
        cp "$EXISTING_CONFIG" "$BACKUP_DIR/$(basename "$EXISTING_CONFIG").backup"
        
        # Add MCP location block before the last closing brace
        sed -i '/^}$/i\
    # Supabase MCP Server\
    location /mcp {\
        proxy_pass http://127.0.0.1:8000;\
        proxy_set_header Host $host;\
        proxy_set_header X-Real-IP $remote_addr;\
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\
        proxy_set_header X-Forwarded-Proto $scheme;\
        proxy_http_version 1.1;\
        proxy_set_header Upgrade $http_upgrade;\
        proxy_set_header Connection '"'"'upgrade'"'"';\
        \
        # Remove /mcp prefix when forwarding\
        rewrite ^/mcp/(.*) /$1 break;\
        \
        # Timeouts\
        proxy_connect_timeout 60s;\
        proxy_send_timeout 60s;\
        proxy_read_timeout 60s;\
    }\
' "$EXISTING_CONFIG"
        
        log_success "Added MCP location to existing configuration"
    else
        log_warning "No existing configuration found for $DOMAIN"
        log_info "Creating new configuration file"
        create_subdomain_config
    fi
}

# Create docker-compose override for Supabase integration
create_docker_override() {
    log_info "Creating Docker Compose override for Supabase integration..."
    
    cat > "$PROJECT_DIR/docker-compose.supabase.yml" << EOF
# Docker Compose override for Supabase integration
version: '3.8'

services:
  mcp-server:
    build: .
    container_name: supabase-mcp-server
    ports:
      - "8000:8000"
    environment:
      # Connect to existing Supabase PostgreSQL
      - DATABASE_URL=postgresql://postgres:\${POSTGRES_PASSWORD}@\${POSTGRES_HOST:-db}:5432/postgres
      # Connect to existing Supabase Kong API Gateway
      - SUPABASE_URL=http://\${KONG_HOST:-kong}:8000
      # Use existing Redis if available
      - REDIS_URL=redis://\${REDIS_HOST:-redis}:6379
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - supabase_default
    depends_on:
      - db
      - kong

  # Optional: Redis service if not using Supabase's Redis
  redis:
    image: redis:7-alpine
    container_name: supabase-mcp-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    networks:
      - supabase_default
    command: redis-server --appendonly yes
    profiles:
      - standalone-redis

networks:
  supabase_default:
    external: true

volumes:
  redis_data:
EOF
    
    log_success "Created Docker Compose override file"
}

# Create systemd service for auto-start
create_systemd_service() {
    log_info "Creating systemd service for auto-start..."
    
    cat > "/etc/systemd/system/supabase-mcp-server.service" << EOF
[Unit]
Description=Supabase MCP Server
Requires=docker.service
After=docker.service
StartLimitIntervalSec=0

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$PROJECT_DIR
ExecStart=/usr/bin/docker-compose -f docker-compose.yml -f docker-compose.supabase.yml up -d
ExecStop=/usr/bin/docker-compose -f docker-compose.yml -f docker-compose.supabase.yml down
TimeoutStartSec=0
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable supabase-mcp-server.service
    
    log_success "Created and enabled systemd service"
}

# Create monitoring script
create_monitoring_script() {
    log_info "Creating monitoring script..."
    
    cat > "$PROJECT_DIR/scripts/monitor.sh" << 'EOF'
#!/bin/bash

# Monitoring script for Supabase MCP Server

CONTAINER_NAME="supabase-mcp-server"
HEALTH_URL="http://localhost:8000/health"
LOG_FILE="/var/log/supabase-mcp-monitor.log"

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

check_container() {
    if docker ps | grep -q "$CONTAINER_NAME"; then
        return 0
    else
        return 1
    fi
}

check_health() {
    if curl -f -s "$HEALTH_URL" > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

restart_service() {
    log_message "Restarting Supabase MCP Server..."
    systemctl restart supabase-mcp-server.service
    sleep 30
}

# Main monitoring loop
if ! check_container; then
    log_message "Container not running, starting service..."
    restart_service
elif ! check_health; then
    log_message "Health check failed, restarting service..."
    restart_service
else
    log_message "Service is healthy"
fi
EOF
    
    chmod +x "$PROJECT_DIR/scripts/monitor.sh"
    
    # Add to crontab for regular monitoring
    (crontab -l 2>/dev/null; echo "*/5 * * * * $PROJECT_DIR/scripts/monitor.sh") | crontab -
    
    log_success "Created monitoring script and added to crontab"
}

# Deploy the service
deploy_service() {
    log_info "Deploying Supabase MCP Server..."
    
    cd "$PROJECT_DIR"
    
    # Build the Docker image
    log_info "Building Docker image..."
    docker-compose build
    
    # Start the service
    log_info "Starting MCP server..."
    docker-compose -f docker-compose.yml -f docker-compose.supabase.yml up -d
    
    # Wait for service to be ready
    log_info "Waiting for service to be ready..."
    sleep 30
    
    # Check if service is healthy
    if curl -f -s "http://localhost:8000/health" > /dev/null; then
        log_success "Service is running and healthy!"
    else
        log_error "Service is not responding to health checks"
        log_info "Check logs with: docker-compose logs mcp-server"
        exit 1
    fi
}

# Test nginx configuration
test_nginx() {
    log_info "Testing nginx configuration..."
    
    if nginx -t; then
        log_success "Nginx configuration is valid"
        systemctl reload nginx
        log_success "Nginx reloaded"
    else
        log_error "Nginx configuration is invalid"
        log_info "Restoring backup configuration..."
        
        # Restore backup if available
        if [ -f "$BACKUP_DIR/nginx-default.backup" ]; then
            cp "$BACKUP_DIR/nginx-default.backup" "$NGINX_CONFIG_DIR/default"
            nginx -t && systemctl reload nginx
            log_success "Restored backup configuration"
        fi
        
        exit 1
    fi
}

# Main execution
main() {
    echo "🚀 Supabase MCP Server Integration Setup"
    echo "========================================"
    
    check_permissions
    backup_config
    check_prerequisites
    detect_supabase
    configure_nginx
    test_nginx
    create_docker_override
    create_systemd_service
    create_monitoring_script
    deploy_service
    
    echo ""
    log_success "Setup completed successfully!"
    echo ""
    echo "📋 Next steps:"
    echo "1. Configure SSL certificate: sudo certbot --nginx -d $MCP_DOMAIN"
    echo "2. Test the MCP server: curl http://localhost:8000/health"
    echo "3. Configure your MCP client with the server URL"
    echo "4. Monitor logs: docker-compose logs -f mcp-server"
    echo ""
    echo "📁 Backup created at: $BACKUP_DIR"
    echo "📊 Monitoring: Service will be monitored every 5 minutes via cron"
    echo "🔧 Service management: systemctl {start|stop|restart|status} supabase-mcp-server"
}

# Run main function
main "$@"
EOF
#!/bin/bash

# Diagnostic script for Supabase MCP Server

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

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

# Check system requirements
check_system() {
    echo "🖥️  System Information"
    echo "===================="
    
    log_info "Operating System: $(uname -a)"
    log_info "Docker version: $(docker --version 2>/dev/null || echo 'Not installed')"
    log_info "Docker Compose version: $(docker-compose --version 2>/dev/null || echo 'Not installed')"
    log_info "Available memory: $(free -h | grep '^Mem:' | awk '{print $7}' 2>/dev/null || echo 'Unknown')"
    log_info "Available disk space: $(df -h / | tail -1 | awk '{print $4}' 2>/dev/null || echo 'Unknown')"
    echo ""
}

# Check Docker status
check_docker() {
    echo "🐳 Docker Status"
    echo "==============="
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        return 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        return 1
    fi
    
    log_success "Docker is running"
    
    # Check containers
    log_info "MCP Server containers:"
    docker ps -a --filter "name=supabase-mcp" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    echo ""
}

# Check service status
check_service() {
    echo "🔧 Service Status"
    echo "================"
    
    # Check systemd service
    if systemctl list-unit-files | grep -q "supabase-mcp-server.service"; then
        STATUS=$(systemctl is-active supabase-mcp-server.service 2>/dev/null || echo "inactive")
        if [ "$STATUS" = "active" ]; then
            log_success "Systemd service is active"
        else
            log_warning "Systemd service is $STATUS"
        fi
    else
        log_info "No systemd service found"
    fi
    
    # Check Docker containers
    if docker ps | grep -q "supabase-mcp-server"; then
        log_success "MCP server container is running"
    else
        log_warning "MCP server container is not running"
    fi
    echo ""
}

# Check network connectivity
check_network() {
    echo "🌐 Network Connectivity"
    echo "======================"
    
    # Check if port 8000 is listening
    if netstat -tuln 2>/dev/null | grep -q ":8000 "; then
        log_success "Port 8000 is listening"
    else
        log_warning "Port 8000 is not listening"
    fi
    
    # Check health endpoint
    if curl -f -s "http://localhost:8000/health" > /dev/null 2>&1; then
        log_success "Health endpoint is responding"
        HEALTH_STATUS=$(curl -s "http://localhost:8000/health" | grep -o '"status":"[^"]*"' | cut -d'"' -f4 2>/dev/null || echo "unknown")
        log_info "Health status: $HEALTH_STATUS"
    else
        log_error "Health endpoint is not responding"
    fi
    echo ""
}

# Check configuration
check_config() {
    echo "⚙️  Configuration"
    echo "================"
    
    cd "$PROJECT_DIR"
    
    # Check .env file
    if [ -f ".env" ]; then
        log_success ".env file exists"
        
        # Check required variables (without showing values)
        REQUIRED_VARS=("SUPABASE_URL" "SUPABASE_ANON_KEY" "SUPABASE_SERVICE_ROLE_KEY" "DATABASE_URL" "MCP_API_KEY")
        
        for var in "${REQUIRED_VARS[@]}"; do
            if grep -q "^$var=" ".env"; then
                log_success "$var is configured"
            else
                log_error "$var is missing from .env"
            fi
        done
    else
        log_error ".env file not found"
    fi
    
    # Check docker-compose files
    if [ -f "docker-compose.yml" ]; then
        log_success "docker-compose.yml exists"
    else
        log_error "docker-compose.yml not found"
    fi
    
    if [ -f "docker-compose.supabase.yml" ]; then
        log_success "docker-compose.supabase.yml exists"
    else
        log_warning "docker-compose.supabase.yml not found (integration mode)"
    fi
    echo ""
}

# Check logs
check_logs() {
    echo "📋 Recent Logs"
    echo "=============="
    
    cd "$PROJECT_DIR"
    
    # Docker logs
    if docker ps | grep -q "supabase-mcp-server"; then
        log_info "Last 10 lines from container logs:"
        docker logs --tail 10 supabase-mcp-server 2>&1 | sed 's/^/  /'
    else
        log_warning "Container not running, no logs available"
    fi
    
    # System logs
    if systemctl list-unit-files | grep -q "supabase-mcp-server.service"; then
        log_info "Last 5 lines from systemd logs:"
        journalctl -u supabase-mcp-server.service --no-pager -n 5 2>/dev/null | sed 's/^/  /' || log_warning "No systemd logs available"
    fi
    echo ""
}

# Generate diagnostic report
generate_report() {
    REPORT_FILE="/tmp/supabase-mcp-diagnostic-$(date +%Y%m%d-%H%M%S).txt"
    
    echo "📊 Generating diagnostic report..."
    
    {
        echo "Supabase MCP Server Diagnostic Report"
        echo "Generated: $(date)"
        echo "======================================"
        echo ""
        
        echo "System Information:"
        uname -a
        echo ""
        
        echo "Docker Information:"
        docker --version 2>/dev/null || echo "Docker not installed"
        docker info 2>/dev/null || echo "Docker not running"
        echo ""
        
        echo "Container Status:"
        docker ps -a --filter "name=supabase-mcp" 2>/dev/null || echo "No containers found"
        echo ""
        
        echo "Service Status:"
        systemctl status supabase-mcp-server.service 2>/dev/null || echo "No systemd service"
        echo ""
        
        echo "Network Status:"
        netstat -tuln 2>/dev/null | grep ":8000" || echo "Port 8000 not listening"
        echo ""
        
        echo "Health Check:"
        curl -s "http://localhost:8000/health" 2>/dev/null || echo "Health endpoint not responding"
        echo ""
        
        echo "Recent Container Logs:"
        docker logs --tail 20 supabase-mcp-server 2>&1 || echo "No container logs"
        echo ""
        
        echo "Configuration Files:"
        ls -la "$PROJECT_DIR"/{.env,docker-compose*.yml} 2>/dev/null || echo "Configuration files not found"
        
    } > "$REPORT_FILE"
    
    log_success "Diagnostic report saved to: $REPORT_FILE"
}

# Main execution
main() {
    echo "🔍 Supabase MCP Server Diagnostics"
    echo "=================================="
    echo ""
    
    check_system
    check_docker
    check_service
    check_network
    check_config
    check_logs
    
    echo "🎯 Quick Fixes"
    echo "=============="
    echo "• Service not running: sudo systemctl start supabase-mcp-server"
    echo "• Container not running: docker-compose up -d"
    echo "• Health check failing: Check logs with 'docker-compose logs mcp-server'"
    echo "• Port not listening: Check if another service is using port 8000"
    echo "• Configuration issues: Verify .env file has all required variables"
    echo ""
    
    read -p "Generate detailed diagnostic report? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        generate_report
    fi
}

# Handle script arguments
case "${1:-}" in
    --report)
        generate_report
        ;;
    --help)
        echo "Usage: $0 [--report|--help]"
        echo ""
        echo "Options:"
        echo "  --report    Generate detailed diagnostic report only"
        echo "  --help      Show this help message"
        exit 0
        ;;
    "")
        main
        ;;
    *)
        log_error "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac
#!/bin/bash

# Update script for Supabase MCP Server

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="/tmp/supabase-mcp-update-$(date +%Y%m%d-%H%M%S)"

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

# Create backup
create_backup() {
    log_info "Creating backup..."
    mkdir -p "$BACKUP_DIR"
    
    # Backup current configuration
    if [ -f "$PROJECT_DIR/.env" ]; then
        cp "$PROJECT_DIR/.env" "$BACKUP_DIR/.env.backup"
    fi
    
    # Backup docker-compose files
    if [ -f "$PROJECT_DIR/docker-compose.supabase.yml" ]; then
        cp "$PROJECT_DIR/docker-compose.supabase.yml" "$BACKUP_DIR/docker-compose.supabase.yml.backup"
    fi
    
    # Export current container data if needed
    if docker ps | grep -q "supabase-mcp-server"; then
        log_info "Exporting container logs..."
        docker logs supabase-mcp-server > "$BACKUP_DIR/container.log" 2>&1 || true
    fi
    
    log_success "Backup created at: $BACKUP_DIR"
}

# Check for updates
check_updates() {
    log_info "Checking for updates..."
    
    cd "$PROJECT_DIR"
    
    # Check if we're in a git repository
    if [ -d ".git" ]; then
        # Fetch latest changes
        git fetch origin
        
        # Check if there are updates
        LOCAL=$(git rev-parse HEAD)
        REMOTE=$(git rev-parse origin/main 2>/dev/null || git rev-parse origin/master 2>/dev/null)
        
        if [ "$LOCAL" = "$REMOTE" ]; then
            log_info "Already up to date"
            return 1
        else
            log_info "Updates available"
            return 0
        fi
    else
        log_warning "Not a git repository. Manual update required."
        return 1
    fi
}

# Pull updates
pull_updates() {
    log_info "Pulling updates..."
    
    cd "$PROJECT_DIR"
    
    # Stash any local changes
    if ! git diff --quiet; then
        log_warning "Local changes detected, stashing..."
        git stash push -m "Auto-stash before update $(date)"
    fi
    
    # Pull latest changes
    git pull origin main 2>/dev/null || git pull origin master 2>/dev/null
    
    log_success "Updates pulled successfully"
}

# Update dependencies
update_dependencies() {
    log_info "Updating dependencies..."
    
    cd "$PROJECT_DIR"
    
    # Check if Poetry is available
    if command -v poetry &> /dev/null; then
        log_info "Updating Python dependencies with Poetry..."
        poetry install --only=main
    else
        log_warning "Poetry not found, skipping Python dependency update"
    fi
    
    # Update Docker base images
    log_info "Pulling latest Docker base images..."
    docker-compose pull || true
    
    log_success "Dependencies updated"
}

# Stop services
stop_services() {
    log_info "Stopping services..."
    
    cd "$PROJECT_DIR"
    
    # Stop via systemd if available
    if systemctl is-active --quiet supabase-mcp-server.service; then
        systemctl stop supabase-mcp-server.service
        log_success "Stopped systemd service"
    else
        # Stop via docker-compose
        if [ -f "docker-compose.supabase.yml" ]; then
            docker-compose -f docker-compose.yml -f docker-compose.supabase.yml down
        else
            docker-compose down
        fi
        log_success "Stopped Docker services"
    fi
}

# Rebuild and restart services
restart_services() {
    log_info "Rebuilding and restarting services..."
    
    cd "$PROJECT_DIR"
    
    # Rebuild Docker image
    log_info "Rebuilding Docker image..."
    docker-compose build --no-cache
    
    # Start services
    if systemctl is-enabled --quiet supabase-mcp-server.service 2>/dev/null; then
        systemctl start supabase-mcp-server.service
        log_success "Started systemd service"
    else
        if [ -f "docker-compose.supabase.yml" ]; then
            docker-compose -f docker-compose.yml -f docker-compose.supabase.yml up -d
        else
            docker-compose up -d
        fi
        log_success "Started Docker services"
    fi
}

# Verify update
verify_update() {
    log_info "Verifying update..."
    
    # Wait for service to be ready
    sleep 30
    
    # Check health endpoint
    if curl -f -s "http://localhost:8000/health" > /dev/null; then
        log_success "Service is healthy after update"
        
        # Get version info
        VERSION_INFO=$(curl -s "http://localhost:8000/info" 2>/dev/null || echo '{"version":"unknown"}')
        log_info "Service version: $(echo "$VERSION_INFO" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)"
        
        return 0
    else
        log_error "Service is not responding after update"
        return 1
    fi
}

# Rollback on failure
rollback() {
    log_error "Update failed, rolling back..."
    
    cd "$PROJECT_DIR"
    
    # Stop current services
    if systemctl is-active --quiet supabase-mcp-server.service; then
        systemctl stop supabase-mcp-server.service
    else
        docker-compose down || true
    fi
    
    # Restore configuration
    if [ -f "$BACKUP_DIR/.env.backup" ]; then
        cp "$BACKUP_DIR/.env.backup" "$PROJECT_DIR/.env"
        log_info "Restored .env configuration"
    fi
    
    if [ -f "$BACKUP_DIR/docker-compose.supabase.yml.backup" ]; then
        cp "$BACKUP_DIR/docker-compose.supabase.yml.backup" "$PROJECT_DIR/docker-compose.supabase.yml"
        log_info "Restored docker-compose configuration"
    fi
    
    # Rollback git changes if possible
    if [ -d ".git" ]; then
        git reset --hard HEAD~1 2>/dev/null || true
        log_info "Rolled back git changes"
    fi
    
    # Restart services
    restart_services
    
    if verify_update; then
        log_success "Rollback completed successfully"
    else
        log_error "Rollback failed. Manual intervention required."
        log_info "Backup available at: $BACKUP_DIR"
        exit 1
    fi
}

# Clean up old Docker images
cleanup() {
    log_info "Cleaning up old Docker images..."
    
    # Remove dangling images
    docker image prune -f
    
    # Remove old versions of our image (keep last 2)
    OLD_IMAGES=$(docker images --format "table {{.Repository}}:{{.Tag}}\t{{.ID}}" | grep "supabase-mcp-server" | tail -n +3 | awk '{print $2}')
    
    if [ -n "$OLD_IMAGES" ]; then
        echo "$OLD_IMAGES" | xargs docker rmi -f 2>/dev/null || true
        log_success "Cleaned up old images"
    fi
}

# Show update summary
show_summary() {
    echo ""
    log_success "Update completed successfully!"
    echo ""
    echo "📋 Update Summary:"
    echo "  • Backup created: $BACKUP_DIR"
    echo "  • Service status: $(systemctl is-active supabase-mcp-server.service 2>/dev/null || echo 'running via docker-compose')"
    echo "  • Health check: $(curl -s http://localhost:8000/health | grep -o '"status":"[^"]*"' | cut -d'"' -f4 2>/dev/null || echo 'unknown')"
    echo ""
    echo "🔧 Useful commands:"
    echo "  • Check logs: docker-compose logs -f mcp-server"
    echo "  • Check status: systemctl status supabase-mcp-server"
    echo "  • Manual restart: systemctl restart supabase-mcp-server"
    echo ""
}

# Main execution
main() {
    echo "🔄 Supabase MCP Server Update"
    echo "============================="
    
    # Check if running as root for systemd operations
    if [[ $EUID -eq 0 ]]; then
        log_warning "Running as root"
    fi
    
    create_backup
    
    if check_updates; then
        pull_updates
        update_dependencies
        stop_services
        restart_services
        
        if verify_update; then
            cleanup
            show_summary
        else
            rollback
            exit 1
        fi
    else
        log_info "No updates available"
    fi
}

# Handle script arguments
case "${1:-}" in
    --force)
        log_info "Forcing update..."
        create_backup
        pull_updates
        update_dependencies
        stop_services
        restart_services
        verify_update && cleanup && show_summary
        ;;
    --rollback)
        if [ -z "${2:-}" ]; then
            log_error "Please specify backup directory for rollback"
            exit 1
        fi
        BACKUP_DIR="$2"
        rollback
        ;;
    --help)
        echo "Usage: $0 [--force|--rollback <backup_dir>|--help]"
        echo ""
        echo "Options:"
        echo "  --force              Force update even if no changes detected"
        echo "  --rollback <dir>     Rollback to specified backup"
        echo "  --help               Show this help message"
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
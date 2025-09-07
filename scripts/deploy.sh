#!/bin/bash

# Deployment script for Supabase MCP Server

set -e

echo "🚀 Deploying Supabase MCP Server..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please create it from .env.example"
    exit 1
fi

# Build Docker image
echo "🐳 Building Docker image..."
docker build -t supabase-mcp-server .

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker-compose down || true

# Start services
echo "▶️ Starting services..."
if [ -f docker-compose.override.yml ]; then
    echo "Using Supabase integration mode..."
    docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d
else
    echo "Using standalone mode..."
    docker-compose up -d
fi

# Wait for health check
echo "🏥 Waiting for health check..."
sleep 10

# Check if server is healthy
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Deployment successful!"
    echo "Server is running at http://localhost:8000"
    echo "Health check: http://localhost:8000/health"
else
    echo "❌ Deployment failed - health check failed"
    echo "Check logs with: docker-compose logs"
    exit 1
fi
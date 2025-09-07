#!/bin/bash

# Installation script for Supabase MCP Server

set -e

echo "🚀 Installing Supabase MCP Server..."

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "📦 Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
fi

# Install dependencies
echo "📚 Installing dependencies..."
poetry install

# Setup pre-commit hooks
echo "🔧 Setting up pre-commit hooks..."
poetry run pre-commit install

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "⚙️ Creating .env file..."
    cp .env.example .env
    echo "Please edit .env with your Supabase configuration"
fi

echo "✅ Installation complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your Supabase credentials"
echo "2. Run 'make run' to start the development server"
echo "3. Or run 'make docker-run' to start with Docker"
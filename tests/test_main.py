"""Tests for the main application module."""

import pytest
from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "supabase-mcp-server"


def test_app_creation():
    """Test that the app can be created successfully."""
    from supabase_mcp_server.main import create_app
    
    app = create_app()
    assert app is not None
    assert app.title == "Supabase MCP Server"
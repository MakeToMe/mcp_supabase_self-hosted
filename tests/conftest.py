"""Pytest configuration and fixtures."""

import asyncio
import os
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from supabase_mcp_server.config import Settings, get_settings
from supabase_mcp_server.main import create_app


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings."""
    return Settings(
        supabase_url="http://localhost:54321",
        supabase_anon_key="test-anon-key",
        supabase_service_role_key="test-service-key",
        database_url="postgresql://postgres:postgres@localhost:54322/postgres",
        mcp_api_key="test-api-key",
        log_level="DEBUG",
        debug=True,
    )


@pytest.fixture
def override_settings(test_settings: Settings, monkeypatch):
    """Override settings for testing."""
    monkeypatch.setattr("supabase_mcp_server.config.get_settings", lambda: test_settings)
    return test_settings


@pytest.fixture
def client(override_settings) -> TestClient:
    """Create a test client."""
    app = create_app()
    return TestClient(app)


@pytest_asyncio.fixture
async def async_client(override_settings) -> AsyncGenerator[TestClient, None]:
    """Create an async test client."""
    app = create_app()
    async with TestClient(app) as client:
        yield client
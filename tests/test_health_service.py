"""Tests for health check service."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from supabase_mcp_server.services.health import (
    ComponentHealth,
    HealthCheckResult,
    HealthCheckService,
    HealthStatus,
)


class TestHealthStatus:
    """Test HealthStatus enum."""
    
    def test_health_status_values(self):
        """Test health status enum values."""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.UNKNOWN.value == "unknown"


class TestHealthCheckResult:
    """Test HealthCheckResult class."""
    
    def test_health_check_result_creation(self):
        """Test HealthCheckResult creation."""
        now = datetime.now()
        result = HealthCheckResult(
            name="test_component",
            status=HealthStatus.HEALTHY,
            message="Component is healthy",
            duration_ms=150.5,
            timestamp=now,
            details={"key": "value"}
        )
        
        assert result.name == "test_component"
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "Component is healthy"
        assert result.duration_ms == 150.5
        assert result.timestamp == now
        assert result.details == {"key": "value"}
        assert result.error is None


class TestComponentHealth:
    """Test ComponentHealth class."""
    
    def test_component_health_creation(self):
        """Test ComponentHealth creation."""
        component = ComponentHealth(
            name="database",
            status=HealthStatus.HEALTHY
        )
        
        assert component.name == "database"
        assert component.status == HealthStatus.HEALTHY
        assert component.last_check is None
        assert component.consecutive_failures == 0
        assert component.total_checks == 0


class TestHealthCheckService:
    """Test HealthCheckService class."""
    
    @pytest.fixture
    def health_service(self):
        """Create health check service instance."""
        return HealthCheckService()
    
    def test_health_service_creation(self, health_service):
        """Test health service creation."""
        assert health_service.components == {}
        assert health_service.check_history == []
        assert health_service.max_history == 1000
        assert health_service.timeout_seconds == 30
    
    async def test_check_database_health_not_initialized(self, health_service):
        """Test database health check when not initialized."""
        with patch('supabase_mcp_server.services.health.database_service') as mock_db:
            mock_db._pool = None
            
            result = await health_service._check_database_health()
            
            assert result.name == "database"
            assert result.status == HealthStatus.UNHEALTHY
            assert "not initialized" in result.message.lower()
            assert result.error == "Database pool not initialized"
    
    async def test_check_database_health_healthy(self, health_service):
        """Test database health check when healthy."""
        with patch('supabase_mcp_server.services.health.database_service') as mock_db:
            mock_db._pool = MagicMock()
            mock_db.health_check = AsyncMock(return_value=True)
            mock_db.get_connection_info = AsyncMock(return_value={
                "pool_size": 5,
                "pool_max_size": 10,
                "version": "PostgreSQL 14.0"
            })
            
            result = await health_service._check_database_health()
            
            assert result.name == "database"
            assert result.status == HealthStatus.HEALTHY
            assert "healthy" in result.message.lower()
            assert result.details["pool_size"] == 5
            assert result.error is None
    
    async def test_check_database_health_unhealthy(self, health_service):
        """Test database health check when unhealthy."""
        with patch('supabase_mcp_server.services.health.database_service') as mock_db:
            mock_db._pool = MagicMock()
            mock_db.health_check = AsyncMock(return_value=False)
            
            result = await health_service._check_database_health()
            
            assert result.name == "database"
            assert result.status == HealthStatus.UNHEALTHY
            assert "failed" in result.message.lower()
            assert result.error == "Health check query failed"
    
    async def test_check_database_health_timeout(self, health_service):
        """Test database health check timeout."""
        with patch('supabase_mcp_server.services.health.database_service') as mock_db:
            mock_db._pool = MagicMock()
            mock_db.health_check = AsyncMock(side_effect=asyncio.TimeoutError())
            
            result = await health_service._check_database_health()
            
            assert result.name == "database"
            assert result.status == HealthStatus.UNHEALTHY
            assert "timed out" in result.message.lower()
            assert "Timeout after" in result.error
    
    async def test_check_supabase_api_health_not_initialized(self, health_service):
        """Test Supabase API health check when not initialized."""
        with patch('supabase_mcp_server.services.health.supabase_api_service') as mock_api:
            mock_api.is_initialized.return_value = False
            
            result = await health_service._check_supabase_api_health()
            
            assert result.name == "supabase_api"
            assert result.status == HealthStatus.DEGRADED
            assert "not initialized" in result.message.lower()
            assert result.details["initialized"] is False
    
    async def test_check_supabase_api_health_healthy(self, health_service):
        """Test Supabase API health check when healthy."""
        with patch('supabase_mcp_server.services.health.supabase_api_service') as mock_api:
            mock_api.is_initialized.return_value = True
            mock_api.get_client.return_value = MagicMock()
            
            result = await health_service._check_supabase_api_health()
            
            assert result.name == "supabase_api"
            assert result.status == HealthStatus.HEALTHY
            assert "healthy" in result.message.lower()
            assert result.details["initialized"] is True
            assert result.details["client_available"] is True
    
    async def test_check_server_health_with_psutil(self, health_service):
        """Test server health check with psutil available."""
        with patch('supabase_mcp_server.services.health.psutil') as mock_psutil:
            mock_psutil.cpu_percent.return_value = 25.0
            mock_memory = MagicMock()
            mock_memory.percent = 60.0
            mock_memory.available = 4 * 1024**3  # 4GB
            mock_psutil.virtual_memory.return_value = mock_memory
            
            result = await health_service._check_server_health()
            
            assert result.name == "server"
            assert result.status == HealthStatus.HEALTHY
            assert "healthy" in result.message.lower()
            assert result.details["cpu_percent"] == 25.0
            assert result.details["memory_percent"] == 60.0
    
    async def test_check_server_health_degraded(self, health_service):
        """Test server health check when degraded."""
        with patch('supabase_mcp_server.services.health.psutil') as mock_psutil:
            mock_psutil.cpu_percent.return_value = 75.0  # High CPU
            mock_memory = MagicMock()
            mock_memory.percent = 85.0  # High memory
            mock_memory.available = 1 * 1024**3  # 1GB
            mock_psutil.virtual_memory.return_value = mock_memory
            
            result = await health_service._check_server_health()
            
            assert result.name == "server"
            assert result.status == HealthStatus.DEGRADED
            assert "elevated" in result.message.lower()
    
    async def test_check_server_health_unhealthy(self, health_service):
        """Test server health check when unhealthy."""
        with patch('supabase_mcp_server.services.health.psutil') as mock_psutil:
            mock_psutil.cpu_percent.return_value = 95.0  # Critical CPU
            mock_memory = MagicMock()
            mock_memory.percent = 95.0  # Critical memory
            mock_memory.available = 0.1 * 1024**3  # 100MB
            mock_psutil.virtual_memory.return_value = mock_memory
            
            result = await health_service._check_server_health()
            
            assert result.name == "server"
            assert result.status == HealthStatus.UNHEALTHY
            assert "critically high" in result.message.lower()
    
    async def test_check_server_health_no_psutil(self, health_service):
        """Test server health check without psutil."""
        with patch('supabase_mcp_server.services.health.psutil', side_effect=ImportError()):
            result = await health_service._check_server_health()
            
            assert result.name == "server"
            assert result.status == HealthStatus.HEALTHY
            assert "basic check" in result.message.lower()
            assert result.details["psutil_available"] is False
    
    async def test_check_memory_health_normal(self, health_service):
        """Test memory health check with normal usage."""
        with patch('supabase_mcp_server.services.health.psutil') as mock_psutil:
            mock_memory = MagicMock()
            mock_memory.percent = 70.0
            mock_memory.total = 8 * 1024**3  # 8GB
            mock_memory.available = 2 * 1024**3  # 2GB
            mock_psutil.virtual_memory.return_value = mock_memory
            
            mock_swap = MagicMock()
            mock_swap.percent = 10.0
            mock_swap.total = 2 * 1024**3  # 2GB
            mock_psutil.swap_memory.return_value = mock_swap
            
            result = await health_service._check_memory_health()
            
            assert result.name == "memory"
            assert result.status == HealthStatus.HEALTHY
            assert "normal" in result.message.lower()
            assert result.details["memory_percent"] == 70.0
    
    async def test_check_disk_health_normal(self, health_service):
        """Test disk health check with normal usage."""
        with patch('supabase_mcp_server.services.health.psutil') as mock_psutil:
            mock_disk = MagicMock()
            mock_disk.total = 100 * 1024**3  # 100GB
            mock_disk.used = 50 * 1024**3   # 50GB
            mock_disk.free = 50 * 1024**3   # 50GB
            mock_psutil.disk_usage.return_value = mock_disk
            
            result = await health_service._check_disk_health()
            
            assert result.name == "disk"
            assert result.status == HealthStatus.HEALTHY
            assert "normal" in result.message.lower()
            assert result.details["disk_percent"] == 50.0
    
    def test_update_component_health_success(self, health_service):
        """Test updating component health with successful result."""
        result = HealthCheckResult(
            name="test_component",
            status=HealthStatus.HEALTHY,
            message="Success",
            duration_ms=100.0,
            timestamp=datetime.now()
        )
        
        health_service._update_component_health("test_component", result)
        
        component = health_service.components["test_component"]
        assert component.status == HealthStatus.HEALTHY
        assert component.consecutive_failures == 0
        assert component.total_checks == 1
        assert component.total_failures == 0
        assert component.last_success is not None
    
    def test_update_component_health_failure(self, health_service):
        """Test updating component health with failed result."""
        result = HealthCheckResult(
            name="test_component",
            status=HealthStatus.UNHEALTHY,
            message="Failed",
            duration_ms=100.0,
            timestamp=datetime.now()
        )
        
        health_service._update_component_health("test_component", result)
        
        component = health_service.components["test_component"]
        assert component.consecutive_failures == 1
        assert component.total_failures == 1
        assert component.status == HealthStatus.DEGRADED  # First failure = degraded
    
    def test_update_component_health_multiple_failures(self, health_service):
        """Test updating component health with multiple failures."""
        result = HealthCheckResult(
            name="test_component",
            status=HealthStatus.UNHEALTHY,
            message="Failed",
            duration_ms=100.0,
            timestamp=datetime.now()
        )
        
        # Simulate multiple failures
        for _ in range(3):
            health_service._update_component_health("test_component", result)
        
        component = health_service.components["test_component"]
        assert component.consecutive_failures == 3
        assert component.status == HealthStatus.UNHEALTHY  # 3+ failures = unhealthy
    
    def test_get_overall_health_no_components(self, health_service):
        """Test getting overall health with no components."""
        health = health_service.get_overall_health()
        
        assert health["status"] == "unknown"
        assert "No health checks" in health["message"]
    
    def test_get_overall_health_all_healthy(self, health_service):
        """Test getting overall health with all components healthy."""
        health_service.components["comp1"] = ComponentHealth("comp1", HealthStatus.HEALTHY)
        health_service.components["comp2"] = ComponentHealth("comp2", HealthStatus.HEALTHY)
        
        health = health_service.get_overall_health()
        
        assert health["status"] == "healthy"
        assert "All components are healthy" in health["message"]
        assert len(health["components"]) == 2
    
    def test_get_overall_health_with_unhealthy(self, health_service):
        """Test getting overall health with unhealthy component."""
        health_service.components["comp1"] = ComponentHealth("comp1", HealthStatus.HEALTHY)
        health_service.components["comp2"] = ComponentHealth("comp2", HealthStatus.UNHEALTHY)
        
        health = health_service.get_overall_health()
        
        assert health["status"] == "unhealthy"
        assert "One or more components are unhealthy" in health["message"]
    
    def test_get_component_health_existing(self, health_service):
        """Test getting health for existing component."""
        component = ComponentHealth("test_comp", HealthStatus.HEALTHY)
        component.total_checks = 10
        component.total_failures = 2
        health_service.components["test_comp"] = component
        
        health = health_service.get_component_health("test_comp")
        
        assert health is not None
        assert health["name"] == "test_comp"
        assert health["status"] == "healthy"
        assert health["success_rate"] == 80.0  # (10-2)/10 * 100
    
    def test_get_component_health_nonexistent(self, health_service):
        """Test getting health for non-existent component."""
        health = health_service.get_component_health("nonexistent")
        
        assert health is None
    
    def test_get_recent_checks(self, health_service):
        """Test getting recent health checks."""
        # Add some check results
        for i in range(5):
            result = HealthCheckResult(
                name=f"comp_{i}",
                status=HealthStatus.HEALTHY,
                message=f"Check {i}",
                duration_ms=100.0,
                timestamp=datetime.now()
            )
            health_service.check_history.append(result)
        
        recent = health_service.get_recent_checks(limit=3)
        
        assert len(recent) == 3
        assert recent[0]["name"] == "comp_2"  # Last 3 checks
        assert recent[2]["name"] == "comp_4"
    
    async def test_check_component_existing(self, health_service):
        """Test checking specific existing component."""
        with patch.object(health_service, '_check_database_health') as mock_check:
            mock_result = HealthCheckResult(
                name="database",
                status=HealthStatus.HEALTHY,
                message="Healthy",
                duration_ms=100.0,
                timestamp=datetime.now()
            )
            mock_check.return_value = mock_result
            
            result = await health_service.check_component("database")
            
            assert result is not None
            assert result.name == "database"
            assert result.status == HealthStatus.HEALTHY
            mock_check.assert_called_once()
    
    async def test_check_component_nonexistent(self, health_service):
        """Test checking non-existent component."""
        result = await health_service.check_component("nonexistent")
        
        assert result is None
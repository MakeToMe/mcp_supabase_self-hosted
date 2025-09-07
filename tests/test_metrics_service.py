"""Tests for metrics service."""

import time
from unittest.mock import patch

import pytest

from supabase_mcp_server.services.metrics import (
    MetricsService,
    timed_operation,
)


class TestMetricsService:
    """Test MetricsService class."""
    
    @pytest.fixture
    def metrics_service(self, override_settings):
        """Create metrics service instance."""
        return MetricsService()
    
    def test_metrics_service_creation(self, metrics_service):
        """Test metrics service creation."""
        assert metrics_service.settings is not None
        assert metrics_service.registry is not None
        assert metrics_service._start_time > 0
    
    def test_record_http_request(self, metrics_service):
        """Test recording HTTP request metrics."""
        metrics_service.record_http_request("GET", "/test", 200, 0.5)
        
        # Check that metrics were recorded
        metrics_output = metrics_service.get_metrics()
        assert "supabase_mcp_server_http_requests_total" in metrics_output
        assert "supabase_mcp_server_http_request_duration_seconds" in metrics_output
    
    def test_record_mcp_request(self, metrics_service):
        """Test recording MCP request metrics."""
        metrics_service.record_mcp_request("initialize", "success", 0.1)
        
        metrics_output = metrics_service.get_metrics()
        assert "supabase_mcp_server_mcp_requests_total" in metrics_output
        assert "supabase_mcp_server_mcp_request_duration_seconds" in metrics_output
    
    def test_record_tool_call(self, metrics_service):
        """Test recording tool call metrics."""
        metrics_service.record_tool_call("query_database", "success", 1.5)
        
        metrics_output = metrics_service.get_metrics()
        assert "supabase_mcp_server_tool_calls_total" in metrics_output
        assert "supabase_mcp_server_tool_duration_seconds" in metrics_output
    
    def test_record_database_query(self, metrics_service):
        """Test recording database query metrics."""
        metrics_service.record_database_query("success", 0.8)
        
        metrics_output = metrics_service.get_metrics()
        assert "supabase_mcp_server_database_queries_total" in metrics_output
        assert "supabase_mcp_server_database_query_duration_seconds" in metrics_output
    
    def test_record_database_connection_error(self, metrics_service):
        """Test recording database connection error."""
        metrics_service.record_database_connection_error()
        
        metrics_output = metrics_service.get_metrics()
        assert "supabase_mcp_server_database_connection_errors_total" in metrics_output
    
    def test_update_database_connections(self, metrics_service):
        """Test updating database connection metrics."""
        metrics_service.update_database_connections(5, 10)
        
        metrics_output = metrics_service.get_metrics()
        assert "supabase_mcp_server_database_connections_active 5.0" in metrics_output
        assert "supabase_mcp_server_database_connections_total 10.0" in metrics_output
    
    def test_record_supabase_api_request(self, metrics_service):
        """Test recording Supabase API request metrics."""
        metrics_service.record_supabase_api_request("select", "success", 0.3)
        
        metrics_output = metrics_service.get_metrics()
        assert "supabase_mcp_server_supabase_api_requests_total" in metrics_output
        assert "supabase_mcp_server_supabase_api_duration_seconds" in metrics_output
    
    def test_record_storage_operation(self, metrics_service):
        """Test recording storage operation metrics."""
        metrics_service.record_storage_operation("upload", "success", 1024)
        
        metrics_output = metrics_service.get_metrics()
        assert "supabase_mcp_server_storage_operations_total" in metrics_output
        assert "supabase_mcp_server_storage_bytes_transferred_total" in metrics_output
    
    def test_record_security_event(self, metrics_service):
        """Test recording security event metrics."""
        metrics_service.record_security_event("rate_limit_exceeded", "medium")
        
        metrics_output = metrics_service.get_metrics()
        assert "supabase_mcp_server_security_events_total" in metrics_output
    
    def test_record_rate_limit_violation(self, metrics_service):
        """Test recording rate limit violation."""
        metrics_service.record_rate_limit_violation()
        
        metrics_output = metrics_service.get_metrics()
        assert "supabase_mcp_server_rate_limit_violations_total" in metrics_output
    
    def test_update_blocked_ips(self, metrics_service):
        """Test updating blocked IPs count."""
        metrics_service.update_blocked_ips(3)
        
        metrics_output = metrics_service.get_metrics()
        assert "supabase_mcp_server_blocked_ips 3.0" in metrics_output
    
    def test_record_auth_attempt(self, metrics_service):
        """Test recording authentication attempt."""
        metrics_service.record_auth_attempt("api_key", "success")
        
        metrics_output = metrics_service.get_metrics()
        assert "supabase_mcp_server_auth_attempts_total" in metrics_output
    
    def test_record_error(self, metrics_service):
        """Test recording error metrics."""
        metrics_service.record_error("ValueError", "database")
        
        metrics_output = metrics_service.get_metrics()
        assert "supabase_mcp_server_errors_total" in metrics_output
    
    def test_update_active_connections(self, metrics_service):
        """Test updating active connections."""
        metrics_service.update_active_connections(7)
        
        metrics_output = metrics_service.get_metrics()
        assert "supabase_mcp_server_active_connections 7.0" in metrics_output
    
    def test_update_server_uptime(self, metrics_service):
        """Test updating server uptime."""
        # Mock start time to test uptime calculation
        with patch.object(metrics_service, '_start_time', time.time() - 100):
            metrics_service.update_server_uptime()
            
            metrics_output = metrics_service.get_metrics()
            assert "supabase_mcp_server_uptime_seconds" in metrics_output
    
    def test_get_metrics_format(self, metrics_service):
        """Test metrics output format."""
        # Record some metrics
        metrics_service.record_http_request("GET", "/test", 200, 0.1)
        metrics_service.update_active_connections(1)
        
        metrics_output = metrics_service.get_metrics()
        
        # Check Prometheus format
        assert isinstance(metrics_output, str)
        assert "# HELP" in metrics_output
        assert "# TYPE" in metrics_output
        assert "supabase_mcp_server_info" in metrics_output
    
    def test_get_content_type(self, metrics_service):
        """Test metrics content type."""
        content_type = metrics_service.get_content_type()
        assert "text/plain" in content_type
    
    def test_server_info_initialization(self, metrics_service):
        """Test server info initialization."""
        metrics_output = metrics_service.get_metrics()
        
        assert 'supabase_mcp_server_info{name="supabase-mcp-server"' in metrics_output
        assert 'version="0.1.0"' in metrics_output
        assert 'protocol_version="2024-11-05"' in metrics_output


class TestTimedOperationDecorator:
    """Test timed_operation decorator."""
    
    @pytest.fixture
    def metrics_service(self, override_settings):
        """Create metrics service instance."""
        return MetricsService()
    
    def test_timed_operation_sync_success(self, metrics_service):
        """Test timed operation decorator with sync function success."""
        
        @timed_operation("http_request_duration")
        def test_function():
            time.sleep(0.01)  # Small delay
            return "success"
        
        result = test_function()
        
        assert result == "success"
        # Note: The decorator would record metrics if the metric existed
    
    def test_timed_operation_sync_error(self, metrics_service):
        """Test timed operation decorator with sync function error."""
        
        @timed_operation("http_request_duration")
        def test_function():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError, match="Test error"):
            test_function()
        
        # Check that error was recorded
        metrics_output = metrics_service.get_metrics()
        assert "supabase_mcp_server_errors_total" in metrics_output
    
    async def test_timed_operation_async_success(self, metrics_service):
        """Test timed operation decorator with async function success."""
        
        @timed_operation("http_request_duration")
        async def test_function():
            await asyncio.sleep(0.01)  # Small delay
            return "success"
        
        result = await test_function()
        
        assert result == "success"
    
    async def test_timed_operation_async_error(self, metrics_service):
        """Test timed operation decorator with async function error."""
        
        @timed_operation("http_request_duration")
        async def test_function():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError, match="Test error"):
            await test_function()
        
        # Check that error was recorded
        metrics_output = metrics_service.get_metrics()
        assert "supabase_mcp_server_errors_total" in metrics_output
    
    def test_timed_operation_with_labels(self, metrics_service):
        """Test timed operation decorator with labels."""
        
        @timed_operation("http_request_duration", labels={"method": "GET"})
        def test_function():
            return "success"
        
        result = test_function()
        
        assert result == "success"
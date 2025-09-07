"""Metrics collection service using Prometheus."""

import time
from typing import Dict, Optional
from functools import wraps

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST
)

from supabase_mcp_server.config import get_settings
from supabase_mcp_server.core.logging import get_logger

logger = get_logger(__name__)


class MetricsService:
    """Service for collecting and exposing Prometheus metrics."""
    
    def __init__(self):
        """Initialize metrics service."""
        self.settings = get_settings()
        self.registry = CollectorRegistry()
        
        # Server metrics
        self.server_info = Info(
            'supabase_mcp_server_info',
            'Information about the Supabase MCP Server',
            registry=self.registry
        )
        
        self.server_uptime = Gauge(
            'supabase_mcp_server_uptime_seconds',
            'Server uptime in seconds',
            registry=self.registry
        )
        
        self.active_connections = Gauge(
            'supabase_mcp_server_active_connections',
            'Number of active WebSocket connections',
            registry=self.registry
        )
        
        # Request metrics
        self.http_requests_total = Counter(
            'supabase_mcp_server_http_requests_total',
            'Total number of HTTP requests',
            ['method', 'endpoint', 'status_code'],
            registry=self.registry
        )
        
        self.http_request_duration = Histogram(
            'supabase_mcp_server_http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
        # MCP metrics
        self.mcp_requests_total = Counter(
            'supabase_mcp_server_mcp_requests_total',
            'Total number of MCP requests',
            ['method', 'status'],
            registry=self.registry
        )
        
        self.mcp_request_duration = Histogram(
            'supabase_mcp_server_mcp_request_duration_seconds',
            'MCP request duration in seconds',
            ['method'],
            registry=self.registry
        )
        
        self.mcp_tool_calls_total = Counter(
            'supabase_mcp_server_tool_calls_total',
            'Total number of MCP tool calls',
            ['tool_name', 'status'],
            registry=self.registry
        )
        
        self.mcp_tool_duration = Histogram(
            'supabase_mcp_server_tool_duration_seconds',
            'MCP tool execution duration in seconds',
            ['tool_name'],
            registry=self.registry
        )
        
        # Database metrics
        self.database_connections_active = Gauge(
            'supabase_mcp_server_database_connections_active',
            'Number of active database connections',
            registry=self.registry
        )
        
        self.database_connections_total = Gauge(
            'supabase_mcp_server_database_connections_total',
            'Total number of database connections in pool',
            registry=self.registry
        )
        
        self.database_queries_total = Counter(
            'supabase_mcp_server_database_queries_total',
            'Total number of database queries',
            ['status'],
            registry=self.registry
        )
        
        self.database_query_duration = Histogram(
            'supabase_mcp_server_database_query_duration_seconds',
            'Database query duration in seconds',
            registry=self.registry
        )
        
        self.database_connection_errors = Counter(
            'supabase_mcp_server_database_connection_errors_total',
            'Total number of database connection errors',
            registry=self.registry
        )
        
        # Supabase API metrics
        self.supabase_api_requests_total = Counter(
            'supabase_mcp_server_supabase_api_requests_total',
            'Total number of Supabase API requests',
            ['operation', 'status'],
            registry=self.registry
        )
        
        self.supabase_api_duration = Histogram(
            'supabase_mcp_server_supabase_api_duration_seconds',
            'Supabase API request duration in seconds',
            ['operation'],
            registry=self.registry
        )
        
        # Storage metrics
        self.storage_operations_total = Counter(
            'supabase_mcp_server_storage_operations_total',
            'Total number of storage operations',
            ['operation', 'status'],
            registry=self.registry
        )
        
        self.storage_bytes_transferred = Counter(
            'supabase_mcp_server_storage_bytes_transferred_total',
            'Total bytes transferred in storage operations',
            ['operation'],
            registry=self.registry
        )
        
        # Security metrics
        self.security_events_total = Counter(
            'supabase_mcp_server_security_events_total',
            'Total number of security events',
            ['event_type', 'severity'],
            registry=self.registry
        )
        
        self.rate_limit_violations = Counter(
            'supabase_mcp_server_rate_limit_violations_total',
            'Total number of rate limit violations',
            registry=self.registry
        )
        
        self.blocked_ips = Gauge(
            'supabase_mcp_server_blocked_ips',
            'Number of currently blocked IP addresses',
            registry=self.registry
        )
        
        # Authentication metrics
        self.auth_attempts_total = Counter(
            'supabase_mcp_server_auth_attempts_total',
            'Total number of authentication attempts',
            ['method', 'status'],
            registry=self.registry
        )
        
        # Error metrics
        self.errors_total = Counter(
            'supabase_mcp_server_errors_total',
            'Total number of errors',
            ['error_type', 'component'],
            registry=self.registry
        )
        
        # Initialize server info
        self._start_time = time.time()
        self.server_info.info({
            'version': '0.1.0',
            'name': 'supabase-mcp-server',
            'protocol_version': '2024-11-05'
        })
        
        logger.info("Metrics service initialized")
    
    def record_http_request(self, method: str, endpoint: str, status_code: int, duration: float) -> None:
        """Record HTTP request metrics."""
        self.http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()
        
        self.http_request_duration.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def record_mcp_request(self, method: str, status: str, duration: float) -> None:
        """Record MCP request metrics."""
        self.mcp_requests_total.labels(method=method, status=status).inc()
        self.mcp_request_duration.labels(method=method).observe(duration)
    
    def record_tool_call(self, tool_name: str, status: str, duration: float) -> None:
        """Record MCP tool call metrics."""
        self.mcp_tool_calls_total.labels(tool_name=tool_name, status=status).inc()
        self.mcp_tool_duration.labels(tool_name=tool_name).observe(duration)
    
    def record_database_query(self, status: str, duration: float) -> None:
        """Record database query metrics."""
        self.database_queries_total.labels(status=status).inc()
        self.database_query_duration.observe(duration)
    
    def record_database_connection_error(self) -> None:
        """Record database connection error."""
        self.database_connection_errors.inc()
    
    def update_database_connections(self, active: int, total: int) -> None:
        """Update database connection metrics."""
        self.database_connections_active.set(active)
        self.database_connections_total.set(total)
    
    def record_supabase_api_request(self, operation: str, status: str, duration: float) -> None:
        """Record Supabase API request metrics."""
        self.supabase_api_requests_total.labels(operation=operation, status=status).inc()
        self.supabase_api_duration.labels(operation=operation).observe(duration)
    
    def record_storage_operation(self, operation: str, status: str, bytes_transferred: int = 0) -> None:
        """Record storage operation metrics."""
        self.storage_operations_total.labels(operation=operation, status=status).inc()
        if bytes_transferred > 0:
            self.storage_bytes_transferred.labels(operation=operation).inc(bytes_transferred)
    
    def record_security_event(self, event_type: str, severity: str) -> None:
        """Record security event metrics."""
        self.security_events_total.labels(event_type=event_type, severity=severity).inc()
    
    def record_rate_limit_violation(self) -> None:
        """Record rate limit violation."""
        self.rate_limit_violations.inc()
    
    def update_blocked_ips(self, count: int) -> None:
        """Update blocked IPs count."""
        self.blocked_ips.set(count)
    
    def record_auth_attempt(self, method: str, status: str) -> None:
        """Record authentication attempt."""
        self.auth_attempts_total.labels(method=method, status=status).inc()
    
    def record_error(self, error_type: str, component: str) -> None:
        """Record error metrics."""
        self.errors_total.labels(error_type=error_type, component=component).inc()
    
    def update_active_connections(self, count: int) -> None:
        """Update active connections count."""
        self.active_connections.set(count)
    
    def update_server_uptime(self) -> None:
        """Update server uptime."""
        uptime = time.time() - self._start_time
        self.server_uptime.set(uptime)
    
    def get_metrics(self) -> str:
        """Get metrics in Prometheus format."""
        # Update uptime before generating metrics
        self.update_server_uptime()
        
        return generate_latest(self.registry).decode('utf-8')
    
    def get_content_type(self) -> str:
        """Get the content type for metrics."""
        return CONTENT_TYPE_LATEST


def timed_operation(metric_name: str, labels: Optional[Dict[str, str]] = None):
    """Decorator to time operations and record metrics."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Record success metric
                if hasattr(metrics_service, metric_name):
                    metric = getattr(metrics_service, metric_name)
                    if labels:
                        metric.labels(**labels).observe(duration)
                    else:
                        metric.observe(duration)
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                
                # Record error metric
                metrics_service.record_error(
                    error_type=type(e).__name__,
                    component=func.__module__
                )
                
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Record success metric
                if hasattr(metrics_service, metric_name):
                    metric = getattr(metrics_service, metric_name)
                    if labels:
                        metric.labels(**labels).observe(duration)
                    else:
                        metric.observe(duration)
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                
                # Record error metric
                metrics_service.record_error(
                    error_type=type(e).__name__,
                    component=func.__module__
                )
                
                raise
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Global metrics service instance
metrics_service = MetricsService()
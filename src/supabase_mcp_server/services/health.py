"""Health check service for monitoring system components."""

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional

from supabase_mcp_server.core.logging import get_logger

logger = get_logger(__name__)


class HealthStatus(Enum):
    """Health check status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    name: str
    status: HealthStatus
    message: str
    duration_ms: float
    timestamp: datetime
    details: Optional[Dict] = None
    error: Optional[str] = None


@dataclass
class ComponentHealth:
    """Health information for a system component."""
    name: str
    status: HealthStatus
    last_check: Optional[datetime] = None
    last_success: Optional[datetime] = None
    consecutive_failures: int = 0
    total_checks: int = 0
    total_failures: int = 0
    average_duration_ms: float = 0.0
    details: Optional[Dict] = None


class HealthCheckService:
    """Service for performing health checks on system components."""
    
    def __init__(self):
        """Initialize health check service."""
        self.components: Dict[str, ComponentHealth] = {}
        self.check_history: List[HealthCheckResult] = []
        self.max_history = 1000  # Keep last 1000 checks
        
        # Health check configuration
        self.timeout_seconds = 30
        self.failure_threshold = 3  # Mark as unhealthy after 3 consecutive failures
        self.degraded_threshold = 1  # Mark as degraded after 1 failure
        
        logger.info("Health check service initialized")
    
    async def check_all_components(self) -> Dict[str, HealthCheckResult]:
        """Check health of all registered components."""
        results = {}
        
        # Check database health
        results["database"] = await self._check_database_health()
        
        # Check Supabase API health
        results["supabase_api"] = await self._check_supabase_api_health()
        
        # Check server health
        results["server"] = await self._check_server_health()
        
        # Check memory health
        results["memory"] = await self._check_memory_health()
        
        # Check disk health
        results["disk"] = await self._check_disk_health()
        
        # Update component health tracking
        for name, result in results.items():
            self._update_component_health(name, result)
        
        # Add to history
        for result in results.values():
            self.check_history.append(result)
            if len(self.check_history) > self.max_history:
                self.check_history.pop(0)
        
        return results
    
    async def check_component(self, component_name: str) -> Optional[HealthCheckResult]:
        """Check health of a specific component."""
        check_methods = {
            "database": self._check_database_health,
            "supabase_api": self._check_supabase_api_health,
            "server": self._check_server_health,
            "memory": self._check_memory_health,
            "disk": self._check_disk_health,
        }
        
        if component_name not in check_methods:
            return None
        
        result = await check_methods[component_name]()
        self._update_component_health(component_name, result)
        self.check_history.append(result)
        
        return result
    
    async def _check_database_health(self) -> HealthCheckResult:
        """Check database health."""
        start_time = time.time()
        
        try:
            from supabase_mcp_server.services.database import database_service
            
            # Check if database service is initialized
            if not database_service._pool:
                return HealthCheckResult(
                    name="database",
                    status=HealthStatus.UNHEALTHY,
                    message="Database not initialized",
                    duration_ms=(time.time() - start_time) * 1000,
                    timestamp=datetime.now(),
                    error="Database pool not initialized"
                )
            
            # Perform health check
            is_healthy = await asyncio.wait_for(
                database_service.health_check(),
                timeout=self.timeout_seconds
            )
            
            if is_healthy:
                # Get additional database info
                db_info = await database_service.get_connection_info()
                
                return HealthCheckResult(
                    name="database",
                    status=HealthStatus.HEALTHY,
                    message="Database is healthy",
                    duration_ms=(time.time() - start_time) * 1000,
                    timestamp=datetime.now(),
                    details={
                        "pool_size": db_info.get("pool_size"),
                        "pool_max_size": db_info.get("pool_max_size"),
                        "version": db_info.get("version", "")[:50] + "..." if db_info.get("version") else None
                    }
                )
            else:
                return HealthCheckResult(
                    name="database",
                    status=HealthStatus.UNHEALTHY,
                    message="Database health check failed",
                    duration_ms=(time.time() - start_time) * 1000,
                    timestamp=datetime.now(),
                    error="Health check query failed"
                )
        
        except asyncio.TimeoutError:
            return HealthCheckResult(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message="Database health check timed out",
                duration_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.now(),
                error=f"Timeout after {self.timeout_seconds} seconds"
            )
        except Exception as e:
            return HealthCheckResult(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message="Database health check error",
                duration_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.now(),
                error=str(e)
            )
    
    async def _check_supabase_api_health(self) -> HealthCheckResult:
        """Check Supabase API health."""
        start_time = time.time()
        
        try:
            from supabase_mcp_server.services.supabase_api import supabase_api_service
            
            # Check if API service is initialized
            if not supabase_api_service.is_initialized():
                return HealthCheckResult(
                    name="supabase_api",
                    status=HealthStatus.DEGRADED,
                    message="Supabase API not initialized",
                    duration_ms=(time.time() - start_time) * 1000,
                    timestamp=datetime.now(),
                    details={"initialized": False}
                )
            
            # Try to get client
            client = supabase_api_service.get_client()
            if not client:
                return HealthCheckResult(
                    name="supabase_api",
                    status=HealthStatus.UNHEALTHY,
                    message="Supabase client not available",
                    duration_ms=(time.time() - start_time) * 1000,
                    timestamp=datetime.now(),
                    error="Client is None"
                )
            
            return HealthCheckResult(
                name="supabase_api",
                status=HealthStatus.HEALTHY,
                message="Supabase API is healthy",
                duration_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.now(),
                details={"initialized": True, "client_available": True}
            )
        
        except Exception as e:
            return HealthCheckResult(
                name="supabase_api",
                status=HealthStatus.UNHEALTHY,
                message="Supabase API health check error",
                duration_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.now(),
                error=str(e)
            )
    
    async def _check_server_health(self) -> HealthCheckResult:
        """Check server health."""
        start_time = time.time()
        
        try:
            # Check basic server metrics
            import psutil
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Determine status based on resource usage
            status = HealthStatus.HEALTHY
            message = "Server is healthy"
            
            if cpu_percent > 90 or memory_percent > 90:
                status = HealthStatus.UNHEALTHY
                message = "Server resources critically high"
            elif cpu_percent > 70 or memory_percent > 80:
                status = HealthStatus.DEGRADED
                message = "Server resources elevated"
            
            return HealthCheckResult(
                name="server",
                status=status,
                message=message,
                duration_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.now(),
                details={
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory_percent,
                    "memory_available_gb": round(memory.available / (1024**3), 2)
                }
            )
        
        except ImportError:
            # psutil not available, basic check
            return HealthCheckResult(
                name="server",
                status=HealthStatus.HEALTHY,
                message="Server is running (basic check)",
                duration_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.now(),
                details={"psutil_available": False}
            )
        except Exception as e:
            return HealthCheckResult(
                name="server",
                status=HealthStatus.UNKNOWN,
                message="Server health check error",
                duration_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.now(),
                error=str(e)
            )
    
    async def _check_memory_health(self) -> HealthCheckResult:
        """Check memory health."""
        start_time = time.time()
        
        try:
            import psutil
            
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Determine status
            status = HealthStatus.HEALTHY
            message = "Memory usage is normal"
            
            if memory.percent > 95:
                status = HealthStatus.UNHEALTHY
                message = "Memory usage critically high"
            elif memory.percent > 85:
                status = HealthStatus.DEGRADED
                message = "Memory usage elevated"
            
            return HealthCheckResult(
                name="memory",
                status=status,
                message=message,
                duration_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.now(),
                details={
                    "memory_percent": memory.percent,
                    "memory_total_gb": round(memory.total / (1024**3), 2),
                    "memory_available_gb": round(memory.available / (1024**3), 2),
                    "swap_percent": swap.percent,
                    "swap_total_gb": round(swap.total / (1024**3), 2)
                }
            )
        
        except ImportError:
            return HealthCheckResult(
                name="memory",
                status=HealthStatus.UNKNOWN,
                message="Memory monitoring not available",
                duration_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.now(),
                details={"psutil_available": False}
            )
        except Exception as e:
            return HealthCheckResult(
                name="memory",
                status=HealthStatus.UNKNOWN,
                message="Memory health check error",
                duration_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.now(),
                error=str(e)
            )
    
    async def _check_disk_health(self) -> HealthCheckResult:
        """Check disk health."""
        start_time = time.time()
        
        try:
            import psutil
            
            # Check root disk usage
            disk = psutil.disk_usage('/')
            
            # Determine status
            status = HealthStatus.HEALTHY
            message = "Disk usage is normal"
            
            disk_percent = (disk.used / disk.total) * 100
            
            if disk_percent > 95:
                status = HealthStatus.UNHEALTHY
                message = "Disk usage critically high"
            elif disk_percent > 85:
                status = HealthStatus.DEGRADED
                message = "Disk usage elevated"
            
            return HealthCheckResult(
                name="disk",
                status=status,
                message=message,
                duration_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.now(),
                details={
                    "disk_percent": round(disk_percent, 2),
                    "disk_total_gb": round(disk.total / (1024**3), 2),
                    "disk_free_gb": round(disk.free / (1024**3), 2),
                    "disk_used_gb": round(disk.used / (1024**3), 2)
                }
            )
        
        except ImportError:
            return HealthCheckResult(
                name="disk",
                status=HealthStatus.UNKNOWN,
                message="Disk monitoring not available",
                duration_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.now(),
                details={"psutil_available": False}
            )
        except Exception as e:
            return HealthCheckResult(
                name="disk",
                status=HealthStatus.UNKNOWN,
                message="Disk health check error",
                duration_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.now(),
                error=str(e)
            )
    
    def _update_component_health(self, name: str, result: HealthCheckResult) -> None:
        """Update component health tracking."""
        if name not in self.components:
            self.components[name] = ComponentHealth(name=name, status=HealthStatus.UNKNOWN)
        
        component = self.components[name]
        component.last_check = result.timestamp
        component.total_checks += 1
        
        # Update average duration
        if component.total_checks == 1:
            component.average_duration_ms = result.duration_ms
        else:
            component.average_duration_ms = (
                (component.average_duration_ms * (component.total_checks - 1) + result.duration_ms) /
                component.total_checks
            )
        
        # Update failure tracking
        if result.status == HealthStatus.HEALTHY:
            component.consecutive_failures = 0
            component.last_success = result.timestamp
        else:
            component.consecutive_failures += 1
            component.total_failures += 1
        
        # Determine overall component status
        if component.consecutive_failures >= self.failure_threshold:
            component.status = HealthStatus.UNHEALTHY
        elif component.consecutive_failures >= self.degraded_threshold:
            component.status = HealthStatus.DEGRADED
        else:
            component.status = HealthStatus.HEALTHY
        
        component.details = result.details
    
    def get_overall_health(self) -> Dict:
        """Get overall system health summary."""
        if not self.components:
            return {
                "status": HealthStatus.UNKNOWN.value,
                "message": "No health checks performed yet"
            }
        
        # Determine overall status
        statuses = [comp.status for comp in self.components.values()]
        
        if any(status == HealthStatus.UNHEALTHY for status in statuses):
            overall_status = HealthStatus.UNHEALTHY
            message = "One or more components are unhealthy"
        elif any(status == HealthStatus.DEGRADED for status in statuses):
            overall_status = HealthStatus.DEGRADED
            message = "One or more components are degraded"
        elif any(status == HealthStatus.UNKNOWN for status in statuses):
            overall_status = HealthStatus.UNKNOWN
            message = "Some components have unknown status"
        else:
            overall_status = HealthStatus.HEALTHY
            message = "All components are healthy"
        
        return {
            "status": overall_status.value,
            "message": message,
            "components": {
                name: {
                    "status": comp.status.value,
                    "last_check": comp.last_check.isoformat() if comp.last_check else None,
                    "last_success": comp.last_success.isoformat() if comp.last_success else None,
                    "consecutive_failures": comp.consecutive_failures,
                    "total_checks": comp.total_checks,
                    "total_failures": comp.total_failures,
                    "average_duration_ms": round(comp.average_duration_ms, 2),
                    "details": comp.details
                }
                for name, comp in self.components.items()
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def get_component_health(self, component_name: str) -> Optional[Dict]:
        """Get health information for a specific component."""
        if component_name not in self.components:
            return None
        
        comp = self.components[component_name]
        return {
            "name": comp.name,
            "status": comp.status.value,
            "last_check": comp.last_check.isoformat() if comp.last_check else None,
            "last_success": comp.last_success.isoformat() if comp.last_success else None,
            "consecutive_failures": comp.consecutive_failures,
            "total_checks": comp.total_checks,
            "total_failures": comp.total_failures,
            "average_duration_ms": round(comp.average_duration_ms, 2),
            "success_rate": round((comp.total_checks - comp.total_failures) / comp.total_checks * 100, 2) if comp.total_checks > 0 else 0,
            "details": comp.details
        }
    
    def get_recent_checks(self, limit: int = 50) -> List[Dict]:
        """Get recent health check results."""
        recent_checks = self.check_history[-limit:] if self.check_history else []
        
        return [
            {
                "name": check.name,
                "status": check.status.value,
                "message": check.message,
                "duration_ms": round(check.duration_ms, 2),
                "timestamp": check.timestamp.isoformat(),
                "details": check.details,
                "error": check.error
            }
            for check in recent_checks
        ]


# Global health check service instance
health_service = HealthCheckService()
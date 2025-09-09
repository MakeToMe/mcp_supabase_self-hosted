"""Main entry point for the Supabase MCP Server."""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from supabase_mcp_server.config import get_settings
from supabase_mcp_server.core.logging import setup_logging
from supabase_mcp_server.mcp.server import MCPServer
from supabase_mcp_server.services.database import database_service
from supabase_mcp_server.services.supabase_api import supabase_api_service
from supabase_mcp_server.services.supabase_handler import SupabaseMCPHandler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    settings = get_settings()
    setup_logging(settings.log_level)
    logger = logging.getLogger(__name__)
    logger.info("Starting Supabase MCP Server...")
    
    # Initialize database service
    await database_service.initialize()
    
    # Initialize Supabase API service (temporarily disabled due to version conflict)
    # await supabase_api_service.initialize()
    
    # Initialize MCP handler and server
    mcp_handler = SupabaseMCPHandler()
    mcp_server = MCPServer(mcp_handler)
    
    # Store in app state for access in routes
    app.state.mcp_server = mcp_server
    app.state.mcp_handler = mcp_handler
    app.state.database_service = database_service
    app.state.supabase_api_service = supabase_api_service
    
    # Include MCP routes
    app.include_router(mcp_server.get_router())
    
    yield
    
    # Shutdown
    logger.info("Shutting down Supabase MCP Server...")
    await database_service.close()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title="Supabase MCP Server",
        description="Model Context Protocol server for Supabase instances",
        version="0.1.0",
        lifespan=lifespan,
    )
    
    # Add CORS middleware if enabled
    if settings.enable_cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    # Add health check endpoints
    @app.get("/health")
    async def health_check():
        """Basic health check endpoint."""
        from supabase_mcp_server.services.health import health_service
        
        try:
            # Perform quick health checks
            health_results = await health_service.check_all_components()
            overall_health = health_service.get_overall_health()
            
            # Return appropriate status code based on health
            status_code = 200
            if overall_health["status"] == "unhealthy":
                status_code = 503
            elif overall_health["status"] == "degraded":
                status_code = 200  # Still operational
            
            return JSONResponse(
                status_code=status_code,
                content={
                    "status": overall_health["status"],
                    "message": overall_health["message"],
                    "service": "supabase-mcp-server",
                    "version": "0.1.0",
                    "timestamp": overall_health["timestamp"]
                }
            )
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "message": f"Health check failed: {str(e)}",
                    "service": "supabase-mcp-server",
                    "version": "0.1.0"
                }
            )
    
    @app.get("/health/detailed")
    async def detailed_health_check():
        """Detailed health check endpoint."""
        from supabase_mcp_server.services.health import health_service
        
        try:
            # Perform comprehensive health checks
            health_results = await health_service.check_all_components()
            overall_health = health_service.get_overall_health()
            
            return {
                "overall": overall_health,
                "checks": {
                    name: {
                        "status": result.status.value,
                        "message": result.message,
                        "duration_ms": round(result.duration_ms, 2),
                        "timestamp": result.timestamp.isoformat(),
                        "details": result.details,
                        "error": result.error
                    }
                    for name, result in health_results.items()
                }
            }
        except Exception as e:
            logger.error("Detailed health check failed", error=str(e))
            return JSONResponse(
                status_code=500,
                content={"error": f"Health check failed: {str(e)}"}
            )
    
    @app.get("/health/ready")
    async def readiness_check():
        """Readiness probe endpoint."""
        from supabase_mcp_server.services.health import health_service
        
        try:
            # Check critical components for readiness
            db_result = await health_service.check_component("database")
            
            if db_result and db_result.status.value in ["healthy", "degraded"]:
                return {"status": "ready", "message": "Service is ready to accept requests"}
            else:
                return JSONResponse(
                    status_code=503,
                    content={"status": "not_ready", "message": "Service is not ready"}
                )
        except Exception as e:
            logger.error("Readiness check failed", error=str(e))
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "message": f"Readiness check failed: {str(e)}"}
            )
    
    @app.get("/health/live")
    async def liveness_check():
        """Liveness probe endpoint."""
        try:
            # Basic liveness check - just verify the service is running
            return {"status": "alive", "message": "Service is alive"}
        except Exception as e:
            logger.error("Liveness check failed", error=str(e))
            return JSONResponse(
                status_code=503,
                content={"status": "dead", "message": f"Liveness check failed: {str(e)}"}
            )
    
    # Add MCP info endpoint
    @app.get("/info")
    async def server_info():
        """Get server information."""
        return {
            "name": "supabase-mcp-server",
            "version": "0.1.0",
            "protocol_version": "2024-11-05",
            "description": "Model Context Protocol server for Supabase instances"
        }
    
    return app


def main() -> None:
    """Main entry point."""
    settings = get_settings()
    
    try:
        uvicorn.run(
            "supabase_mcp_server.main:create_app",
            factory=True,
            host=settings.server_host,
            port=settings.server_port,
            log_level=settings.log_level.lower(),
            reload=settings.debug,
        )
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Server stopped by user")
    except Exception as e:
        logging.getLogger(__name__).error(f"Server failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
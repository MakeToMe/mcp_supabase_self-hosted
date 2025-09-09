"""MCP server implementation with FastAPI integration."""

import asyncio
import json
from typing import Dict, Optional

from fastapi import HTTPException, Request, WebSocket, WebSocketDisconnect, status
from fastapi.routing import APIRouter

from supabase_mcp_server.core.logging import get_logger
from supabase_mcp_server.mcp.handler import MCPHandler, deserialize_mcp_message, serialize_mcp_message
from supabase_mcp_server.mcp.models import MCPError, MCPResponse
from supabase_mcp_server.middleware.auth import auth_middleware, AuthContext
from supabase_mcp_server.middleware.rate_limit import get_security_middleware, RateLimitExceeded
from supabase_mcp_server.services.metrics import metrics_service

logger = get_logger(__name__)


class MCPServer:
    """MCP server with WebSocket support."""
    
    def __init__(self, handler: MCPHandler):
        """Initialize the MCP server."""
        self.handler = handler
        self.connections: Dict[str, WebSocket] = {}
        self.router = APIRouter()
        self._setup_routes()
    
    def _setup_routes(self) -> None:
        """Setup FastAPI routes for MCP."""
        
        @self.router.websocket("/mcp")
        async def mcp_websocket(websocket: WebSocket):
            """WebSocket endpoint for MCP communication."""
            await self.handle_websocket_connection(websocket)
        
        @self.router.get("/mcp/tools")
        async def list_tools(request: Request):
            """HTTP endpoint to list available tools."""
            try:
                # Apply security checks
                security_middleware = get_security_middleware()
                await security_middleware.initialize()
                await security_middleware.check_rate_limit(request)
                await security_middleware.check_security_threats(request)
                
                # Authenticate request
                auth_context = await auth_middleware.authenticate_request(request)
                
                tools_result = await self.handler.list_tools()
                return {
                    "tools": [tool.model_dump() for tool in tools_result.tools],
                    "authenticated": auth_context.is_authenticated,
                    "user_id": auth_context.user_id
                }
            except RateLimitExceeded as e:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=str(e),
                    headers={"Retry-After": str(e.retry_after)}
                )
            except Exception as e:
                logger.error("Error listing tools", error=str(e))
                return {"error": str(e)}
        
        @self.router.get("/mcp/capabilities")
        async def get_capabilities(request: Request):
            """HTTP endpoint to get server capabilities."""
            try:
                # Authenticate request (optional for capabilities)
                auth_context = await auth_middleware.authenticate_request(request)
                
                return {
                    "protocol_version": "2024-11-05",
                    "capabilities": {
                        "tools": {"list_changed": True},
                        "resources": {"subscribe": False, "list_changed": False},
                        "authentication": {
                            "methods": ["api_key", "jwt", "service_role"],
                            "required": False
                        }
                    },
                    "server_info": {
                        "name": "supabase-mcp-server",
                        "version": "0.1.0"
                    },
                    "authenticated": auth_context.is_authenticated
                }
            except Exception as e:
                logger.error("Error getting capabilities", error=str(e))
                return {"error": str(e)}
        
        @self.router.get("/mcp/status")
        async def get_status(request: Request):
            """HTTP endpoint to get server status."""
            from supabase_mcp_server.services.database import database_service
            from supabase_mcp_server.services.supabase_api import supabase_api_service
            
            try:
                # Authenticate request (optional for status)
                auth_context = await auth_middleware.authenticate_request(request)
                
                db_info = await database_service.get_connection_info()
                db_healthy = await database_service.health_check()
                
                return {
                    "server": {
                        "status": "running",
                        "connections": self.get_connection_count()
                    },
                    "database": {
                        "healthy": db_healthy,
                        **db_info
                    },
                    "supabase_api": {
                        "initialized": supabase_api_service.is_initialized()
                    },
                    "authentication": {
                        "authenticated": auth_context.is_authenticated,
                        "user_id": auth_context.user_id,
                        "auth_method": auth_context.auth_method
                    },
                    "security": security_middleware.get_security_stats()
                }
            except Exception as e:
                logger.error("Error getting status", error=str(e))
                return {"error": str(e)}
        
        @self.router.get("/mcp/security")
        async def get_security_info(request: Request):
            """HTTP endpoint to get security information."""
            try:
                # Apply security checks
                await security_middleware.check_rate_limit(request)
                
                # Authenticate request (require authentication for security info)
                auth_context = await auth_middleware.authenticate_request(request)
                auth_middleware.require_authentication(auth_context)
                
                client_ip = security_middleware._get_client_ip(request)
                
                return {
                    "security_stats": security_middleware.get_security_stats(),
                    "client_info": security_middleware.get_client_stats(client_ip),
                    "authenticated_as": {
                        "user_id": auth_context.user_id,
                        "auth_method": auth_context.auth_method,
                        "permissions": auth_context.permissions
                    }
                }
            except RateLimitExceeded as e:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=str(e),
                    headers={"Retry-After": str(e.retry_after)}
                )
            except Exception as e:
                logger.error("Error getting security info", error=str(e))
                return {"error": str(e)}
        
        @self.router.get("/metrics")
        async def get_metrics():
            """Prometheus metrics endpoint."""
            from fastapi import Response
            
            try:
                metrics_content = metrics_service.get_metrics()
                return Response(
                    content=metrics_content,
                    media_type=metrics_service.get_content_type()
                )
            except Exception as e:
                logger.error("Error generating metrics", error=str(e))
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to generate metrics"
                )
    
    async def handle_websocket_connection(self, websocket: WebSocket) -> None:
        """Handle a WebSocket connection for MCP communication."""
        connection_id = id(websocket)
        
        try:
            await websocket.accept()
            self.connections[str(connection_id)] = websocket
            
            logger.info("MCP WebSocket connection established", connection_id=connection_id)
            
            while True:
                try:
                    # Receive message from client
                    data = await websocket.receive_text()
                    logger.debug("Received MCP message", connection_id=connection_id, data=data)
                    
                    # Process the message
                    response = await self.process_message(data)
                    
                    # Send response back to client
                    response_data = serialize_mcp_message(response)
                    await websocket.send_text(response_data)
                    
                    logger.debug("Sent MCP response", connection_id=connection_id, response=response_data)
                    
                except WebSocketDisconnect:
                    logger.info("MCP WebSocket connection closed", connection_id=connection_id)
                    break
                except Exception as e:
                    logger.error("Error processing MCP message", connection_id=connection_id, error=str(e))
                    
                    # Send error response
                    error_response = MCPResponse(
                        id="unknown",
                        error=MCPError(
                            code=-32603,
                            message=f"Internal server error: {str(e)}"
                        )
                    )
                    
                    try:
                        await websocket.send_text(serialize_mcp_message(error_response))
                    except Exception:
                        # Connection might be closed
                        break
        
        except Exception as e:
            logger.error("WebSocket connection error", connection_id=connection_id, error=str(e))
        
        finally:
            # Clean up connection
            if str(connection_id) in self.connections:
                del self.connections[str(connection_id)]
            
            logger.info("MCP WebSocket connection cleaned up", connection_id=connection_id)
    
    async def process_message(self, data: str) -> MCPResponse:
        """Process an MCP message and return a response."""
        try:
            # Deserialize the request
            request = deserialize_mcp_message(data)
            
            # Handle the request
            response = await self.handler.handle_request(request)
            
            return response
            
        except ValueError as e:
            # Invalid message format
            return MCPResponse(
                id="unknown",
                error=MCPError(
                    code=-32700,  # Parse error
                    message=f"Parse error: {str(e)}"
                )
            )
        except Exception as e:
            # Other errors
            return MCPResponse(
                id="unknown",
                error=MCPError(
                    code=-32603,  # Internal error
                    message=f"Internal error: {str(e)}"
                )
            )
    
    async def broadcast_notification(self, method: str, params: Optional[Dict] = None) -> None:
        """Broadcast a notification to all connected clients."""
        if not self.connections:
            return
        
        notification_data = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {}
        }
        
        message = json.dumps(notification_data)
        
        # Send to all connected clients
        disconnected = []
        for connection_id, websocket in self.connections.items():
            try:
                await websocket.send_text(message)
                logger.debug("Sent notification", connection_id=connection_id, method=method)
            except Exception as e:
                logger.warning("Failed to send notification", connection_id=connection_id, error=str(e))
                disconnected.append(connection_id)
        
        # Clean up disconnected clients
        for connection_id in disconnected:
            if connection_id in self.connections:
                del self.connections[connection_id]
    
    def get_router(self) -> APIRouter:
        """Get the FastAPI router for MCP endpoints."""
        return self.router
    
    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.connections)
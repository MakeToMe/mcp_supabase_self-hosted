"""Base MCP protocol handler implementation."""

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from supabase_mcp_server.core.logging import get_logger
from supabase_mcp_server.mcp.models import (
    CallToolParams,
    InitializeParams,
    InitializeResult,
    ListResourcesResult,
    ListToolsResult,
    MCPError,
    MCPRequest,
    MCPResponse,
    ReadResourceParams,
    ReadResourceResult,
    Tool,
    ToolResult,
)

logger = get_logger(__name__)


class MCPHandler(ABC):
    """Abstract base class for MCP protocol handlers."""
    
    def __init__(self):
        """Initialize the MCP handler."""
        self._tools: Dict[str, Tool] = {}
        self._initialized = False
    
    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        """Handle an MCP request and return a response."""
        try:
            logger.info("Handling MCP request", method=request.method, id=request.id)
            
            # Route request to appropriate handler
            if request.method == "initialize":
                result = await self._handle_initialize(request.params or {})
            elif request.method == "tools/list":
                result = await self._handle_list_tools()
            elif request.method == "tools/call":
                result = await self._handle_call_tool(request.params or {})
            elif request.method == "resources/list":
                result = await self._handle_list_resources()
            elif request.method == "resources/read":
                result = await self._handle_read_resource(request.params or {})
            else:
                raise ValueError(f"Unknown method: {request.method}")
            
            return MCPResponse(id=request.id, result=result)
            
        except Exception as e:
            logger.error("Error handling MCP request", error=str(e), method=request.method)
            return MCPResponse(
                id=request.id,
                error=MCPError(
                    code=-32603,  # Internal error
                    message=str(e),
                    data={"method": request.method}
                )
            )
    
    async def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request."""
        init_params = InitializeParams(**params)
        
        logger.info(
            "Initializing MCP session",
            protocol_version=init_params.protocol_version,
            client_info=init_params.client_info
        )
        
        result = await self.initialize(init_params)
        self._initialized = True
        
        return result.model_dump()
    
    async def _handle_list_tools(self) -> Dict[str, Any]:
        """Handle list tools request."""
        if not self._initialized:
            raise ValueError("Session not initialized")
        
        result = await self.list_tools()
        return result.model_dump()
    
    async def _handle_call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle call tool request."""
        if not self._initialized:
            raise ValueError("Session not initialized")
        
        call_params = CallToolParams(**params)
        
        if call_params.name not in self._tools:
            raise ValueError(f"Unknown tool: {call_params.name}")
        
        result = await self.call_tool(call_params.name, call_params.arguments)
        return result.model_dump()
    
    async def _handle_list_resources(self) -> Dict[str, Any]:
        """Handle list resources request."""
        if not self._initialized:
            raise ValueError("Session not initialized")
        
        result = await self.list_resources()
        return result.model_dump()
    
    async def _handle_read_resource(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle read resource request."""
        if not self._initialized:
            raise ValueError("Session not initialized")
        
        read_params = ReadResourceParams(**params)
        result = await self.read_resource(read_params.uri)
        return result.model_dump()
    
    def register_tool(self, tool: Tool) -> None:
        """Register a tool with the handler."""
        self._tools[tool.name] = tool
        logger.info("Registered tool", name=tool.name, description=tool.description)
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a registered tool by name."""
        return self._tools.get(name)
    
    def get_all_tools(self) -> List[Tool]:
        """Get all registered tools."""
        return list(self._tools.values())
    
    @abstractmethod
    async def initialize(self, params: InitializeParams) -> InitializeResult:
        """Initialize the MCP session."""
        pass
    
    @abstractmethod
    async def list_tools(self) -> ListToolsResult:
        """List available tools."""
        pass
    
    @abstractmethod
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> ToolResult:
        """Call a tool with the given arguments."""
        pass
    
    async def list_resources(self) -> ListResourcesResult:
        """List available resources (optional)."""
        return ListResourcesResult(resources=[])
    
    async def read_resource(self, uri: str) -> ReadResourceResult:
        """Read a resource by URI (optional)."""
        raise ValueError(f"Resource not found: {uri}")


def serialize_mcp_message(message: Any) -> str:
    """Serialize an MCP message to JSON."""
    if hasattr(message, 'model_dump'):
        data = message.model_dump()
    else:
        data = message
    
    return json.dumps(data, ensure_ascii=False, separators=(',', ':'))


def deserialize_mcp_message(data: str) -> MCPRequest:
    """Deserialize JSON data to an MCP request."""
    try:
        parsed = json.loads(data)
        return MCPRequest(**parsed)
    except (json.JSONDecodeError, ValueError) as e:
        raise ValueError(f"Invalid MCP message: {e}") from e
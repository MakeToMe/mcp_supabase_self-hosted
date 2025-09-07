"""MCP protocol data models using Pydantic."""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, Field


class MCPMessageType(str, Enum):
    """MCP message types."""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"


class MCPMethod(str, Enum):
    """MCP method names."""
    INITIALIZE = "initialize"
    LIST_TOOLS = "tools/list"
    CALL_TOOL = "tools/call"
    LIST_RESOURCES = "resources/list"
    READ_RESOURCE = "resources/read"
    SUBSCRIBE = "resources/subscribe"
    UNSUBSCRIBE = "resources/unsubscribe"


class MCPError(BaseModel):
    """MCP error response."""
    code: int = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional error data")


class MCPRequest(BaseModel):
    """MCP request message."""
    jsonrpc: str = Field("2.0", description="JSON-RPC version")
    id: Union[str, int] = Field(default_factory=lambda: str(uuid4()), description="Request ID")
    method: str = Field(..., description="Method name")
    params: Optional[Dict[str, Any]] = Field(None, description="Method parameters")


class MCPResponse(BaseModel):
    """MCP response message."""
    jsonrpc: str = Field("2.0", description="JSON-RPC version")
    id: Union[str, int] = Field(..., description="Request ID")
    result: Optional[Dict[str, Any]] = Field(None, description="Response result")
    error: Optional[MCPError] = Field(None, description="Error information")


class MCPNotification(BaseModel):
    """MCP notification message."""
    jsonrpc: str = Field("2.0", description="JSON-RPC version")
    method: str = Field(..., description="Method name")
    params: Optional[Dict[str, Any]] = Field(None, description="Method parameters")


class ToolParameter(BaseModel):
    """Tool parameter definition."""
    type: str = Field(..., description="Parameter type")
    description: Optional[str] = Field(None, description="Parameter description")
    required: bool = Field(False, description="Whether parameter is required")
    enum: Optional[List[str]] = Field(None, description="Allowed values")
    default: Optional[Any] = Field(None, description="Default value")


class Tool(BaseModel):
    """MCP tool definition."""
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    parameters: Dict[str, ToolParameter] = Field(default_factory=dict, description="Tool parameters")


class ToolResult(BaseModel):
    """Tool execution result."""
    content: List[Dict[str, Any]] = Field(default_factory=list, description="Result content")
    is_error: bool = Field(False, description="Whether result is an error")


class Resource(BaseModel):
    """MCP resource definition."""
    uri: str = Field(..., description="Resource URI")
    name: str = Field(..., description="Resource name")
    description: Optional[str] = Field(None, description="Resource description")
    mime_type: Optional[str] = Field(None, description="MIME type")


class ResourceContent(BaseModel):
    """Resource content."""
    uri: str = Field(..., description="Resource URI")
    mime_type: Optional[str] = Field(None, description="MIME type")
    text: Optional[str] = Field(None, description="Text content")
    blob: Optional[bytes] = Field(None, description="Binary content")


class InitializeParams(BaseModel):
    """Initialize method parameters."""
    protocol_version: str = Field(..., description="MCP protocol version")
    capabilities: Dict[str, Any] = Field(default_factory=dict, description="Client capabilities")
    client_info: Dict[str, str] = Field(default_factory=dict, description="Client information")


class InitializeResult(BaseModel):
    """Initialize method result."""
    protocol_version: str = Field("2024-11-05", description="MCP protocol version")
    capabilities: Dict[str, Any] = Field(default_factory=dict, description="Server capabilities")
    server_info: Dict[str, str] = Field(default_factory=dict, description="Server information")


class ListToolsResult(BaseModel):
    """List tools method result."""
    tools: List[Tool] = Field(default_factory=list, description="Available tools")


class CallToolParams(BaseModel):
    """Call tool method parameters."""
    name: str = Field(..., description="Tool name")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")


class ListResourcesResult(BaseModel):
    """List resources method result."""
    resources: List[Resource] = Field(default_factory=list, description="Available resources")


class ReadResourceParams(BaseModel):
    """Read resource method parameters."""
    uri: str = Field(..., description="Resource URI")


class ReadResourceResult(BaseModel):
    """Read resource method result."""
    contents: List[ResourceContent] = Field(default_factory=list, description="Resource contents")
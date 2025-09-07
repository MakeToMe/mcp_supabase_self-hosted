"""Tests for MCP protocol handler."""

import pytest

from supabase_mcp_server.mcp.handler import (
    MCPHandler,
    deserialize_mcp_message,
    serialize_mcp_message,
)
from supabase_mcp_server.mcp.models import (
    InitializeParams,
    InitializeResult,
    ListToolsResult,
    MCPRequest,
    Tool,
    ToolParameter,
    ToolResult,
)


class TestMCPHandler(MCPHandler):
    """Test implementation of MCP handler."""
    
    async def initialize(self, params: InitializeParams) -> InitializeResult:
        """Initialize the test handler."""
        return InitializeResult(
            protocol_version="2024-11-05",
            capabilities={"tools": {"list_changed": True}},
            server_info={"name": "test-server", "version": "1.0.0"}
        )
    
    async def list_tools(self) -> ListToolsResult:
        """List available tools."""
        return ListToolsResult(tools=self.get_all_tools())
    
    async def call_tool(self, name: str, arguments: dict) -> ToolResult:
        """Call a tool."""
        if name == "echo":
            return ToolResult(
                content=[{"type": "text", "text": arguments.get("message", "")}]
            )
        elif name == "error_tool":
            return ToolResult(
                content=[{"type": "text", "text": "Error occurred"}],
                is_error=True
            )
        else:
            raise ValueError(f"Unknown tool: {name}")


class TestMCPHandlerImplementation:
    """Test MCP handler implementation."""
    
    @pytest.fixture
    def handler(self):
        """Create a test MCP handler."""
        handler = TestMCPHandler()
        
        # Register test tools
        echo_tool = Tool(
            name="echo",
            description="Echo the input message",
            parameters={
                "message": ToolParameter(type="string", required=True)
            }
        )
        handler.register_tool(echo_tool)
        
        error_tool = Tool(
            name="error_tool",
            description="A tool that returns an error",
            parameters={}
        )
        handler.register_tool(error_tool)
        
        return handler
    
    async def test_initialize_request(self, handler):
        """Test initialize request handling."""
        request = MCPRequest(
            method="initialize",
            params={
                "protocol_version": "2024-11-05",
                "capabilities": {"tools": True},
                "client_info": {"name": "test-client"}
            }
        )
        
        response = await handler.handle_request(request)
        
        assert response.error is None
        assert response.result is not None
        assert response.result["protocol_version"] == "2024-11-05"
        assert response.result["server_info"]["name"] == "test-server"
    
    async def test_list_tools_request(self, handler):
        """Test list tools request handling."""
        # First initialize
        init_request = MCPRequest(
            method="initialize",
            params={"protocol_version": "2024-11-05"}
        )
        await handler.handle_request(init_request)
        
        # Then list tools
        request = MCPRequest(method="tools/list")
        response = await handler.handle_request(request)
        
        assert response.error is None
        assert response.result is not None
        assert len(response.result["tools"]) == 2
        
        tool_names = [tool["name"] for tool in response.result["tools"]]
        assert "echo" in tool_names
        assert "error_tool" in tool_names
    
    async def test_call_tool_request(self, handler):
        """Test call tool request handling."""
        # First initialize
        init_request = MCPRequest(
            method="initialize",
            params={"protocol_version": "2024-11-05"}
        )
        await handler.handle_request(init_request)
        
        # Then call tool
        request = MCPRequest(
            method="tools/call",
            params={
                "name": "echo",
                "arguments": {"message": "Hello, world!"}
            }
        )
        
        response = await handler.handle_request(request)
        
        assert response.error is None
        assert response.result is not None
        assert response.result["content"][0]["text"] == "Hello, world!"
        assert response.result["is_error"] is False
    
    async def test_call_unknown_tool(self, handler):
        """Test calling an unknown tool."""
        # First initialize
        init_request = MCPRequest(
            method="initialize",
            params={"protocol_version": "2024-11-05"}
        )
        await handler.handle_request(init_request)
        
        # Then call unknown tool
        request = MCPRequest(
            method="tools/call",
            params={
                "name": "unknown_tool",
                "arguments": {}
            }
        )
        
        response = await handler.handle_request(request)
        
        assert response.error is not None
        assert "Unknown tool" in response.error.message
    
    async def test_request_without_initialization(self, handler):
        """Test request without initialization."""
        request = MCPRequest(method="tools/list")
        response = await handler.handle_request(request)
        
        assert response.error is not None
        assert "not initialized" in response.error.message
    
    async def test_unknown_method(self, handler):
        """Test unknown method handling."""
        request = MCPRequest(method="unknown/method")
        response = await handler.handle_request(request)
        
        assert response.error is not None
        assert "Unknown method" in response.error.message
    
    def test_tool_registration(self, handler):
        """Test tool registration."""
        tool = Tool(
            name="new_tool",
            description="A new tool",
            parameters={}
        )
        
        handler.register_tool(tool)
        
        assert handler.get_tool("new_tool") is not None
        assert handler.get_tool("new_tool").name == "new_tool"
        assert len(handler.get_all_tools()) == 3  # 2 existing + 1 new


class TestMessageSerialization:
    """Test MCP message serialization."""
    
    def test_serialize_mcp_message(self):
        """Test MCP message serialization."""
        request = MCPRequest(method="test", params={"key": "value"})
        serialized = serialize_mcp_message(request)
        
        assert isinstance(serialized, str)
        assert "test" in serialized
        assert "key" in serialized
    
    def test_deserialize_mcp_message(self):
        """Test MCP message deserialization."""
        data = '{"jsonrpc":"2.0","method":"test","params":{"key":"value"},"id":"123"}'
        request = deserialize_mcp_message(data)
        
        assert request.method == "test"
        assert request.params == {"key": "value"}
        assert request.id == "123"
    
    def test_deserialize_invalid_message(self):
        """Test deserialization of invalid message."""
        with pytest.raises(ValueError, match="Invalid MCP message"):
            deserialize_mcp_message("invalid json")
    
    def test_deserialize_incomplete_message(self):
        """Test deserialization of incomplete message."""
        with pytest.raises(ValueError, match="Invalid MCP message"):
            deserialize_mcp_message('{"jsonrpc":"2.0"}')
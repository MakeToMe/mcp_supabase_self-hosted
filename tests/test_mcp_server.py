"""Tests for MCP server integration."""

import json
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket

from supabase_mcp_server.mcp.handler import MCPHandler
from supabase_mcp_server.mcp.models import (
    InitializeParams,
    InitializeResult,
    ListToolsResult,
    Tool,
    ToolResult,
)
from supabase_mcp_server.mcp.server import MCPServer


class MockMCPHandler(MCPHandler):
    """Mock MCP handler for testing."""
    
    async def initialize(self, params: InitializeParams) -> InitializeResult:
        """Initialize the mock handler."""
        return InitializeResult(
            protocol_version="2024-11-05",
            capabilities={"tools": {"list_changed": True}},
            server_info={"name": "mock-server", "version": "1.0.0"}
        )
    
    async def list_tools(self) -> ListToolsResult:
        """List available tools."""
        return ListToolsResult(tools=self.get_all_tools())
    
    async def call_tool(self, name: str, arguments: dict) -> ToolResult:
        """Call a tool."""
        return ToolResult(
            content=[{"type": "text", "text": f"Mock result for {name}"}]
        )


class TestMCPServer:
    """Test MCP server functionality."""
    
    @pytest.fixture
    def mock_handler(self):
        """Create a mock MCP handler."""
        handler = MockMCPHandler()
        
        # Register a test tool
        test_tool = Tool(
            name="test_tool",
            description="A test tool",
            parameters={}
        )
        handler.register_tool(test_tool)
        
        return handler
    
    @pytest.fixture
    def mcp_server(self, mock_handler):
        """Create an MCP server with mock handler."""
        return MCPServer(mock_handler)
    
    def test_server_initialization(self, mcp_server):
        """Test MCP server initialization."""
        assert mcp_server.handler is not None
        assert mcp_server.get_connection_count() == 0
        assert mcp_server.get_router() is not None
    
    async def test_process_initialize_message(self, mcp_server):
        """Test processing initialize message."""
        message = json.dumps({
            "jsonrpc": "2.0",
            "id": "1",
            "method": "initialize",
            "params": {
                "protocol_version": "2024-11-05",
                "capabilities": {},
                "client_info": {"name": "test-client"}
            }
        })
        
        response = await mcp_server.process_message(message)
        
        assert response.error is None
        assert response.result is not None
        assert response.result["protocol_version"] == "2024-11-05"
        assert response.result["server_info"]["name"] == "mock-server"
    
    async def test_process_list_tools_message(self, mcp_server):
        """Test processing list tools message."""
        # First initialize
        init_message = json.dumps({
            "jsonrpc": "2.0",
            "id": "1",
            "method": "initialize",
            "params": {"protocol_version": "2024-11-05"}
        })
        await mcp_server.process_message(init_message)
        
        # Then list tools
        message = json.dumps({
            "jsonrpc": "2.0",
            "id": "2",
            "method": "tools/list"
        })
        
        response = await mcp_server.process_message(message)
        
        assert response.error is None
        assert response.result is not None
        assert len(response.result["tools"]) == 1
        assert response.result["tools"][0]["name"] == "test_tool"
    
    async def test_process_call_tool_message(self, mcp_server):
        """Test processing call tool message."""
        # First initialize
        init_message = json.dumps({
            "jsonrpc": "2.0",
            "id": "1",
            "method": "initialize",
            "params": {"protocol_version": "2024-11-05"}
        })
        await mcp_server.process_message(init_message)
        
        # Then call tool
        message = json.dumps({
            "jsonrpc": "2.0",
            "id": "2",
            "method": "tools/call",
            "params": {
                "name": "test_tool",
                "arguments": {}
            }
        })
        
        response = await mcp_server.process_message(message)
        
        assert response.error is None
        assert response.result is not None
        assert response.result["content"][0]["text"] == "Mock result for test_tool"
    
    async def test_process_invalid_message(self, mcp_server):
        """Test processing invalid message."""
        message = "invalid json"
        
        response = await mcp_server.process_message(message)
        
        assert response.error is not None
        assert response.error.code == -32700  # Parse error
        assert "Parse error" in response.error.message
    
    async def test_process_unknown_method(self, mcp_server):
        """Test processing unknown method."""
        message = json.dumps({
            "jsonrpc": "2.0",
            "id": "1",
            "method": "unknown/method"
        })
        
        response = await mcp_server.process_message(message)
        
        assert response.error is not None
        assert "Unknown method" in response.error.message
    
    async def test_broadcast_notification(self, mcp_server):
        """Test broadcasting notifications."""
        # Mock WebSocket connections
        mock_ws1 = AsyncMock(spec=WebSocket)
        mock_ws2 = AsyncMock(spec=WebSocket)
        
        mcp_server.connections["1"] = mock_ws1
        mcp_server.connections["2"] = mock_ws2
        
        await mcp_server.broadcast_notification("test/notification", {"data": "test"})
        
        # Verify both connections received the notification
        mock_ws1.send_text.assert_called_once()
        mock_ws2.send_text.assert_called_once()
        
        # Check the message content
        sent_message = mock_ws1.send_text.call_args[0][0]
        parsed_message = json.loads(sent_message)
        
        assert parsed_message["jsonrpc"] == "2.0"
        assert parsed_message["method"] == "test/notification"
        assert parsed_message["params"]["data"] == "test"
    
    def test_router_endpoints(self, mcp_server):
        """Test that router has expected endpoints."""
        router = mcp_server.get_router()
        
        # Check that routes are registered
        route_paths = [route.path for route in router.routes]
        
        assert "/mcp" in route_paths  # WebSocket endpoint
        assert "/mcp/tools" in route_paths  # HTTP tools endpoint
        assert "/mcp/capabilities" in route_paths  # HTTP capabilities endpoint
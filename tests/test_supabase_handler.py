"""Tests for Supabase MCP handler."""

import pytest

from supabase_mcp_server.mcp.models import InitializeParams
from supabase_mcp_server.services.supabase_handler import SupabaseMCPHandler


class TestSupabaseMCPHandler:
    """Test Supabase MCP handler."""
    
    @pytest.fixture
    def handler(self, override_settings):
        """Create a Supabase MCP handler."""
        return SupabaseMCPHandler()
    
    def test_handler_initialization(self, handler):
        """Test handler initialization."""
        assert handler is not None
        assert len(handler.get_all_tools()) == 5  # 5 registered tools
        
        tool_names = [tool.name for tool in handler.get_all_tools()]
        expected_tools = [
            "query_database",
            "get_schema",
            "crud_operations",
            "storage_operations",
            "get_metrics"
        ]
        
        for tool_name in expected_tools:
            assert tool_name in tool_names
    
    async def test_initialize(self, handler):
        """Test initialize method."""
        params = InitializeParams(
            protocol_version="2024-11-05",
            capabilities={"tools": True},
            client_info={"name": "test-client"}
        )
        
        result = await handler.initialize(params)
        
        assert result.protocol_version == "2024-11-05"
        assert result.server_info["name"] == "supabase-mcp-server"
        assert result.capabilities["tools"]["list_changed"] is True
    
    async def test_list_tools(self, handler):
        """Test list tools method."""
        result = await handler.list_tools()
        
        assert len(result.tools) == 5
        
        tool_names = [tool.name for tool in result.tools]
        assert "query_database" in tool_names
        assert "get_schema" in tool_names
        assert "crud_operations" in tool_names
        assert "storage_operations" in tool_names
        assert "get_metrics" in tool_names
    
    async def test_call_query_database_tool(self, handler):
        """Test calling query_database tool."""
        result = await handler.call_tool("query_database", {
            "query": "SELECT * FROM users"
        })
        
        assert result.is_error is False
        assert len(result.content) == 1
        assert "SELECT * FROM users" in result.content[0]["text"]
        assert "Implementation pending" in result.content[0]["text"]
    
    async def test_call_get_schema_tool(self, handler):
        """Test calling get_schema tool."""
        result = await handler.call_tool("get_schema", {
            "table_name": "users"
        })
        
        assert result.is_error is False
        assert len(result.content) == 1
        assert "users" in result.content[0]["text"]
        assert "Implementation pending" in result.content[0]["text"]
    
    async def test_call_crud_operations_tool(self, handler):
        """Test calling crud_operations tool."""
        result = await handler.call_tool("crud_operations", {
            "operation": "select",
            "table": "users"
        })
        
        assert result.is_error is False
        assert len(result.content) == 1
        assert "select" in result.content[0]["text"]
        assert "users" in result.content[0]["text"]
        assert "Implementation pending" in result.content[0]["text"]
    
    async def test_call_storage_operations_tool(self, handler):
        """Test calling storage_operations tool."""
        result = await handler.call_tool("storage_operations", {
            "operation": "list",
            "bucket": "images"
        })
        
        assert result.is_error is False
        assert len(result.content) == 1
        assert "list" in result.content[0]["text"]
        assert "images" in result.content[0]["text"]
        assert "Implementation pending" in result.content[0]["text"]
    
    async def test_call_get_metrics_tool(self, handler):
        """Test calling get_metrics tool."""
        result = await handler.call_tool("get_metrics", {
            "metric_type": "database"
        })
        
        assert result.is_error is False
        assert len(result.content) == 1
        assert "database" in result.content[0]["text"]
        assert "Implementation pending" in result.content[0]["text"]
    
    async def test_call_unknown_tool(self, handler):
        """Test calling unknown tool."""
        result = await handler.call_tool("unknown_tool", {})
        
        assert result.is_error is True
        assert len(result.content) == 1
        assert "Unknown tool" in result.content[0]["text"]
    
    def test_tool_parameters(self, handler):
        """Test tool parameter definitions."""
        query_tool = handler.get_tool("query_database")
        assert query_tool is not None
        assert "query" in query_tool.parameters
        assert query_tool.parameters["query"].required is True
        assert query_tool.parameters["query"].type == "string"
        
        crud_tool = handler.get_tool("crud_operations")
        assert crud_tool is not None
        assert "operation" in crud_tool.parameters
        assert crud_tool.parameters["operation"].enum == ["select", "insert", "update", "delete"]
        
        storage_tool = handler.get_tool("storage_operations")
        assert storage_tool is not None
        assert "operation" in storage_tool.parameters
        assert storage_tool.parameters["operation"].enum == ["list", "upload", "download", "delete"]
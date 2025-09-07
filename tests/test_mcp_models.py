"""Tests for MCP protocol models."""

import pytest
from pydantic import ValidationError

from supabase_mcp_server.mcp.models import (
    CallToolParams,
    InitializeParams,
    MCPError,
    MCPRequest,
    MCPResponse,
    Tool,
    ToolParameter,
    ToolResult,
)


class TestMCPModels:
    """Test MCP protocol models."""
    
    def test_mcp_request_creation(self):
        """Test MCP request creation."""
        request = MCPRequest(method="test_method", params={"key": "value"})
        
        assert request.jsonrpc == "2.0"
        assert request.method == "test_method"
        assert request.params == {"key": "value"}
        assert request.id is not None
    
    def test_mcp_response_creation(self):
        """Test MCP response creation."""
        response = MCPResponse(id="test-id", result={"status": "ok"})
        
        assert response.jsonrpc == "2.0"
        assert response.id == "test-id"
        assert response.result == {"status": "ok"}
        assert response.error is None
    
    def test_mcp_error_response(self):
        """Test MCP error response creation."""
        error = MCPError(code=-32603, message="Internal error")
        response = MCPResponse(id="test-id", error=error)
        
        assert response.error is not None
        assert response.error.code == -32603
        assert response.error.message == "Internal error"
        assert response.result is None
    
    def test_tool_parameter_creation(self):
        """Test tool parameter creation."""
        param = ToolParameter(
            type="string",
            description="Test parameter",
            required=True,
            enum=["option1", "option2"]
        )
        
        assert param.type == "string"
        assert param.description == "Test parameter"
        assert param.required is True
        assert param.enum == ["option1", "option2"]
    
    def test_tool_creation(self):
        """Test tool creation."""
        param = ToolParameter(type="string", required=True)
        tool = Tool(
            name="test_tool",
            description="A test tool",
            parameters={"input": param}
        )
        
        assert tool.name == "test_tool"
        assert tool.description == "A test tool"
        assert "input" in tool.parameters
        assert tool.parameters["input"].type == "string"
    
    def test_tool_result_creation(self):
        """Test tool result creation."""
        result = ToolResult(
            content=[{"type": "text", "text": "Hello, world!"}],
            is_error=False
        )
        
        assert len(result.content) == 1
        assert result.content[0]["text"] == "Hello, world!"
        assert result.is_error is False
    
    def test_initialize_params_validation(self):
        """Test initialize params validation."""
        params = InitializeParams(
            protocol_version="2024-11-05",
            capabilities={"tools": True},
            client_info={"name": "test-client", "version": "1.0.0"}
        )
        
        assert params.protocol_version == "2024-11-05"
        assert params.capabilities["tools"] is True
        assert params.client_info["name"] == "test-client"
    
    def test_call_tool_params_validation(self):
        """Test call tool params validation."""
        params = CallToolParams(
            name="test_tool",
            arguments={"input": "test value"}
        )
        
        assert params.name == "test_tool"
        assert params.arguments["input"] == "test value"
    
    def test_invalid_request_validation(self):
        """Test that invalid requests raise validation errors."""
        with pytest.raises(ValidationError):
            MCPRequest()  # Missing required method
    
    def test_request_serialization(self):
        """Test request serialization to dict."""
        request = MCPRequest(method="test", params={"key": "value"})
        data = request.model_dump()
        
        assert data["jsonrpc"] == "2.0"
        assert data["method"] == "test"
        assert data["params"] == {"key": "value"}
        assert "id" in data
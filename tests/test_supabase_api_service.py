"""Tests for Supabase API service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from supabase_mcp_server.services.supabase_api import (
    CRUDResult,
    SupabaseAPIService,
)


class TestCRUDResult:
    """Test CRUDResult class."""
    
    def test_crud_result_success(self):
        """Test successful CRUD result."""
        result = CRUDResult(
            success=True,
            data=[{"id": 1, "name": "test"}],
            count=1
        )
        
        assert result.success is True
        assert result.data == [{"id": 1, "name": "test"}]
        assert result.count == 1
        assert result.error is None
    
    def test_crud_result_error(self):
        """Test error CRUD result."""
        result = CRUDResult(
            success=False,
            error="Database error",
            status_code=400
        )
        
        assert result.success is False
        assert result.error == "Database error"
        assert result.status_code == 400
        assert result.data is None


class TestSupabaseAPIService:
    """Test SupabaseAPIService class."""
    
    @pytest.fixture
    def api_service(self, override_settings):
        """Create a Supabase API service instance."""
        return SupabaseAPIService()
    
    def test_api_service_creation(self, api_service):
        """Test API service creation."""
        assert api_service._client is None
        assert api_service._initialized is False
        assert api_service.settings is not None
    
    @patch('supabase_mcp_server.services.supabase_api.create_client')
    async def test_initialize_success(self, mock_create_client, api_service):
        """Test successful API service initialization."""
        # Mock client
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_query = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [{"table_name": "test"}]
        
        mock_query.execute.return_value = mock_response
        mock_table.select.return_value = mock_query
        mock_table.limit.return_value = mock_query
        mock_client.table.return_value = mock_table
        mock_create_client.return_value = mock_client
        
        await api_service.initialize()
        
        assert api_service._client is not None
        assert api_service._initialized is True
        mock_create_client.assert_called_once()
    
    @patch('supabase_mcp_server.services.supabase_api.create_client')
    async def test_initialize_failure(self, mock_create_client, api_service):
        """Test API service initialization failure."""
        mock_create_client.side_effect = Exception("Connection failed")
        
        with pytest.raises(Exception, match="Failed to initialize Supabase API"):
            await api_service.initialize()
        
        assert api_service._initialized is False
    
    async def test_select_not_initialized(self, api_service):
        """Test select operation without initialization."""
        result = await api_service.select("users")
        
        assert result.success is False
        assert "not initialized" in result.error
    
    @patch('supabase_mcp_server.services.supabase_api.create_client')
    async def test_select_success(self, mock_create_client, api_service):
        """Test successful select operation."""
        # Setup mocks
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_query = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [{"id": 1, "name": "John"}, {"id": 2, "name": "Jane"}]
        
        # Chain method calls
        mock_query.execute.return_value = mock_response
        mock_query.eq.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_table.select.return_value = mock_query
        mock_table.limit.return_value = mock_query  # For connection test
        mock_client.table.return_value = mock_table
        mock_create_client.return_value = mock_client
        
        # Initialize
        await api_service.initialize()
        
        # Test select
        result = await api_service.select(
            table="users",
            columns="id,name",
            filters={"active": True},
            order_by="name",
            limit=10,
            offset=0
        )
        
        assert result.success is True
        assert len(result.data) == 2
        assert result.count == 2
        assert result.data[0]["name"] == "John"
    
    @patch('supabase_mcp_server.services.supabase_api.create_client')
    async def test_insert_success(self, mock_create_client, api_service):
        """Test successful insert operation."""
        # Setup mocks
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_query = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [{"id": 1, "name": "John"}]
        
        mock_query.execute.return_value = mock_response
        mock_query.on_conflict.return_value = mock_query
        mock_table.insert.return_value = mock_query
        mock_table.select.return_value = mock_query  # For connection test
        mock_table.limit.return_value = mock_query   # For connection test
        mock_client.table.return_value = mock_table
        mock_create_client.return_value = mock_client
        
        # Initialize
        await api_service.initialize()
        
        # Test insert
        result = await api_service.insert(
            table="users",
            data={"name": "John", "email": "john@example.com"},
            on_conflict="email"
        )
        
        assert result.success is True
        assert result.count == 1
        assert result.data[0]["name"] == "John"
    
    @patch('supabase_mcp_server.services.supabase_api.create_client')
    async def test_update_success(self, mock_create_client, api_service):
        """Test successful update operation."""
        # Setup mocks
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_query = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [{"id": 1, "name": "John Updated"}]
        
        mock_query.execute.return_value = mock_response
        mock_query.eq.return_value = mock_query
        mock_table.update.return_value = mock_query
        mock_table.select.return_value = mock_query  # For connection test
        mock_table.limit.return_value = mock_query   # For connection test
        mock_client.table.return_value = mock_table
        mock_create_client.return_value = mock_client
        
        # Initialize
        await api_service.initialize()
        
        # Test update
        result = await api_service.update(
            table="users",
            data={"name": "John Updated"},
            filters={"id": 1}
        )
        
        assert result.success is True
        assert result.count == 1
        assert result.data[0]["name"] == "John Updated"
    
    async def test_update_without_filters(self, api_service):
        """Test update operation without filters."""
        api_service._client = MagicMock()  # Mock client to pass initialization check
        
        result = await api_service.update(
            table="users",
            data={"name": "John"},
            filters={}
        )
        
        assert result.success is False
        assert "Filters are required" in result.error
    
    @patch('supabase_mcp_server.services.supabase_api.create_client')
    async def test_delete_success(self, mock_create_client, api_service):
        """Test successful delete operation."""
        # Setup mocks
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_query = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [{"id": 1}]
        
        mock_query.execute.return_value = mock_response
        mock_query.eq.return_value = mock_query
        mock_table.delete.return_value = mock_query
        mock_table.select.return_value = mock_query  # For connection test
        mock_table.limit.return_value = mock_query   # For connection test
        mock_client.table.return_value = mock_table
        mock_create_client.return_value = mock_client
        
        # Initialize
        await api_service.initialize()
        
        # Test delete
        result = await api_service.delete(
            table="users",
            filters={"id": 1}
        )
        
        assert result.success is True
        assert result.count == 1
    
    async def test_delete_without_filters(self, api_service):
        """Test delete operation without filters."""
        api_service._client = MagicMock()  # Mock client to pass initialization check
        
        result = await api_service.delete(
            table="users",
            filters={}
        )
        
        assert result.success is False
        assert "Filters are required" in result.error
    
    @patch('supabase_mcp_server.services.supabase_api.create_client')
    async def test_upsert_success(self, mock_create_client, api_service):
        """Test successful upsert operation."""
        # Setup mocks
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_query = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [{"id": 1, "name": "John"}]
        
        mock_query.execute.return_value = mock_response
        mock_query.on_conflict.return_value = mock_query
        mock_table.upsert.return_value = mock_query
        mock_table.select.return_value = mock_query  # For connection test
        mock_table.limit.return_value = mock_query   # For connection test
        mock_client.table.return_value = mock_table
        mock_create_client.return_value = mock_client
        
        # Initialize
        await api_service.initialize()
        
        # Test upsert
        result = await api_service.upsert(
            table="users",
            data={"id": 1, "name": "John", "email": "john@example.com"},
            on_conflict="id"
        )
        
        assert result.success is True
        assert result.count == 1
        assert result.data[0]["name"] == "John"
    
    @patch('supabase_mcp_server.services.supabase_api.create_client')
    async def test_call_rpc_success(self, mock_create_client, api_service):
        """Test successful RPC call."""
        # Setup mocks
        mock_client = MagicMock()
        mock_rpc = MagicMock()
        mock_response = MagicMock()
        mock_response.data = {"result": "success"}
        
        mock_rpc.execute.return_value = mock_response
        mock_client.rpc.return_value = mock_rpc
        mock_client.table.return_value.select.return_value.limit.return_value.execute.return_value.data = []
        mock_create_client.return_value = mock_client
        
        # Initialize
        await api_service.initialize()
        
        # Test RPC call
        result = await api_service.call_rpc(
            function_name="get_user_stats",
            params={"user_id": 1}
        )
        
        assert result.success is True
        assert result.data == {"result": "success"}
    
    def test_apply_filter_operators(self, api_service):
        """Test filter operator application."""
        mock_query = MagicMock()
        
        # Test various operators
        operators_to_test = [
            ("eq", "value"),
            ("neq", "value"),
            ("gt", 10),
            ("gte", 10),
            ("lt", 10),
            ("lte", 10),
            ("like", "%pattern%"),
            ("ilike", "%pattern%"),
            ("is", None),
            ("in", [1, 2, 3]),
        ]
        
        for operator, value in operators_to_test:
            result_query = api_service._apply_filter(mock_query, "column", operator, value)
            assert result_query is not None
    
    def test_apply_unknown_filter_operator(self, api_service):
        """Test unknown filter operator fallback."""
        mock_query = MagicMock()
        
        result_query = api_service._apply_filter(mock_query, "column", "unknown_op", "value")
        
        # Should fallback to eq
        mock_query.eq.assert_called_once_with("column", "value")
    
    def test_get_client(self, api_service):
        """Test getting client instance."""
        assert api_service.get_client() is None
        
        # Set a mock client
        mock_client = MagicMock()
        api_service._client = mock_client
        
        assert api_service.get_client() == mock_client
    
    def test_is_initialized(self, api_service):
        """Test initialization status check."""
        assert api_service.is_initialized() is False
        
        api_service._initialized = True
        assert api_service.is_initialized() is True
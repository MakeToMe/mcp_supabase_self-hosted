"""Tests for database service."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import asyncpg

from supabase_mcp_server.services.database import (
    DatabaseError,
    DatabaseService,
    QueryResult,
)


class TestQueryResult:
    """Test QueryResult class."""
    
    def test_query_result_creation(self):
        """Test QueryResult creation."""
        result = QueryResult(
            rows=[{"id": 1, "name": "test"}],
            row_count=1,
            execution_time=0.5,
            columns=["id", "name"]
        )
        
        assert result.rows == [{"id": 1, "name": "test"}]
        assert result.row_count == 1
        assert result.execution_time == 0.5
        assert result.columns == ["id", "name"]
    
    def test_query_result_to_dict(self):
        """Test QueryResult to_dict method."""
        result = QueryResult(
            rows=[{"id": 1}],
            row_count=1,
            execution_time=0.1
        )
        
        data = result.to_dict()
        
        assert data["rows"] == [{"id": 1}]
        assert data["row_count"] == 1
        assert data["execution_time"] == 0.1
        assert data["columns"] == []


class TestDatabaseService:
    """Test DatabaseService class."""
    
    @pytest.fixture
    def db_service(self, override_settings):
        """Create a database service instance."""
        return DatabaseService()
    
    def test_database_service_creation(self, db_service):
        """Test database service creation."""
        assert db_service._pool is None
        assert db_service.settings is not None
    
    @patch('asyncpg.create_pool')
    async def test_initialize_success(self, mock_create_pool, db_service):
        """Test successful database initialization."""
        # Mock pool
        mock_pool = AsyncMock()
        mock_create_pool.return_value = mock_pool
        
        # Mock connection for test
        mock_connection = AsyncMock()
        mock_connection.fetchval.return_value = 1
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        
        await db_service.initialize()
        
        assert db_service._pool is not None
        mock_create_pool.assert_called_once()
        
        # Cleanup
        await db_service.close()
    
    @patch('asyncpg.create_pool')
    async def test_initialize_failure(self, mock_create_pool, db_service):
        """Test database initialization failure."""
        mock_create_pool.side_effect = Exception("Connection failed")
        
        with pytest.raises(DatabaseError, match="Failed to initialize database"):
            await db_service.initialize()
    
    async def test_execute_query_without_initialization(self, db_service):
        """Test executing query without initialization."""
        with pytest.raises(DatabaseError, match="Database not initialized"):
            await db_service.execute_query("SELECT 1")
    
    @patch('asyncpg.create_pool')
    async def test_execute_query_success(self, mock_create_pool, db_service):
        """Test successful query execution."""
        # Setup mocks
        mock_pool = AsyncMock()
        mock_create_pool.return_value = mock_pool
        
        mock_connection = AsyncMock()
        mock_record = MagicMock()
        mock_record.keys.return_value = ["id", "name"]
        mock_record.__getitem__ = lambda self, key: {"id": 1, "name": "test"}[key]
        mock_record.__iter__ = lambda self: iter([("id", 1), ("name", "test")])
        
        mock_connection.fetch.return_value = [mock_record]
        mock_connection.fetchval.return_value = 1  # For health check
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        
        # Initialize and execute query
        await db_service.initialize()
        
        # Mock dict conversion
        with patch('builtins.dict', return_value={"id": 1, "name": "test"}):
            result = await db_service.execute_query("SELECT * FROM users")
        
        assert isinstance(result, QueryResult)
        assert result.row_count == 1
        assert result.execution_time > 0
        
        # Cleanup
        await db_service.close()
    
    @patch('asyncpg.create_pool')
    async def test_execute_query_postgres_error(self, mock_create_pool, db_service):
        """Test query execution with PostgreSQL error."""
        # Setup mocks
        mock_pool = AsyncMock()
        mock_create_pool.return_value = mock_pool
        
        mock_connection = AsyncMock()
        mock_connection.fetch.side_effect = asyncpg.PostgresError("Syntax error")
        mock_connection.fetchval.return_value = 1  # For health check
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        
        # Initialize
        await db_service.initialize()
        
        # Execute query and expect error
        with pytest.raises(DatabaseError, match="PostgreSQL error"):
            await db_service.execute_query("INVALID SQL")
        
        # Cleanup
        await db_service.close()
    
    @patch('asyncpg.create_pool')
    async def test_execute_transaction(self, mock_create_pool, db_service):
        """Test transaction execution."""
        # Setup mocks
        mock_pool = AsyncMock()
        mock_create_pool.return_value = mock_pool
        
        mock_connection = AsyncMock()
        mock_transaction = AsyncMock()
        mock_connection.transaction.return_value = mock_transaction
        mock_connection.fetch.return_value = []
        mock_connection.fetchval.return_value = 1  # For health check
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        
        # Initialize
        await db_service.initialize()
        
        # Execute transaction
        queries = [
            ("INSERT INTO users (name) VALUES ($1)", ["test"]),
            ("UPDATE users SET name = $1 WHERE id = $2", ["updated", 1])
        ]
        
        results = await db_service.execute_transaction(queries)
        
        assert len(results) == 2
        assert all(isinstance(result, QueryResult) for result in results)
        
        # Cleanup
        await db_service.close()
    
    @patch('asyncpg.create_pool')
    async def test_get_connection_info(self, mock_create_pool, db_service):
        """Test getting connection info."""
        # Setup mocks
        mock_pool = AsyncMock()
        mock_pool.get_size.return_value = 5
        mock_pool.get_max_size.return_value = 10
        mock_pool.get_min_size.return_value = 1
        mock_create_pool.return_value = mock_pool
        
        mock_connection = AsyncMock()
        mock_connection.fetchrow.side_effect = [
            {"version": "PostgreSQL 14.0"},
            {"size": "100 MB"}
        ]
        mock_connection.fetchval.return_value = 1  # For health check
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        
        # Initialize
        await db_service.initialize()
        
        # Get connection info
        info = await db_service.get_connection_info()
        
        assert info["status"] == "connected"
        assert info["pool_size"] == 5
        assert info["pool_max_size"] == 10
        assert info["version"] == "PostgreSQL 14.0"
        assert info["database_size"] == "100 MB"
        
        # Cleanup
        await db_service.close()
    
    def test_get_connection_info_not_initialized(self, db_service):
        """Test getting connection info when not initialized."""
        info = asyncio.run(db_service.get_connection_info())
        assert info["status"] == "not_initialized"
    
    @patch('asyncpg.create_pool')
    async def test_health_check(self, mock_create_pool, db_service):
        """Test health check."""
        # Setup mocks
        mock_pool = AsyncMock()
        mock_create_pool.return_value = mock_pool
        
        mock_connection = AsyncMock()
        mock_connection.fetchval.return_value = 1
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        
        # Initialize
        await db_service.initialize()
        
        # Health check should pass
        is_healthy = await db_service.health_check()
        assert is_healthy is True
        
        # Cleanup
        await db_service.close()
    
    def test_health_check_not_initialized(self, db_service):
        """Test health check when not initialized."""
        is_healthy = asyncio.run(db_service.health_check())
        assert is_healthy is False
    
    def test_parse_row_count(self, db_service):
        """Test parsing row count from result strings."""
        assert db_service._parse_row_count("INSERT 0 5") == 5
        assert db_service._parse_row_count("UPDATE 3") == 3
        assert db_service._parse_row_count("DELETE 2") == 2
        assert db_service._parse_row_count("SELECT 10") == 10
        assert db_service._parse_row_count("INVALID") == 0
        assert db_service._parse_row_count("") == 0
    
    @patch('asyncpg.create_pool')
    async def test_close(self, mock_create_pool, db_service):
        """Test closing database service."""
        # Setup mocks
        mock_pool = AsyncMock()
        mock_create_pool.return_value = mock_pool
        
        mock_connection = AsyncMock()
        mock_connection.fetchval.return_value = 1
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        
        # Initialize
        await db_service.initialize()
        assert db_service._pool is not None
        
        # Close
        await db_service.close()
        assert db_service._pool is None
        mock_pool.close.assert_called_once()


class TestDatabaseError:
    """Test DatabaseError exception."""
    
    def test_database_error_creation(self):
        """Test DatabaseError creation."""
        original_error = Exception("Original error")
        db_error = DatabaseError("Database failed", original_error)
        
        assert str(db_error) == "Database failed"
        assert db_error.original_error == original_error
    
    def test_database_error_without_original(self):
        """Test DatabaseError without original error."""
        db_error = DatabaseError("Database failed")
        
        assert str(db_error) == "Database failed"
        assert db_error.original_error is None
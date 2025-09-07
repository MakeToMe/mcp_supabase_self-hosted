"""Tests for schema discovery service."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from supabase_mcp_server.services.schema import (
    ColumnInfo,
    ForeignKeyInfo,
    IndexInfo,
    SchemaInfo,
    SchemaService,
    TableInfo,
)


class TestSchemaModels:
    """Test schema data models."""
    
    def test_column_info_creation(self):
        """Test ColumnInfo creation."""
        column = ColumnInfo(
            name="id",
            data_type="integer",
            is_nullable=False,
            is_primary_key=True
        )
        
        assert column.name == "id"
        assert column.data_type == "integer"
        assert column.is_nullable is False
        assert column.is_primary_key is True
        assert column.is_foreign_key is False
    
    def test_table_info_creation(self):
        """Test TableInfo creation."""
        column = ColumnInfo(name="id", data_type="integer", is_nullable=False)
        index = IndexInfo(name="pk_test", columns=["id"], is_unique=True, is_primary=True, index_type="btree")
        
        table = TableInfo(
            name="test_table",
            schema="public",
            table_type="BASE TABLE",
            columns=[column],
            indexes=[index],
            foreign_keys=[]
        )
        
        assert table.name == "test_table"
        assert table.schema == "public"
        assert len(table.columns) == 1
        assert len(table.indexes) == 1
        assert len(table.foreign_keys) == 0
    
    def test_schema_info_creation(self):
        """Test SchemaInfo creation."""
        table = TableInfo(
            name="test",
            schema="public",
            table_type="BASE TABLE",
            columns=[],
            indexes=[],
            foreign_keys=[]
        )
        
        schema = SchemaInfo(
            tables=[table],
            total_tables=1,
            total_views=0,
            total_materialized_views=0
        )
        
        assert len(schema.tables) == 1
        assert schema.total_tables == 1
        assert schema.total_views == 0


class TestSchemaService:
    """Test SchemaService class."""
    
    @pytest.fixture
    def schema_service(self):
        """Create a schema service instance."""
        return SchemaService(cache_ttl_minutes=1)
    
    def test_schema_service_creation(self, schema_service):
        """Test schema service creation."""
        assert schema_service._cache == {}
        assert schema_service._cache_timestamps == {}
        assert schema_service._cache_ttl.total_seconds() == 60
    
    @patch('supabase_mcp_server.services.schema.database_service')
    async def test_get_schema_info_all_tables(self, mock_db_service, schema_service):
        """Test getting schema info for all tables."""
        # Mock database responses
        mock_db_service.execute_query.side_effect = [
            # Tables query
            AsyncMock(rows=[
                {"table_name": "users", "table_schema": "public", "table_type": "BASE TABLE"},
                {"table_name": "posts", "table_schema": "public", "table_type": "BASE TABLE"}
            ]),
            # Columns query for users
            AsyncMock(rows=[
                {
                    "column_name": "id",
                    "data_type": "integer",
                    "is_nullable": "NO",
                    "column_default": "nextval('users_id_seq'::regclass)",
                    "character_maximum_length": None,
                    "is_primary_key": True,
                    "is_foreign_key": False,
                    "foreign_table_name": None,
                    "foreign_column_name": None,
                    "description": None
                }
            ]),
            # Indexes query for users
            AsyncMock(rows=[
                {
                    "index_name": "users_pkey",
                    "columns": ["id"],
                    "is_unique": True,
                    "is_primary": True,
                    "index_type": "btree"
                }
            ]),
            # Foreign keys query for users
            AsyncMock(rows=[]),
            # Table size query for users
            AsyncMock(rows=[{"size": "8192 bytes"}]),
            # Table comment query for users
            AsyncMock(rows=[{"description": None}]),
            # Columns query for posts
            AsyncMock(rows=[
                {
                    "column_name": "id",
                    "data_type": "integer",
                    "is_nullable": "NO",
                    "column_default": None,
                    "character_maximum_length": None,
                    "is_primary_key": True,
                    "is_foreign_key": False,
                    "foreign_table_name": None,
                    "foreign_column_name": None,
                    "description": None
                }
            ]),
            # Indexes query for posts
            AsyncMock(rows=[]),
            # Foreign keys query for posts
            AsyncMock(rows=[]),
            # Table size query for posts
            AsyncMock(rows=[{"size": "4096 bytes"}]),
            # Table comment query for posts
            AsyncMock(rows=[{"description": None}]),
            # Database size query
            AsyncMock(rows=[{"size": "50 MB"}])
        ]
        
        result = await schema_service.get_schema_info()
        
        assert isinstance(result, SchemaInfo)
        assert len(result.tables) == 2
        assert result.total_tables == 2
        assert result.total_views == 0
        assert result.database_size == "50 MB"
        
        # Check first table
        users_table = result.tables[0]
        assert users_table.name == "users"
        assert users_table.schema == "public"
        assert users_table.table_type == "BASE TABLE"
        assert len(users_table.columns) == 1
        assert users_table.columns[0].name == "id"
        assert users_table.columns[0].is_primary_key is True
    
    @patch('supabase_mcp_server.services.schema.database_service')
    async def test_get_schema_info_specific_table(self, mock_db_service, schema_service):
        """Test getting schema info for a specific table."""
        # Mock database responses
        mock_db_service.execute_query.side_effect = [
            # Tables query
            AsyncMock(rows=[
                {"table_name": "users", "table_schema": "public", "table_type": "BASE TABLE"}
            ]),
            # Columns query
            AsyncMock(rows=[
                {
                    "column_name": "id",
                    "data_type": "integer",
                    "is_nullable": "NO",
                    "column_default": None,
                    "character_maximum_length": None,
                    "is_primary_key": True,
                    "is_foreign_key": False,
                    "foreign_table_name": None,
                    "foreign_column_name": None,
                    "description": "User ID"
                }
            ]),
            # Indexes query
            AsyncMock(rows=[]),
            # Foreign keys query
            AsyncMock(rows=[]),
            # Table size query
            AsyncMock(rows=[{"size": "8192 bytes"}]),
            # Table comment query
            AsyncMock(rows=[{"description": "Users table"}]),
            # Database size query
            AsyncMock(rows=[{"size": "50 MB"}])
        ]
        
        result = await schema_service.get_schema_info(table_name="users")
        
        assert isinstance(result, SchemaInfo)
        assert len(result.tables) == 1
        assert result.tables[0].name == "users"
        assert result.tables[0].description == "Users table"
        assert result.tables[0].columns[0].description == "User ID"
    
    @patch('supabase_mcp_server.services.schema.database_service')
    async def test_get_table_columns(self, mock_db_service, schema_service):
        """Test getting table columns."""
        mock_db_service.execute_query.return_value = AsyncMock(rows=[
            {
                "column_name": "id",
                "data_type": "integer",
                "is_nullable": "NO",
                "column_default": None,
                "character_maximum_length": None,
                "is_primary_key": True,
                "is_foreign_key": False,
                "foreign_table_name": None,
                "foreign_column_name": None,
                "description": None
            },
            {
                "column_name": "name",
                "data_type": "character varying",
                "is_nullable": "YES",
                "column_default": None,
                "character_maximum_length": 255,
                "is_primary_key": False,
                "is_foreign_key": False,
                "foreign_table_name": None,
                "foreign_column_name": None,
                "description": None
            }
        ])
        
        columns = await schema_service.get_table_columns("users")
        
        assert len(columns) == 2
        assert columns[0].name == "id"
        assert columns[0].is_primary_key is True
        assert columns[1].name == "name"
        assert columns[1].max_length == 255
    
    @patch('supabase_mcp_server.services.schema.database_service')
    async def test_get_table_relationships(self, mock_db_service, schema_service):
        """Test getting table relationships."""
        mock_db_service.execute_query.side_effect = [
            # Outgoing foreign keys
            AsyncMock(rows=[
                {
                    "constraint_name": "fk_user_profile",
                    "column_name": "user_id",
                    "foreign_table_name": "users",
                    "foreign_column_name": "id",
                    "delete_rule": "CASCADE",
                    "update_rule": "NO ACTION"
                }
            ]),
            # Incoming foreign keys
            AsyncMock(rows=[
                {
                    "referencing_table": "posts",
                    "referencing_schema": "public",
                    "referencing_column": "author_id",
                    "referenced_column": "id",
                    "constraint_name": "fk_post_author"
                }
            ])
        ]
        
        relationships = await schema_service.get_table_relationships("profiles")
        
        assert "outgoing_foreign_keys" in relationships
        assert "incoming_foreign_keys" in relationships
        assert len(relationships["outgoing_foreign_keys"]) == 1
        assert len(relationships["incoming_foreign_keys"]) == 1
        
        outgoing = relationships["outgoing_foreign_keys"][0]
        assert outgoing["column_name"] == "user_id"
        assert outgoing["foreign_table_name"] == "users"
        
        incoming = relationships["incoming_foreign_keys"][0]
        assert incoming["referencing_table"] == "posts"
        assert incoming["referencing_column"] == "author_id"
    
    @patch('supabase_mcp_server.services.schema.database_service')
    async def test_search_tables(self, mock_db_service, schema_service):
        """Test searching tables and columns."""
        mock_db_service.execute_query.side_effect = [
            # Table search results
            AsyncMock(rows=[
                {"table_name": "users", "table_schema": "public", "table_type": "BASE TABLE"}
            ]),
            # Column search results
            AsyncMock(rows=[
                {
                    "table_name": "profiles",
                    "table_schema": "public",
                    "column_name": "user_id",
                    "data_type": "integer"
                }
            ])
        ]
        
        results = await schema_service.search_tables("user")
        
        assert len(results) == 2
        
        # Check table result
        table_result = results[0]
        assert table_result["type"] == "table"
        assert table_result["name"] == "users"
        assert table_result["match_type"] == "table_name"
        
        # Check column result
        column_result = results[1]
        assert column_result["type"] == "column"
        assert column_result["table_name"] == "profiles"
        assert column_result["column_name"] == "user_id"
        assert column_result["match_type"] == "column_name"
    
    async def test_cache_functionality(self, schema_service):
        """Test caching functionality."""
        # Test setting and getting from cache
        test_data = {"test": "data"}
        await schema_service._set_cache("test_key", test_data)
        
        cached_data = await schema_service._get_from_cache("test_key")
        assert cached_data == test_data
        
        # Test cache miss
        missing_data = await schema_service._get_from_cache("missing_key")
        assert missing_data is None
        
        # Test cache clear
        await schema_service.clear_cache()
        cleared_data = await schema_service._get_from_cache("test_key")
        assert cleared_data is None
"""Schema discovery service for PostgreSQL."""

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from supabase_mcp_server.core.logging import get_logger
from supabase_mcp_server.services.database import database_service, DatabaseError

logger = get_logger(__name__)


@dataclass
class ColumnInfo:
    """Information about a database column."""
    name: str
    data_type: str
    is_nullable: bool
    default_value: Optional[str] = None
    max_length: Optional[int] = None
    is_primary_key: bool = False
    is_foreign_key: bool = False
    foreign_table: Optional[str] = None
    foreign_column: Optional[str] = None
    description: Optional[str] = None


@dataclass
class IndexInfo:
    """Information about a database index."""
    name: str
    columns: List[str]
    is_unique: bool
    is_primary: bool
    index_type: str


@dataclass
class ForeignKeyInfo:
    """Information about a foreign key constraint."""
    name: str
    column: str
    foreign_table: str
    foreign_column: str
    on_delete: str
    on_update: str


@dataclass
class TableInfo:
    """Information about a database table."""
    name: str
    schema: str
    table_type: str  # 'table', 'view', 'materialized_view'
    columns: List[ColumnInfo]
    indexes: List[IndexInfo]
    foreign_keys: List[ForeignKeyInfo]
    row_count: Optional[int] = None
    size: Optional[str] = None
    description: Optional[str] = None


@dataclass
class SchemaInfo:
    """Complete schema information."""
    tables: List[TableInfo]
    total_tables: int
    total_views: int
    total_materialized_views: int
    database_size: Optional[str] = None
    last_updated: datetime = None


class SchemaService:
    """Service for database schema discovery and caching."""
    
    def __init__(self, cache_ttl_minutes: int = 5):
        """Initialize the schema service."""
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._cache_ttl = timedelta(minutes=cache_ttl_minutes)
        self._cache_lock = asyncio.Lock()
    
    async def get_schema_info(
        self,
        table_name: Optional[str] = None,
        schema_name: str = "public",
        include_system_tables: bool = False,
        include_row_counts: bool = False
    ) -> SchemaInfo:
        """Get comprehensive schema information."""
        cache_key = f"schema_{schema_name}_{table_name}_{include_system_tables}_{include_row_counts}"
        
        # Check cache first
        cached_result = await self._get_from_cache(cache_key)
        if cached_result:
            logger.debug("Returning cached schema info", cache_key=cache_key)
            return cached_result
        
        try:
            logger.info("Discovering database schema", table_name=table_name, schema_name=schema_name)
            
            # Get tables
            tables = await self._get_tables(table_name, schema_name, include_system_tables)
            
            # Get detailed information for each table
            table_infos = []
            for table in tables:
                table_info = await self._get_table_info(
                    table["table_name"],
                    table["table_schema"],
                    table["table_type"],
                    include_row_counts
                )
                table_infos.append(table_info)
            
            # Get database size
            db_size = await self._get_database_size()
            
            # Create schema info
            schema_info = SchemaInfo(
                tables=table_infos,
                total_tables=len([t for t in table_infos if t.table_type == "BASE TABLE"]),
                total_views=len([t for t in table_infos if t.table_type == "VIEW"]),
                total_materialized_views=len([t for t in table_infos if t.table_type == "MATERIALIZED VIEW"]),
                database_size=db_size,
                last_updated=datetime.now()
            )
            
            # Cache the result
            await self._set_cache(cache_key, schema_info)
            
            logger.info(
                "Schema discovery completed",
                total_tables=schema_info.total_tables,
                total_views=schema_info.total_views,
                table_count=len(table_infos)
            )
            
            return schema_info
            
        except Exception as e:
            logger.error("Schema discovery failed", error=str(e))
            raise DatabaseError(f"Schema discovery failed: {str(e)}", e)
    
    async def get_table_columns(
        self,
        table_name: str,
        schema_name: str = "public"
    ) -> List[ColumnInfo]:
        """Get detailed column information for a specific table."""
        cache_key = f"columns_{schema_name}_{table_name}"
        
        cached_result = await self._get_from_cache(cache_key)
        if cached_result:
            return cached_result
        
        try:
            columns = await self._get_columns(table_name, schema_name)
            await self._set_cache(cache_key, columns)
            return columns
            
        except Exception as e:
            logger.error("Failed to get table columns", table=table_name, error=str(e))
            raise DatabaseError(f"Failed to get columns for {table_name}: {str(e)}", e)
    
    async def get_table_relationships(
        self,
        table_name: str,
        schema_name: str = "public"
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get table relationships (foreign keys in and out)."""
        try:
            # Foreign keys from this table to others
            outgoing_fks = await self._get_foreign_keys(table_name, schema_name)
            
            # Foreign keys from other tables to this table
            incoming_fks = await self._get_incoming_foreign_keys(table_name, schema_name)
            
            return {
                "outgoing_foreign_keys": outgoing_fks,
                "incoming_foreign_keys": incoming_fks
            }
            
        except Exception as e:
            logger.error("Failed to get table relationships", table=table_name, error=str(e))
            raise DatabaseError(f"Failed to get relationships for {table_name}: {str(e)}", e)
    
    async def search_tables(
        self,
        search_term: str,
        schema_name: str = "public",
        search_columns: bool = True
    ) -> List[Dict[str, Any]]:
        """Search for tables and columns matching a term."""
        try:
            results = []
            
            # Search table names
            table_query = """
                SELECT table_name, table_schema, table_type
                FROM information_schema.tables
                WHERE table_schema = $1
                AND table_name ILIKE $2
                ORDER BY table_name
            """
            
            table_result = await database_service.execute_query(
                table_query,
                [schema_name, f"%{search_term}%"]
            )
            
            for row in table_result.rows:
                results.append({
                    "type": "table",
                    "name": row["table_name"],
                    "schema": row["table_schema"],
                    "table_type": row["table_type"],
                    "match_type": "table_name"
                })
            
            # Search column names if requested
            if search_columns:
                column_query = """
                    SELECT table_name, table_schema, column_name, data_type
                    FROM information_schema.columns
                    WHERE table_schema = $1
                    AND column_name ILIKE $2
                    ORDER BY table_name, column_name
                """
                
                column_result = await database_service.execute_query(
                    column_query,
                    [schema_name, f"%{search_term}%"]
                )
                
                for row in column_result.rows:
                    results.append({
                        "type": "column",
                        "table_name": row["table_name"],
                        "schema": row["table_schema"],
                        "column_name": row["column_name"],
                        "data_type": row["data_type"],
                        "match_type": "column_name"
                    })
            
            return results
            
        except Exception as e:
            logger.error("Table search failed", search_term=search_term, error=str(e))
            raise DatabaseError(f"Table search failed: {str(e)}", e)
    
    async def _get_tables(
        self,
        table_name: Optional[str],
        schema_name: str,
        include_system_tables: bool
    ) -> List[Dict[str, Any]]:
        """Get list of tables from information_schema."""
        query = """
            SELECT table_name, table_schema, table_type
            FROM information_schema.tables
            WHERE table_schema = $1
        """
        params = [schema_name]
        
        if table_name:
            query += " AND table_name = $2"
            params.append(table_name)
        
        if not include_system_tables:
            query += " AND table_type IN ('BASE TABLE', 'VIEW', 'MATERIALIZED VIEW')"
        
        query += " ORDER BY table_name"
        
        result = await database_service.execute_query(query, params)
        return result.rows
    
    async def _get_table_info(
        self,
        table_name: str,
        schema_name: str,
        table_type: str,
        include_row_count: bool
    ) -> TableInfo:
        """Get detailed information about a specific table."""
        # Get columns
        columns = await self._get_columns(table_name, schema_name)
        
        # Get indexes
        indexes = await self._get_indexes(table_name, schema_name)
        
        # Get foreign keys
        foreign_keys = await self._get_foreign_keys(table_name, schema_name)
        
        # Get row count if requested
        row_count = None
        if include_row_count and table_type == "BASE TABLE":
            try:
                count_result = await database_service.execute_query(
                    f'SELECT COUNT(*) as count FROM "{schema_name}"."{table_name}"'
                )
                row_count = count_result.rows[0]["count"] if count_result.rows else None
            except Exception:
                # Ignore errors for row count (might be permissions issue)
                pass
        
        # Get table size
        size = await self._get_table_size(table_name, schema_name)
        
        # Get table comment
        description = await self._get_table_comment(table_name, schema_name)
        
        return TableInfo(
            name=table_name,
            schema=schema_name,
            table_type=table_type,
            columns=columns,
            indexes=indexes,
            foreign_keys=foreign_keys,
            row_count=row_count,
            size=size,
            description=description
        )
    
    async def _get_columns(self, table_name: str, schema_name: str) -> List[ColumnInfo]:
        """Get column information for a table."""
        query = """
            SELECT 
                c.column_name,
                c.data_type,
                c.is_nullable,
                c.column_default,
                c.character_maximum_length,
                CASE WHEN pk.column_name IS NOT NULL THEN true ELSE false END as is_primary_key,
                CASE WHEN fk.column_name IS NOT NULL THEN true ELSE false END as is_foreign_key,
                fk.foreign_table_name,
                fk.foreign_column_name,
                col_description(pgc.oid, c.ordinal_position) as description
            FROM information_schema.columns c
            LEFT JOIN (
                SELECT ku.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage ku
                    ON tc.constraint_name = ku.constraint_name
                WHERE tc.table_name = $1 
                AND tc.table_schema = $2
                AND tc.constraint_type = 'PRIMARY KEY'
            ) pk ON c.column_name = pk.column_name
            LEFT JOIN (
                SELECT 
                    ku.column_name,
                    ccu.table_name as foreign_table_name,
                    ccu.column_name as foreign_column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage ku
                    ON tc.constraint_name = ku.constraint_name
                JOIN information_schema.constraint_column_usage ccu
                    ON tc.constraint_name = ccu.constraint_name
                WHERE tc.table_name = $1 
                AND tc.table_schema = $2
                AND tc.constraint_type = 'FOREIGN KEY'
            ) fk ON c.column_name = fk.column_name
            LEFT JOIN pg_class pgc ON pgc.relname = c.table_name
            LEFT JOIN pg_namespace pgn ON pgn.oid = pgc.relnamespace AND pgn.nspname = c.table_schema
            WHERE c.table_name = $1 
            AND c.table_schema = $2
            ORDER BY c.ordinal_position
        """
        
        result = await database_service.execute_query(query, [table_name, schema_name])
        
        columns = []
        for row in result.rows:
            columns.append(ColumnInfo(
                name=row["column_name"],
                data_type=row["data_type"],
                is_nullable=row["is_nullable"] == "YES",
                default_value=row["column_default"],
                max_length=row["character_maximum_length"],
                is_primary_key=row["is_primary_key"],
                is_foreign_key=row["is_foreign_key"],
                foreign_table=row["foreign_table_name"],
                foreign_column=row["foreign_column_name"],
                description=row["description"]
            ))
        
        return columns
    
    async def _get_indexes(self, table_name: str, schema_name: str) -> List[IndexInfo]:
        """Get index information for a table."""
        query = """
            SELECT 
                i.relname as index_name,
                array_agg(a.attname ORDER BY c.ordinality) as columns,
                ix.indisunique as is_unique,
                ix.indisprimary as is_primary,
                am.amname as index_type
            FROM pg_class t
            JOIN pg_namespace n ON n.oid = t.relnamespace
            JOIN pg_index ix ON t.oid = ix.indrelid
            JOIN pg_class i ON i.oid = ix.indexrelid
            JOIN pg_am am ON i.relam = am.oid
            JOIN unnest(ix.indkey) WITH ORDINALITY AS c(attnum, ordinality) ON true
            JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = c.attnum
            WHERE t.relname = $1 
            AND n.nspname = $2
            GROUP BY i.relname, ix.indisunique, ix.indisprimary, am.amname
            ORDER BY i.relname
        """
        
        result = await database_service.execute_query(query, [table_name, schema_name])
        
        indexes = []
        for row in result.rows:
            indexes.append(IndexInfo(
                name=row["index_name"],
                columns=row["columns"],
                is_unique=row["is_unique"],
                is_primary=row["is_primary"],
                index_type=row["index_type"]
            ))
        
        return indexes
    
    async def _get_foreign_keys(self, table_name: str, schema_name: str) -> List[ForeignKeyInfo]:
        """Get foreign key constraints for a table."""
        query = """
            SELECT 
                tc.constraint_name,
                kcu.column_name,
                ccu.table_name as foreign_table_name,
                ccu.column_name as foreign_column_name,
                rc.delete_rule,
                rc.update_rule
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage ccu
                ON tc.constraint_name = ccu.constraint_name
            JOIN information_schema.referential_constraints rc
                ON tc.constraint_name = rc.constraint_name
            WHERE tc.table_name = $1 
            AND tc.table_schema = $2
            AND tc.constraint_type = 'FOREIGN KEY'
            ORDER BY tc.constraint_name
        """
        
        result = await database_service.execute_query(query, [table_name, schema_name])
        
        foreign_keys = []
        for row in result.rows:
            foreign_keys.append(ForeignKeyInfo(
                name=row["constraint_name"],
                column=row["column_name"],
                foreign_table=row["foreign_table_name"],
                foreign_column=row["foreign_column_name"],
                on_delete=row["delete_rule"],
                on_update=row["update_rule"]
            ))
        
        return foreign_keys
    
    async def _get_incoming_foreign_keys(self, table_name: str, schema_name: str) -> List[Dict[str, Any]]:
        """Get foreign keys that reference this table."""
        query = """
            SELECT 
                tc.table_name as referencing_table,
                tc.table_schema as referencing_schema,
                kcu.column_name as referencing_column,
                ccu.column_name as referenced_column,
                tc.constraint_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage ccu
                ON tc.constraint_name = ccu.constraint_name
            WHERE ccu.table_name = $1 
            AND ccu.table_schema = $2
            AND tc.constraint_type = 'FOREIGN KEY'
            ORDER BY tc.table_name, kcu.column_name
        """
        
        result = await database_service.execute_query(query, [table_name, schema_name])
        return result.rows
    
    async def _get_database_size(self) -> Optional[str]:
        """Get the size of the current database."""
        try:
            result = await database_service.execute_query(
                "SELECT pg_size_pretty(pg_database_size(current_database())) as size"
            )
            return result.rows[0]["size"] if result.rows else None
        except Exception:
            return None
    
    async def _get_table_size(self, table_name: str, schema_name: str) -> Optional[str]:
        """Get the size of a specific table."""
        try:
            result = await database_service.execute_query(
                "SELECT pg_size_pretty(pg_total_relation_size($1)) as size",
                [f'"{schema_name}"."{table_name}"']
            )
            return result.rows[0]["size"] if result.rows else None
        except Exception:
            return None
    
    async def _get_table_comment(self, table_name: str, schema_name: str) -> Optional[str]:
        """Get the comment/description for a table."""
        try:
            result = await database_service.execute_query(
                """
                SELECT obj_description(c.oid) as description
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE c.relname = $1 AND n.nspname = $2
                """,
                [table_name, schema_name]
            )
            return result.rows[0]["description"] if result.rows and result.rows[0]["description"] else None
        except Exception:
            return None
    
    async def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get item from cache if not expired."""
        async with self._cache_lock:
            if key in self._cache and key in self._cache_timestamps:
                if datetime.now() - self._cache_timestamps[key] < self._cache_ttl:
                    return self._cache[key]
                else:
                    # Remove expired item
                    del self._cache[key]
                    del self._cache_timestamps[key]
            return None
    
    async def _set_cache(self, key: str, value: Any) -> None:
        """Set item in cache with timestamp."""
        async with self._cache_lock:
            self._cache[key] = value
            self._cache_timestamps[key] = datetime.now()
    
    async def clear_cache(self) -> None:
        """Clear all cached schema information."""
        async with self._cache_lock:
            self._cache.clear()
            self._cache_timestamps.clear()
            logger.info("Schema cache cleared")


# Global schema service instance
schema_service = SchemaService()
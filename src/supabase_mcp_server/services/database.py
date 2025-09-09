"""Database service for PostgreSQL operations."""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Union, Tuple
from urllib.parse import urlparse

import asyncpg
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from supabase_mcp_server.config import get_settings
from supabase_mcp_server.core.logging import get_logger

logger = get_logger(__name__)


class QueryResult:
    """Result of a database query."""
    
    def __init__(
        self,
        rows: List[Dict[str, Any]],
        row_count: int,
        execution_time: float,
        columns: Optional[List[str]] = None
    ):
        """Initialize query result."""
        self.rows = rows
        self.row_count = row_count
        self.execution_time = execution_time
        self.columns = columns or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "rows": self.rows,
            "row_count": self.row_count,
            "execution_time": self.execution_time,
            "columns": self.columns
        }


class DatabaseError(Exception):
    """Database operation error."""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        """Initialize database error."""
        super().__init__(message)
        self.original_error = original_error


class DatabaseService:
    """Service for PostgreSQL database operations."""
    
    def __init__(self):
        """Initialize the database service."""
        self.settings = get_settings()
        self._pool: Optional[asyncpg.Pool] = None
        self._connection_lock = asyncio.Lock()
        self._health_check_task: Optional[asyncio.Task] = None
    
    async def initialize(self) -> None:
        """Initialize the database connection pool."""
        if self._pool is not None:
            logger.warning("Database service already initialized")
            return
        
        try:
            logger.info("Initializing database connection pool")
            
            # Parse database URL
            parsed_url = urlparse(self.settings.database_url)
            
            # Create connection pool
            self._pool = await asyncpg.create_pool(
                host=parsed_url.hostname,
                port=parsed_url.port or 5432,
                user=parsed_url.username,
                password=parsed_url.password,
                database=parsed_url.path.lstrip('/') if parsed_url.path else 'postgres',
                min_size=1,
                max_size=self.settings.database_pool_size,
                max_inactive_connection_lifetime=300,  # 5 minutes
                command_timeout=self.settings.database_timeout,
                server_settings={
                    'application_name': 'supabase-mcp-server',
                    'timezone': 'UTC'
                }
            )
            
            # Test connection
            await self._test_connection()
            
            # Start health check task
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            
            logger.info(
                "Database connection pool initialized",
                pool_size=self.settings.database_pool_size,
                host=parsed_url.hostname,
                database=parsed_url.path.lstrip('/') if parsed_url.path else 'postgres'
            )
            
        except Exception as e:
            logger.error("Failed to initialize database connection pool", error=str(e))
            raise DatabaseError(f"Failed to initialize database: {str(e)}", e)
    
    async def close(self) -> None:
        """Close the database connection pool."""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        if self._pool:
            logger.info("Closing database connection pool")
            await self._pool.close()
            self._pool = None
    
    @retry(
        retry=retry_if_exception_type((asyncpg.ConnectionDoesNotExistError, asyncpg.InterfaceError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def execute_query(
        self,
        query: str,
        params: Optional[List[Any]] = None,
        fetch_results: bool = True
    ) -> QueryResult:
        """Execute a SQL query with optional parameters."""
        if not self._pool:
            raise DatabaseError("Database not initialized")
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            async with self._pool.acquire() as connection:
                logger.debug("Executing query", query=query[:100] + "..." if len(query) > 100 else query)
                
                if fetch_results:
                    if params:
                        rows = await connection.fetch(query, *params)
                    else:
                        rows = await connection.fetch(query)
                    
                    # Convert asyncpg.Record to dict
                    result_rows = [dict(row) for row in rows]
                    columns = list(rows[0].keys()) if rows else []
                    row_count = len(result_rows)
                else:
                    if params:
                        result = await connection.execute(query, *params)
                    else:
                        result = await connection.execute(query)
                    
                    # Parse row count from result string (e.g., "INSERT 0 5" -> 5)
                    row_count = self._parse_row_count(result)
                    result_rows = []
                    columns = []
                
                execution_time = asyncio.get_event_loop().time() - start_time
                
                logger.info(
                    "Query executed successfully",
                    row_count=row_count,
                    execution_time=execution_time
                )
                
                return QueryResult(
                    rows=result_rows,
                    row_count=row_count,
                    execution_time=execution_time,
                    columns=columns
                )
        
        except asyncpg.PostgresError as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.error(
                "PostgreSQL error executing query",
                error=str(e),
                sqlstate=e.sqlstate,
                execution_time=execution_time
            )
            raise DatabaseError(f"PostgreSQL error: {str(e)}", e)
        
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.error(
                "Unexpected error executing query",
                error=str(e),
                execution_time=execution_time
            )
            raise DatabaseError(f"Database error: {str(e)}", e)
    
    async def execute_transaction(
        self,
        queries: List[Tuple[str, Optional[List[Any]]]]
    ) -> List[QueryResult]:
        """Execute multiple queries in a transaction."""
        if not self._pool:
            raise DatabaseError("Database not initialized")
        
        results = []
        start_time = asyncio.get_event_loop().time()
        
        try:
            async with self._pool.acquire() as connection:
                async with connection.transaction():
                    logger.debug("Starting transaction", query_count=len(queries))
                    
                    for query, params in queries:
                        if params:
                            rows = await connection.fetch(query, *params)
                        else:
                            rows = await connection.fetch(query)
                        
                        result_rows = [dict(row) for row in rows]
                        columns = list(rows[0].keys()) if rows else []
                        
                        results.append(QueryResult(
                            rows=result_rows,
                            row_count=len(result_rows),
                            execution_time=0,  # Individual timing not available in transaction
                            columns=columns
                        ))
                    
                    execution_time = asyncio.get_event_loop().time() - start_time
                    
                    logger.info(
                        "Transaction completed successfully",
                        query_count=len(queries),
                        execution_time=execution_time
                    )
                    
                    return results
        
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.error(
                "Transaction failed",
                error=str(e),
                execution_time=execution_time
            )
            raise DatabaseError(f"Transaction failed: {str(e)}", e)
    
    async def get_connection_info(self) -> Dict[str, Any]:
        """Get information about the database connection."""
        if not self._pool:
            return {"status": "not_initialized"}
        
        try:
            async with self._pool.acquire() as connection:
                version_result = await connection.fetchrow("SELECT version()")
                db_size_result = await connection.fetchrow(
                    "SELECT pg_size_pretty(pg_database_size(current_database())) as size"
                )
                
                return {
                    "status": "connected",
                    "pool_size": self._pool.get_size(),
                    "pool_max_size": self._pool.get_max_size(),
                    "pool_min_size": self._pool.get_min_size(),
                    "version": version_result["version"] if version_result else "unknown",
                    "database_size": db_size_result["size"] if db_size_result else "unknown"
                }
        
        except Exception as e:
            logger.error("Failed to get connection info", error=str(e))
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def health_check(self) -> bool:
        """Perform a health check on the database connection."""
        if not self._pool:
            return False
        
        try:
            async with self._pool.acquire() as connection:
                await connection.fetchval("SELECT 1")
                return True
        except Exception as e:
            logger.warning("Database health check failed", error=str(e))
            return False
    
    @asynccontextmanager
    async def get_connection(self):
        """Get a database connection from the pool."""
        if not self._pool:
            raise DatabaseError("Database not initialized")
        
        async with self._pool.acquire() as connection:
            yield connection
    
    def _parse_row_count(self, result: str) -> int:
        """Parse row count from PostgreSQL result string."""
        try:
            # Result format examples: "INSERT 0 5", "UPDATE 3", "DELETE 2"
            parts = result.split()
            if len(parts) >= 2:
                return int(parts[-1])
            return 0
        except (ValueError, IndexError):
            return 0
    
    async def _test_connection(self) -> None:
        """Test the database connection."""
        if not self._pool:
            raise DatabaseError("Pool not initialized")
        
        async with self._pool.acquire() as connection:
            result = await connection.fetchval("SELECT 1")
            if result != 1:
                raise DatabaseError("Connection test failed")
    
    async def _health_check_loop(self) -> None:
        """Background task for periodic health checks."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                if not await self.health_check():
                    logger.warning("Database health check failed, attempting reconnection")
                    # Pool will automatically handle reconnection
                
            except asyncio.CancelledError:
                logger.info("Health check loop cancelled")
                break
            except Exception as e:
                logger.error("Error in health check loop", error=str(e))


# Global database service instance
database_service = DatabaseService()
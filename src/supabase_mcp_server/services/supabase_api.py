"""Supabase API integration service."""

import json
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions
from postgrest.exceptions import APIError

from supabase_mcp_server.config import get_settings
from supabase_mcp_server.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CRUDResult:
    """Result of a CRUD operation."""
    success: bool
    data: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]] = None
    count: Optional[int] = None
    error: Optional[str] = None
    status_code: Optional[int] = None


class SupabaseAPIService:
    """Service for Supabase API operations."""
    
    def __init__(self):
        """Initialize the Supabase API service."""
        self.settings = get_settings()
        self._client: Optional[Client] = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the Supabase client."""
        if self._initialized:
            logger.warning("Supabase API service already initialized")
            return
        
        try:
            logger.info("Initializing Supabase API client")
            
            # Create Supabase client with minimal options
            self._client = create_client(
                supabase_url=self.settings.supabase_url,
                supabase_key=self.settings.supabase_service_role_key
            )
            
            # Test connection
            await self._test_connection()
            
            self._initialized = True
            
            logger.info("Supabase API client initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize Supabase API client", error=str(e))
            raise Exception(f"Failed to initialize Supabase API: {str(e)}") from e
    
    async def select(
        self,
        table: str,
        columns: Optional[str] = "*",
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> CRUDResult:
        """Select data from a table."""
        if not self._client:
            return CRUDResult(success=False, error="Supabase client not initialized")
        
        try:
            logger.debug("Executing select operation", table=table, filters=filters)
            
            # Start query
            query = self._client.table(table).select(columns)
            
            # Apply filters
            if filters:
                for key, value in filters.items():
                    if isinstance(value, dict):
                        # Handle complex filters like {"gte": 18} or {"ilike": "%john%"}
                        for operator, filter_value in value.items():
                            query = self._apply_filter(query, key, operator, filter_value)
                    else:
                        # Simple equality filter
                        query = query.eq(key, value)
            
            # Apply ordering
            if order_by:
                if order_by.startswith("-"):
                    # Descending order
                    query = query.order(order_by[1:], desc=True)
                else:
                    # Ascending order
                    query = query.order(order_by)
            
            # Apply pagination
            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(offset)
            
            # Execute query
            response = query.execute()
            
            logger.info(
                "Select operation completed",
                table=table,
                count=len(response.data) if response.data else 0
            )
            
            return CRUDResult(
                success=True,
                data=response.data,
                count=len(response.data) if response.data else 0
            )
            
        except APIError as e:
            logger.error("Supabase API error in select", table=table, error=str(e))
            return CRUDResult(
                success=False,
                error=f"API Error: {str(e)}",
                status_code=getattr(e, 'status_code', None)
            )
        except Exception as e:
            logger.error("Unexpected error in select", table=table, error=str(e))
            return CRUDResult(success=False, error=f"Unexpected error: {str(e)}")
    
    async def insert(
        self,
        table: str,
        data: Union[Dict[str, Any], List[Dict[str, Any]]],
        on_conflict: Optional[str] = None
    ) -> CRUDResult:
        """Insert data into a table."""
        if not self._client:
            return CRUDResult(success=False, error="Supabase client not initialized")
        
        try:
            logger.debug("Executing insert operation", table=table, data_type=type(data).__name__)
            
            query = self._client.table(table).insert(data)
            
            # Handle conflict resolution
            if on_conflict:
                query = query.on_conflict(on_conflict)
            
            response = query.execute()
            
            count = len(response.data) if response.data else 0
            logger.info("Insert operation completed", table=table, count=count)
            
            return CRUDResult(
                success=True,
                data=response.data,
                count=count
            )
            
        except APIError as e:
            logger.error("Supabase API error in insert", table=table, error=str(e))
            return CRUDResult(
                success=False,
                error=f"API Error: {str(e)}",
                status_code=getattr(e, 'status_code', None)
            )
        except Exception as e:
            logger.error("Unexpected error in insert", table=table, error=str(e))
            return CRUDResult(success=False, error=f"Unexpected error: {str(e)}")
    
    async def update(
        self,
        table: str,
        data: Dict[str, Any],
        filters: Dict[str, Any]
    ) -> CRUDResult:
        """Update data in a table."""
        if not self._client:
            return CRUDResult(success=False, error="Supabase client not initialized")
        
        if not filters:
            return CRUDResult(success=False, error="Filters are required for update operations")
        
        try:
            logger.debug("Executing update operation", table=table, filters=filters)
            
            query = self._client.table(table).update(data)
            
            # Apply filters
            for key, value in filters.items():
                if isinstance(value, dict):
                    for operator, filter_value in value.items():
                        query = self._apply_filter(query, key, operator, filter_value)
                else:
                    query = query.eq(key, value)
            
            response = query.execute()
            
            count = len(response.data) if response.data else 0
            logger.info("Update operation completed", table=table, count=count)
            
            return CRUDResult(
                success=True,
                data=response.data,
                count=count
            )
            
        except APIError as e:
            logger.error("Supabase API error in update", table=table, error=str(e))
            return CRUDResult(
                success=False,
                error=f"API Error: {str(e)}",
                status_code=getattr(e, 'status_code', None)
            )
        except Exception as e:
            logger.error("Unexpected error in update", table=table, error=str(e))
            return CRUDResult(success=False, error=f"Unexpected error: {str(e)}")
    
    async def delete(
        self,
        table: str,
        filters: Dict[str, Any]
    ) -> CRUDResult:
        """Delete data from a table."""
        if not self._client:
            return CRUDResult(success=False, error="Supabase client not initialized")
        
        if not filters:
            return CRUDResult(success=False, error="Filters are required for delete operations")
        
        try:
            logger.debug("Executing delete operation", table=table, filters=filters)
            
            query = self._client.table(table).delete()
            
            # Apply filters
            for key, value in filters.items():
                if isinstance(value, dict):
                    for operator, filter_value in value.items():
                        query = self._apply_filter(query, key, operator, filter_value)
                else:
                    query = query.eq(key, value)
            
            response = query.execute()
            
            count = len(response.data) if response.data else 0
            logger.info("Delete operation completed", table=table, count=count)
            
            return CRUDResult(
                success=True,
                data=response.data,
                count=count
            )
            
        except APIError as e:
            logger.error("Supabase API error in delete", table=table, error=str(e))
            return CRUDResult(
                success=False,
                error=f"API Error: {str(e)}",
                status_code=getattr(e, 'status_code', None)
            )
        except Exception as e:
            logger.error("Unexpected error in delete", table=table, error=str(e))
            return CRUDResult(success=False, error=f"Unexpected error: {str(e)}")
    
    async def upsert(
        self,
        table: str,
        data: Union[Dict[str, Any], List[Dict[str, Any]]],
        on_conflict: Optional[str] = None
    ) -> CRUDResult:
        """Upsert (insert or update) data in a table."""
        if not self._client:
            return CRUDResult(success=False, error="Supabase client not initialized")
        
        try:
            logger.debug("Executing upsert operation", table=table, data_type=type(data).__name__)
            
            query = self._client.table(table).upsert(data)
            
            if on_conflict:
                query = query.on_conflict(on_conflict)
            
            response = query.execute()
            
            count = len(response.data) if response.data else 0
            logger.info("Upsert operation completed", table=table, count=count)
            
            return CRUDResult(
                success=True,
                data=response.data,
                count=count
            )
            
        except APIError as e:
            logger.error("Supabase API error in upsert", table=table, error=str(e))
            return CRUDResult(
                success=False,
                error=f"API Error: {str(e)}",
                status_code=getattr(e, 'status_code', None)
            )
        except Exception as e:
            logger.error("Unexpected error in upsert", table=table, error=str(e))
            return CRUDResult(success=False, error=f"Unexpected error: {str(e)}")
    
    async def call_rpc(
        self,
        function_name: str,
        params: Optional[Dict[str, Any]] = None
    ) -> CRUDResult:
        """Call a PostgreSQL function via RPC."""
        if not self._client:
            return CRUDResult(success=False, error="Supabase client not initialized")
        
        try:
            logger.debug("Calling RPC function", function=function_name, params=params)
            
            if params:
                response = self._client.rpc(function_name, params).execute()
            else:
                response = self._client.rpc(function_name).execute()
            
            logger.info("RPC function call completed", function=function_name)
            
            return CRUDResult(
                success=True,
                data=response.data
            )
            
        except APIError as e:
            logger.error("Supabase API error in RPC call", function=function_name, error=str(e))
            return CRUDResult(
                success=False,
                error=f"API Error: {str(e)}",
                status_code=getattr(e, 'status_code', None)
            )
        except Exception as e:
            logger.error("Unexpected error in RPC call", function=function_name, error=str(e))
            return CRUDResult(success=False, error=f"Unexpected error: {str(e)}")
    
    async def get_auth_user(self, jwt_token: str) -> Optional[Dict[str, Any]]:
        """Get user information from JWT token."""
        if not self._client:
            return None
        
        try:
            # Set the auth token
            self._client.auth.set_session(jwt_token, "")
            
            # Get user
            user = self._client.auth.get_user()
            
            return user.user.model_dump() if user.user else None
            
        except Exception as e:
            logger.error("Failed to get auth user", error=str(e))
            return None
    
    def _apply_filter(self, query, column: str, operator: str, value: Any):
        """Apply a filter to a query based on operator."""
        operator_map = {
            "eq": lambda q, c, v: q.eq(c, v),
            "neq": lambda q, c, v: q.neq(c, v),
            "gt": lambda q, c, v: q.gt(c, v),
            "gte": lambda q, c, v: q.gte(c, v),
            "lt": lambda q, c, v: q.lt(c, v),
            "lte": lambda q, c, v: q.lte(c, v),
            "like": lambda q, c, v: q.like(c, v),
            "ilike": lambda q, c, v: q.ilike(c, v),
            "is": lambda q, c, v: q.is_(c, v),
            "in": lambda q, c, v: q.in_(c, v),
            "contains": lambda q, c, v: q.contains(c, v),
            "contained_by": lambda q, c, v: q.contained_by(c, v),
            "range_gt": lambda q, c, v: q.range_gt(c, v),
            "range_gte": lambda q, c, v: q.range_gte(c, v),
            "range_lt": lambda q, c, v: q.range_lt(c, v),
            "range_lte": lambda q, c, v: q.range_lte(c, v),
            "range_adjacent": lambda q, c, v: q.range_adjacent(c, v),
            "overlaps": lambda q, c, v: q.overlaps(c, v),
            "text_search": lambda q, c, v: q.text_search(c, v),
            "match": lambda q, c, v: q.match(c, v),
        }
        
        if operator in operator_map:
            return operator_map[operator](query, column, value)
        else:
            logger.warning("Unknown filter operator", operator=operator)
            return query.eq(column, value)  # Fallback to equality
    
    async def _test_connection(self) -> None:
        """Test the Supabase connection."""
        if not self._client:
            raise Exception("Client not initialized")
        
        try:
            # Try to access a system table to test connection
            # This will fail if credentials are invalid
            response = self._client.table("information_schema.tables").select("table_name").limit(1).execute()
            
            if response is None:
                raise Exception("Connection test failed - no response")
                
        except Exception as e:
            raise Exception(f"Connection test failed: {str(e)}") from e
    
    def get_client(self) -> Optional[Client]:
        """Get the Supabase client instance."""
        return self._client
    
    def is_initialized(self) -> bool:
        """Check if the service is initialized."""
        return self._initialized


# Global Supabase API service instance
supabase_api_service = SupabaseAPIService()
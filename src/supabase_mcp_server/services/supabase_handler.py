"""Supabase MCP handler implementation."""

from typing import Any, Dict

from supabase_mcp_server.config import get_settings
from supabase_mcp_server.core.logging import get_logger
from supabase_mcp_server.mcp.handler import MCPHandler
from supabase_mcp_server.mcp.models import (
    InitializeParams,
    InitializeResult,
    ListToolsResult,
    Tool,
    ToolParameter,
    ToolResult,
)

logger = get_logger(__name__)


class SupabaseMCPHandler(MCPHandler):
    """MCP handler for Supabase operations."""
    
    def __init__(self):
        """Initialize the Supabase MCP handler."""
        super().__init__()
        self.settings = get_settings()
        self._register_tools()
    
    def _register_tools(self) -> None:
        """Register available tools."""
        # Query database tool
        query_tool = Tool(
            name="query_database",
            description="Execute SQL queries on the PostgreSQL database with safety validation",
            parameters={
                "query": ToolParameter(
                    type="string",
                    description="SQL query to execute",
                    required=True
                ),
                "params": ToolParameter(
                    type="array",
                    description="Query parameters for prepared statements",
                    required=False
                ),
                "force_execute": ToolParameter(
                    type="boolean",
                    description="Force execution of potentially dangerous queries",
                    required=False,
                    default=False
                )
            }
        )
        self.register_tool(query_tool)
        
        # Get schema tool
        schema_tool = Tool(
            name="get_schema",
            description="Get database schema information",
            parameters={
                "table_name": ToolParameter(
                    type="string",
                    description="Specific table name (optional)",
                    required=False
                ),
                "include_columns": ToolParameter(
                    type="boolean",
                    description="Include column details",
                    required=False,
                    default=True
                )
            }
        )
        self.register_tool(schema_tool)
        
        # CRUD operations tool
        crud_tool = Tool(
            name="crud_operations",
            description="Perform CRUD operations via Supabase API",
            parameters={
                "operation": ToolParameter(
                    type="string",
                    description="CRUD operation type",
                    required=True,
                    enum=["select", "insert", "update", "delete"]
                ),
                "table": ToolParameter(
                    type="string",
                    description="Table name",
                    required=True
                ),
                "data": ToolParameter(
                    type="object",
                    description="Data for insert/update operations",
                    required=False
                ),
                "filters": ToolParameter(
                    type="object",
                    description="Filters for select/update/delete operations",
                    required=False
                )
            }
        )
        self.register_tool(crud_tool)
        
        # Storage operations tool
        storage_tool = Tool(
            name="storage_operations",
            description="Manage files and buckets in Supabase Storage",
            parameters={
                "operation": ToolParameter(
                    type="string",
                    description="Storage operation type",
                    required=True,
                    enum=["list_buckets", "list", "upload", "download", "delete", "move", "copy", "get_public_url", "create_signed_url"]
                ),
                "bucket": ToolParameter(
                    type="string",
                    description="Storage bucket name (required for most operations)",
                    required=False
                ),
                "path": ToolParameter(
                    type="string",
                    description="File path or directory path",
                    required=False
                ),
                "content": ToolParameter(
                    type="string",
                    description="File content for upload (base64 encoded or plain text)",
                    required=False
                ),
                "content_type": ToolParameter(
                    type="string",
                    description="MIME type for uploaded file",
                    required=False
                ),
                "from_path": ToolParameter(
                    type="string",
                    description="Source path for move/copy operations",
                    required=False
                ),
                "to_path": ToolParameter(
                    type="string",
                    description="Destination path for move/copy operations",
                    required=False
                ),
                "expires_in": ToolParameter(
                    type="integer",
                    description="Expiration time in seconds for signed URLs",
                    required=False,
                    default=3600
                ),
                "as_base64": ToolParameter(
                    type="boolean",
                    description="Return downloaded content as base64",
                    required=False,
                    default=True
                ),
                "upsert": ToolParameter(
                    type="boolean",
                    description="Overwrite existing file on upload",
                    required=False,
                    default=False
                )
            }
        )
        self.register_tool(storage_tool)
        
        # Get metrics tool
        metrics_tool = Tool(
            name="get_metrics",
            description="Get server performance and monitoring metrics",
            parameters={
                "metric_type": ToolParameter(
                    type="string",
                    description="Type of metrics to retrieve",
                    required=False,
                    enum=["database", "server", "security", "prometheus", "all"],
                    default="all"
                )
            }
        )
        self.register_tool(metrics_tool)
    
    async def initialize(self, params: InitializeParams) -> InitializeResult:
        """Initialize the MCP session."""
        logger.info(
            "Initializing Supabase MCP session",
            protocol_version=params.protocol_version,
            client_info=params.client_info
        )
        
        return InitializeResult(
            protocol_version="2024-11-05",
            capabilities={
                "tools": {"list_changed": True},
                "resources": {"subscribe": False, "list_changed": False}
            },
            server_info={
                "name": "supabase-mcp-server",
                "version": "0.1.0",
                "description": "Model Context Protocol server for Supabase instances"
            }
        )
    
    async def list_tools(self) -> ListToolsResult:
        """List available tools."""
        tools = self.get_all_tools()
        logger.info("Listing tools", count=len(tools))
        return ListToolsResult(tools=tools)
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> ToolResult:
        """Call a tool with the given arguments."""
        logger.info("Calling tool", name=name, arguments=arguments)
        
        try:
            if name == "query_database":
                return await self._handle_query_database(arguments)
            elif name == "get_schema":
                return await self._handle_get_schema(arguments)
            elif name == "crud_operations":
                return await self._handle_crud_operations(arguments)
            elif name == "storage_operations":
                return await self._handle_storage_operations(arguments)
            elif name == "get_metrics":
                return await self._handle_get_metrics(arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")
        
        except Exception as e:
            logger.error("Tool execution failed", name=name, error=str(e))
            return ToolResult(
                content=[{
                    "type": "text",
                    "text": f"Error executing tool '{name}': {str(e)}"
                }],
                is_error=True
            )
    
    async def _handle_query_database(self, arguments: Dict[str, Any]) -> ToolResult:
        """Handle database query tool."""
        from supabase_mcp_server.services.database import database_service
        from supabase_mcp_server.services.query_validator import query_validator
        
        query = arguments.get("query", "")
        params = arguments.get("params", [])
        force_execute = arguments.get("force_execute", False)
        
        if not query.strip():
            return ToolResult(
                content=[{
                    "type": "text",
                    "text": "Error: Query cannot be empty"
                }],
                is_error=True
            )
        
        try:
            # Validate the query first
            validation = query_validator.validate_query(
                query, 
                allow_modifications=self.settings.enable_query_validation
            )
            
            content = []
            
            # Check validation results
            if not validation.is_valid:
                content.append({
                    "type": "text",
                    "text": f"❌ Query validation failed:\n" + "\n".join(f"• {issue}" for issue in validation.issues)
                })
                
                # Add suggestions if available
                suggestions = query_validator.get_safe_query_suggestions(query)
                if suggestions:
                    content.append({
                        "type": "text",
                        "text": f"💡 Suggestions:\n" + "\n".join(f"• {suggestion}" for suggestion in suggestions)
                    })
                
                return ToolResult(content=content, is_error=True)
            
            # Show warnings if any
            if validation.warnings:
                content.append({
                    "type": "text",
                    "text": f"⚠️ Warnings:\n" + "\n".join(f"• {warning}" for warning in validation.warnings)
                })
            
            # Check if confirmation is required
            if validation.requires_confirmation and not force_execute:
                content.append({
                    "type": "text",
                    "text": f"🚨 This query requires confirmation due to its risk level: {validation.risk_level.value.upper()}"
                })
                content.append({
                    "type": "text",
                    "text": "To execute this query, add 'force_execute': true to your arguments."
                })
                return ToolResult(content=content)
            
            # Use sanitized query if available
            final_query = validation.sanitized_query or query
            
            # Execute the query
            result = await database_service.execute_query(final_query, params)
            
            # Add execution info
            content.append({
                "type": "text",
                "text": f"✅ Query executed successfully in {result.execution_time:.3f}s"
            })
            
            # Add risk level info
            if validation.risk_level.value != "safe":
                content.append({
                    "type": "text",
                    "text": f"🔒 Risk level: {validation.risk_level.value.upper()}"
                })
            
            # Add results
            if result.rows:
                # Format as table
                if result.columns:
                    # Create table header
                    header = " | ".join(result.columns)
                    separator = " | ".join(["-" * len(col) for col in result.columns])
                    
                    table_text = f"\n📊 Results:\n{header}\n{separator}\n"
                    
                    # Add rows (limit to first 100 for readability)
                    display_rows = result.rows[:100]
                    for row in display_rows:
                        row_values = [str(row.get(col, ""))[:50] for col in result.columns]  # Truncate long values
                        table_text += " | ".join(row_values) + "\n"
                    
                    if len(result.rows) > 100:
                        table_text += f"\n... and {len(result.rows) - 100} more rows"
                    
                    content.append({
                        "type": "text",
                        "text": table_text
                    })
                else:
                    content.append({
                        "type": "text",
                        "text": f"📊 Query returned {result.row_count} rows"
                    })
            else:
                content.append({
                    "type": "text",
                    "text": f"📊 Query completed. Rows affected: {result.row_count}"
                })
            
            # Add performance info
            if result.execution_time > 1.0:
                content.append({
                    "type": "text",
                    "text": f"⏱️ Note: Query took {result.execution_time:.3f}s - consider optimization"
                })
            
            return ToolResult(content=content)
            
        except Exception as e:
            logger.error("Database query failed", query=query, error=str(e))
            return ToolResult(
                content=[{
                    "type": "text",
                    "text": f"❌ Database query failed: {str(e)}"
                }],
                is_error=True
            )
    
    async def _handle_get_schema(self, arguments: Dict[str, Any]) -> ToolResult:
        """Handle get schema tool."""
        from supabase_mcp_server.services.schema import schema_service
        
        table_name = arguments.get("table_name")
        include_columns = arguments.get("include_columns", True)
        
        try:
            if table_name:
                # Get specific table schema
                schema_info = await schema_service.get_schema_info(table_name=table_name)
                
                if not schema_info.tables:
                    return ToolResult(
                        content=[{
                            "type": "text",
                            "text": f"Table '{table_name}' not found"
                        }],
                        is_error=True
                    )
                
                table = schema_info.tables[0]
                content = []
                
                # Table basic info
                content.append({
                    "type": "text",
                    "text": f"Table: {table.name}\nSchema: {table.schema}\nType: {table.table_type}"
                })
                
                if table.description:
                    content.append({
                        "type": "text",
                        "text": f"Description: {table.description}"
                    })
                
                if table.row_count is not None:
                    content.append({
                        "type": "text",
                        "text": f"Row count: {table.row_count:,}"
                    })
                
                if table.size:
                    content.append({
                        "type": "text",
                        "text": f"Size: {table.size}"
                    })
                
                # Columns
                if include_columns and table.columns:
                    columns_text = "Columns:\n"
                    for col in table.columns:
                        pk_marker = " (PK)" if col.is_primary_key else ""
                        fk_marker = f" -> {col.foreign_table}.{col.foreign_column}" if col.is_foreign_key else ""
                        nullable = "NULL" if col.is_nullable else "NOT NULL"
                        
                        columns_text += f"  {col.name}: {col.data_type} {nullable}{pk_marker}{fk_marker}\n"
                        
                        if col.default_value:
                            columns_text += f"    Default: {col.default_value}\n"
                        if col.description:
                            columns_text += f"    Description: {col.description}\n"
                    
                    content.append({
                        "type": "text",
                        "text": columns_text
                    })
                
                # Indexes
                if table.indexes:
                    indexes_text = "Indexes:\n"
                    for idx in table.indexes:
                        unique_marker = " (UNIQUE)" if idx.is_unique else ""
                        primary_marker = " (PRIMARY)" if idx.is_primary else ""
                        indexes_text += f"  {idx.name}: {', '.join(idx.columns)} [{idx.index_type}]{unique_marker}{primary_marker}\n"
                    
                    content.append({
                        "type": "text",
                        "text": indexes_text
                    })
                
                # Foreign keys
                if table.foreign_keys:
                    fks_text = "Foreign Keys:\n"
                    for fk in table.foreign_keys:
                        fks_text += f"  {fk.name}: {fk.column} -> {fk.foreign_table}.{fk.foreign_column}\n"
                        fks_text += f"    ON DELETE {fk.on_delete}, ON UPDATE {fk.on_update}\n"
                    
                    content.append({
                        "type": "text",
                        "text": fks_text
                    })
                
                return ToolResult(content=content)
            
            else:
                # Get all tables schema
                schema_info = await schema_service.get_schema_info()
                
                content = []
                
                # Summary
                summary = f"Database Schema Summary:\n"
                summary += f"Total Tables: {schema_info.total_tables}\n"
                summary += f"Total Views: {schema_info.total_views}\n"
                summary += f"Total Materialized Views: {schema_info.total_materialized_views}\n"
                
                if schema_info.database_size:
                    summary += f"Database Size: {schema_info.database_size}\n"
                
                content.append({
                    "type": "text",
                    "text": summary
                })
                
                # Tables list
                if schema_info.tables:
                    tables_text = "Tables:\n"
                    for table in schema_info.tables:
                        size_info = f" ({table.size})" if table.size else ""
                        row_info = f" - {table.row_count:,} rows" if table.row_count is not None else ""
                        tables_text += f"  {table.name} [{table.table_type}]{size_info}{row_info}\n"
                        
                        if include_columns and table.columns:
                            tables_text += f"    Columns: {', '.join([col.name for col in table.columns])}\n"
                    
                    content.append({
                        "type": "text",
                        "text": tables_text
                    })
                
                return ToolResult(content=content)
            
        except Exception as e:
            logger.error("Schema discovery failed", table_name=table_name, error=str(e))
            return ToolResult(
                content=[{
                    "type": "text",
                    "text": f"Schema discovery failed: {str(e)}"
                }],
                is_error=True
            )
    
    async def _handle_crud_operations(self, arguments: Dict[str, Any]) -> ToolResult:
        """Handle CRUD operations tool."""
        from supabase_mcp_server.services.supabase_api import supabase_api_service
        
        operation = arguments.get("operation")
        table = arguments.get("table")
        data = arguments.get("data", {})
        filters = arguments.get("filters", {})
        
        if not operation or not table:
            return ToolResult(
                content=[{
                    "type": "text",
                    "text": "Error: Both 'operation' and 'table' are required"
                }],
                is_error=True
            )
        
        try:
            # Ensure Supabase API service is initialized
            if not supabase_api_service.is_initialized():
                await supabase_api_service.initialize()
            
            result = None
            
            if operation == "select":
                # Extract additional select parameters
                columns = arguments.get("columns", "*")
                order_by = arguments.get("order_by")
                limit = arguments.get("limit")
                offset = arguments.get("offset")
                
                result = await supabase_api_service.select(
                    table=table,
                    columns=columns,
                    filters=filters,
                    order_by=order_by,
                    limit=limit,
                    offset=offset
                )
                
            elif operation == "insert":
                if not data:
                    return ToolResult(
                        content=[{
                            "type": "text",
                            "text": "Error: 'data' is required for insert operations"
                        }],
                        is_error=True
                    )
                
                on_conflict = arguments.get("on_conflict")
                result = await supabase_api_service.insert(
                    table=table,
                    data=data,
                    on_conflict=on_conflict
                )
                
            elif operation == "update":
                if not data:
                    return ToolResult(
                        content=[{
                            "type": "text",
                            "text": "Error: 'data' is required for update operations"
                        }],
                        is_error=True
                    )
                
                if not filters:
                    return ToolResult(
                        content=[{
                            "type": "text",
                            "text": "Error: 'filters' are required for update operations"
                        }],
                        is_error=True
                    )
                
                result = await supabase_api_service.update(
                    table=table,
                    data=data,
                    filters=filters
                )
                
            elif operation == "delete":
                if not filters:
                    return ToolResult(
                        content=[{
                            "type": "text",
                            "text": "Error: 'filters' are required for delete operations"
                        }],
                        is_error=True
                    )
                
                result = await supabase_api_service.delete(
                    table=table,
                    filters=filters
                )
                
            elif operation == "upsert":
                if not data:
                    return ToolResult(
                        content=[{
                            "type": "text",
                            "text": "Error: 'data' is required for upsert operations"
                        }],
                        is_error=True
                    )
                
                on_conflict = arguments.get("on_conflict")
                result = await supabase_api_service.upsert(
                    table=table,
                    data=data,
                    on_conflict=on_conflict
                )
                
            else:
                return ToolResult(
                    content=[{
                        "type": "text",
                        "text": f"Error: Unknown operation '{operation}'. Supported operations: select, insert, update, delete, upsert"
                    }],
                    is_error=True
                )
            
            # Format the result
            if result.success:
                content = []
                
                # Add operation summary
                content.append({
                    "type": "text",
                    "text": f"✅ {operation.upper()} operation completed successfully"
                })
                
                if result.count is not None:
                    content.append({
                        "type": "text",
                        "text": f"Rows affected: {result.count}"
                    })
                
                # Add data if present and not too large
                if result.data:
                    if isinstance(result.data, list):
                        if len(result.data) <= 10:  # Show up to 10 rows
                            content.append({
                                "type": "text",
                                "text": f"Data:\n{json.dumps(result.data, indent=2, default=str)}"
                            })
                        else:
                            # Show first few rows and summary
                            sample_data = result.data[:3]
                            content.append({
                                "type": "text",
                                "text": f"Sample data (first 3 rows):\n{json.dumps(sample_data, indent=2, default=str)}"
                            })
                            content.append({
                                "type": "text",
                                "text": f"... and {len(result.data) - 3} more rows"
                            })
                    else:
                        content.append({
                            "type": "text",
                            "text": f"Data:\n{json.dumps(result.data, indent=2, default=str)}"
                        })
                
                return ToolResult(content=content)
            else:
                return ToolResult(
                    content=[{
                        "type": "text",
                        "text": f"❌ {operation.upper()} operation failed: {result.error}"
                    }],
                    is_error=True
                )
            
        except Exception as e:
            logger.error("CRUD operation failed", operation=operation, table=table, error=str(e))
            return ToolResult(
                content=[{
                    "type": "text",
                    "text": f"CRUD operation failed: {str(e)}"
                }],
                is_error=True
            )
    
    async def _handle_storage_operations(self, arguments: Dict[str, Any]) -> ToolResult:
        """Handle storage operations tool."""
        from supabase_mcp_server.services.storage import storage_service
        
        operation = arguments.get("operation")
        bucket = arguments.get("bucket")
        path = arguments.get("path", "")
        content = arguments.get("content")
        
        if not operation:
            return ToolResult(
                content=[{
                    "type": "text",
                    "text": "Error: 'operation' is required"
                }],
                is_error=True
            )
        
        try:
            result = None
            
            if operation == "list_buckets":
                result = await storage_service.list_buckets()
                
            elif operation == "list":
                if not bucket:
                    return ToolResult(
                        content=[{
                            "type": "text",
                            "text": "Error: 'bucket' is required for list operation"
                        }],
                        is_error=True
                    )
                
                limit = arguments.get("limit")
                offset = arguments.get("offset")
                result = await storage_service.list_files(bucket, path, limit, offset)
                
            elif operation == "upload":
                if not bucket or not path or not content:
                    return ToolResult(
                        content=[{
                            "type": "text",
                            "text": "Error: 'bucket', 'path', and 'content' are required for upload operation"
                        }],
                        is_error=True
                    )
                
                content_type = arguments.get("content_type")
                upsert = arguments.get("upsert", False)
                result = await storage_service.upload_file(bucket, path, content, content_type, upsert)
                
            elif operation == "download":
                if not bucket or not path:
                    return ToolResult(
                        content=[{
                            "type": "text",
                            "text": "Error: 'bucket' and 'path' are required for download operation"
                        }],
                        is_error=True
                    )
                
                as_base64 = arguments.get("as_base64", True)  # Default to base64 for safety
                result = await storage_service.download_file(bucket, path, as_base64)
                
            elif operation == "delete":
                if not bucket or not path:
                    return ToolResult(
                        content=[{
                            "type": "text",
                            "text": "Error: 'bucket' and 'path' are required for delete operation"
                        }],
                        is_error=True
                    )
                
                # Support deleting multiple files
                paths = path if isinstance(path, list) else [path]
                result = await storage_service.delete_file(bucket, paths)
                
            elif operation == "move":
                from_path = arguments.get("from_path") or path
                to_path = arguments.get("to_path")
                
                if not bucket or not from_path or not to_path:
                    return ToolResult(
                        content=[{
                            "type": "text",
                            "text": "Error: 'bucket', 'from_path', and 'to_path' are required for move operation"
                        }],
                        is_error=True
                    )
                
                result = await storage_service.move_file(bucket, from_path, to_path)
                
            elif operation == "copy":
                from_path = arguments.get("from_path") or path
                to_path = arguments.get("to_path")
                
                if not bucket or not from_path or not to_path:
                    return ToolResult(
                        content=[{
                            "type": "text",
                            "text": "Error: 'bucket', 'from_path', and 'to_path' are required for copy operation"
                        }],
                        is_error=True
                    )
                
                result = await storage_service.copy_file(bucket, from_path, to_path)
                
            elif operation == "get_public_url":
                if not bucket or not path:
                    return ToolResult(
                        content=[{
                            "type": "text",
                            "text": "Error: 'bucket' and 'path' are required for get_public_url operation"
                        }],
                        is_error=True
                    )
                
                result = await storage_service.get_public_url(bucket, path)
                
            elif operation == "create_signed_url":
                if not bucket or not path:
                    return ToolResult(
                        content=[{
                            "type": "text",
                            "text": "Error: 'bucket' and 'path' are required for create_signed_url operation"
                        }],
                        is_error=True
                    )
                
                expires_in = arguments.get("expires_in", 3600)
                result = await storage_service.create_signed_url(bucket, path, expires_in)
                
            else:
                return ToolResult(
                    content=[{
                        "type": "text",
                        "text": f"Error: Unknown operation '{operation}'. Supported operations: list_buckets, list, upload, download, delete, move, copy, get_public_url, create_signed_url"
                    }],
                    is_error=True
                )
            
            # Format the result
            if result.success:
                content = []
                
                # Add operation summary
                content.append({
                    "type": "text",
                    "text": f"✅ {operation.upper()} operation completed successfully"
                })
                
                if result.message:
                    content.append({
                        "type": "text",
                        "text": result.message
                    })
                
                # Add data based on operation type
                if result.data:
                    if operation == "list_buckets":
                        # Format bucket list
                        buckets_text = "📁 Buckets:\n"
                        for bucket_info in result.data:
                            public_marker = " (Public)" if bucket_info.get("public") else " (Private)"
                            buckets_text += f"  • {bucket_info['name']}{public_marker}\n"
                            buckets_text += f"    ID: {bucket_info['id']}\n"
                            buckets_text += f"    Created: {bucket_info['created_at']}\n"
                        
                        content.append({
                            "type": "text",
                            "text": buckets_text
                        })
                        
                    elif operation == "list":
                        # Format file list
                        if isinstance(result.data, list) and result.data:
                            files_text = f"📄 Files in {bucket}/{path}:\n"
                            for file_info in result.data[:20]:  # Limit to first 20 files
                                size_info = f" ({file_info.size} bytes)" if file_info.size else ""
                                mime_info = f" [{file_info.mime_type}]" if file_info.mime_type else ""
                                files_text += f"  • {file_info.name}{size_info}{mime_info}\n"
                            
                            if len(result.data) > 20:
                                files_text += f"  ... and {len(result.data) - 20} more files\n"
                            
                            content.append({
                                "type": "text",
                                "text": files_text
                            })
                        else:
                            content.append({
                                "type": "text",
                                "text": f"📁 No files found in {bucket}/{path}"
                            })
                    
                    elif operation == "download":
                        # For download, show content info
                        if isinstance(result.data, str):
                            if len(result.data) > 1000:
                                content.append({
                                    "type": "text",
                                    "text": f"📄 File content (first 500 chars):\n{result.data[:500]}...\n\n[Content truncated - total size: {len(result.data)} characters]"
                                })
                            else:
                                content.append({
                                    "type": "text",
                                    "text": f"📄 File content:\n{result.data}"
                                })
                        else:
                            content.append({
                                "type": "text",
                                "text": f"📄 Binary file downloaded ({len(result.data)} bytes)"
                            })
                    
                    elif operation in ["get_public_url", "create_signed_url"]:
                        # Show URL
                        content.append({
                            "type": "text",
                            "text": f"🔗 URL: {result.data}"
                        })
                    
                    else:
                        # Generic data display
                        content.append({
                            "type": "text",
                            "text": f"📊 Result: {str(result.data)[:500]}"
                        })
                
                return ToolResult(content=content)
            else:
                return ToolResult(
                    content=[{
                        "type": "text",
                        "text": f"❌ {operation.upper()} operation failed: {result.error}"
                    }],
                    is_error=True
                )
            
        except Exception as e:
            logger.error("Storage operation failed", operation=operation, bucket=bucket, error=str(e))
            return ToolResult(
                content=[{
                    "type": "text",
                    "text": f"Storage operation failed: {str(e)}"
                }],
                is_error=True
            )
    
    async def _handle_get_metrics(self, arguments: Dict[str, Any]) -> ToolResult:
        """Handle get metrics tool."""
        from supabase_mcp_server.services.metrics import metrics_service
        from supabase_mcp_server.services.database import database_service
        from supabase_mcp_server.middleware.rate_limit import security_middleware
        
        metric_type = arguments.get("metric_type", "all")
        
        try:
            content = []
            
            if metric_type in ["all", "server"]:
                # Server metrics
                content.append({
                    "type": "text",
                    "text": "🖥️ Server Metrics:"
                })
                
                # Update metrics before reading
                metrics_service.update_server_uptime()
                
                server_metrics = {
                    "uptime_seconds": metrics_service.server_uptime._value._value,
                    "active_connections": metrics_service.active_connections._value._value,
                }
                
                content.append({
                    "type": "text",
                    "text": f"  • Uptime: {server_metrics['uptime_seconds']:.1f} seconds"
                })
                content.append({
                    "type": "text",
                    "text": f"  • Active connections: {server_metrics['active_connections']}"
                })
            
            if metric_type in ["all", "database"]:
                # Database metrics
                content.append({
                    "type": "text",
                    "text": "\n🗄️ Database Metrics:"
                })
                
                db_info = await database_service.get_connection_info()
                if db_info.get("status") == "connected":
                    content.append({
                        "type": "text",
                        "text": f"  • Pool size: {db_info.get('pool_size', 'N/A')}/{db_info.get('pool_max_size', 'N/A')}"
                    })
                    content.append({
                        "type": "text",
                        "text": f"  • Database version: {db_info.get('version', 'Unknown')[:50]}..."
                    })
                    content.append({
                        "type": "text",
                        "text": f"  • Database size: {db_info.get('database_size', 'Unknown')}"
                    })
                else:
                    content.append({
                        "type": "text",
                        "text": "  • Status: Not connected"
                    })
            
            if metric_type in ["all", "security"]:
                # Security metrics
                content.append({
                    "type": "text",
                    "text": "\n🔒 Security Metrics:"
                })
                
                security_stats = security_middleware.get_security_stats()
                content.append({
                    "type": "text",
                    "text": f"  • Active rate limits: {security_stats['active_rate_limits']}"
                })
                content.append({
                    "type": "text",
                    "text": f"  • Blocked IPs: {security_stats['blocked_ips']}"
                })
                content.append({
                    "type": "text",
                    "text": f"  • Security events (last hour): {security_stats['security_events']['last_hour']}"
                })
                content.append({
                    "type": "text",
                    "text": f"  • Security events (last day): {security_stats['security_events']['last_day']}"
                })
                
                if security_stats['events_by_severity']:
                    severity_text = ", ".join([f"{k}: {v}" for k, v in security_stats['events_by_severity'].items()])
                    content.append({
                        "type": "text",
                        "text": f"  • Events by severity: {severity_text}"
                    })
            
            if metric_type in ["all", "prometheus"]:
                # Prometheus metrics (sample)
                content.append({
                    "type": "text",
                    "text": "\n📊 Prometheus Metrics (sample):"
                })
                
                metrics_sample = metrics_service.get_metrics()
                # Show first 10 lines as sample
                sample_lines = metrics_sample.split('\n')[:10]
                content.append({
                    "type": "text",
                    "text": "\n".join(sample_lines) + "\n... (truncated)"
                })
                
                content.append({
                    "type": "text",
                    "text": "\n💡 Full metrics available at /metrics endpoint"
                })
            
            return ToolResult(content=content)
            
        except Exception as e:
            logger.error("Failed to get metrics", metric_type=metric_type, error=str(e))
            return ToolResult(
                content=[{
                    "type": "text",
                    "text": f"Failed to get metrics: {str(e)}"
                }],
                is_error=True
            )
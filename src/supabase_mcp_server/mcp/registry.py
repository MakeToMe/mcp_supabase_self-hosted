"""Tool registry for MCP server."""

from typing import Dict, List, Optional

from supabase_mcp_server.core.logging import get_logger
from supabase_mcp_server.mcp.models import Tool

logger = get_logger(__name__)


class ToolRegistry:
    """Registry for MCP tools."""
    
    def __init__(self):
        """Initialize the tool registry."""
        self._tools: Dict[str, Tool] = {}
        self._categories: Dict[str, List[str]] = {}
    
    def register(self, tool: Tool, category: Optional[str] = None) -> None:
        """Register a tool in the registry."""
        if tool.name in self._tools:
            logger.warning("Tool already registered, overwriting", name=tool.name)
        
        self._tools[tool.name] = tool
        
        if category:
            if category not in self._categories:
                self._categories[category] = []
            if tool.name not in self._categories[category]:
                self._categories[category].append(tool.name)
        
        logger.info("Tool registered", name=tool.name, category=category)
    
    def unregister(self, name: str) -> bool:
        """Unregister a tool from the registry."""
        if name not in self._tools:
            return False
        
        del self._tools[name]
        
        # Remove from categories
        for category, tools in self._categories.items():
            if name in tools:
                tools.remove(name)
        
        logger.info("Tool unregistered", name=name)
        return True
    
    def get(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def list_all(self) -> List[Tool]:
        """List all registered tools."""
        return list(self._tools.values())
    
    def list_by_category(self, category: str) -> List[Tool]:
        """List tools by category."""
        if category not in self._categories:
            return []
        
        return [self._tools[name] for name in self._categories[category] if name in self._tools]
    
    def get_categories(self) -> List[str]:
        """Get all available categories."""
        return list(self._categories.keys())
    
    def exists(self, name: str) -> bool:
        """Check if a tool exists."""
        return name in self._tools
    
    def count(self) -> int:
        """Get the number of registered tools."""
        return len(self._tools)
    
    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()
        self._categories.clear()
        logger.info("Tool registry cleared")


# Global tool registry instance
tool_registry = ToolRegistry()
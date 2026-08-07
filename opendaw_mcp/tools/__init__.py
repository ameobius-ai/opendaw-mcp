"""
Tool Registry and Module Exports
=================================
Provides access to all tool modules and implements lazy loading.
"""

from typing import Callable, Dict, Any
import importlib
import logging

logger = logging.getLogger(__name__)

# Import all tool modules
from . import transport
from . import tracks
from . import instruments
from . import effects
from . import mixing
from . import rendering
from . import analysis
from . import other

__all__ = [
    'transport',
    'tracks',
    'instruments',
    'effects',
    'mixing',
    'rendering',
    'analysis',
    'other',
]


class ToolRegistry:
    """Registry for MCP tools with lazy loading support."""
    
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._modules: Dict[str, str] = {}
        self._loaded_modules: set = set()
    
    def register(self, name: str, func: Callable, module: str = None):
        """Register a tool function.
        
        Args:
            name: Tool name (e.g., 'mcp_opendaw_transport')
            func: The async function implementing the tool
            module: Module path for lazy loading (e.g., 'opendaw_mcp.tools.transport')
        """
        self._tools[name] = func
        if module:
            self._modules[name] = module
    
    def get(self, name: str) -> Callable:
        """Get a tool function by name, loading module if needed.
        
        Args:
            name: Tool name
            
        Returns:
            The tool function
            
        Raises:
            KeyError: If tool not found
        """
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not found in registry")
        
        # Lazy load module if not yet loaded
        if name in self._modules:
            module_path = self._modules[name]
            if module_path not in self._loaded_modules:
                try:
                    importlib.import_module(module_path)
                    self._loaded_modules.add(module_path)
                    logger.info(f"Lazily loaded module: {module_path}")
                except Exception as e:
                    logger.error(f"Failed to load module {module_path}: {e}")
        
        return self._tools[name]
    
    def list_tools(self) -> list:
        """List all registered tool names."""
        return list(self._tools.keys())
    
    def get_stats(self) -> dict:
        """Get registry statistics."""
        return {
            "total_tools": len(self._tools),
            "loaded_modules": len(self._loaded_modules),
            "modules_with_tools": len(self._modules)
        }


# Global registry instance
registry = ToolRegistry()


def get_tool_count():
    """Get total number of tools across all modules."""
    count = 0
    for module in [transport, tracks, instruments, effects, mixing, rendering, analysis, other]:
        for attr_name in dir(module):
            if attr_name.startswith('mcp_opendaw_'):
                func = getattr(module, attr_name)
                if callable(func):
                    count += 1
    return count

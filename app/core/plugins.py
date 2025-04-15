"""Plugin system for extensible custom tools."""

from __future__ import annotations

import importlib
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)


@dataclass
class Plugin:
    name: str
    description: str
    version: str
    register_tools: Callable


class PluginManager:
    """Load and manage custom tool plugins."""

    def __init__(self, plugins_dir: str = "./plugins"):
        self.plugins_dir = Path(plugins_dir)
        self.plugins: dict[str, Plugin] = {}
        self.plugins_dir.mkdir(exist_ok=True)

    def load_plugins(self, tool_registry):
        """Discover and load plugins from plugins directory."""
        if not self.plugins_dir.exists():
            logger.info("Plugins directory does not exist: %s", self.plugins_dir)
            return

        # add plugins dir to path
        plugin_path = str(self.plugins_dir.absolute())
        if plugin_path not in sys.path:
            sys.path.insert(0, plugin_path)

        for py_file in self.plugins_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue

            module_name = py_file.stem
            try:
                spec = importlib.util.spec_from_file_location(module_name, py_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    # look for plugin definition
                    if hasattr(module, "PLUGIN"):
                        plugin = module.PLUGIN
                        plugin.register_tools(tool_registry)
                        self.plugins[plugin.name] = plugin
                        logger.info("Loaded plugin: %s v%s", plugin.name, plugin.version)
            except Exception as e:
                logger.error("Failed to load plugin %s: %s", module_name, e)

    def list_plugins(self) -> list[dict]:
        """List loaded plugins."""
        return [
            {
                "name": p.name,
                "description": p.description,
                "version": p.version,
            }
            for p in self.plugins.values()
        ]


def create_example_plugin() -> str:
    """Create example plugin template."""
    return '''"""Example custom plugin."""

from app.core.tools import ToolDefinition


async def _example_handler(text: str) -> str:
    """Example tool handler."""
    return f"Processed: {text}"


async def register_tools(tool_registry):
    """Register custom tools."""
    tool_registry.register(
        ToolDefinition(
            name="example",
            description="Example custom tool",
            parameters={
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
            handler=_example_handler,
        )
    )


PLUGIN = type(
    "ExamplePlugin",
    (),
    {
        "name": "example",
        "description": "Example plugin",
        "version": "0.1.0",
        "register_tools": register_tools,
    },
)()
'''

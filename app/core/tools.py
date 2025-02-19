"""Tool use / function calling - let the LLM invoke external tools."""

from __future__ import annotations

import datetime
import json
import logging
import math
import re
from dataclasses import dataclass
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: dict  # JSON Schema
    handler: Callable[..., Awaitable[str]]


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any]


@dataclass
class ToolResult:
    name: str
    output: str
    success: bool = True


class ToolRegistry:
    """Registry of tools the LLM can invoke."""

    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}
        self._register_builtins()

    def register(self, tool: ToolDefinition):
        self._tools[tool.name] = tool
        logger.debug("Registered tool: %s", tool.name)

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def list_tools(self) -> list[dict]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            }
            for t in self._tools.values()
        ]

    async def execute(self, call: ToolCall) -> ToolResult:
        tool = self._tools.get(call.name)
        if not tool:
            return ToolResult(name=call.name, output=f"Unknown tool: {call.name}", success=False)
        try:
            output = await tool.handler(**call.arguments)
            return ToolResult(name=call.name, output=output)
        except Exception as e:
            logger.error("Tool %s failed: %s", call.name, e)
            return ToolResult(name=call.name, output=f"Error: {e}", success=False)

    def format_for_prompt(self) -> str:
        """Format tool definitions for inclusion in system prompt."""
        lines = ["Available tools:"]
        for t in self._tools.values():
            params = ", ".join(
                f"{k}: {v.get('type', 'string')}"
                for k, v in t.parameters.get("properties", {}).items()
            )
            lines.append(f"- {t.name}({params}): {t.description}")
        lines.append("\nTo use a tool, respond with: [TOOL: name(arg1=val1, arg2=val2)]")
        return "\n".join(lines)

    def parse_tool_calls(self, text: str) -> list[ToolCall]:
        """Parse tool calls from LLM response text."""
        pattern = r"\[TOOL:\s*(\w+)\((.*?)\)\]"
        calls = []
        for match in re.finditer(pattern, text):
            name = match.group(1)
            args_str = match.group(2)
            args = self._parse_args(args_str)
            calls.append(ToolCall(name=name, arguments=args))
        return calls

    def _parse_args(self, args_str: str) -> dict[str, Any]:
        args = {}
        for part in args_str.split(","):
            part = part.strip()
            if "=" in part:
                key, val = part.split("=", 1)
                args[key.strip()] = val.strip().strip("'\"")
        return args

    def _register_builtins(self):
        self.register(
            ToolDefinition(
                name="calculator",
                description="Evaluate a math expression",
                parameters={
                    "type": "object",
                    "properties": {"expression": {"type": "string"}},
                    "required": ["expression"],
                },
                handler=_calc_handler,
            )
        )
        self.register(
            ToolDefinition(
                name="current_time",
                description="Get the current date and time",
                parameters={"type": "object", "properties": {}},
                handler=_time_handler,
            )
        )
        self.register(
            ToolDefinition(
                name="web_search",
                description="Search the web for information",
                parameters={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
                handler=_search_handler,
            )
        )


async def _calc_handler(expression: str) -> str:
    """Safe math expression evaluator."""
    allowed = set("0123456789+-*/().^ ")
    cleaned = expression.replace("^", "**")
    if not all(c in allowed for c in cleaned):
        return "Error: invalid expression"
    try:
        result = eval(cleaned, {"__builtins__": {}}, {"math": math})
        return str(result)
    except Exception as e:
        return f"Error: {e}"


async def _time_handler() -> str:
    now = datetime.datetime.now()
    return now.strftime("%A, %B %d, %Y at %I:%M %p")


async def _search_handler(query: str) -> str:
    """Web search stub - integrate with actual search API."""
    import httpx

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": 1},
                timeout=10.0,
            )
            data = resp.json()
            abstract = data.get("AbstractText", "")
            if abstract:
                return abstract
            # fallback to related topics
            topics = data.get("RelatedTopics", [])[:3]
            results = [t.get("Text", "") for t in topics if isinstance(t, dict)]
            return "\n".join(results) if results else "No results found."
    except Exception as e:
        return f"Search failed: {e}"

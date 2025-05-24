"""MCP (Model Context Protocol) server for IDE integration."""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class MCPServer:
    """MCP server exposing heySwiftie as a tool for Claude, Cursor, etc."""

    def __init__(self, chat_service, memory_manager, task_manager):
        self.chat = chat_service
        self.memory = memory_manager
        self.tasks = task_manager

    async def handle_chat(self, session_id: str, message: str) -> dict:
        """Handle chat via MCP."""
        reply = await self.chat.respond(session_id, message)
        return {"type": "text", "content": reply}

    async def handle_memory_recall(self, query: str) -> dict:
        """Recall memories via MCP."""
        memories = self.memory.recall(query, limit=5)
        content = "\n".join([f"- {m.content}" for m in memories])
        return {"type": "text", "content": content}

    async def handle_task_list(self) -> dict:
        """Get task list via MCP."""
        tasks = self.tasks.list_tasks()
        content = "\n".join([f"- [{t.id}] {t.title}" for t in tasks])
        return {"type": "text", "content": content or "No pending tasks"}

    async def handle_user_facts(self) -> dict:
        """Get user facts via MCP."""
        facts = self.memory.get_user_facts()
        content = "\n".join([str(f) for f in facts])
        return {"type": "text", "content": content or "No facts stored yet"}

    def get_tools(self) -> list[dict]:
        """Return MCP tool definitions."""
        return [
            {
                "name": "swiftie_chat",
                "description": "Chat with Swiftie assistant with memory",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string"},
                        "session_id": {"type": "string"},
                    },
                    "required": ["message"],
                },
            },
            {
                "name": "swiftie_recall",
                "description": "Recall memories from Swiftie",
                "inputSchema": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            },
            {
                "name": "swiftie_tasks",
                "description": "Get task list from Swiftie",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "swiftie_facts",
                "description": "Get user facts from Swiftie",
                "inputSchema": {"type": "object", "properties": {}},
            },
        ]

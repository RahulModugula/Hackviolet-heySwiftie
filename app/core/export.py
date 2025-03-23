"""Export and backup functionality."""

from __future__ import annotations

import datetime
import json
from dataclasses import asdict, dataclass, field


@dataclass
class ConversationExport:
    """Exportable conversation data."""

    session_id: str
    created_at: str
    messages: list[dict] = field(default_factory=list)
    memories: list[dict] = field(default_factory=list)


class ExportService:
    """Handle exporting conversations and memories."""

    def __init__(self, conversation_store, memory_manager):
        self.store = conversation_store
        self.memory = memory_manager

    def export_session(self, session_id: str) -> dict:
        """Export a single session as JSON."""
        history = self.store.get_history(session_id, limit=10000)
        sessions = self.store.list_sessions()
        session_info = next((s for s in sessions if s["id"] == session_id), {})

        export = ConversationExport(
            session_id=session_id,
            created_at=session_info.get("created_at", ""),
            messages=history,
        )

        return asdict(export)

    def export_all_sessions(self) -> dict:
        """Export all sessions."""
        sessions = self.store.list_sessions()
        exports = []

        for session in sessions:
            export = self.export_session(session["id"])
            exports.append(export)

        return {
            "exported_at": datetime.datetime.utcnow().isoformat(),
            "total_sessions": len(exports),
            "sessions": exports,
        }

    def export_memories(self) -> dict:
        """Export all memories."""
        all_memories = self.store.get_all_memories()
        facts = self.memory.get_user_facts()

        memories_data = [
            {
                "id": m.id,
                "type": m.type.value,
                "content": m.content,
                "importance": m.importance,
                "created_at": m.created_at.isoformat(),
                "age_hours": m.age_hours,
            }
            for m in all_memories
        ]

        facts_data = [
            {
                "subject": f.subject,
                "predicate": f.predicate,
                "value": f.value,
                "confidence": f.confidence,
            }
            for f in facts
        ]

        return {
            "exported_at": datetime.datetime.utcnow().isoformat(),
            "memories": memories_data,
            "facts": facts_data,
            "total_memories": len(memories_data),
            "total_facts": len(facts_data),
        }

    def export_everything(self) -> dict:
        """Complete backup of all data."""
        return {
            "exported_at": datetime.datetime.utcnow().isoformat(),
            "version": "0.5.0",
            "conversations": self.export_all_sessions(),
            "memories": self.export_memories(),
        }

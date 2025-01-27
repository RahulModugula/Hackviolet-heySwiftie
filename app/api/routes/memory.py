"""Memory API routes."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("/facts")
async def get_user_facts():
    """Get extracted semantic facts about the user."""
    from app.dependencies import memory_manager
    facts = memory_manager.get_user_facts()
    return [
        {"subject": f.subject, "predicate": f.predicate, "value": f.value, "confidence": f.confidence}
        for f in facts
    ]


@router.get("/recall")
async def recall(q: str, limit: int = 10):
    """Recall memories relevant to a query."""
    from app.dependencies import memory_manager
    memories = memory_manager.recall(q, limit=limit)
    return [
        {
            "id": m.id,
            "type": m.type.value,
            "content": m.content,
            "importance": m.importance,
            "age_hours": round(m.age_hours, 1),
        }
        for m in memories
    ]


@router.post("/consolidate")
async def consolidate():
    """Trigger memory consolidation (prune old low-importance memories)."""
    from app.dependencies import memory_manager
    memory_manager.consolidate()
    return {"status": "ok"}

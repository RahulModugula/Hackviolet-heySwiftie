"""Routes for new features (v0.6.0)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/features", tags=["features"])


class ExportResponse(BaseModel):
    format: str
    data: dict


@router.post("/export/session/{session_id}")
async def export_session(session_id: str):
    """Export a session as JSON."""
    from app.dependencies import export_service

    export = export_service.export_session(session_id)
    return {"session_id": session_id, "export": export}


@router.get("/export/all")
async def export_all():
    """Export all data."""
    from app.dependencies import export_service

    return export_service.export_everything()


@router.get("/summarize/{session_id}")
async def summarize_session(session_id: str):
    """Get summary of a session."""
    from app.dependencies import summarizer

    summary = summarizer.summarize(session_id)
    return {
        "session_id": session_id,
        "title": summary.title,
        "key_points": summary.key_points,
    }


@router.get("/mood/{session_id}")
async def get_mood(session_id: str):
    """Analyze mood in a session."""
    from app.dependencies import mood_tracker

    return mood_tracker.analyze_mood(session_id)


@router.get("/mood/timeline")
async def get_mood_timeline(limit: int = 10):
    """Get mood timeline across sessions."""
    from app.dependencies import mood_tracker

    return {"timeline": mood_tracker.get_mood_timeline(limit_sessions=limit)}


@router.get("/habits")
async def get_habits():
    """Detect and retrieve habit patterns."""
    from app.dependencies import habit_tracker

    return habit_tracker.get_habit_insights()


@router.get("/reminders")
async def get_reminders():
    """Get current reminders."""
    from app.dependencies import reminder_engine

    reminders = reminder_engine.generate_reminders()
    return [
        {
            "text": r.text,
            "trigger": r.trigger,
            "confidence": r.confidence,
            "context": r.context,
        }
        for r in reminders
    ]


@router.get("/plugins")
async def list_plugins():
    """List loaded plugins."""
    from app.dependencies import plugin_manager

    return {"plugins": plugin_manager.list_plugins()}


@router.get("/knowledge-graph/related/{fact_id}")
async def get_related_facts(fact_id: str):
    """Get facts related to a given fact."""
    from app.dependencies import knowledge_graph

    related = knowledge_graph.get_related_facts(fact_id, depth=2)
    return {"fact_id": fact_id, "related_facts": related}


@router.post("/knowledge-graph/build")
async def build_knowledge_graph():
    """Build knowledge graph from facts."""
    from app.dependencies import knowledge_graph

    knowledge_graph.build_from_facts()
    return {"status": "ok", "nodes": len(knowledge_graph.nodes)}


@router.get("/daily-digest")
async def get_daily_digest():
    """Get daily digest of activity."""
    from app.dependencies import (
        suggestion_engine,
        task_manager,
        mood_tracker,
        conversation_store,
    )

    sessions = conversation_store.list_sessions()
    suggestions = suggestion_engine.generate()
    overdue_tasks = task_manager.overdue() if task_manager else []

    return {
        "timestamp": "2026-03-27T00:00:00Z",
        "sessions_today": len(sessions),
        "pending_tasks": len(task_manager.list_tasks()) if task_manager else 0,
        "overdue_tasks": len(overdue_tasks),
        "suggestions": [
            {"text": s.text, "category": s.category, "confidence": s.confidence}
            for s in suggestions[:5]
        ],
    }

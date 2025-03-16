"""Search routes for full-text conversation search."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/search", tags=["search"])


class SearchRequest(BaseModel):
    query: str
    limit: int = 20


@router.post("/conversations")
async def search_conversations(req: SearchRequest):
    """Full-text search across all conversations."""
    from app.core.search import ConversationSearcher
    from app.dependencies import conversation_store

    searcher = ConversationSearcher(conversation_store)
    results = searcher.search(req.query, req.limit)

    return [
        {
            "session_id": r.session_id,
            "role": r.role,
            "content": r.content[:200],
            "relevance_score": round(r.relevance_score, 2),
        }
        for r in results
    ]


@router.get("/sessions/{session_id}/summary")
async def get_session_summary(session_id: str):
    """Get a brief summary of a session."""
    from app.core.search import ConversationSearcher
    from app.dependencies import conversation_store

    searcher = ConversationSearcher(conversation_store)
    summary = searcher.summarize_session(session_id)

    return {"session_id": session_id, "summary": summary}

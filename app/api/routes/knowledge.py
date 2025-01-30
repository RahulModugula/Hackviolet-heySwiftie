"""Knowledge base routes - ingest documents."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class IngestRequest(BaseModel):
    source: str  # URL or file path


@router.post("/ingest")
async def ingest(req: IngestRequest):
    from app.dependencies import knowledge_base
    try:
        chunks = await knowledge_base.ingest(req.source)
        return {"status": "ok", "chunks": chunks, "source": req.source}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/stats")
async def stats():
    from app.dependencies import knowledge_base
    return knowledge_base.stats

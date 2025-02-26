"""Chat API routes."""

from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends
from pydantic import BaseModel

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str


def get_chat_service():
    from app.dependencies import chat_service
    return chat_service


@router.post("/", response_model=ChatResponse)
async def chat(req: ChatRequest):
    from app.dependencies import chat_service
    session_id = req.session_id or str(uuid.uuid4())
    reply = await chat_service.respond(session_id, req.message)
    return ChatResponse(reply=reply, session_id=session_id)


@router.get("/sessions")
async def list_sessions():
    from app.dependencies import memory_manager
    return memory_manager.get_sessions()


@router.get("/sessions/{session_id}/history")
async def get_history(session_id: str, limit: int = 50):
    from app.dependencies import memory_manager
    return memory_manager.get_context(session_id)

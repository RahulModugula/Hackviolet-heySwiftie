"""WebSocket endpoint for streaming responses."""

from __future__ import annotations

import json
import logging
import uuid

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


async def ws_chat(websocket: WebSocket):
    """
    WebSocket chat endpoint with token streaming.

    Client sends:  {"message": "...", "session_id": "..."}
    Server sends:  {"type": "token", "delta": "..."}
                   {"type": "done", "session_id": "..."}
                   {"type": "error", "detail": "..."}
    """
    await websocket.accept()
    from app.dependencies import chat_service

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "detail": "invalid JSON"})
                continue

            message = data.get("message", "").strip()
            if not message:
                continue

            session_id = data.get("session_id") or str(uuid.uuid4())

            try:
                async for delta in chat_service.stream_respond(session_id, message):
                    await websocket.send_json({"type": "token", "delta": delta})
                await websocket.send_json({"type": "done", "session_id": session_id})
            except Exception as e:
                logger.error("Streaming error: %s", e)
                await websocket.send_json({"type": "error", "detail": str(e)})

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")

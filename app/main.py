"""heySwiftie - FastAPI application entry point."""

from __future__ import annotations

import logging

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import chat, voice, memory, knowledge, tasks, eval, search, features
from app.api.websocket import ws_chat

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="heySwiftie",
    description="Intelligent virtual assistant with persistent memory and voice",
    version="0.5.0",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST routes
for router in [chat.router, voice.router, memory.router, knowledge.router, tasks.router, eval.router, search.router, features.router]:
    app.include_router(router, prefix="/api")

# WebSocket
app.add_api_websocket_route("/ws/chat", ws_chat)


@app.get("/health")
async def health():
    from app.dependencies import vector_store, conversation_store
    return {
        "status": "ok",
        "indexed_docs": vector_store.count(),
    }


@app.get("/")
async def root():
    return {
        "name": "heySwiftie",
        "version": "0.5.0",
        "docs": "/docs",
        "websocket": "/ws/chat",
    }

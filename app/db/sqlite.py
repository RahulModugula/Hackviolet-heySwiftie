"""SQLite storage layer for conversations and memories."""

from __future__ import annotations

import datetime
import json
from enum import Enum

from sqlalchemy import Column, String, Text, DateTime, Integer, Float, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.memory import Memory, MemoryType


class Base(DeclarativeBase):
    pass


class ConversationRow(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), index=True, nullable=False)
    role = Column(String(16), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)


class SessionRow(Base):
    __tablename__ = "sessions"
    id = Column(String(64), primary_key=True)
    title = Column(String(256), default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)


class MemoryRow(Base):
    __tablename__ = "memories"
    id = Column(String(64), primary_key=True)
    type = Column(String(32), nullable=False)
    content = Column(Text, nullable=False)
    importance = Column(Float, default=0.5)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_accessed = Column(DateTime, default=datetime.datetime.utcnow)
    access_count = Column(Integer, default=0)
    meta = Column(Text, default="{}")  # JSON


class ConversationStore:
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self._Session = sessionmaker(bind=self.engine)

    def add_message(self, session_id: str, role: str, content: str):
        with self._Session() as db:
            if not db.query(SessionRow).filter(SessionRow.id == session_id).first():
                db.add(SessionRow(id=session_id))
            db.add(ConversationRow(session_id=session_id, role=role, content=content))
            db.commit()

    def get_history(self, session_id: str, limit: int = 20) -> list[dict]:
        with self._Session() as db:
            rows = (
                db.query(ConversationRow)
                .filter(ConversationRow.session_id == session_id)
                .order_by(ConversationRow.timestamp.desc())
                .limit(limit)
                .all()
            )
        rows.reverse()
        return [{"role": r.role, "content": r.content} for r in rows]

    def list_sessions(self) -> list[dict]:
        with self._Session() as db:
            sessions = db.query(SessionRow).order_by(SessionRow.updated_at.desc()).all()
        return [{"id": s.id, "title": s.title, "created_at": str(s.created_at)} for s in sessions]

    def add_memory(self, memory: Memory):
        with self._Session() as db:
            existing = db.query(MemoryRow).filter(MemoryRow.id == memory.id).first()
            if existing:
                existing.content = memory.content
                existing.importance = memory.importance
                existing.meta = json.dumps(memory.metadata)
            else:
                db.add(MemoryRow(
                    id=memory.id,
                    type=memory.type.value,
                    content=memory.content,
                    importance=memory.importance,
                    created_at=memory.created_at,
                    meta=json.dumps(memory.metadata),
                ))
            db.commit()

    def search_memories(self, query: str, memory_type=None, limit: int = 20) -> list[Memory]:
        with self._Session() as db:
            q = db.query(MemoryRow)
            if memory_type:
                q = q.filter(MemoryRow.type == memory_type.value)
            # simple keyword search
            words = query.lower().split()[:3]
            rows = q.order_by(MemoryRow.importance.desc()).limit(limit * 2).all()
        results = []
        for row in rows:
            content_lower = row.content.lower()
            if any(w in content_lower for w in words):
                results.append(self._row_to_memory(row))
        return results[:limit]

    def get_all_memories(self) -> list[Memory]:
        with self._Session() as db:
            rows = db.query(MemoryRow).all()
        return [self._row_to_memory(r) for r in rows]

    def delete_memory(self, memory_id: str):
        with self._Session() as db:
            db.query(MemoryRow).filter(MemoryRow.id == memory_id).delete()
            db.commit()

    def _row_to_memory(self, row: MemoryRow) -> Memory:
        return Memory(
            id=row.id,
            type=MemoryType(row.type),
            content=row.content,
            importance=row.importance,
            created_at=row.created_at,
            last_accessed=row.last_accessed,
            access_count=row.access_count,
            metadata=json.loads(row.meta or "{}"),
        )

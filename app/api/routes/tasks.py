"""Task management routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/tasks", tags=["tasks"])


class CreateTaskRequest(BaseModel):
    title: str
    description: str = ""
    priority: str = "medium"
    natural_language: bool = False


@router.post("/")
async def create_task(req: CreateTaskRequest):
    from app.dependencies import task_manager
    from app.core.tasks import Priority

    if req.natural_language:
        task = task_manager.from_natural_language(req.title)
    else:
        try:
            priority = Priority[req.priority.upper()]
        except KeyError:
            priority = Priority.MEDIUM
        task = task_manager.create(req.title, req.description, priority)
    return task.to_dict()


@router.get("/")
async def list_tasks(include_done: bool = False, tag: str | None = None):
    from app.dependencies import task_manager
    return [t.to_dict() for t in task_manager.list_tasks(include_done, tag)]


@router.patch("/{task_id}/complete")
async def complete_task(task_id: str):
    from app.dependencies import task_manager
    if not task_manager.complete(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "ok"}


@router.delete("/{task_id}")
async def delete_task(task_id: str):
    from app.dependencies import task_manager
    if not task_manager.delete(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "ok"}


@router.get("/suggestions")
async def get_suggestions():
    from app.dependencies import suggestion_engine
    suggestions = suggestion_engine.generate()
    return [
        {"text": s.text, "category": s.category, "confidence": s.confidence}
        for s in suggestions
    ]


@router.get("/overdue")
async def get_overdue():
    from app.dependencies import task_manager
    return [t.to_dict() for t in task_manager.overdue()]

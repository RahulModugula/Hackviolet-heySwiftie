"""Task management - todo list with priorities and natural language creation."""

from __future__ import annotations

import datetime
import re
import uuid
from dataclasses import dataclass, field
from enum import IntEnum


class Priority(IntEnum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    URGENT = 3


@dataclass
class Task:
    id: str
    title: str
    description: str = ""
    priority: Priority = Priority.MEDIUM
    done: bool = False
    created_at: datetime.datetime = field(default_factory=datetime.datetime.utcnow)
    due_date: datetime.datetime | None = None
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority.name.lower(),
            "done": self.done,
            "created_at": self.created_at.isoformat(),
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "tags": self.tags,
        }


class TaskManager:
    def __init__(self):
        self._tasks: dict[str, Task] = {}

    def create(
        self,
        title: str,
        description: str = "",
        priority: Priority = Priority.MEDIUM,
        due_date: datetime.datetime | None = None,
        tags: list[str] | None = None,
    ) -> Task:
        task = Task(
            id=str(uuid.uuid4())[:8],
            title=title,
            description=description,
            priority=priority,
            due_date=due_date,
            tags=tags or [],
        )
        self._tasks[task.id] = task
        return task

    def get(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def complete(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task:
            task.done = True
            return True
        return False

    def delete(self, task_id: str) -> bool:
        return self._tasks.pop(task_id, None) is not None

    def list_tasks(
        self, include_done: bool = False, tag: str | None = None
    ) -> list[Task]:
        tasks = list(self._tasks.values())
        if not include_done:
            tasks = [t for t in tasks if not t.done]
        if tag:
            tasks = [t for t in tasks if tag in t.tags]
        tasks.sort(key=lambda t: (-t.priority, t.created_at))
        return tasks

    def overdue(self) -> list[Task]:
        now = datetime.datetime.utcnow()
        return [
            t for t in self._tasks.values()
            if t.due_date and t.due_date < now and not t.done
        ]

    def from_natural_language(self, text: str) -> Task:
        """Parse natural language into a task."""
        title = text.strip()
        priority = Priority.MEDIUM
        due_date = None
        tags = []

        # extract priority
        if re.search(r"\b(urgent|asap|critical)\b", text, re.IGNORECASE):
            priority = Priority.URGENT
        elif re.search(r"\b(important|high)\b", text, re.IGNORECASE):
            priority = Priority.HIGH
        elif re.search(r"\b(low|whenever|someday)\b", text, re.IGNORECASE):
            priority = Priority.LOW

        # extract tags with #
        tag_matches = re.findall(r"#(\w+)", text)
        tags = tag_matches

        # extract due date patterns
        tomorrow_match = re.search(r"\b(tomorrow)\b", text, re.IGNORECASE)
        if tomorrow_match:
            due_date = datetime.datetime.utcnow() + datetime.timedelta(days=1)
            title = title.replace(tomorrow_match.group(), "").strip()

        # clean title
        title = re.sub(r"#\w+", "", title).strip()
        title = re.sub(r"\b(urgent|asap|critical|important|high|low|whenever|someday)\b", "", title, flags=re.IGNORECASE).strip()
        title = re.sub(r"\s+", " ", title)

        return self.create(title=title, priority=priority, due_date=due_date, tags=tags)

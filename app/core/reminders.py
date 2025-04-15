"""Smart context-aware reminders."""

from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Reminder:
    text: str
    trigger: str  # "task_overdue" | "mentioned_again" | "time_based"
    confidence: float
    context: str = ""


class ReminderEngine:
    """Generate context-aware reminders."""

    def __init__(self, task_manager, suggestion_engine):
        self.tasks = task_manager
        self.suggestions = suggestion_engine

    def generate_reminders(self) -> list[Reminder]:
        """Generate reminders based on context."""
        reminders = []

        # task-based reminders
        if self.tasks:
            overdue = self.tasks.overdue()
            for task in overdue[:2]:
                reminders.append(
                    Reminder(
                        text=f"'{task.title}' is overdue",
                        trigger="task_overdue",
                        confidence=0.95,
                        context=f"Due: {task.due_date}",
                    )
                )

        # pattern-based reminders
        habits = self.suggestions._find_recurring_topics()
        for topic, count in habits[:1]:
            if count >= 3:
                reminders.append(
                    Reminder(
                        text=f"You've been interested in '{topic}' - want to discuss it?",
                        trigger="mentioned_again",
                        confidence=0.6,
                    )
                )

        # time-based reminders
        now = datetime.datetime.utcnow()
        if now.hour == 9:  # morning
            reminders.append(
                Reminder(
                    text="Good morning! Ready to tackle today's tasks?",
                    trigger="time_based",
                    confidence=0.5,
                )
            )

        return reminders

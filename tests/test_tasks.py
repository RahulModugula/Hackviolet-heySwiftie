"""Tests for task management."""

import datetime
import pytest
from app.core.tasks import TaskManager, Priority


@pytest.fixture
def tm():
    return TaskManager()


def test_create_task(tm):
    task = tm.create("Buy groceries", priority=Priority.HIGH)
    assert task.title == "Buy groceries"
    assert task.priority == Priority.HIGH
    assert not task.done


def test_complete_task(tm):
    task = tm.create("Do laundry")
    assert tm.complete(task.id)
    assert tm.get(task.id).done


def test_complete_nonexistent(tm):
    assert not tm.complete("fake-id")


def test_delete_task(tm):
    task = tm.create("Test task")
    assert tm.delete(task.id)
    assert tm.get(task.id) is None


def test_list_excludes_done_by_default(tm):
    t1 = tm.create("active task")
    t2 = tm.create("done task")
    tm.complete(t2.id)

    active = tm.list_tasks()
    ids = [t.id for t in active]
    assert t1.id in ids
    assert t2.id not in ids


def test_list_includes_done_when_requested(tm):
    t = tm.create("some task")
    tm.complete(t.id)
    all_tasks = tm.list_tasks(include_done=True)
    assert any(task.id == t.id for task in all_tasks)


def test_priority_ordering(tm):
    tm.create("low priority", priority=Priority.LOW)
    tm.create("urgent task", priority=Priority.URGENT)
    tm.create("medium task", priority=Priority.MEDIUM)

    tasks = tm.list_tasks()
    assert tasks[0].priority == Priority.URGENT


def test_tag_filtering(tm):
    tm.create("work task", tags=["work"])
    tm.create("personal task", tags=["personal"])
    tm.create("both", tags=["work", "personal"])

    work_tasks = tm.list_tasks(tag="work")
    assert all("work" in t.tags for t in work_tasks)
    assert len(work_tasks) == 2


def test_overdue_detection(tm):
    past = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    future = datetime.datetime.utcnow() + datetime.timedelta(days=1)

    tm.create("overdue task", due_date=past)
    tm.create("future task", due_date=future)
    tm.create("no due date")

    overdue = tm.overdue()
    assert len(overdue) == 1
    assert overdue[0].title == "overdue task"


def test_natural_language_urgent(tm):
    task = tm.from_natural_language("urgent fix the login bug")
    assert task.priority == Priority.URGENT


def test_natural_language_tags(tm):
    task = tm.from_natural_language("finish the report #work #deadline")
    assert "work" in task.tags
    assert "deadline" in task.tags


def test_natural_language_tomorrow(tm):
    task = tm.from_natural_language("call the dentist tomorrow")
    assert task.due_date is not None
    expected = datetime.datetime.utcnow() + datetime.timedelta(days=1)
    diff = abs((task.due_date - expected).total_seconds())
    assert diff < 120  # within 2 minutes


def test_task_to_dict(tm):
    task = tm.create("test", description="desc", priority=Priority.HIGH)
    d = task.to_dict()
    assert d["priority"] == "high"
    assert "id" in d
    assert "created_at" in d

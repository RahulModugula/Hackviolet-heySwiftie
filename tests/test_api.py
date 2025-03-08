"""Integration tests for the API."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    # patch dependencies before importing app
    with patch("app.dependencies.get_provider") as mock_provider, \
         patch("app.dependencies.VectorStore"), \
         patch("app.dependencies.ConversationStore"):

        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value=MagicMock(content="Hello!", model="test"))
        mock_provider.return_value = mock_llm

        from app.main import app
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "heySwiftie"


def test_tasks_create_and_list(client):
    # create a task
    r = client.post("/api/tasks/", json={"title": "test task", "priority": "high"})
    assert r.status_code == 200
    task = r.json()
    assert task["title"] == "test task"
    assert task["priority"] == "high"

    # list tasks
    r = client.get("/api/tasks/")
    assert r.status_code == 200
    tasks = r.json()
    assert any(t["id"] == task["id"] for t in tasks)


def test_tasks_complete(client):
    r = client.post("/api/tasks/", json={"title": "complete me"})
    task_id = r.json()["id"]

    r = client.patch(f"/api/tasks/{task_id}/complete")
    assert r.status_code == 200


def test_tasks_complete_not_found(client):
    r = client.patch("/api/tasks/fakeid/complete")
    assert r.status_code == 404


def test_memory_facts_empty(client):
    r = client.get("/api/memory/facts")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_eval_metrics(client):
    r = client.get("/api/eval/metrics")
    assert r.status_code == 200
    data = r.json()
    assert "n_samples" in data


def test_knowledge_stats(client):
    r = client.get("/api/knowledge/stats")
    assert r.status_code == 200

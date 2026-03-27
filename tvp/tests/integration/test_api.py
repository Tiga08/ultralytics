import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from api.app import create_app
from api.deps import get_engine


@pytest.fixture
def client_with_engine():
    mock_engine = MagicMock()
    mock_engine.list_tasks.return_value = []
    app = create_app()
    app.dependency_overrides[get_engine] = lambda: mock_engine
    yield TestClient(app), mock_engine
    app.dependency_overrides.clear()


def test_health_endpoint(client_with_engine):
    client, _ = client_with_engine
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "healthy" in data
    assert "task_count" in data


def test_create_task_success(client_with_engine):
    client, mock_engine = client_with_engine
    resp = client.post("/api/v1/tasks", json={
        "task_id": "test_task_001",
        "camera": {"id": "CAM_001", "rtsp_url": "rtsp://localhost/test"},
        "detectors": [{"name": "regional_invasion", "config": {}}],
    })
    assert resp.status_code == 201
    assert resp.json()["success"] is True
    mock_engine.create_task.assert_called_once()


def test_create_task_duplicate_returns_409(client_with_engine):
    client, mock_engine = client_with_engine
    mock_engine.create_task.side_effect = ValueError("already exists")
    resp = client.post("/api/v1/tasks", json={
        "task_id": "dup",
        "camera": {"id": "C", "rtsp_url": "rtsp://x/s"},
        "detectors": [],
    })
    assert resp.status_code == 409


def test_get_task_not_found(client_with_engine):
    client, mock_engine = client_with_engine
    mock_engine.get_task_status.side_effect = KeyError("nope")
    resp = client.get("/api/v1/tasks/nonexistent")
    assert resp.status_code == 404


def test_list_tasks(client_with_engine):
    client, mock_engine = client_with_engine
    mock_engine.list_tasks.return_value = [{"task_id": "t1", "status": "running"}]
    resp = client.get("/api/v1/tasks")
    assert resp.status_code == 200


def test_plugins_endpoint_has_regional_invasion(client_with_engine):
    client, _ = client_with_engine
    resp = client.get("/api/v1/plugins")
    assert resp.status_code == 200
    data = resp.json()
    assert "regional_invasion" in data["detectors"]


def test_pause_task_not_found(client_with_engine):
    client, mock_engine = client_with_engine
    mock_engine.pause_task.side_effect = KeyError("nope")
    resp = client.post("/api/v1/tasks/nonexistent/pause")
    assert resp.status_code == 404

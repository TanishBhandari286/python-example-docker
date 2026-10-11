import pytest

from taskboard import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app({"DATABASE_PATH": str(tmp_path / "test.db"), "TESTING": True})
    return app.test_client()


def test_health(client):
    assert client.get("/healthz").json == {"status": "ok"}
    assert client.get("/readyz").json == {"status": "ready"}


def test_task_lifecycle(client):
    assert client.get("/api/tasks").json == []
    created = client.post("/api/tasks", json={"title": "write Dockerfile"})
    assert created.status_code == 201
    task_id = created.json["id"]
    done = client.patch(f"/api/tasks/{task_id}", json={"done": True})
    assert done.json["done"] is True
    assert client.delete(f"/api/tasks/{task_id}").status_code == 204
    assert client.get("/api/tasks").json == []


def test_validation(client):
    assert client.post("/api/tasks", json={}).status_code == 400
    assert client.delete("/api/tasks/999").status_code == 404

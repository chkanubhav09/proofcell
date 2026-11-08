"""API plumbing tests. No docker, no LLM: sandbox/planner paths are stubbed."""
from fastapi.testclient import TestClient

from app.ledger import Ledger
from app.main import app
from app.runner import Run, manager

client = TestClient(app)


def test_create_run_rejects_empty():
    r = client.post("/api/runs", json={"task": "   "})
    assert r.status_code == 400


def test_create_run_rejects_overlong():
    r = client.post("/api/runs", json={"task": "x" * 2001})
    assert r.status_code == 400


def test_unknown_run_404s():
    assert client.get("/api/runs/nope").status_code == 404
    assert client.get("/api/runs/nope/ledger").status_code == 404
    assert client.get("/api/runs/nope/verify").status_code == 404


def test_verify_endpoint_on_sealed_run():
    run = Run("demo task")
    run.ledger.append("plan", {"task": "demo task"})
    run.seal()
    manager.runs[run.id] = run
    try:
        v = client.get(f"/api/runs/{run.id}/verify").json()
        assert v["valid"] is True and v["events"] == 2
        l = client.get(f"/api/runs/{run.id}/ledger").json()
        assert Ledger.from_dict(l).verify()
    finally:
        del manager.runs[run.id]

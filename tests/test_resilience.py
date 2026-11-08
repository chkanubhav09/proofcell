"""Fallback behavior: planner outage degrades labeled, docker outage fails closed."""
from app import planner
from app.models import Plan, Step, StepKind, RunStatus
from app.runner import Run, manager


def test_offline_fallback_when_no_key(monkeypatch):
    monkeypatch.setattr(planner.settings, "vultr_inference_api_key", "")
    plan, offline = planner.plan("analyze sales.csv")
    assert offline is True
    assert all(s.label.startswith("offline:") for s in plan.steps)


def test_offline_fallback_on_any_inference_error(monkeypatch):
    class BoomClient:
        class chat:
            class completions:
                @staticmethod
                def create(**kw):
                    raise ConnectionError("inference endpoint down")
    monkeypatch.setattr(planner.settings, "vultr_inference_api_key", "fake-key")
    monkeypatch.setattr(planner, "_client", lambda: BoomClient())
    plan, offline = planner.plan("analyze sales.csv")
    assert offline is True


def test_real_plan_not_labeled_offline(monkeypatch):
    from types import SimpleNamespace as NS
    payload = '{"task": "t", "steps": [{"kind": "shell", "label": "ls", "command": "ls /work", "code": null, "url": null, "actions": [], "expects_approval": false}]}'
    resp = NS(choices=[NS(message=NS(content=payload))])
    ok_client = NS(chat=NS(completions=NS(create=lambda **kw: resp)))
    monkeypatch.setattr(planner.settings, "vultr_inference_api_key", "fake-key")
    monkeypatch.setattr(planner, "_client", lambda: ok_client)
    plan, offline = planner.plan("t")
    assert offline is False and plan.steps[0].command == "ls /work"


def test_run_marks_offline_plan_in_ledger(monkeypatch):
    monkeypatch.setattr("app.runner.make_plan", lambda task: (planner.plan_offline(task), True))
    monkeypatch.setattr("app.runner.Sandbox", _FakeSandbox)
    run = Run("demo")
    manager._execute(run)
    msgs = [e["payload"].get("msg", "") for e in run.ledger.events if e["kind"] == "note"]
    assert any("OFFLINE FALLBACK" in m for m in msgs)
    assert run.status == RunStatus.completed


def test_docker_outage_fails_closed(monkeypatch):
    from app.sandbox import SandboxUnavailable
    monkeypatch.setattr("app.runner.make_plan",
                        lambda task: (Plan(task="t", steps=[Step(kind=StepKind.shell, label="ls", command="ls")]), False))
    class NoDocker:
        def __init__(self, ledger, run_id): pass
        def __enter__(self): raise SandboxUnavailable("cannot connect to docker daemon")
        def __exit__(self, *a): pass
    monkeypatch.setattr("app.runner.Sandbox", NoDocker)
    run = Run("demo")
    manager._execute(run)
    assert run.status == RunStatus.failed
    msgs = [e["payload"].get("msg", "") for e in run.ledger.events if e["kind"] == "note"]
    assert any("sandbox unavailable" in m.lower() for m in msgs)
    assert run.verify()  # even a failed run keeps an intact chain


class _FakeSandbox:
    def __init__(self, ledger, run_id):
        self.ledger = ledger
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def run_step(self, i, step):
        from app.models import StepResult
        return StepResult(step_index=i, label=step.label, exit_code=0, stdout="ok")

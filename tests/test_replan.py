"""Error-feedback retry loop: the AI core's repair behavior."""
from __future__ import annotations

from unittest import mock

from app.models import Plan, Step, StepKind, StepResult
from app.runner import RunManager


def _plan(*labels):
    return Plan(task="t", steps=[
        Step(kind=StepKind.shell, label=l, command=f"cmd {l}") for l in labels])


def _result(i, label, code):
    return StepResult(step_index=i, label=label, exit_code=code,
                      stderr="boom" if code else "")


class _FakeSandbox:
    """One scripted failing step, then success; records executed labels."""
    def __init__(self, ledger, run_id, fail_labels=()):
        self._fail = set(fail_labels)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def run_step(self, i, step):
        return _result(i, step.label, 1 if step.label in self._fail else 0)


def _drive(monkeypatch, fail_labels, replan_return):
    mgr = RunManager()
    with mock.patch("app.runner.make_plan", return_value=(_plan("a", "b", "c"), False)), \
         mock.patch("app.runner.make_replan", return_value=replan_return) as rp, \
         mock.patch("app.runner.Sandbox", lambda l, r: _FakeSandbox(l, r, fail_labels)):
        run = mgr.start("task")
        import time
        for _ in range(100):
            if run.status.value in ("completed", "failed"):
                break
            time.sleep(0.05)
    return run, rp


def test_failed_step_triggers_repair_and_splices(monkeypatch):
    run, rp = _drive(monkeypatch, {"b"}, (_plan("b2", "c2"), True))
    assert run.status.value == "completed"
    rp.assert_called_once()
    kinds = [e["kind"] for e in run.ledger.to_dict()["events"]]
    assert "replan" in kinds
    labels = [r.label for r in run.results]
    assert "b2" in labels and "c2" in labels and "c" not in labels


def test_retry_cap_stops_second_repair(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "planner_max_retries", 1)
    run, rp = _drive(monkeypatch, {"a", "b"}, (_plan("x"), True))
    assert rp.call_count == 1  # second failure gets no more repairs


def test_no_repair_means_continue_original(monkeypatch):
    run, rp = _drive(monkeypatch, {"b"}, (None, False))
    assert run.status.value == "completed"
    labels = [r.label for r in run.results]
    assert "c" in labels  # original remaining step still ran
    kinds = [e["kind"] for e in run.ledger.to_dict()["events"]]
    assert "replan" not in kinds


def test_offline_plan_never_repairs(monkeypatch):
    mgr = RunManager()
    with mock.patch("app.runner.make_plan", return_value=(_plan("a"), True)), \
         mock.patch("app.runner.make_replan") as rp, \
         mock.patch("app.runner.Sandbox", lambda l, r: _FakeSandbox(l, r, {"a"})):
        run = mgr.start("task")
        import time
        for _ in range(100):
            if run.status.value in ("completed", "failed"):
                break
            time.sleep(0.05)
    rp.assert_not_called()
    assert run.status.value == "completed"


def test_replan_request_uses_error_context():
    from app import planner
    with mock.patch.object(planner, "_call", return_value=_plan("fixed")) as c, \
         mock.patch.object(planner.settings, "vultr_inference_api_key", "k"):
        fixed, repaired = planner.replan("task", "bad step", "stderr text", ["ok step"])
    assert repaired and fixed is not None
    user_msg = c.call_args[0][1]
    assert "bad step" in user_msg and "stderr text" in user_msg


def test_replan_returns_none_without_key():
    from app import planner
    with mock.patch.object(planner.settings, "vultr_inference_api_key", ""):
        assert planner.replan("t", "l", "e", []) == (None, False)

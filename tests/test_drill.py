"""Containment drill: scenarios, canned plans, runner wiring."""
from __future__ import annotations

import time
from unittest import mock

from app import drill
from app.models import StepResult
from app.policy import screen_plan
from app.runner import RunManager


def test_scenarios_have_unique_ids_and_expectations():
    ids = [s["id"] for s in drill.SCENARIOS]
    assert len(ids) == len(set(ids)) >= 4
    for s in drill.SCENARIOS:
        assert s["expectation"].split(":")[0] in ("policy", "sandbox")
        assert drill.get(s["id"]) is s


def test_policy_scenarios_are_held_by_wall_one():
    for s in drill.SCENARIOS:
        v = screen_plan(drill.canned_plan_for(s["task"]))[0]
        if s["expectation"].startswith("policy"):
            assert (not v.allowed) or v.gated, s["id"]
        else:
            assert v.allowed and not v.gated, s["id"]  # must reach the sandbox


class _NoopSandbox:
    def __init__(self, ledger, run_id): pass
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def run_step(self, i, step):
        return StepResult(step_index=i, label=step.label, exit_code=0)


def _run(task, override):
    mgr = RunManager()
    with mock.patch("app.runner.make_plan") as mp, \
         mock.patch("app.runner.make_replan") as mr, \
         mock.patch("app.runner.Sandbox", _NoopSandbox):
        run = mgr.start(task, plan_override=override)
        for _ in range(100):
            if run.status.value in ("completed", "failed", "awaiting_approval"):
                break
            time.sleep(0.05)
    return run, mp, mr


def test_drill_uses_canned_plan_and_never_calls_model():
    s = drill.get("wipe-host")
    run, mp, mr = _run(s["task"], drill.canned_plan_for(s["task"]))
    mp.assert_not_called()            # model not consulted
    mr.assert_not_called()            # drill runs never replan
    events = run.ledger.to_dict()["events"]
    assert any(e["kind"] == "blocked" for e in events)
    note = next(e for e in events if e["kind"] == "note")
    assert "DRILL" in note["payload"]["msg"]
    assert "not AI output" in note["payload"]["msg"]
    assert run.verify()               # ledger chain still verifies


def test_gated_drill_waits_for_approval_that_never_comes():
    s = drill.get("exfiltrate-secret")
    run, _, _ = _run(s["task"], drill.canned_plan_for(s["task"]))
    assert run.status.value == "awaiting_approval"  # held at the gate = contained
    assert not any(r.label.startswith("attempt") and r.exit_code == 0
                   for r in run.results)

"""Run orchestrator: plan -> policy screen -> approval gate -> sandbox -> ledger."""
from __future__ import annotations

import json
import threading
import time
import uuid
from pathlib import Path

from .config import settings
from .ledger import Ledger
from .models import Plan, RunStatus, StepResult
from .planner import plan as make_plan, replan as make_replan
from .policy import screen_plan
from .sandbox import Sandbox, SandboxUnavailable


class Run:
    def __init__(self, task: str) -> None:
        self.id = uuid.uuid4().hex[:12]
        self.task = task
        self.status = RunStatus.planned
        self.plan: Plan | None = None
        self.results: list[StepResult] = []
        self.ledger = Ledger()
        self.created_at = time.time()
        self._approval = threading.Event()
        self._cond = threading.Condition()

    def approve(self) -> None:
        self.ledger.append("approval", {"by": "human", "run": self.id})
        self._approval.set()
        with self._cond:
            self.status = RunStatus.running
            self._cond.notify_all()

    @property
    def dir(self) -> Path:
        d = Path(settings.data_dir) / self.id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def seal(self) -> None:
        self.ledger.append("run_sealed", {"status": self.status.value})
        (self.dir / "ledger.json").write_text(json.dumps(self.ledger.to_dict(), indent=2))

    def verify(self) -> bool:
        return self.ledger.verify()


class RunManager:
    def __init__(self) -> None:
        self.runs: dict[str, Run] = {}

    def get(self, run_id: str) -> Run | None:
        return self.runs.get(run_id)

    def start(self, task: str, plan_override: Plan | None = None) -> Run:
        run = Run(task)
        run.plan_override = plan_override
        self.runs[run.id] = run
        threading.Thread(target=self._execute, args=(run,), daemon=True).start()
        return run

    def _execute(self, run: Run) -> None:
        try:
            if getattr(run, "plan_override", None) is not None:
                run.plan, offline = run.plan_override, False
                run.ledger.append("note", {
                    "msg": "DRILL: canned hostile plan authored by the "
                           "containment drill - deterministic, not AI output"})
            else:
                run.plan, offline = make_plan(run.task)
            run.ledger.append("plan", run.plan.model_dump())
            if offline:
                run.ledger.append("note", {
                    "msg": "OFFLINE FALLBACK: rule-based plan (inference "
                           "unavailable or failed) - not an AI plan"})

            verdicts = screen_plan(run.plan)
            gated = [
                (i, v) for i, v in enumerate(verdicts)
                if v.allowed and v.gated
            ]
            if gated:
                with run._cond:
                    run.status = RunStatus.awaiting_approval
                    for i, v in gated:
                        run.ledger.append("note", {
                            "msg": f"step {i} held for approval: {v.reason}"})
                    run._cond.wait_for(run._approval.is_set,
                                       timeout=settings.sandbox_run_timeout_s)
                if not run._approval.is_set():
                    run.status = RunStatus.failed
                    run.ledger.append("note", {"msg": "approval timed out"})
                    run.seal()
                    return

            run.status = RunStatus.running
            retries_left = (0 if (offline or getattr(run, "plan_override", None) is not None)
                            else settings.planner_max_retries)
            # Sandbox is created lazily on the first step the policy ALLOWS,
            # so policy refusals are recorded even when no container runtime
            # is available - a refused step must never depend on Docker.
            sandbox: Sandbox | None = None
            try:
                steps = list(run.plan.steps)
                verdicts = list(verdicts)
                i = 0
                while i < len(steps):
                    step, verdict = steps[i], verdicts[i]
                    if not verdict.allowed:
                        run.ledger.append("blocked", {
                            "step_index": i, "label": step.label,
                            "reason": verdict.reason})
                        run.results.append(StepResult(
                            step_index=i, label=step.label, blocked=True,
                            block_reason=verdict.reason))
                        i += 1
                        continue
                    if sandbox is None:
                        sandbox = Sandbox(run.ledger, run.id)
                        sandbox.__enter__()
                    result = sandbox.run_step(i, step)
                    run.results.append(result)
                    failed = (result.exit_code not in (0, None))
                    if failed and retries_left > 0:
                        retries_left -= 1
                        fixed, repaired = make_replan(
                            run.task, step.label,
                            (result.stderr or result.stdout)[:2000],
                            [s.label for s in steps[:i]])
                        run.ledger.append("note", {
                            "msg": f"step {i} failed; requesting repair plan "
                                   f"(retries left: {retries_left})"})
                        if repaired and fixed is not None and fixed.steps:
                            new_verdicts = screen_plan(fixed)
                            run.ledger.append("replan", fixed.model_dump())
                            steps = steps[:i + 1] + fixed.steps
                            verdicts = verdicts[:i + 1] + new_verdicts
                        else:
                            run.ledger.append("note", {
                                "msg": "no repair available; continuing with "
                                       "remaining original steps"})
                    i += 1
            finally:
                if sandbox is not None:
                    sandbox.__exit__(None, None, None)
            run.status = RunStatus.completed
        except SandboxUnavailable as exc:
            run.status = RunStatus.failed
            run.ledger.append("note", {"msg": f"sandbox unavailable: {exc}"})
        except Exception as exc:  # never leak a half-run
            run.status = RunStatus.failed
            run.ledger.append("note", {"msg": f"orchestrator error: {exc}"})
        finally:
            run.seal()


manager = RunManager()

from __future__ import annotations

from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field


class StepKind(str, Enum):
    shell = "shell"        # run a shell command in the sandbox
    python = "python"      # run a python snippet in the sandbox
    browser = "browser"    # drive Playwright chromium in the sandbox


class Step(BaseModel):
    kind: StepKind
    label: str = ""
    command: str | None = None        # shell
    code: str | None = None           # python
    url: str | None = None            # browser
    actions: list[str] = Field(default_factory=list)  # browser: high-level actions
    expects_approval: bool = False    # human gate before executing


class Plan(BaseModel):
    task: str
    steps: list[Step]


class RunStatus(str, Enum):
    planned = "planned"
    awaiting_approval = "awaiting_approval"
    running = "running"
    completed = "completed"
    failed = "failed"


class StepResult(BaseModel):
    step_index: int
    label: str
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    duration_s: float = 0.0
    artifacts: list[dict[str, Any]] = Field(default_factory=list)  # {path, sha256, bytes}
    blocked: bool = False
    block_reason: str = ""


EventKind = Literal[
    "plan", "replan", "step_start", "step_result", "blocked", "approval",
    "artifact", "run_sealed", "note",
]


class LedgerEvent(BaseModel):
    seq: int
    kind: EventKind
    payload: dict[str, Any]
    prev_hash: str
    hash: str

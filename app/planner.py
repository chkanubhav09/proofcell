"""Task planner: natural language -> validated step plan.

Uses Vultr Serverless Inference (OpenAI-compatible). The client is created
on the HOST; sandbox containers never see the key.
"""
from __future__ import annotations

import json

from pydantic import ValidationError

from .config import settings
from .models import Plan, Step, StepKind

SYSTEM = """You are the planner for ProofCell, a sandboxed execution agent.
Break the user's task into concrete executable steps. Output ONLY JSON:
{"task": str, "steps": [{"kind": "shell"|"python"|"browser", "label": str,
"command": str|null, "code": str|null, "url": str|null, "actions": [str],
"expects_approval": bool}]}
Rules:
- Prefer "python" for data work, "shell" for file/git ops, "browser" for web.
- Browser steps must set url and short high-level actions.
- Mark expects_approval=true for anything irreversible or externally visible.
- All file work happens under /work inside the sandbox. Never touch other paths.
- Keep it under 8 steps."""


REPAIR_SYSTEM = """You are the planner for ProofCell, a sandboxed execution agent.
A previous plan step FAILED. Produce a corrected plan for the REMAINING work.
Output ONLY JSON, same schema as before:
{"task": str, "steps": [{"kind": "shell"|"python"|"browser", "label": str,
"command": str|null, "code": str|null, "url": str|null, "actions": [str],
"expects_approval": bool}]}
Rules:
- Read the failure output and fix the cause (wrong flag, missing file, bad parsing).
- Do not repeat the failed command unchanged.
- All file work happens under /work inside the sandbox. Never touch other paths.
- Keep it under 6 steps."""


class PlannerError(Exception):
    pass


def _client():
    if not settings.vultr_inference_api_key:
        raise PlannerError("VULTR_INFERENCE_API_KEY is not set on the host")
    from openai import OpenAI
    return OpenAI(
        api_key=settings.vultr_inference_api_key,
        base_url=settings.vultr_inference_base_url,
    )


def plan_offline(task: str) -> Plan:
    """Deterministic rule-based fallback when inference is unavailable.

    Deliberately trivial: it NEVER attempts to solve the task. It exists so a
    planner outage degrades a run to a clearly-labeled no-op instead of an
    orchestrator crash. The UI/ledger must always mark it as offline output,
    never as agent work.
    """
    return Plan(
        task=task,
        steps=[
            Step(kind=StepKind.shell, label="offline: echo task",
                 command=f"echo {task!r}"),
            Step(kind=StepKind.shell, label="offline: list workspace",
                 command="ls -la /work"),
        ],
    )


def _call(system: str, user: str) -> Plan:
    resp = _client().chat.completions.create(
        model=settings.planner_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
    )
    raw = resp.choices[0].message.content or ""
    data = json.loads(raw.strip().removeprefix("```json").removesuffix("```").strip())
    return Plan.model_validate(data)


def replan(task: str, failed_label: str, error: str,
           completed: list[str]) -> tuple[Plan | None, bool]:
    """Ask the model for a corrected plan after a step failure.

    Returns (plan, True) on a live repair, (None, False) when no repair is
    possible (no key, any API/parse failure). Offline fallback NEVER repairs:
    a rule-based echo plan cannot meaningfully fix a failure, and presenting
    one as a retry would mislabel non-AI output as agent recovery.
    """
    if not settings.vultr_inference_api_key:
        return None, False
    user = (
        f"Original task: {task}\n"
        f"Completed steps: {completed or 'none'}\n"
        f"Failed step: {failed_label}\n"
        f"Failure output:\n{error[:2000]}\n"
        "Return the corrected plan for the remaining work."
    )
    try:
        return _call(REPAIR_SYSTEM, user), True
    except Exception:
        return None, False


def plan(task: str) -> tuple[Plan, bool]:
    """Plan with the hosted model; fall back to plan_offline on ANY failure.

    Returns (plan, used_offline_fallback). The LLM path is tried only when a
    key is configured; every failure mode (no key, network, auth, rate limit,
    malformed JSON, schema mismatch) degrades to the labeled offline plan.
    """
    try:
        return _call(SYSTEM, task), False
    except Exception:
        # Broad by design: any inference failure ( PlannerError for a missing
        # key, openai API/network errors, ValidationError, JSONDecodeError )
        # must degrade, never crash a run.
        return plan_offline(task), True

"""Containment policy engine.

Static screening of every planned step BEFORE it reaches the sandbox. This is
the first of two walls: the policy refuses or gates dangerous steps, and the
sandbox makes sure that even a missed one cannot hurt the host.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .models import Plan, Step, StepKind


@dataclass
class Verdict:
    allowed: bool
    gated: bool          # needs human approval
    reason: str = ""


# severity: "refuse" = never runs, "gate" = human approval required
PATTERNS: list[tuple[str, str, str]] = [
    (r"rm\s+(-[a-zA-Z]*[rf][a-zA-Z]*\s+)?/(\s|$|\*|['\"\)])", "refuse", "recursive delete from filesystem root"),
    (r"rm\s+-[a-zA-Z]*[rf][a-zA-Z]*\s+~", "refuse", "recursive delete of home directory"),
    (r"\bmkfs\b", "refuse", "filesystem format attempt"),
    (r"\bdd\b.*\bof=/dev/", "refuse", "raw write to block device"),
    (r":\(\)\s*\{\s*:\|:\s*&\s*\}\s*;", "refuse", "fork bomb"),
    (r"\b(shutdown|reboot|halt|poweroff)\b", "refuse", "host power action"),
    (r"/etc/(shadow|sudoers|passwd)\b", "refuse", "read/write of host account database"),
    (r"\bid_rsa\b|\.ssh/", "refuse", "ssh key access"),
    (r"\b(curl|wget|nc|ncat)\b[^\n]*\|[^\n]*(sh|bash)\b", "refuse", "pipe remote payload into a shell"),
    (r"\b(curl|wget)\b[^\n]*--(data|upload-file|post)", "gate", "possible data exfiltration over HTTP"),
    (r"\bchmod\s+777\b", "gate", "world-writable permissions"),
    (r"\b(sudo|doas)\b", "gate", "privilege escalation attempt"),
    (r"\bapt(-get)?\s+install\b|\bpip\s+install\b", "gate", "installs new software into the sandbox"),
    (r"\bgit\s+push\b", "gate", "pushes code to a remote"),
]

_COMPILED = [(re.compile(p, re.IGNORECASE), sev, why) for p, sev, why in PATTERNS]


def _text_of(step: Step) -> str:
    parts = [step.command or "", step.code or "", step.url or "", " ".join(step.actions)]
    return "\n".join(parts)


def screen_step(step: Step) -> Verdict:
    text = _text_of(step)
    for rx, sev, why in _COMPILED:
        if rx.search(text):
            if sev == "refuse":
                return Verdict(allowed=False, gated=False, reason=why)
            return Verdict(allowed=True, gated=True, reason=why)
    if step.expects_approval:
        return Verdict(allowed=True, gated=True, reason="step marked as needing human approval")
    return Verdict(allowed=True, gated=False)


def screen_plan(plan: Plan) -> list[Verdict]:
    return [screen_step(s) for s in plan.steps]

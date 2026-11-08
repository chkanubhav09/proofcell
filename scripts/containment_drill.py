#!/usr/bin/env python3
"""Run every containment-drill scenario through the policy wall and report.

No Docker or API key needed: this exercises wall 1 (policy screening) with
the drill's canned hostile plans and checks each verdict against the
scenario's stated expectation. Wall 2 (sandbox) is exercised by the same
scenarios against the live app, where the ledger records the result.

Exit code 0 = every scenario behaved as expected.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import drill
from app.policy import screen_plan


def expected_verdict(expectation: str) -> str:
    return expectation.split(":", 1)[0].strip()


def main() -> int:
    failures = 0
    for s in drill.SCENARIOS:
        verdicts = screen_plan(drill.canned_plan_for(s["task"]))
        v = verdicts[0]
        wall = expected_verdict(s["expectation"])
        if wall == "policy":
            held = (not v.allowed) or v.gated
            kind = "REFUSED" if not v.allowed else ("GATED" if v.gated else "ALLOWED")
            ok = held
        elif wall == "sandbox":
            kind, ok = "ALLOWED (must die in sandbox)", v.allowed and not v.gated
        else:
            kind, ok = "?", False
        mark = "PASS" if ok else "FAIL"
        failures += 0 if ok else 1
        print(f"[{mark}] {s['id']:<26} wall={wall:<7} verdict={kind:<28} {v.reason}")
    print(f"\n{len(drill.SCENARIOS) - failures}/{len(drill.SCENARIOS)} scenarios contained as expected")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

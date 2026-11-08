"""Hash-chained proof ledger.

Every event is chained: hash_n = sha256(prev_hash || canonical_json(event)).
canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
plus the event kind and sequence number, so reordering or retyping an event
also breaks the chain.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

GENESIS = "0" * 64


def _canonical(kind: str, seq: int, payload: dict[str, Any]) -> bytes:
    body = {"kind": kind, "seq": seq, "payload": payload}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), default=str).encode()


class Ledger:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self.head: str = GENESIS

    def append(self, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
        seq = len(self.events)
        digest = hashlib.sha256(
            self.head.encode() + _canonical(kind, seq, payload)
        ).hexdigest()
        event = {
            "seq": seq,
            "kind": kind,
            "payload": payload,
            "prev_hash": self.head,
            "hash": digest,
        }
        self.events.append(event)
        self.head = digest
        return event

    def verify(self) -> bool:
        prev = GENESIS
        for i, ev in enumerate(self.events):
            if ev["seq"] != i or ev["prev_hash"] != prev:
                return False
            expect = hashlib.sha256(
                prev.encode() + _canonical(ev["kind"], ev["seq"], ev["payload"])
            ).hexdigest()
            if expect != ev["hash"]:
                return False
            prev = ev["hash"]
        return True

    def to_dict(self) -> dict[str, Any]:
        return {"head": self.head, "events": self.events}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Ledger":
        ledger = cls()
        ledger.events = list(data["events"])
        ledger.head = data["head"]
        return ledger


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _load(arg: str) -> "Ledger":
    """Load a sealed ledger from a ledger.json path or a run id under data_dir."""
    import sys
    from pathlib import Path

    p = Path(arg)
    if not p.is_file():
        from .config import settings
        p = Path(settings.data_dir) / arg / "ledger.json"
    if not p.is_file():
        print(f"no sealed ledger at {arg} (or {p})", file=sys.stderr)
        raise SystemExit(2)
    return Ledger.from_dict(json.loads(p.read_text()))


def main(argv: list[str] | None = None) -> int:
    import sys

    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 2 or args[0] != "verify":
        print("usage: python -m app.ledger verify <run-id|ledger.json>", file=sys.stderr)
        return 2
    ledger = _load(args[1])
    if ledger.verify():
        print(f"chain intact, {len(ledger.events)} entries, head {ledger.head[:16]}...")
        return 0
    print("CHAIN BROKEN: ledger fails verification", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

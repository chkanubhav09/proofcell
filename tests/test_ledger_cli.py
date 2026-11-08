import json
from pathlib import Path

from app.ledger import Ledger, main


def seal(tmp_path: Path, tamper: bool = False) -> Path:
    ledger = Ledger()
    ledger.append("plan", {"task": "demo"})
    ledger.append("blocked", {"step_index": 0, "reason": "recursive delete from filesystem root"})
    ledger.append("run_sealed", {"status": "completed"})
    if tamper:
        ledger.events[1]["payload"]["reason"] = "nothing happened, honest"
    p = tmp_path / "ledger.json"
    p.write_text(json.dumps(ledger.to_dict()))
    return p


def test_cli_verify_intact(tmp_path, capsys):
    rc = main(["verify", str(seal(tmp_path))])
    out = capsys.readouterr().out
    assert rc == 0 and "chain intact, 3 entries" in out


def test_cli_verify_tampered(tmp_path, capsys):
    rc = main(["verify", str(seal(tmp_path, tamper=True))])
    assert rc == 1


def test_cli_missing_file(capsys):
    import pytest
    with pytest.raises(SystemExit):
        main(["verify", "no-such-run-id"])

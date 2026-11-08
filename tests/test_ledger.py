from app.ledger import Ledger


def test_chain_verifies():
    l = Ledger()
    l.append("plan", {"task": "demo"})
    l.append("step_start", {"index": 0})
    l.append("step_result", {"exit_code": 0})
    assert l.verify()
    assert len(l.events) == 3
    assert l.events[2]["prev_hash"] == l.events[1]["hash"]


def test_tamper_breaks_chain():
    l = Ledger()
    l.append("plan", {"task": "demo"})
    l.append("step_result", {"exit_code": 0})
    l.events[1]["payload"]["exit_code"] = 42  # judge edits history
    assert not l.verify()


def test_delete_event_breaks_chain():
    l = Ledger()
    for i in range(4):
        l.append("note", {"i": i})
    del l.events[2]
    assert not l.verify()


def test_roundtrip():
    l = Ledger()
    l.append("plan", {"task": "x"})
    l2 = Ledger.from_dict(l.to_dict())
    assert l2.verify() and l2.head == l.head

from app.sandbox import build_sandbox_config


def test_containment_defaults():
    c = build_sandbox_config()
    assert c["user"] == "1000:1000"
    assert c["read_only"] is True
    assert c["cap_drop"] == ["ALL"]
    assert "no-new-privileges" in c["security_opt"]
    assert c["environment"] == {}  # no secrets ever enter a sandbox
    assert c["network_mode"] == "none"
    assert "/work" in c["tmpfs"]

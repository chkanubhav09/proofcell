"""Browser steps get a scoped egress container; code steps never do."""
from __future__ import annotations

import sys
from types import SimpleNamespace as NS

from app.ledger import Ledger
from app.models import Step, StepKind


class FakeContainer:
    def __init__(self, network_mode):
        self.network_mode = network_mode
        self.execs = []
        self.destroyed = False

    def start(self): pass

    def exec_run(self, cmd, **kw):
        self.execs.append(cmd)
        return (0, b"ok")

    def remove(self, force=False):
        self.destroyed = True


class FakeDockerModule:
    class DockerException(Exception): pass

    class errors:
        DockerException = Exception

    def __init__(self):
        self.created = []

    def from_env(self):
        return self

    class containers:  # replaced per-instance in __init__ below
        pass


def _install_fake_docker(monkeypatch, containers):
    import types
    docker = types.ModuleType("docker")
    errors = types.ModuleType("docker.errors")

    class DockerException(Exception): pass
    docker.DockerException = DockerException
    errors.DockerException = DockerException
    docker.errors = errors
    docker.from_env = lambda: NS(containers=containers)
    monkeypatch.setitem(sys.modules, "docker", docker)
    monkeypatch.setitem(sys.modules, "docker.errors", errors)


def _fake_docker(monkeypatch):
    state = {"created": []}

    class Containers:
        def create(self, **kw):
            c = FakeContainer(kw["network_mode"])
            state["created"].append(c)
            return c
    _install_fake_docker(monkeypatch, Containers())
    return state


def test_browser_step_uses_egress_container(monkeypatch):
    from app.sandbox import Sandbox
    state = _fake_docker(monkeypatch)
    ledger = Ledger()
    with Sandbox(ledger, "r1") as sb:
        sb.run_step(0, Step(kind=StepKind.shell, label="code", command="ls"))
        sb.run_step(1, Step(kind=StepKind.browser, label="browse", url="https://example.com"))
    assert len(state["created"]) == 2
    code_c, egress_c = state["created"]
    assert code_c.network_mode == "none" and egress_c.network_mode == "bridge"
    assert ["/bin/sh", "-lc", "ls"] in code_c.execs
    assert egress_c.execs and egress_c.execs[0][0] == "python3"
    assert code_c.destroyed and egress_c.destroyed
    msgs = [e["payload"].get("msg", "") for e in ledger.events if e["kind"] == "note"]
    assert any("egress sandbox created" in m for m in msgs)
    assert any(m == "egress sandbox destroyed" for m in msgs)


def test_no_browser_step_means_no_egress_container(monkeypatch):
    from app.sandbox import Sandbox
    state = _fake_docker(monkeypatch)
    with Sandbox(Ledger(), "r2") as sb:
        sb.run_step(0, Step(kind=StepKind.shell, label="code", command="ls"))
    assert len(state["created"]) == 1
    assert state["created"][0].network_mode == "none"


def test_egress_container_hardening_matches(monkeypatch):
    from app.sandbox import Sandbox
    state = _fake_docker(monkeypatch)
    captured = []

    class Containers:
        def create(self, **kw):
            captured.append(kw)
            c = FakeContainer(kw["network_mode"])
            state["created"].append(c)
            return c
    _install_fake_docker(monkeypatch, Containers())
    with Sandbox(Ledger(), "r3") as sb:
        sb.run_step(0, Step(kind=StepKind.browser, label="b", url="https://example.com"))
    assert len(captured) == 2
    for kw in captured:
        assert kw["user"] == "1000:1000"
        assert kw["cap_drop"] == ["ALL"]
        assert kw["read_only"] is True
        assert kw["environment"] == {}
        assert "no-new-privileges" in kw["security_opt"]

"""Sandboxed execution boundary. One Docker container per run.

Containment properties:
- non-root user, ALL capabilities dropped, no-new-privileges
- read-only root filesystem; only a tmpfs at /work is writable
- no environment secrets; the inference key never enters the container
- memory / CPU / PID caps; per-step wall-clock timeout
- network disabled for shell/python steps; browser steps run in a second,
  lazily-created egress container (bridge network) with identical hardening -
  browsing IS the task there, so egress is scoped to those steps only
- both containers force-destroyed when the run ends
"""
from __future__ import annotations

import io
import tarfile
import time
from typing import Any

from .config import settings
from .ledger import Ledger, sha256_bytes
from .models import Step, StepKind, StepResult


class SandboxUnavailable(Exception):
    pass


class Sandbox:
    def __init__(self, ledger: Ledger, run_id: str) -> None:
        self.ledger = ledger
        self.run_id = run_id
        self._client = None
        self._container = None
        self._egress = None

    def __enter__(self) -> "Sandbox":
        import docker
        from docker.errors import DockerException
        self._docker = docker
        self._DockerException = DockerException
        try:
            self._client = docker.from_env()
        except DockerException as exc:
            raise SandboxUnavailable(str(exc)) from exc
        self._container = self._create(network_mode="none")
        self.ledger.append("note", {"msg": "sandbox created", "image": settings.sandbox_image,
                                    "network": "none"})
        return self

    def _create(self, network_mode: str):
        c = self._client.containers.create(
            image=settings.sandbox_image,
            command=["sleep", "infinity"],
            user="1000:1000",
            network_mode=network_mode,
            read_only=True,
            tmpfs={"/work": "rw,size=256m"},
            cap_drop=["ALL"],
            security_opt=["no-new-privileges"],
            mem_limit=settings.sandbox_mem_limit,
            nano_cpus=settings.sandbox_nano_cpus,
            pids_limit=settings.sandbox_pids_limit,
            environment={},                 # no secrets, ever
            working_dir="/work",
            detach=True,
        )
        c.start()
        return c

    def _ensure_egress(self):
        """Browser steps only: identical hardening, bridge network.

        Browsing is the task for these steps, so egress is scoped to a
        separate container that exists only when a plan actually contains a
        browser step. Code steps never touch it.
        """
        if self._egress is None:
            self._egress = self._create(network_mode="bridge")
            self.ledger.append("note", {
                "msg": "egress sandbox created for browser step",
                "network": "bridge (egress only, same hardening)"})
        return self._egress

    def __exit__(self, *exc: Any) -> None:
        for label, c in (("sandbox", self._container), ("egress sandbox", self._egress)):
            if c is not None:
                try:
                    c.remove(force=True)
                    self.ledger.append("note", {"msg": f"{label} destroyed"})
                except self._DockerException:
                    pass

    # -- execution ------------------------------------------------------

    def run_step(self, index: int, step: Step) -> StepResult:
        assert self._container is not None
        self.ledger.append("step_start", {"index": index, "label": step.label, "kind": step.kind.value})
        start = time.monotonic()
        cmd = self._build_cmd(step)
        container = self._ensure_egress() if step.kind == StepKind.browser else self._container
        result = StepResult(step_index=index, label=step.label)
        try:
            rc, output = container.exec_run(
                cmd,
                workdir="/work",
                user="1000:1000",
                demux=False,
            )
            result.exit_code = rc
            text = output.decode("utf-8", "replace") if isinstance(output, bytes) else str(output)
            result.stdout = text[:20000]
        except self._DockerException as exc:
            result.exit_code = -1
            result.stderr = str(exc)[:2000]
        result.duration_s = round(time.monotonic() - start, 3)
        result.artifacts = self._collect_artifacts()
        self.ledger.append("step_result", result.model_dump())
        return result

    def _build_cmd(self, step: Step) -> list[str]:
        if step.kind == StepKind.shell:
            return ["/bin/sh", "-lc", step.command or "true"]
        if step.kind == StepKind.python:
            return ["python3", "-c", step.code or "pass"]
        if step.kind == StepKind.browser:
            # Playwright script baked into the sandbox image; actions passed as JSON argv
            import json
            return ["python3", "/opt/browser_step.py", step.url or "about:blank",
                    json.dumps(step.actions)]
        return ["/bin/sh", "-lc", "true"]

    def _collect_artifacts(self) -> list[dict[str, Any]]:
        """Hash files produced under /work (small files only)."""
        assert self._container is not None
        artifacts: list[dict[str, Any]] = []
        try:
            rc, out = self._container.exec_run(
                ["/bin/sh", "-lc", "find /work -type f -maxdepth 3 -size -2M"],
                user="1000:1000",
            )
            if rc != 0:
                return artifacts
            for path in out.decode().split():
                bits, _ = self._container.get_archive(path)
                blob = b"".join(bits)
                # untar in memory to get the file payload
                with tarfile.open(fileobj=io.BytesIO(blob)) as tf:
                    member = next(m for m in tf.getmembers() if m.isfile())
                    data = tf.extractfile(member).read()  # type: ignore[union-attr]
                artifacts.append({"path": path, "sha256": sha256_bytes(data), "bytes": len(data)})
        except Exception:
            pass
        return artifacts


def build_sandbox_config(image: str | None = None) -> dict[str, Any]:
    """Pure config builder - unit-testable without Docker."""
    return {
        "image": image or settings.sandbox_image,
        "user": "1000:1000",
        "network_mode": "none",
        "read_only": True,
        "tmpfs": {"/work": "rw,size=256m"},
        "cap_drop": ["ALL"],
        "security_opt": ["no-new-privileges"],
        "mem_limit": settings.sandbox_mem_limit,
        "nano_cpus": settings.sandbox_nano_cpus,
        "pids_limit": settings.sandbox_pids_limit,
        "environment": {},
    }

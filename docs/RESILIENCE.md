# External dependencies and fallback behavior

Every external thing ProofCell depends on, what happens when it fails, and
why. Principle: degrade visibly, never silently, never fake a success.

## 1. Vultr Serverless Inference (planner LLM)

- Failure modes: no API key configured, endpoint down, auth error, rate
  limit, malformed/unparseable model output.
- Fallback: `app.planner.plan_offline()` - a deliberately trivial
  rule-based plan (echo the task, list /work). It NEVER attempts to solve
  the task. Every offline plan is labeled `OFFLINE FALLBACK ... not an AI
  plan` in the proof ledger, and offline steps are prefixed `offline:`.
  Tests: tests/test_resilience.py (no-key, connection error, good response).
- Design note: a planner outage must never crash a run or produce an
  unlabeled plan.

## 2. Docker daemon (execution sandbox)

- Failure modes: daemon unreachable, image missing, container create fails.
- Fallback: NONE, by design. ProofCell's promise is that agent code never
  runs unsandboxed, so there is no safe degraded execution path. The run
  fails closed: status `failed`, a `sandbox unavailable` note in the ledger,
  and the hash chain stays intact and verifiable.
  Test: tests/test_resilience.py::test_docker_outage_fails_closed.

## 3. Vultr Cloud Compute VM (hosting / public demo URL)

- Failure modes: VM down, credits exhausted, account unverified.
- Fallback: none automated - deployment is an operations decision (redeploy
  from deploy/DEPLOY.md). The app itself is self-contained and runs on any
  single Linux host with Docker; nothing in the code is Vultr-specific.

## 4. Host disk (ledger + artifacts)

- Ledgers seal to `<data_dir>/<run-id>/ledger.json` after every run,
  including failed runs, so a crashed or refused run still leaves a
  verifiable record. Verify any sealed ledger with
  `python -m app.ledger verify <run-id|ledger.json>`.

## Explicit non-goals

- No substitute model provider is wired in silently; switching inference
  providers is a deliberate config change (planner_model / base_url), not an
  automatic runtime fallback.
- No execution outside the sandbox, ever, even when Docker is down.

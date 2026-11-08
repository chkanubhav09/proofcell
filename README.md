# ProofCell

**AI agents that do real work inside disposable sandboxes, with a verifiable record of every step.**

ProofCell is a web-based agent control layer. You hand it a task in plain
language - analyze this CSV, fix this failing test, QA this website - and it:

1. **Plans** the task with an LLM running on Vultr Serverless Inference.
2. **Dispatches** each step into a fresh, locked-down Docker sandbox on a Vultr
   VM: non-root user, read-only filesystem, no credentials inside, CPU / memory
   / time caps, destroyed when the task ends.
3. **Records** what happened: every command, output, file diff and screenshot is
   written to a hash-chained ledger whose integrity anyone can recompute and check.

Containment is a product feature, not plumbing. ProofCell ships with a
built-in **containment drill**: watch the agent attempt something dangerous
(`rm -rf /`, reading a planted secret outside its workspace, exfiltrating a
file) and watch the sandbox refuse, log and flag each tested attempt.

Built for the **Vultr: Agent Rush Hackathon** (lablab.ai, 3-8 Nov 2026),
Challenge 1: *Blast Radius Zero*.

## Why

Agents that only chat are demos. Agents that execute are useful - and
dangerous. Teams will not hand real work to an agent they cannot contain or
audit. ProofCell is the trust layer: real executed work, designed for a blast
radius of zero, with a receipt for everything.

## Containment drill

Five canned hostile scenarios exercise the two walls, live, with the ledger as
evidence. Policy-only check (no Docker or API key needed):

    python3 scripts/containment_drill.py

Against the running app, each scenario is a normal run whose dangerous step
is drill-authored (labeled in the ledger, never presented as model output):

    GET  /api/drill/scenarios
    POST /api/drill/{scenario_id}     # returns run_id + which wall stops it

## Architecture

```
Browser UI (htmx)  -->  FastAPI control plane (Vultr VM)
                              |
                    Planner (Vultr Serverless Inference)
                              |
                    Run orchestrator -- approval gate
                              |
              +---------------+----------------+
              |                                |
      Sandbox container A              Sandbox container B
      (code execution)                 (Playwright browser)
      non-root, RO fs,                 non-root, capped,
      no secrets, capped               destroyed after use
              |                                |
              +---------------+----------------+
                              |
                    Proof ledger (hash-chained,
                    tamper-evident)
```

- **Control plane**: Python 3.12 + FastAPI on a single Vultr Cloud Compute VM.
- **LLM**: Vultr Serverless Inference (`https://api.vultrinference.com/v1`,
  OpenAI-compatible). The API key lives only on the host - never inside a
  sandbox.
- **Sandboxing**: one Docker container per task. `cap_drop: ALL`,
  `no-new-privileges`, read-only root, tmpfs `/work`, memory and CPU limits,
  wall-clock timeout, destroyed after the run.
- **Proof**: every step event is SHA-256 chained to the previous one
  (`docs/ARCHITECTURE.md`). A run manifest plus the replay verifier let a
  judge confirm the ledger was not tampered with.

## Quick start (local, needs Docker)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
docker build -t proofcell-sandbox deploy/sandbox-image
export VULTR_INFERENCE_API_KEY=...   # host only, never enters a sandbox
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000 and run the built-in **Containment Drill**.

Deployment to a Vultr VM: `deploy/DEPLOY.md`.

## The four things a judge should check

1. The demo URL runs a real task end to end (try the CSV analyst seed task).
2. The run page shows a live step stream and a proof ledger with hashes.
3. The Containment Drill shows dangerous actions blocked and logged.
4. `GET /api/runs/{id}/verify` recomputes the ledger and returns `valid: true`.

## License

MIT - see `LICENSE`.

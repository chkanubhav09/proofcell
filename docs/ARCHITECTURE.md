# ProofCell architecture

## Components

- **app/main.py** - FastAPI app: pages, run CRUD, SSE step stream, approvals,
  ledger verification endpoint.
- **app/planner.py** - turns a natural-language task into a validated step plan
  via Vultr Serverless Inference (OpenAI-compatible chat completions with a
  JSON schema). Falls back to a deterministic plan if the model output does
  not validate.
- **app/policy.py** - the containment policy engine. Statically screens every
  planned step for dangerous patterns (destructive fs ops, device writes,
  fork bombs, secret reads, exfiltration shapes). A flagged step is either
  refused outright or held for human approval, depending on severity.
- **app/sandbox.py** - the execution boundary. One Docker container per run:
  - `user=1000:1000` (non-root)
  - `read_only=True` root fs, writable tmpfs mounted at `/work`
  - `cap_drop=["ALL"]`, `security_opt=["no-new-privileges"]`
  - `mem_limit=512m`, `nano_cpus=1e9`, `pids_limit=256`
  - per-step wall-clock timeout; container force-removed at run end
  - network: `none` for shell/python steps. Browser steps run in a second,
    lazily-created egress container (bridge network) with identical
    hardening - browsing is the task there, so egress is scoped to those
    steps only; code steps never touch it. Both are destroyed at run end.
  - no environment secrets are passed in; the inference key never leaves the
    host
- **app/ledger.py** - the proof ledger. Each event (plan, step start, output,
  artifact, block, approval, completion) is serialized canonically and chained:
  `hash_n = sha256(hash_{n-1} || canonical(event_n))`. The run manifest stores
  the final head hash. `verify()` recomputes the chain from the event log;
  any edit, deletion or reorder breaks the chain.
- **app/main.py:/api/runs/{id}/verify** - exposes that recomputation to judges.

## Data flow for one run

1. User submits a task. The planner returns steps `[{kind, payload}]`.
2. Policy screens the plan. Refused steps are logged as `blocked`; gated steps
   pause the run until an approval event arrives.
3. The orchestrator boots a sandbox container and executes steps in order.
   stdout, stderr, exit code, timing and produced artifacts (with SHA-256 of
   each file) are appended to the ledger after every step.
4. On completion (or failure) the container is destroyed and the manifest is
   sealed with the head hash.

## Why this is "Blast Radius Zero"

- Process isolation: agent code never executes in the app runtime or on the
  host; it only ever runs inside the per-task container.
- Secret hygiene: sandboxes receive no API keys; the only credential in the
  system (the inference key) stays in the host environment.
- Resource limits: hard caps on memory, CPU, PIDs and wall-clock per step.
- Lifecycle discipline: containers are created per task and force-destroyed
  after; nothing persists between tasks except the ledger and user artifacts.
- Independent verification: the ledger does not ask you to trust the UI.

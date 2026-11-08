# Submission text (draft - finalize during the build window)

**Project title:** ProofCell - sandboxed AI agents with verifiable proof of work

**Short description (~140 chars):**
ProofCell runs AI agents inside disposable Docker sandboxes on Vultr: real
executed work, contained by design, with a hash-chained record of every step.

**Long description (draft):**
Agents that only chat are demos; agents that execute are useful - and
dangerous. ProofCell is a web-based control layer that lets anyone hand a
real task to an AI agent without handing it the keys.

Give ProofCell a task in plain language - analyze a spreadsheet, fix a failing
test, QA a website. A planner on Vultr Serverless Inference breaks the task
into steps. Every step executes inside a fresh, locked-down Docker sandbox on
a Vultr VM: non-root, read-only filesystem, no credentials, hard CPU / memory /
time caps, destroyed when the task ends. The sandbox is designed so the agent's
work cannot touch the host, the app, or your secrets - and the built-in drill
exercises exactly those boundaries.

Then ProofCell records it. Every command, output, file diff and screenshot is
chained into a SHA-256 ledger that anyone can recompute to confirm the record
was not altered after the fact. When a step fails, the planner
gets the error back and repairs its own plan - self-healing retries, each
one on the record. A built-in containment drill runs canned hostile
scenarios - wipe the filesystem, exfiltrate a planted secret, steal SSH
keys - and shows the two walls refusing, gating or containing each tested
scenario, with the ledger as evidence.

ProofCell is the trust layer for agentic work: containment-first execution,
human approval for irreversible steps, and a receipt for everything.

**Tech:** Vultr Cloud Compute, Vultr Serverless Inference, Docker, Python /
FastAPI, Playwright, htmx.

**Tags:** AI agents, sandboxing, code execution, browser automation, security,
verification, Vultr

**Demo platform:** Self-hosted on Vultr Cloud Compute (public URL at submission)

**Video beats (must include one containment moment):** see DEMO_SCRIPT.md

## Compliance checklist (verified against event page 2026-11-04)

Event-mandated (https://lablab.ai/ai-hackathons/vultr-hackathon):
- [ ] Vultr VM backend deployment ("web application must be deployed on Vultr") - blocked at Vultr payment verification; support ticket open
- [x] Vultr Serverless Inference for agent LLM calls (Challenge 1 required) - wired in code; first live calls at deployment
- [x] Isolated sandbox execution (Docker) - implemented
- [ ] Public demo URL - depends on provisioning decision
- [ ] Recorded demo video incl. ONE CONTAINMENT MOMENT - drill covers it
- [ ] Public GitHub repo with setup/docs - repo ready, flip at publication gate
- [x] Clear architecture and use-case explanation - ARCHITECTURE.md + deck

Form fields (rule book; actual event form outranks - inspect after team creation):
title / short + long descriptions / tech + category tags / optional 16:9
cover / video MP4 or MOV / PDF deck / public repo / demo platform /
Application URL. Deadline: Nov 9, 2026 04:30 IST (hard; printed 5-min
grace not relied on).

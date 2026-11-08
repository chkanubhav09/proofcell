# Deck outline (8 slides, export to PDF for submission)

Format: 16:9, dark background, one idea per slide, big text. Build in the
last build day once the product is final; screenshots from the live demo.

## 1. Title
ProofCell - sandboxed AI agents with verifiable proof of work.
Anubhav Chakraborty - Vultr Agent Rush, Challenge 1: Blast Radius Zero.
Screenshot: the run view mid-execution.

## 2. Problem
Agents that execute are useful and dangerous; nothing sits between an
agent's plan and your machine. One vivid failure image (wiped terminal).
Statistic or one-liner: teams won't hand real work to agents they can't
contain or audit.

## 3. What ProofCell does
Three-step diagram: Plan (Serverless Inference) -> Execute (disposable Docker
sandboxes on a Vultr VM) -> Prove (hash-chained ledger). One sentence each.

## 4. Containment architecture (the technical slide)
Layer diagram: policy engine (refuse/gate patterns, human approval) ->
sandbox config (non-root, read-only FS, no creds, CPU/mem/time caps,
destroyed after run) -> ledger (SHA-256 chain, independently verifiable).
Callout: "Blast radius: the workspace. Nothing else."

## 5. The containment moment
Screenshot triptych from the drill: REFUSED (rm -rf /), GATED+DENIED
(exfiltration), BLOCKED-BY-SANDBOX (privilege escalation). One line each.

## 6. Proof you can verify
Ledger screenshot + verifier output ("chain intact"). One line: anyone can
recompute the chain; executed results, not described results.

## 7. Built on Vultr
Cloud Compute VM hosts the whole control plane and the sandbox pool;
Serverless Inference powers the planner; $200 credits covered everything.
Cost note: runs comfortably on a single regular-performance VM.

## 8. What's next + links
Roadmap 3 bullets (policy learning from drills, multi-step approvals,
hosted verifier page). Links: live demo URL, GitHub repo (MIT).

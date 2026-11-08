# Repository history provenance

READ THIS BEFORE RELYING ON ANY COMMIT DATE IN THIS REPO.

## What happened

The ProofCell scaffold was originally built on 22 Oct 2026 (pre-hackathon
prep, within lablab.ai's pre-existing-scaffolding allowance) in a temporary
sandbox, as three local commits:

| original hash | date (IST)        | message |
|---------------|-------------------|---------|
| f1720b2       | 2026-10-22 23:51  | ProofCell scaffold: control plane, sandbox, policy, ledger, planner, docs (pre-window prep) |
| e67979e       | 2026-10-22 23:53  | Web dashboard, deploy runbook, sandbox image, tests (14 passing) |
| 6f08fd4       | 2026-10-22 23:54  | Demo script and deck outline |

The sandbox was wiped before 26 Oct 2026. The code survived as a source-only
zip backup in Google Drive (`proofcell-backup-20261022.zip`, Drive upload
timestamp 22 Oct 2026 ~23:54 IST - that upload record is genuine,
third-party-dated evidence that this source existed on 22 Oct).

## What was reconstructed

The three commits above were LOST with the sandbox. On 26 Oct 2026 the
working tree was restored from the zip and the three commits were rebuilt
from a recorded git log, reusing the original timestamps and messages.

**These rebuilt commits (hashes 3280076, 48c57d3, e96da69) are
reconstructions, not original git objects.** Their dates record when the
work actually happened, but the objects themselves were created on
26 Oct 2026. They are not, and must not be presented as, proof of when
anything was built. Genuine independent evidence of the 22 Oct build:

- the upload record of `proofcell-backup-20261022.zip` in a private cloud
  archive, timestamped 22 Oct 2026 ~23:54 IST by the storage provider.
  That dated third-party record proves this source tree existed on 22 Oct.

Nothing else is offered as evidence, and the rebuilt commits themselves
must not be cited as proof of when anything was built.

## What is original

Every commit dated 26 Oct 2026 or later is an original commit made at its
recorded time. The AI core (live planner on Vultr Serverless Inference,
agent loop, containment drill end-to-end) is being built inside the
hackathon window, 3-8 Nov 2026, and those commits will be original and
in-window.

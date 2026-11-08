# Deploying ProofCell on Vultr

Built to run on the Vultr Agent Rush hackathon credits (Cloud Compute +
Serverless Inference).

## 1. Provision the VM (prices verified 3 Nov via api.vultr.com/v2/plans)
- Product: Cloud Compute - Shared CPU (vc2)
- Image: Ubuntu 24.04 LTS x64
- Plan: vc2-1c-1gb ($5/mo, $0.007/hr). If browser steps OOM with both
  containers up on 1 GB, lower sandbox_mem_limit in config before considering
  a larger plan. Stopped instances still bill - destroy, never just stop.
- Region: Mumbai (bom) or Delhi NCR (del); vc2-1c-1gb listed for bom/del/blr.
- Hostname: proofcell

## 2. Host setup
```bash
ssh root@<vm-ip>
apt-get update && apt-get install -y docker.io git
systemctl enable --now docker
git clone https://github.com/chkanubhav09/proofcell.git
cd proofcell
docker build -t proofcell-sandbox deploy/sandbox-image
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

## 3. Serverless Inference key (host only - NEVER inside a sandbox)
- Vultr console -> Serverless Inference -> create API key.
- `export VULTR_INFERENCE_API_KEY=...` in the service environment.
- Planner model: `mimo-v2.6-pro` (default in config). Override via
  `PLANNER_MODEL` only after re-checking the live model list at
  https://api.vultrinference.com/docs/models.

## 4. Run as a service
```bash
cp deploy/proofcell.service /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now proofcell
```
The app listens on :8000. Point the demo URL at http://<vm-ip>:8000
(add Caddy/nginx + a free TLS cert only if time allows; a plain IP:port demo
URL is acceptable for judging as long as it is public and working).

## 5. Smoke test
- Open the UI, run "CSV analyst", then the Containment Drill.
- `curl http://<vm-ip>:8000/api/runs/<id>/verify` must return "valid": true.

## 6. Teardown discipline
Sandboxes destroy themselves per run. Destroy the VM after judging concludes
(or keep it only while hackathon credits cover it).

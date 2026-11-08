#!/usr/bin/env python3
"""Record the PRE-DEPLOYMENT prototype video scenes against a locally running
ProofCell app (no Docker, no Vultr). Honest recording: everything on camera is
the real app; what cannot run without the container runtime is labeled in
post-production captions, not faked.

Usage: uvicorn app.main:app --port 8000 &  python3 scripts/record_prototype.py /tmp/demo
"""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8000"
TASK = ("Analyze the CSV at /work/samples/sales.csv, compute monthly revenue "
        "totals, and write /work/revenue_by_month.json")


def scene_ctx(p, outdir):
    browser = p.chromium.launch()
    ctx = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        record_video_dir=str(outdir),
        record_video_size={"width": 1920, "height": 1080})
    return browser, ctx, ctx.new_page()


def main() -> int:
    outdir = Path(sys.argv[1])
    outdir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        # S2: submit the CSV analyst task - real UI, offline planner label
        browser, ctx, page = scene_ctx(p, outdir)
        page.goto(BASE, wait_until="networkidle")
        page.wait_for_timeout(1500)
        page.click("button.sample")  # CSV analyst sample fills the textarea
        page.wait_for_timeout(800)
        page.click("text=Run in sandbox")
        page.wait_for_url("**/runs/**", timeout=15000)
        page.wait_for_timeout(10000)  # plan + policy screening + offline label
        ctx.close(); browser.close()

        # S3: containment drill - wipe refused (the containment moment)
        browser, ctx, page = scene_ctx(p, outdir)
        page.goto(BASE, wait_until="networkidle")
        page.wait_for_timeout(1200)
        page.click("#drill")
        page.wait_for_timeout(1200)
        page.click("text=Wipe the filesystem")
        page.wait_for_url("**/runs/**", timeout=15000)
        page.wait_for_timeout(9000)  # BLOCKED entry + completed + valid check
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(4000)  # ledger + verify line on camera
        ctx.close(); browser.close()

        # S4: exfiltration gated - approval dialog holds, nobody approves
        browser, ctx, page = scene_ctx(p, outdir)
        page.goto(BASE, wait_until="networkidle")
        page.wait_for_timeout(1200)
        page.click("#drill")
        page.wait_for_timeout(1200)
        page.click("text=Exfiltrate a planted secret")
        page.wait_for_url("**/runs/**", timeout=15000)
        page.wait_for_timeout(12000)  # approval panel visible, gate holding
        ctx.close(); browser.close()

        # S5: two more refusals back to back (shadow + ssh key)
        for title in ("Read the host account database", "Steal SSH keys"):
            browser, ctx, page = scene_ctx(p, outdir)
            page.goto(BASE, wait_until="networkidle")
            page.wait_for_timeout(1000)
            page.click("#drill")
            page.wait_for_timeout(1000)
            page.click(f"text={title}")
            page.wait_for_url("**/runs/**", timeout=15000)
            page.wait_for_timeout(7000)
            ctx.close(); browser.close()

    print(f"scene clips in {outdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

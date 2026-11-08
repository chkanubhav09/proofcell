#!/usr/bin/env python3
"""Record the demo video scenes against the deployed app (deploy day only).

Runs on the workspace box: pip install playwright && playwright install chromium.
Usage: python3 scripts/record_demo.py https://<vm-ip>:8000 /tmp/demo

Playwright records WebM per scene; splice with ffmpeg per docs/DEMO_SCRIPT.md.
Scene list mirrors DEMO_SCRIPT.md - update both together. NO real API keys or
private data on screen; drill scenarios only.
"""
from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    base, outdir = sys.argv[1].rstrip("/"), Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True)
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=str(outdir), record_video_size={"width": 1920, "height": 1080})
        page = ctx.new_page()

        # Scene 2-3: submit the CSV analyst task, watch the run
        page.goto(base, wait_until="networkidle")
        page.fill("#task", "Analyze the CSV at /work/samples/sales.csv, compute "
                           "monthly revenue totals, and write /work/revenue_by_month.json")
        page.click("text=Run in sandbox")
        page.wait_for_url("**/runs/**", timeout=15000)
        page.wait_for_timeout(45000)  # let the run play out on camera
        ctx.close()  # scene clip saved on context close

        # Scene 4: containment drill - wipe refused
        ctx2 = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=str(outdir), record_video_size={"width": 1920, "height": 1080})
        page2 = ctx2.new_page()
        page2.goto(base, wait_until="networkidle")
        page2.click("text=Run containment drill")
        page2.click("text=Wipe the filesystem")
        page2.wait_for_url("**/runs/**", timeout=15000)
        page2.wait_for_timeout(20000)  # ledger shows REFUSED + seal
        ctx2.close()
        browser.close()
    print(f"clips in {outdir}; splice per docs/DEMO_SCRIPT.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Runs INSIDE the sandbox container. Drives chromium for one browser step.

Usage: python3 /opt/browser_step.py <url> '<actions-json>'
Actions (high-level): ["goto <url>", "click <text>", "type <selector>=<text>",
"expect <text>", "screenshot <name>"]
Writes screenshots to /work and prints a JSON result line to stdout.
"""
import json
import sys

from playwright.sync_api import sync_playwright


def main() -> int:
    url, actions = sys.argv[1], json.loads(sys.argv[2])
    result = {"url": url, "done": [], "screens": [], "ok": True, "error": ""}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--no-sandbox"])
            page = browser.new_page()
            page.goto(url, timeout=30000)
            for i, action in enumerate(actions):
                verb, _, arg = action.partition(" ")
                if verb == "goto":
                    page.goto(arg, timeout=30000)
                elif verb == "click":
                    page.get_by_text(arg, exact=False).first.click(timeout=10000)
                elif verb == "type":
                    sel, _, text = arg.partition("=")
                    page.fill(sel, text, timeout=10000)
                elif verb == "expect":
                    page.get_by_text(arg, exact=False).first.wait_for(timeout=10000)
                elif verb == "screenshot":
                    name = arg or f"shot_{i}.png"
                    path = f"/work/{name}"
                    page.screenshot(path=path, full_page=True)
                    result["screens"].append(path)
                result["done"].append(action)
            result["title"] = page.title()
            browser.close()
    except Exception as exc:  # surface failures as data, never crash the ledger
        result["ok"] = False
        result["error"] = str(exc)[:500]
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())

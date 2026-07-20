"""Quick local test: Playwright against test_host on :5174.
Checks that window.opendaw.service is non-null after boot.
"""
import asyncio
import json
import sys
from playwright.async_api import async_playwright

URL = "https://localhost:5174/"

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page(ignore_https_errors=True)

        print("[test] navigating to", URL)
        await page.goto(URL, timeout=30000)

        # Capture console logs
        logs = []
        page.on("console", lambda msg: logs.append(f"[{msg.type}] {msg.text}"))

        print("[test] waiting for window.opendaw.service...")
        try:
            await page.wait_for_function(
                "typeof window.opendaw !== 'undefined' && window.opendaw.service !== undefined && window.opendaw.service !== null",
                timeout=60000,
            )
            print("[test] ✓ window.opendaw.service is available!")
        except Exception as e:
            print(f"[test] ✗ timeout: {e}")
            # Diagnostic
            try:
                diag = await page.evaluate("""() => ({
                    status: document.getElementById('status')?.textContent || 'no status el',
                    hasOpendaw: typeof window.opendaw,
                    hasService: window.opendaw ? typeof window.opendaw.service : 'no opendaw',
                    url: window.location.href,
                    title: document.title,
                })""")
                print(f"[test] diagnostic: {json.dumps(diag, indent=2)}")
            except Exception as diag_err:
                print(f"[test] diagnostic failed: {diag_err}")

            print("[test] console logs:")
            for log in logs[-20:]:
                print(f"  {log}")

            await browser.close()
            return 1

        # If service exists, check project
        try:
            state = await page.evaluate("""() => {
                const p = window.opendaw.service.project;
                return {
                    hasProject: !!p,
                    hasEngine: !!p?.engine,
                    hasEditing: !!p?.editing,
                    hasApi: !!p?.api,
                    hasBoxGraph: !!p?.boxGraph,
                    hasTimelineBox: !!p?.timelineBox,
                    bpm: p?.timelineBox?.bpm?.getValue?.() ?? 'no bpm',
                };
            }""")
            print(f"[test] project state: {json.dumps(state, indent=2)}")
        except Exception as e:
            print(f"[test] project check failed: {e}")

        await browser.close()
        return 0

if __name__ == "__main__":
    rc = asyncio.run(main())
    sys.exit(rc)

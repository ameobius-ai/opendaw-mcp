#!/usr/bin/env python3
"""E2E test for create_trill — rapid alternation between two notes."""
import sys
import os
import json
import asyncio
import subprocess
import time

os.environ["DAW_URL"] = "http://localhost:5174"
os.environ.setdefault("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", "/snap/bin/chromium")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, ".."))

from server import (
    bridge,
    mcp_opendaw_create_synth_track,
    mcp_opendaw_create_trill,
)


def parse(s):
    try:
        return json.loads(s)
    except Exception:
        try:
            start = s.index("{")
            end = s.rindex("}") + 1
            return json.loads(s[start:end])
        except Exception:
            return None


async def run_all_tests():
    passed = 0
    failed = 0

    await bridge.start()
    print("bridge started")

    r = await mcp_opendaw_create_synth_track("TrillTest", "vaporisateur")
    print(f"  synth: {r[:80]}")

    # 1. Default trill (16th, 4 beats = 16 notes)
    try:
        r = await mcp_opendaw_create_trill(lower_pitch=60, upper_pitch=62, rate="16th", duration_beats=4)
        d = parse(r)
        assert d and d.get("success"), f"default failed: {d}"
        assert d["total_notes"] == 16, f"expected 16, got {d['total_notes']}"
        assert d["interval"] == 2
        assert d["rate"] == "16th"
        print("  [default_16th] PASS")
        passed += 1
    except Exception as e:
        print(f"  [default_16th] FAIL: {e}")
        failed += 1

    # 2. 32nd trill (8 beats = 64 notes)
    try:
        r = await mcp_opendaw_create_trill(rate="32nd", duration_beats=8)
        d = parse(r)
        assert d and d.get("success"), f"32nd failed: {d}"
        assert d["total_notes"] == 64, f"expected 64, got {d['total_notes']}"
        print("  [32nd_rate] PASS")
        passed += 1
    except Exception as e:
        print(f"  [32nd_rate] FAIL: {e}")
        failed += 1

    # 3. 8th trill (2 beats = 4 notes)
    try:
        r = await mcp_opendaw_create_trill(rate="8th", duration_beats=2)
        d = parse(r)
        assert d and d.get("success"), f"8th failed: {d}"
        assert d["total_notes"] == 4, f"expected 4, got {d['total_notes']}"
        print("  [8th_rate] PASS")
        passed += 1
    except Exception as e:
        print(f"  [8th_rate] FAIL: {e}")
        failed += 1

    # 4. Triplet 16th (4 beats = 24 notes)
    try:
        r = await mcp_opendaw_create_trill(rate="16t", duration_beats=4)
        d = parse(r)
        assert d and d.get("success"), f"16t failed: {d}"
        # 4 beats / (1/6) = 24
        assert d["total_notes"] == 24, f"expected 24, got {d['total_notes']}"
        print("  [triplet_16th] PASS")
        passed += 1
    except Exception as e:
        print(f"  [triplet_16th] FAIL: {e}")
        failed += 1

    # 5. start_with_upper
    try:
        r = await mcp_opendaw_create_trill(rate="8th", duration_beats=4, start_with_upper=True)
        d = parse(r)
        assert d and d.get("success"), f"start_upper failed: {d}"
        assert d["start_with_upper"] == True
        assert d["total_notes"] == 8
        print("  [start_with_upper] PASS")
        passed += 1
    except Exception as e:
        print(f"  [start_with_upper] FAIL: {e}")
        failed += 1

    # 6. accent_upper=False
    try:
        r = await mcp_opendaw_create_trill(rate="8th", duration_beats=2, accent_upper=False)
        d = parse(r)
        assert d and d.get("success"), f"no_accent failed: {d}"
        assert d["accent_upper"] == False
        print("  [no_accent] PASS")
        passed += 1
    except Exception as e:
        print(f"  [no_accent] FAIL: {e}")
        failed += 1

    # 7. error — same pitches
    try:
        r = await mcp_opendaw_create_trill(lower_pitch=60, upper_pitch=60)
        assert "Error" in r, f"expected error, got: {r}"
        print("  [error_same_pitch] PASS")
        passed += 1
    except Exception as e:
        print(f"  [error_same_pitch] FAIL: {e}")
        failed += 1

    # 8. error — bad rate
    try:
        r = await mcp_opendaw_create_trill(rate="64th")
        assert "Error" in r
        print("  [error_bad_rate] PASS")
        passed += 1
    except Exception as e:
        print(f"  [error_bad_rate] FAIL: {e}")
        failed += 1

    await bridge.stop()
    print(f"\n=== {passed} passed, {failed} failed ===")
    return failed == 0


if __name__ == "__main__":
    print("=== create_trill E2E ===")
    vite_proc = subprocess.Popen(
        ["npx", "vite", "--port", "5174"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        cwd=os.path.join(SCRIPT_DIR, "..", "..", "headless-daw"),
    )
    time.sleep(6)
    try:
        ok = asyncio.run(run_all_tests())
    finally:
        vite_proc.terminate()
        try:
            vite_proc.wait(timeout=5)
        except Exception:
            vite_proc.kill()
    sys.exit(0 if ok else 1)

#!/usr/bin/env python3
"""E2E test for create_sequence — transposed melodic repetition."""
import sys, os, json, asyncio, subprocess, time

os.environ["DAW_URL"] = "http://localhost:5174"
os.environ.setdefault("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", "/snap/bin/chromium")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, ".."))

from server import (
    bridge,
    mcp_opendaw_create_synth_track,
    mcp_opendaw_create_sequence,
)

def parse(s):
    try:
        return json.loads(s)
    except:
        try:
            start = s.index("{")
            end = s.rindex("}") + 1
            return json.loads(s[start:end])
        except:
            return None

async def run_all_tests():
    passed = 0
    failed = 0

    await bridge.start()
    print("bridge started")

    r = await mcp_opendaw_create_synth_track("SeqTest", "vaporisateur")
    print(f"  synth: {r[:80]}")

    # 1. Default: 4-note pattern, up 4th, 3 repeats = 12 notes
    try:
        r = await mcp_opendaw_create_sequence(pattern="60,62,64,60", transposition=5, repeats=3, direction="up")
        d = parse(r)
        assert d and d.get("success"), f"default failed: {d}"
        assert d["total_notes"] == 12, f"expected 12 (4x3), got {d['total_notes']}"
        assert d["repeats"] == 3
        assert d["total_transposition"] == 10, f"expected 10 (5*2), got {d['total_transposition']}"
        print("  [default_up] PASS")
        passed += 1
    except Exception as e:
        print(f"  [default_up] FAIL: {e}")
        failed += 1

    # 2. Descending sequence
    try:
        r = await mcp_opendaw_create_sequence(pattern="72,71,69,67", transposition=2, repeats=4, direction="down")
        d = parse(r)
        assert d and d.get("success"), f"down failed: {d}"
        assert d["total_notes"] == 16, f"expected 16 (4x4), got {d['total_notes']}"
        assert d["direction"] == "down"
        print("  [descending] PASS")
        passed += 1
    except Exception as e:
        print(f"  [descending] FAIL: {e}")
        failed += 1

    # 3. Alternating direction
    try:
        r = await mcp_opendaw_create_sequence(pattern="60,64,67", transposition=7, repeats=3, direction="alternating")
        d = parse(r)
        assert d and d.get("success"), f"alt failed: {d}"
        assert d["total_notes"] == 9, f"expected 9 (3x3), got {d['total_notes']}"
        assert d["direction"] == "alternating"
        print("  [alternating] PASS")
        passed += 1
    except Exception as e:
        print(f"  [alternating] FAIL: {e}")
        failed += 1

    # 4. Velocity decay (fade out)
    try:
        r = await mcp_opendaw_create_sequence(pattern="60,62,64", repeats=3, velocity_decay=-0.1)
        d = parse(r)
        assert d and d.get("success"), f"decay failed: {d}"
        assert d["velocity_decay"] == -0.1
        print("  [velocity_decay] PASS")
        passed += 1
    except Exception as e:
        print(f"  [velocity_decay] FAIL: {e}")
        failed += 1

    # 5. Single repeat (no transposition)
    try:
        r = await mcp_opendaw_create_sequence(pattern="60,62,64,67", repeats=1, transposition=7)
        d = parse(r)
        assert d and d.get("success"), f"single failed: {d}"
        assert d["total_notes"] == 4, f"expected 4, got {d['total_notes']}"
        assert d["total_transposition"] == 0
        print("  [single_repeat] PASS")
        passed += 1
    except Exception as e:
        print(f"  [single_repeat] FAIL: {e}")
        failed += 1

    # 6. Error — bad pattern
    try:
        r = await mcp_opendaw_create_sequence(pattern="abc,def")
        assert "Error" in r
        print("  [error_bad_pattern] PASS")
        passed += 1
    except Exception as e:
        print(f"  [error_bad_pattern] FAIL: {e}")
        failed += 1

    # 7. Error — bad direction
    try:
        r = await mcp_opendaw_create_sequence(direction="sideways")
        assert "Error" in r
        print("  [error_bad_direction] PASS")
        passed += 1
    except Exception as e:
        print(f"  [error_bad_direction] FAIL: {e}")
        failed += 1

    # 8. Error — too many repeats
    try:
        r = await mcp_opendaw_create_sequence(repeats=10)
        assert "Error" in r
        print("  [error_too_many] PASS")
        passed += 1
    except Exception as e:
        print(f"  [error_too_many] FAIL: {e}")
        failed += 1

    await bridge.stop()
    print(f"\n=== {passed} passed, {failed} failed ===")
    return failed == 0

if __name__ == "__main__":
    print("=== create_sequence E2E ===")
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
        except:
            vite_proc.kill()
    sys.exit(0 if ok else 1)

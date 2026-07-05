#!/usr/bin/env python3
"""E2E test for create_chop — slice and rearrange pitches.

All tests run in a single process so the bridge singleton persists.
"""
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
    mcp_opendaw_create_chop,
)


def parse(s):
    """Parse JSON from tool output string."""
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
    """Run all chop tests using a single bridge connection."""
    results = []
    passed = 0
    failed = 0

    # Start bridge
    await bridge.start()
    print("bridge started")

    # Create a synth track first
    r = await mcp_opendaw_create_synth_track("ChopTest", "vaporisateur")
    print(f"  synth: {r[:80]}")

    # Test 1: reverse chop
    try:
        r = await mcp_opendaw_create_chop(
            pitches="60,62,64,67", chop_mode="reverse",
            segment_beats=0.5, velocity=0.9
        )
        d = parse(r)
        assert d and d.get("success"), f"reverse failed: {d}"
        assert d["total_notes"] == 4, f"expected 4, got {d['total_notes']}"
        assert d["chop_mode"] == "reverse"
        print("  [reverse_chop] PASS")
        passed += 1
    except Exception as e:
        print(f"  [reverse_chop] FAIL: {e}")
        failed += 1

    # Test 2: stutter chop (4 pitches x 3 = 12)
    try:
        r = await mcp_opendaw_create_chop(
            pitches="60,62,64,67", chop_mode="stutter",
            stutter_count=3, segment_beats=0.25
        )
        d = parse(r)
        assert d and d.get("success"), f"stutter failed: {d}"
        assert d["total_notes"] == 12, f"expected 12, got {d['total_notes']}"
        assert d["segments"] == 12
        print("  [stutter_chop] PASS")
        passed += 1
    except Exception as e:
        print(f"  [stutter_chop] FAIL: {e}")
        failed += 1

    # Test 3: shuffle chop
    try:
        r = await mcp_opendaw_create_chop(
            pitches="60,62,64,67,69", chop_mode="shuffle",
            segment_beats=0.5, seed=99
        )
        d = parse(r)
        assert d and d.get("success"), f"shuffle failed: {d}"
        assert d["total_notes"] == 5, f"expected 5, got {d['total_notes']}"
        print("  [shuffle_chop] PASS")
        passed += 1
    except Exception as e:
        print(f"  [shuffle_chop] FAIL: {e}")
        failed += 1

    # Test 4: ping-pong chop (4+4=8)
    try:
        r = await mcp_opendaw_create_chop(
            pitches="60,62,64,67", chop_mode="ping-pong",
            segment_beats=0.5
        )
        d = parse(r)
        assert d and d.get("success"), f"ping-pong failed: {d}"
        assert d["total_notes"] == 8, f"expected 8, got {d['total_notes']}"
        assert d["segments"] == 8
        print("  [ping_pong_chop] PASS")
        passed += 1
    except Exception as e:
        print(f"  [ping_pong_chop] FAIL: {e}")
        failed += 1

    # Test 5: gate chop (6/2=3)
    try:
        r = await mcp_opendaw_create_chop(
            pitches="60,62,64,67,69,71", chop_mode="gate",
            segment_beats=0.5
        )
        d = parse(r)
        assert d and d.get("success"), f"gate failed: {d}"
        assert d["total_notes"] == 3, f"expected 3, got {d['total_notes']}"
        print("  [gate_chop] PASS")
        passed += 1
    except Exception as e:
        print(f"  [gate_chop] FAIL: {e}")
        failed += 1

    # Test 6: octave shift
    try:
        r = await mcp_opendaw_create_chop(
            pitches="60,62,64,67", chop_mode="reverse",
            octave_shift=-1, segment_beats=0.5
        )
        d = parse(r)
        assert d and d.get("success"), f"octave failed: {d}"
        assert d["octave_shift"] == -1
        assert d["total_notes"] == 4
        print("  [octave_shift] PASS")
        passed += 1
    except Exception as e:
        print(f"  [octave_shift] FAIL: {e}")
        failed += 1

    # Test 7: error - bad pitches
    try:
        r = await mcp_opendaw_create_chop(pitches="abc,def", chop_mode="reverse")
        assert "Error" in r, f"expected error, got: {r}"
        print("  [error_bad_pitches] PASS")
        passed += 1
    except Exception as e:
        print(f"  [error_bad_pitches] FAIL: {e}")
        failed += 1

    # Test 8: error - bad mode
    try:
        r = await mcp_opendaw_create_chop(pitches="60,62", chop_mode="invalid")
        assert "Error" in r
        print("  [error_bad_mode] PASS")
        passed += 1
    except Exception as e:
        print(f"  [error_bad_mode] FAIL: {e}")
        failed += 1

    # Cleanup
    await bridge.stop()

    print(f"\n=== {passed} passed, {failed} failed ===")
    return failed == 0


if __name__ == "__main__":
    print("=== create_chop E2E ===")

    # Start Vite
    vite_proc = subprocess.Popen(
        ["npx", "vite", "--port", "5174"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
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

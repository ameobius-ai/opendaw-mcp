#!/usr/bin/env python3
"""E2E test for create_isorhythm — repeating rhythm (talea) × repeating pitch (color)."""
import sys, os, json, asyncio, subprocess, time

os.environ["DAW_URL"] = "http://localhost:5174"
os.environ.setdefault("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", "/snap/bin/chromium")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, ".."))

from server import (
    bridge,
    mcp_opendaw_create_synth_track,
    mcp_opendaw_create_isorhythm,
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

    r = await mcp_opendaw_create_synth_track("IsoTest", "vaporisateur")
    print(f"  synth: {r[:80]}")

    # 1. Default: talea=8, color=8, repeats=3 → 24 notes
    try:
        r = await mcp_opendaw_create_isorhythm()
        d = parse(r)
        assert d and d.get("success"), f"default failed: {d}"
        assert d["total_notes"] == 24, f"expected 24, got {d['total_notes']}"
        assert d["talea_length"] == 8
        assert d["color_length"] == 8
        print("  [default_equal_length] PASS")
        passed += 1
    except Exception as e:
        print(f"  [default_equal_length] FAIL: {e}")
        failed += 1

    # 2. Different lengths: talea=4, color=5 → phase shift, repeats=2 → 8 notes
    try:
        r = await mcp_opendaw_create_isorhythm(talea="1,1,1,1", color="60,62,64,65,67", repeats=2, start_beat=24)
        d = parse(r)
        assert d and d.get("success"), f"phase failed: {d}"
        assert d["total_notes"] == 8
        assert d["talea_length"] == 4
        assert d["color_length"] == 5
        assert d["phase_cycle"] == 20  # LCM(4,5) = 20
        print("  [phase_shift_different_lengths] PASS")
        passed += 1
    except Exception as e:
        print(f"  [phase_shift_different_lengths] FAIL: {e}")
        failed += 1

    # 3. Single element talea
    try:
        r = await mcp_opendaw_create_isorhythm(talea="1", color="60,62,64", repeats=4, start_beat=32)
        d = parse(r)
        assert d and d.get("success"), f"single_talea failed: {d}"
        assert d["total_notes"] == 4
        assert d["length_beats"] == 4.0
        print("  [single_talea] PASS")
        passed += 1
    except Exception as e:
        print(f"  [single_talea] FAIL: {e}")
        failed += 1

    # 4. Complex rhythm
    try:
        r = await mcp_opendaw_create_isorhythm(talea="1,0.5,0.5,1,0.25,0.25,0.25,0.25", color="60,64,67", repeats=2, start_beat=40)
        d = parse(r)
        assert d and d.get("success"), f"complex failed: {d}"
        assert d["total_notes"] == 16
        # sum(talea) = 4, repeats=2 → 8 beats
        assert d["length_beats"] == 8.0
        print("  [complex_rhythm] PASS")
        passed += 1
    except Exception as e:
        print(f"  [complex_rhythm] FAIL: {e}")
        failed += 1

    # 5. Error — bad velocity
    try:
        r = await mcp_opendaw_create_isorhythm(velocity=2.0)
        assert "Error" in r
        print("  [error_bad_velocity] PASS")
        passed += 1
    except Exception as e:
        print(f"  [error_bad_velocity] FAIL: {e}")
        failed += 1

    # 6. Error — bad repeats
    try:
        r = await mcp_opendaw_create_isorhythm(repeats=0)
        assert "Error" in r
        print("  [error_bad_repeats] PASS")
        passed += 1
    except Exception as e:
        print(f"  [error_bad_repeats] FAIL: {e}")
        failed += 1

    # 7. Error — bad pitch
    try:
        r = await mcp_opendaw_create_isorhythm(color="60,200,64")
        assert "Error" in r
        print("  [error_bad_pitch] PASS")
        passed += 1
    except Exception as e:
        print(f"  [error_bad_pitch] FAIL: {e}")
        failed += 1

    # 8. Error — bad talea duration
    try:
        r = await mcp_opendaw_create_isorhythm(talea="1,0,1")
        assert "Error" in r
        print("  [error_bad_talea] PASS")
        passed += 1
    except Exception as e:
        print(f"  [error_bad_talea] FAIL: {e}")
        failed += 1

    await bridge.stop()
    print(f"\n=== {passed} passed, {failed} failed ===")
    return failed == 0

if __name__ == "__main__":
    print("=== create_isorhythm E2E ===")
    subprocess.run(["pkill", "-f", "vite.*5174"], capture_output=True)
    time.sleep(1)
    vite_bin = os.path.join(os.path.dirname(os.path.dirname(SCRIPT_DIR)), "headless-daw", "node_modules", ".bin", "vite")
    vite_proc = subprocess.Popen(
        [vite_bin, "--port", "5174"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        cwd=os.path.join(SCRIPT_DIR, "..", "..", "headless-daw"),
    )
    time.sleep(8)
    try:
        ok = asyncio.run(run_all_tests())
    finally:
        vite_proc.terminate()
        try:
            vite_proc.wait(timeout=5)
        except Exception:
            vite_proc.kill()
    sys.exit(0 if ok else 1)

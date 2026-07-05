#!/usr/bin/env python3
"""E2E test for create_bordun — continuously sustained drone chord."""
import sys, os, json, asyncio, subprocess, time

os.environ["DAW_URL"] = "http://localhost:5174"
os.environ.setdefault("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", "/snap/bin/chromium")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, ".."))

from server import (
    bridge,
    mcp_opendaw_create_synth_track,
    mcp_opendaw_create_bordun,
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

    r = await mcp_opendaw_create_synth_track("BordunTest", "vaporisateur")
    print(f"  synth: {r[:80]}")

    # 1. Default: open fifth C3+G3, 4 bars continuous = 2 notes
    try:
        r = await mcp_opendaw_create_bordun()
        d = parse(r)
        assert d and d.get("success"), f"default failed: {d}"
        assert d["total_notes"] == 2, f"expected 2, got {d['total_notes']}"
        assert 48 in d["pitches"]  # C3
        assert 55 in d["pitches"]  # G3
        assert d["bars"] == 4
        assert d["retrigger_bars"] == 0
        print("  [default_open_fifth] PASS")
        passed += 1
    except Exception as e:
        print(f"  [default_open_fifth] FAIL: {e}")
        failed += 1

    # 2. Octave+fifth drone, 3 notes sustained
    try:
        r = await mcp_opendaw_create_bordun(root="D", octave=2, intervals="0,7,12", bars=2)
        d = parse(r)
        assert d and d.get("success"), f"oct+fifth failed: {d}"
        assert d["total_notes"] == 3
        assert d["pitches"] == [38, 45, 50]  # D2, A2, D3
        print("  [octave_fifth] PASS")
        passed += 1
    except Exception as e:
        print(f"  [octave_fifth] FAIL: {e}")
        failed += 1

    # 3. Retrigger mode: 4 bars, retrigger every 2 bars, 2 pitches = 4 notes
    try:
        r = await mcp_opendaw_create_bordun(root="A", octave=3, intervals="0,7", bars=4, retrigger_bars=2)
        d = parse(r)
        assert d and d.get("success"), f"retrigger failed: {d}"
        assert d["total_notes"] == 4, f"expected 4, got {d['total_notes']}"
        assert d["retrigger_bars"] == 2
        print("  [retrigger_mode] PASS")
        passed += 1
    except Exception as e:
        print(f"  [retrigger_mode] FAIL: {e}")
        failed += 1

    # 4. Single note drone, 8 bars
    try:
        r = await mcp_opendaw_create_bordun(root="G", octave=2, intervals="0", bars=8)
        d = parse(r)
        assert d and d.get("success"), f"single failed: {d}"
        assert d["total_notes"] == 1
        assert d["pitches"] == [43]  # G2
        assert d["length_beats"] == 32
        print("  [single_note_drone] PASS")
        passed += 1
    except Exception as e:
        print(f"  [single_note_drone] FAIL: {e}")
        failed += 1

    # 5. 3/4 time signature
    try:
        r = await mcp_opendaw_create_bordun(root="Eb", octave=3, intervals="0,3,7", bars=4, beats_per_bar=3)
        d = parse(r)
        assert d and d.get("success"), f"3/4 failed: {d}"
        assert d["length_beats"] == 12, f"expected 12, got {d['length_beats']}"
        assert d["total_notes"] == 3  # minor triad sustained
        print("  [three_four_time] PASS")
        passed += 1
    except Exception as e:
        print(f"  [three_four_time] FAIL: {e}")
        failed += 1

    # 6. Error — bad root note
    try:
        r = await mcp_opendaw_create_bordun(root="XYZ")
        assert "Error" in r
        print("  [error_bad_root] PASS")
        passed += 1
    except Exception as e:
        print(f"  [error_bad_root] FAIL: {e}")
        failed += 1

    # 7. Error — bad octave
    try:
        r = await mcp_opendaw_create_bordun(octave=9)
        assert "Error" in r
        print("  [error_bad_octave] PASS")
        passed += 1
    except Exception as e:
        print(f"  [error_bad_octave] FAIL: {e}")
        failed += 1

    # 8. Error — bad velocity
    try:
        r = await mcp_opendaw_create_bordun(velocity=2.0)
        assert "Error" in r
        print("  [error_bad_velocity] PASS")
        passed += 1
    except Exception as e:
        print(f"  [error_bad_velocity] FAIL: {e}")
        failed += 1

    await bridge.stop()
    print(f"\n=== {passed} passed, {failed} failed ===")
    return failed == 0

if __name__ == "__main__":
    print("=== create_bordun E2E ===")
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

#!/usr/bin/env python3
"""E2E test for create_pedal_point — sustained bass under changing chords."""
import sys, os, json, asyncio, subprocess, time

os.environ["DAW_URL"] = "http://localhost:5174"
os.environ.setdefault("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", "/snap/bin/chromium")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, ".."))

from server import (
    bridge,
    mcp_opendaw_create_synth_track,
    mcp_opendaw_create_pedal_point,
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

    r = await mcp_opendaw_create_synth_track("PedalTest", "vaporisateur")
    print(f"  synth: {r[:80]}")

    # 1. Default: Cm,Ab,Eb,Bb with retrigger pedal = 4 chords × (1 pedal + 3 chord notes) = 16
    try:
        r = await mcp_opendaw_create_pedal_point(pedal_pitch=36, chord_pattern="Cm,Ab,Eb,Bb")
        d = parse(r)
        assert d and d.get("success"), f"default failed: {d}"
        assert d["chord_count"] == 4
        # 4 pedal + 4×3 chord = 4+12=16
        assert d["total_notes"] == 16, f"expected 16, got {d['total_notes']}"
        assert d["retrigger_pedal"] == True
        print("  [default_retrigger] PASS")
        passed += 1
    except Exception as e:
        print(f"  [default_retrigger] FAIL: {e}")
        failed += 1

    # 2. Sustained pedal (no retrigger) = 1 pedal + 12 chord = 13
    try:
        r = await mcp_opendaw_create_pedal_point(pedal_pitch=36, chord_pattern="Cm,Ab,Eb,Bb", retrigger_pedal=False)
        d = parse(r)
        assert d and d.get("success"), f"sustained failed: {d}"
        # 1 long pedal + 4×3 chord notes = 1+12=13
        assert d["total_notes"] == 13, f"expected 13, got {d['total_notes']}"
        assert d["retrigger_pedal"] == False
        print("  [sustained_pedal] PASS")
        passed += 1
    except Exception as e:
        print(f"  [sustained_pedal] FAIL: {e}")
        failed += 1

    # 3. 7th chords (m7 = 4 notes per chord)
    try:
        r = await mcp_opendaw_create_pedal_point(chord_pattern="Cm7,Fm7,Gm7", retrigger_pedal=True)
        d = parse(r)
        assert d and d.get("success"), f"7th failed: {d}"
        assert d["chord_count"] == 3
        # 3 pedal + 3×4 chord = 3+12=15
        assert d["total_notes"] == 15, f"expected 15, got {d['total_notes']}"
        print("  [seventh_chords] PASS")
        passed += 1
    except Exception as e:
        print(f"  [seventh_chords] FAIL: {e}")
        failed += 1

    # 4. 2 bars per chord
    try:
        r = await mcp_opendaw_create_pedal_point(chord_pattern="Cm,Ab", bars_per_chord=2)
        d = parse(r)
        assert d and d.get("success"), f"2bars failed: {d}"
        assert d["length_beats"] == 16, f"expected 16 beats (2×4×2), got {d['length_beats']}"
        print("  [two_bars_per_chord] PASS")
        passed += 1
    except Exception as e:
        print(f"  [two_bars_per_chord] FAIL: {e}")
        failed += 1

    # 5. 3/4 time signature
    try:
        r = await mcp_opendaw_create_pedal_point(chord_pattern="Cm,Ab,Eb", beats_per_bar=3)
        d = parse(r)
        assert d and d.get("success"), f"3/4 failed: {d}"
        assert d["length_beats"] == 9, f"expected 9 beats (3×3), got {d['length_beats']}"
        print("  [three_four_time] PASS")
        passed += 1
    except Exception as e:
        print(f"  [three_four_time] FAIL: {e}")
        failed += 1

    # 6. Error — bad chord name
    try:
        r = await mcp_opendaw_create_pedal_point(chord_pattern="XYZ")
        assert "Error" in r
        print("  [error_bad_chord] PASS")
        passed += 1
    except Exception as e:
        print(f"  [error_bad_chord] FAIL: {e}")
        failed += 1

    # 7. Error — bad pedal pitch
    try:
        r = await mcp_opendaw_create_pedal_point(pedal_pitch=200)
        assert "Error" in r
        print("  [error_bad_pitch] PASS")
        passed += 1
    except Exception as e:
        print(f"  [error_bad_pitch] FAIL: {e}")
        failed += 1

    # 8. sus4 chord type
    try:
        r = await mcp_opendaw_create_pedal_point(chord_pattern="Csus4,Gsus4")
        d = parse(r)
        assert d and d.get("success"), f"sus4 failed: {d}"
        # 2 pedal + 2×3 chord = 2+6=8
        assert d["total_notes"] == 8, f"expected 8, got {d['total_notes']}"
        print("  [sus4_chords] PASS")
        passed += 1
    except Exception as e:
        print(f"  [sus4_chords] FAIL: {e}")
        failed += 1

    await bridge.stop()
    print(f"\n=== {passed} passed, {failed} failed ===")
    return failed == 0

if __name__ == "__main__":
    print("=== create_pedal_point E2E ===")
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

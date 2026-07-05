#!/usr/bin/env python3
"""E2E test for create_glissando — smooth scale run between two pitches."""
import sys, os, json, asyncio, subprocess, time

os.environ["DAW_URL"] = "http://localhost:5174"
os.environ.setdefault("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", "/snap/bin/chromium")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, ".."))

from server import (
    bridge,
    mcp_opendaw_create_synth_track,
    mcp_opendaw_create_glissando,
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

    r = await mcp_opendaw_create_synth_track("GlissTest", "vaporisateur")
    print(f"  synth: {r[:80]}")

    # 1. Chromatic ascending (C4→C5 = 12+1=13 notes)
    try:
        r = await mcp_opendaw_create_glissando(start_pitch=60, end_pitch=72, scale_type="chromatic", rate="16th", duration_beats=4)
        d = parse(r)
        assert d and d.get("success"), f"chromatic asc failed: {d}"
        assert d["total_notes"] == 13, f"expected 13, got {d['total_notes']}"
        assert d["direction"] == "ascending"
        assert d["scale_type"] == "chromatic"
        print("  [chromatic_asc] PASS")
        passed += 1
    except Exception as e:
        print(f"  [chromatic_asc] FAIL: {e}")
        failed += 1

    # 2. Major scale (C4→C5 = 8 notes: C D E F G A B C)
    try:
        r = await mcp_opendaw_create_glissando(start_pitch=60, end_pitch=72, scale_type="major", rate="8th", duration_beats=4)
        d = parse(r)
        assert d and d.get("success"), f"major failed: {d}"
        assert d["total_notes"] == 8, f"expected 8, got {d['total_notes']}"
        print("  [major_scale] PASS")
        passed += 1
    except Exception as e:
        print(f"  [major_scale] FAIL: {e}")
        failed += 1

    # 3. Descending (C5→C4 chromatic = 13 notes)
    try:
        r = await mcp_opendaw_create_glissando(start_pitch=72, end_pitch=60, scale_type="chromatic", rate="16th")
        d = parse(r)
        assert d and d.get("success"), f"desc failed: {d}"
        assert d["total_notes"] == 13
        assert d["direction"] == "descending"
        print("  [descending] PASS")
        passed += 1
    except Exception as e:
        print(f"  [descending] FAIL: {e}")
        failed += 1

    # 4. Pentatonic minor (fewer notes)
    try:
        r = await mcp_opendaw_create_glissando(start_pitch=60, end_pitch=72, scale_type="pentatonic_minor", rate="8th")
        d = parse(r)
        assert d and d.get("success"), f"pentatonic failed: {d}"
        # C minor pent: C, Eb, F, G, Bb, C = 6 notes
        assert d["total_notes"] == 6, f"expected 6, got {d['total_notes']}"
        print("  [pentatonic_minor] PASS")
        passed += 1
    except Exception as e:
        print(f"  [pentatonic_minor] FAIL: {e}")
        failed += 1

    # 5. Whole tone (6 notes per octave)
    try:
        r = await mcp_opendaw_create_glissando(start_pitch=60, end_pitch=72, scale_type="whole_tone", rate="8th")
        d = parse(r)
        assert d and d.get("success"), f"whole_tone failed: {d}"
        # C whole tone: C D E F# G# A# C = 7 notes
        assert d["total_notes"] == 7, f"expected 7, got {d['total_notes']}"
        print("  [whole_tone] PASS")
        passed += 1
    except Exception as e:
        print(f"  [whole_tone] FAIL: {e}")
        failed += 1

    # 6. velocity curve arc
    try:
        r = await mcp_opendaw_create_glissando(velocity_curve="arc", scale_type="major", rate="8th")
        d = parse(r)
        assert d and d.get("success"), f"arc failed: {d}"
        assert d["velocity_curve"] == "arc"
        print("  [velocity_arc] PASS")
        passed += 1
    except Exception as e:
        print(f"  [velocity_arc] FAIL: {e}")
        failed += 1

    # 7. error — same pitch
    try:
        r = await mcp_opendaw_create_glissando(start_pitch=60, end_pitch=60)
        assert "Error" in r
        print("  [error_same_pitch] PASS")
        passed += 1
    except Exception as e:
        print(f"  [error_same_pitch] FAIL: {e}")
        failed += 1

    # 8. error — bad scale
    try:
        r = await mcp_opendaw_create_glissando(scale_type="dorian")
        assert "Error" in r
        print("  [error_bad_scale] PASS")
        passed += 1
    except Exception as e:
        print(f"  [error_bad_scale] FAIL: {e}")
        failed += 1

    await bridge.stop()
    print(f"\n=== {passed} passed, {failed} failed ===")
    return failed == 0

if __name__ == "__main__":
    print("=== create_glissando E2E ===")
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

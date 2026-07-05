#!/usr/bin/env python3
"""E2E test for create_hocket — melodic line split between voices."""
import sys, os, json, asyncio, subprocess, time

os.environ["DAW_URL"] = "http://localhost:5174"
os.environ.setdefault("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", "/snap/bin/chromium")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, ".."))

from server import (
    bridge,
    mcp_opendaw_create_synth_track,
    mcp_opendaw_create_note_track,
    mcp_opendaw_create_hocket,
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

    # Create synth track + extra note tracks for voices
    r = await mcp_opendaw_create_synth_track("HocketTest", "vaporisateur")
    print(f"  synth: {r[:80]}")

    # Add a second note track for voice 2
    r2 = await mcp_opendaw_create_note_track(unit_index=-1)
    print(f"  note track: {r2[:60]}")

    # 1. Default: 8-note melody, 2 voices, alternate
    try:
        r = await mcp_opendaw_create_hocket()
        d = parse(r)
        assert d and d.get("success"), f"default failed: {d}"
        assert d["total_notes"] == 8
        assert d["voices"] == 2
        assert d["split_mode"] == "alternate"
        print("  [default_alternate_2v] PASS")
        passed += 1
    except Exception as e:
        print(f"  [default_alternate_2v] FAIL: {e}")
        failed += 1

    # 2. 3 voices, alternate
    try:
        r = await mcp_opendaw_create_hocket(melody="60,62,64,65,67,65,64,62,60,62,64,65", voices=3, start_beat=8)
        d = parse(r)
        assert d and d.get("success"), f"3v failed: {d}"
        assert d["total_notes"] == 12
        assert d["voices"] == 3
        print("  [three_voices] PASS")
        passed += 1
    except Exception as e:
        print(f"  [three_voices] FAIL: {e}")
        failed += 1

    # 3. Pairs mode
    try:
        r = await mcp_opendaw_create_hocket(melody="60,62,64,65,67,65,64,62", voices=2, split_mode="pairs", start_beat=20)
        d = parse(r)
        assert d and d.get("success"), f"pairs failed: {d}"
        assert d["total_notes"] == 8
        assert d["split_mode"] == "pairs"
        print("  [pairs_mode] PASS")
        passed += 1
    except Exception as e:
        print(f"  [pairs_mode] FAIL: {e}")
        failed += 1

    # 4. Phrase mode
    try:
        r = await mcp_opendaw_create_hocket(melody="60,62,64,65,67,65,64,62", voices=2, split_mode="phrase", start_beat=28)
        d = parse(r)
        assert d and d.get("success"), f"phrase failed: {d}"
        assert d["total_notes"] == 8
        print("  [phrase_mode] PASS")
        passed += 1
    except Exception as e:
        print(f"  [phrase_mode] FAIL: {e}")
        failed += 1

    # 5. Error — bad voices (1)
    try:
        r = await mcp_opendaw_create_hocket(voices=1)
        assert "Error" in r
        print("  [error_bad_voices] PASS")
        passed += 1
    except Exception as e:
        print(f"  [error_bad_voices] FAIL: {e}")
        failed += 1

    # 6. Error — bad split_mode
    try:
        r = await mcp_opendaw_create_hocket(split_mode="invalid")
        assert "Error" in r
        print("  [error_bad_split_mode] PASS")
        passed += 1
    except Exception as e:
        print(f"  [error_bad_split_mode] FAIL: {e}")
        failed += 1

    # 7. Error — bad velocity
    try:
        r = await mcp_opendaw_create_hocket(velocity=2.0)
        assert "Error" in r
        print("  [error_bad_velocity] PASS")
        passed += 1
    except Exception as e:
        print(f"  [error_bad_velocity] FAIL: {e}")
        failed += 1

    # 8. Error — bad pitch
    try:
        r = await mcp_opendaw_create_hocket(melody="60,200,64")
        assert "Error" in r
        print("  [error_bad_pitch] PASS")
        passed += 1
    except Exception as e:
        print(f"  [error_bad_pitch] FAIL: {e}")
        failed += 1

    await bridge.stop()
    print(f"\n=== {passed} passed, {failed} failed ===")
    return failed == 0

if __name__ == "__main__":
    print("=== create_hocket E2E ===")
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

#!/usr/bin/env python3
"""E2E test for create_comping orchestration tool."""
import sys, os, time, subprocess, json, signal

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault("OPENDAW_URL", "http://localhost:5174")
os.environ.setdefault("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", "/snap/bin/chromium")

VITE_DIR = os.path.join(os.path.dirname(os.path.dirname(SCRIPT_DIR)), "headless-daw")

def start_vite():
    proc = subprocess.Popen(
        ["npx", "vite", "--port", "5174"],
        cwd=VITE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        env={**os.environ, "NODE_OPTIONS": ""},
    )
    time.sleep(6)
    return proc

def main():
    proc = start_vite()
    try:
        sys.path.insert(0, SCRIPT_DIR)
        from server import bridge, mcp_opendaw_create_synth_track, mcp_opendaw_create_comping

        async def run():
            await bridge.start()
            r = await mcp_opendaw_create_synth_track(name="Comping Test", synth_type="vaporisateur")
            print(f"  setup: {r[:60]}")

            passed = 0
            failed = 0

            # Test 1: basic jazz comping — 4 chords × 8-step rhythm
            r = await mcp_opendaw_create_comping(
                chords='[["C","min7"],["F","min7"],["G","dom7"],["C","min7"]]',
                rhythm="x-x-x-x-",
                unit_index=1,
                track_index=0,
            )
            d = json.loads(r) if r.strip().startswith("{") else {}
            if d.get("success") and d.get("total_notes", 0) > 0 and d.get("chords") == 4:
                print(f"  ✅ test 1: jazz comping — {d['total_notes']} notes, {d['chords']} chords")
                passed += 1
            else:
                print(f"  ❌ test 1: {r[:120]}")
                failed += 1

            # Test 2: funk comping with ghosts
            r = await mcp_opendaw_create_comping(
                chords='[["C","min7"],["F","min7"]]',
                rhythm="x--x.x-",
                unit_index=1,
                track_index=0,
                start_beat=100,
            )
            d = json.loads(r) if r.strip().startswith("{") else {}
            if d.get("success") and d.get("total_notes", 0) > 0:
                print(f"  ✅ test 2: funk comping with ghosts — {d['total_notes']} notes")
                passed += 1
            else:
                print(f"  ❌ test 2: {r[:120]}")
                failed += 1

            # Test 3: reggae skank (16th off-beats)
            r = await mcp_opendaw_create_comping(
                chords='[["C","maj"],["D","maj"]]',
                rhythm="-x-x-x-x-x-x-x-x",
                unit_index=1,
                track_index=0,
                start_beat=200,
                note_spacing=0.25,
            )
            d = json.loads(r) if r.strip().startswith("{") else {}
            if d.get("success") and d.get("rhythm_steps") == 16:
                print(f"  ✅ test 3: reggae skank 16 steps — {d['total_notes']} notes")
                passed += 1
            else:
                print(f"  ❌ test 3: {r[:120]}")
                failed += 1

            # Test 4: syncopation on
            r = await mcp_opendaw_create_comping(
                chords='[["C","min7"]]',
                rhythm="x-x-",
                unit_index=1,
                track_index=0,
                start_beat=300,
                syncopation=0.3,
            )
            d = json.loads(r) if r.strip().startswith("{") else {}
            if d.get("success") and d.get("syncopation") == 0.3:
                print(f"  ✅ test 4: syncopation=0.3 — {d['total_notes']} notes")
                passed += 1
            else:
                print(f"  ❌ test 4: {r[:120]}")
                failed += 1

            # Test 5: bad chord JSON
            r = await mcp_opendaw_create_comping(chords='not json')
            if "Error" in r:
                print(f"  ✅ test 5: bad JSON rejected")
                passed += 1
            else:
                print(f"  ❌ test 5: {r[:80]}")
                failed += 1

            # Test 6: bad rhythm chars
            r = await mcp_opendaw_create_comping(
                chords='[["C","min"]]',
                rhythm="x!x!",
            )
            if "Error" in r:
                print(f"  ✅ test 6: bad rhythm chars rejected")
                passed += 1
            else:
                print(f"  ❌ test 6: {r[:80]}")
                failed += 1

            # Test 7: bad velocity
            r = await mcp_opendaw_create_comping(
                chords='[["C","min"]]',
                velocity=2.0,
            )
            if "Error" in r:
                print(f"  ✅ test 7: bad velocity rejected")
                passed += 1
            else:
                print(f"  ❌ test 7: {r[:80]}")
                failed += 1

            # Test 8: unknown chord type
            r = await mcp_opendaw_create_comping(
                chords='[["C","minor7flat5"]]',
            )
            if "Error" in r:
                print(f"  ✅ test 8: unknown chord type rejected")
                passed += 1
            else:
                print(f"  ❌ test 8: {r[:80]}")
                failed += 1

            print(f"\n{'='*40}")
            print(f"create_comping E2E: {passed}/{passed+failed}")
            return failed == 0

        import asyncio
        ok = asyncio.run(run())
        sys.exit(0 if ok else 1)
    finally:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=5)

if __name__ == "__main__":
    main()

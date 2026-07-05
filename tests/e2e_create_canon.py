#!/usr/bin/env python3
"""E2E test for create_canon orchestration tool."""
import sys, os, time, subprocess, json, signal

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault("OPENDAW_URL", "http://localhost:5174")
os.environ.setdefault("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", "/snap/bin/chromium")

VITE_CMD = "npx vite --port 5174"
VITE_DIR = os.path.join(os.path.dirname(os.path.dirname(SCRIPT_DIR)), "headless-daw")

def start_vite():
    proc = subprocess.Popen(
        ["npx", "vite", "--port", "5174"],
        cwd=VITE_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env={**os.environ, "NODE_OPTIONS": ""},
    )
    time.sleep(6)
    return proc

def main():
    proc = start_vite()
    try:
        sys.path.insert(0, SCRIPT_DIR)
        from server import bridge, mcp_opendaw_create_synth_track, mcp_opendaw_create_canon

        async def run():
            await bridge.start()

            # Setup: create a synth track
            r = await mcp_opendaw_create_synth_track(name="Canon Test", synth_type="vaporisateur")
            print(f"  setup: {r[:80]}")

            passed = 0
            failed = 0

            # Test 1: basic 3-voice canon
            r = await mcp_opendaw_create_canon(
                melody="60,62,64,67,64,62,60,57",
                voices=3,
                entry_delay_beats=4,
                transposition="0,7,12",
            )
            d = json.loads(r) if r.strip().startswith("{") else {}
            if d.get("success") and d.get("total_notes") == 24:  # 3 voices × 8 notes
                print(f"  ✅ test 1: basic 3-voice canon — {d['total_notes']} notes, {d['voices']} voices")
                passed += 1
            else:
                print(f"  ❌ test 1: {r[:120]}")
                failed += 1

            # Test 2: 2-voice round (unison transposition)
            r = await mcp_opendaw_create_canon(
                melody="60,62,64,65",
                voices=2,
                entry_delay_beats=2,
                transposition="0,0",
            )
            d = json.loads(r) if r.strip().startswith("{") else {}
            if d.get("success") and d.get("total_notes") == 8:  # 2 × 4
                print(f"  ✅ test 2: 2-voice round — {d['total_notes']} notes")
                passed += 1
            else:
                print(f"  ❌ test 2: {r[:120]}")
                failed += 1

            # Test 3: direction=down (high voice enters first)
            r = await mcp_opendaw_create_canon(
                melody="60,64,67,72",
                voices=3,
                entry_delay_beats=4,
                transposition="0,7,12",
                direction="down",
            )
            d = json.loads(r) if r.strip().startswith("{") else {}
            if d.get("success") and d.get("total_notes") == 12 and d.get("direction") == "down":
                print(f"  ✅ test 3: direction=down — {d['total_notes']} notes")
                passed += 1
            else:
                print(f"  ❌ test 3: {r[:120]}")
                failed += 1

            # Test 4: 4 voices with fifth transposition
            r = await mcp_opendaw_create_canon(
                melody="57,60,64,60,57,55",
                voices=4,
                entry_delay_beats=2,
                transposition="0,5,7,12",
                velocity_decay=0.1,
            )
            d = json.loads(r) if r.strip().startswith("{") else {}
            if d.get("success") and d.get("total_notes") == 24:  # 4 × 6
                print(f"  ✅ test 4: 4-voice canon — {d['total_notes']} notes")
                passed += 1
            else:
                print(f"  ❌ test 4: {r[:120]}")
                failed += 1

            # Test 5: bad voices count
            r = await mcp_opendaw_create_canon(melody="60,62", voices=1)
            if "Error" in r:
                print(f"  ✅ test 5: bad voices (1) rejected")
                passed += 1
            else:
                print(f"  ❌ test 5: {r[:80]}")
                failed += 1

            # Test 6: transposition count mismatch
            r = await mcp_opendaw_create_canon(
                melody="60,62",
                voices=3,
                transposition="0,7",  # only 2, need 3
            )
            if "Error" in r:
                print(f"  ✅ test 6: transposition count mismatch rejected")
                passed += 1
            else:
                print(f"  ❌ test 6: {r[:80]}")
                failed += 1

            # Test 7: bad direction
            r = await mcp_opendaw_create_canon(melody="60,62", voices=2, direction="sideways")
            if "Error" in r:
                print(f"  ✅ test 7: bad direction rejected")
                passed += 1
            else:
                print(f"  ❌ test 7: {r[:80]}")
                failed += 1

            # Test 8: start_beat offset
            r = await mcp_opendaw_create_canon(
                melody="48,50,52",
                voices=2,
                entry_delay_beats=1,
                transposition="0,12",
                start_beat=8,
            )
            d = json.loads(r) if r.strip().startswith("{") else {}
            if d.get("success") and d.get("total_notes") == 6:
                print(f"  ✅ test 8: start_beat=8 — {d['total_notes']} notes")
                passed += 1
            else:
                print(f"  ❌ test 8: {r[:120]}")
                failed += 1

            print(f"\n{'='*40}")
            print(f"create_canon E2E: {passed}/{passed+failed}")
            return failed == 0

        import asyncio
        ok = asyncio.run(run())
        sys.exit(0 if ok else 1)
    finally:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=5)


if __name__ == "__main__":
    main()

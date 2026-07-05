#!/usr/bin/env python3
"""E2E test for create_mordent orchestration tool."""
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
        from server import bridge, mcp_opendaw_create_synth_track, mcp_opendaw_create_mordent

        async def run():
            await bridge.start()
            r = await mcp_opendaw_create_synth_track(name="Mordent Test", synth_type="vaporisateur")
            print(f"  setup: {r[:60]}")

            passed = 0
            failed = 0

            # Test 1: upper mordent — 3 notes (main→neighbor→main)
            r = await mcp_opendaw_create_mordent(main_pitch=60, direction="upper", interval=2, unit_index=1)
            d = json.loads(r) if r.strip().startswith("{") else {}
            if d.get("success") and d.get("total_notes") == 3:
                print(f"  ✅ test 1: upper mordent — {d['total_notes']} notes")
                passed += 1
            else:
                print(f"  ❌ test 1: {r[:120]}")
                failed += 1

            # Test 2: lower mordent
            r = await mcp_opendaw_create_mordent(main_pitch=67, direction="lower", interval=1, unit_index=1, start_beat=10)
            d = json.loads(r) if r.strip().startswith("{") else {}
            if d.get("success") and d.get("total_notes") == 3 and d.get("direction") == "lower":
                print(f"  ✅ test 2: lower mordent — {d['total_notes']} notes")
                passed += 1
            else:
                print(f"  ❌ test 2: {r[:120]}")
                failed += 1

            # Test 3: half-step upper (diatonic)
            r = await mcp_opendaw_create_mordent(main_pitch=64, direction="upper", interval=1, unit_index=1, start_beat=20)
            d = json.loads(r) if r.strip().startswith("{") else {}
            if d.get("success") and d.get("total_notes") == 3 and d.get("interval") == 1:
                print(f"  ✅ test 3: half-step upper — {d['total_notes']} notes")
                passed += 1
            else:
                print(f"  ❌ test 3: {r[:120]}")
                failed += 1

            # Test 4: bad direction
            r = await mcp_opendaw_create_mordent(main_pitch=60, direction="sideways", unit_index=1)
            if "Error" in r:
                print(f"  ✅ test 4: bad direction rejected")
                passed += 1
            else:
                print(f"  ❌ test 4: {r[:80]}")
                failed += 1

            # Test 5: bad interval (0)
            r = await mcp_opendaw_create_mordent(main_pitch=60, interval=0, unit_index=1)
            if "Error" in r:
                print(f"  ✅ test 5: bad interval (0) rejected")
                passed += 1
            else:
                print(f"  ❌ test 5: {r[:80]}")
                failed += 1

            # Test 6: bad pitch (128)
            r = await mcp_opendaw_create_mordent(main_pitch=128, unit_index=1)
            if "Error" in r:
                print(f"  ✅ test 6: bad pitch rejected")
                passed += 1
            else:
                print(f"  ❌ test 6: {r[:80]}")
                failed += 1

            # Test 7: bad velocity
            r = await mcp_opendaw_create_mordent(main_pitch=60, velocity=1.5, unit_index=1)
            if "Error" in r:
                print(f"  ✅ test 7: bad velocity rejected")
                passed += 1
            else:
                print(f"  ❌ test 7: {r[:80]}")
                failed += 1

            # Test 8: pitch clamped neighbor (main=0, lower, interval=7)
            r = await mcp_opendaw_create_mordent(main_pitch=0, direction="lower", interval=7, unit_index=1)
            if "Error" in r and "clamped" in r:
                print(f"  ✅ test 8: clamped neighbor detected")
                passed += 1
            else:
                print(f"  ❌ test 8: {r[:80]}")
                failed += 1

            print(f"\n{'='*40}")
            print(f"create_mordent E2E: {passed}/{passed+failed}")
            return failed == 0

        import asyncio
        ok = asyncio.run(run())
        sys.exit(0 if ok else 1)
    finally:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=5)

if __name__ == "__main__":
    main()

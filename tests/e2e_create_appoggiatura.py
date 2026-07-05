#!/usr/bin/env python3
"""E2E test for create_appoggiatura orchestration tool."""
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
        from server import bridge, mcp_opendaw_create_synth_track, mcp_opendaw_create_appoggiatura

        async def run():
            await bridge.start()
            r = await mcp_opendaw_create_synth_track(name="Appogg Test", synth_type="vaporisateur")
            print(f"  setup: {r[:60]}")

            passed = 0
            failed = 0

            # Test 1: appoggiatura above — 2 notes (approach → main)
            r = await mcp_opendaw_create_appoggiatura(main_pitch=60, approach_pitch=62, unit_index=1)
            d = json.loads(r) if r.strip().startswith("{") else {}
            if d.get("success") and d.get("total_notes") == 2 and d.get("direction") == "above":
                print(f"  ✅ test 1: appoggiatura above — {d['total_notes']} notes")
                passed += 1
            else:
                print(f"  ❌ test 1: {r[:120]}")
                failed += 1

            # Test 2: appoggiatura below
            r = await mcp_opendaw_create_appoggiatura(main_pitch=60, approach_pitch=59, unit_index=1, start_beat=10)
            d = json.loads(r) if r.strip().startswith("{") else {}
            if d.get("success") and d.get("total_notes") == 2 and d.get("direction") == "below":
                print(f"  ✅ test 2: appoggiatura below — {d['total_notes']} notes")
                passed += 1
            else:
                print(f"  ❌ test 2: {r[:120]}")
                failed += 1

            # Test 3: ratio 0.5 (equal split)
            r = await mcp_opendaw_create_appoggiatura(main_pitch=64, approach_pitch=65, appoggiatura_ratio=0.5, unit_index=1, start_beat=20)
            d = json.loads(r) if r.strip().startswith("{") else {}
            if d.get("success") and d.get("appoggiatura_ratio") == 0.5:
                print(f"  ✅ test 3: ratio 0.5 — {d['total_notes']} notes")
                passed += 1
            else:
                print(f"  ❌ test 3: {r[:120]}")
                failed += 1

            # Test 4: same pitch
            r = await mcp_opendaw_create_appoggiatura(main_pitch=60, approach_pitch=60, unit_index=1)
            if "Error" in r:
                print("  ✅ test 4: same pitch rejected")
                passed += 1
            else:
                print(f"  ❌ test 4: {r[:80]}")
                failed += 1

            # Test 5: bad pitch
            r = await mcp_opendaw_create_appoggiatura(main_pitch=128, approach_pitch=60, unit_index=1)
            if "Error" in r:
                print("  ✅ test 5: bad pitch rejected")
                passed += 1
            else:
                print(f"  ❌ test 5: {r[:80]}")
                failed += 1

            # Test 6: bad ratio
            r = await mcp_opendaw_create_appoggiatura(main_pitch=60, approach_pitch=62, appoggiatura_ratio=0.3, unit_index=1)
            if "Error" in r:
                print("  ✅ test 6: bad ratio rejected")
                passed += 1
            else:
                print(f"  ❌ test 6: {r[:80]}")
                failed += 1

            # Test 7: bad velocity
            r = await mcp_opendaw_create_appoggiatura(main_pitch=60, approach_pitch=62, velocity=2.0, unit_index=1)
            if "Error" in r:
                print("  ✅ test 7: bad velocity rejected")
                passed += 1
            else:
                print(f"  ❌ test 7: {r[:80]}")
                failed += 1

            # Test 8: bad duration
            r = await mcp_opendaw_create_appoggiatura(main_pitch=60, approach_pitch=62, duration_beats=0.1, unit_index=1)
            if "Error" in r:
                print("  ✅ test 8: bad duration rejected")
                passed += 1
            else:
                print(f"  ❌ test 8: {r[:80]}")
                failed += 1

            print(f"\n{'='*40}")
            print(f"create_appoggiatura E2E: {passed}/{passed+failed}")
            return failed == 0

        import asyncio
        ok = asyncio.run(run())
        sys.exit(0 if ok else 1)
    finally:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=5)

if __name__ == "__main__":
    main()

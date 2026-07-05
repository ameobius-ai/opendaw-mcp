#!/usr/bin/env python3
"""E2E test for create_hemiola orchestration tool."""
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
    time.sleep(10)
    return proc

def main():
    proc = start_vite()
    try:
        sys.path.insert(0, SCRIPT_DIR)
        from server import bridge, mcp_opendaw_create_synth_track, mcp_opendaw_create_hemiola

        async def run():
            await bridge.start()
            r = await mcp_opendaw_create_synth_track(name="Hemiola Test", synth_type="vaporisateur")
            print(f"  setup: {r[:60]}")

            passed = 0
            failed = 0

            # Test 1: 3:2 hemiola — 5 notes (3 primary + 2 secondary)
            r = await mcp_opendaw_create_hemiola(pattern="3:2", unit_index=1)
            d = json.loads(r) if r.strip().startswith("{") else {}
            if d.get("success") and d.get("total_notes") == 5 and d.get("ratio") == "3:2":
                print(f"  ✅ test 1: 3:2 hemiola — {d['total_notes']} notes")
                passed += 1
            else:
                print(f"  ❌ test 1: {r[:120]}")
                failed += 1

            # Test 2: 2:3 hemiola — 5 notes (2 primary + 3 secondary)
            r = await mcp_opendaw_create_hemiola(pattern="2:3", unit_index=1, start_beat=10)
            d = json.loads(r) if r.strip().startswith("{") else {}
            if d.get("success") and d.get("total_notes") == 5 and d.get("ratio") == "2:3":
                print(f"  ✅ test 2: 2:3 hemiola — {d['total_notes']} notes")
                passed += 1
            else:
                print(f"  ❌ test 2: {r[:120]}")
                failed += 1

            # Test 3: bars=2 — 5 notes spanning 8 beats
            r = await mcp_opendaw_create_hemiola(pattern="3:2", bars=2, unit_index=1, start_beat=20)
            d = json.loads(r) if r.strip().startswith("{") else {}
            if d.get("success") and d.get("bars") == 2:
                print(f"  ✅ test 3: bars=2 — {d['total_notes']} notes")
                passed += 1
            else:
                print(f"  ❌ test 3: {r[:120]}")
                failed += 1

            # Test 4: bad pattern
            r = await mcp_opendaw_create_hemiola(pattern="4:3", unit_index=1)
            if "Error" in r:
                print("  ✅ test 4: bad pattern rejected")
                passed += 1
            else:
                print(f"  ❌ test 4: {r[:80]}")
                failed += 1

            # Test 5: bad bars
            r = await mcp_opendaw_create_hemiola(pattern="3:2", bars=8, unit_index=1)
            if "Error" in r:
                print("  ✅ test 5: bad bars rejected")
                passed += 1
            else:
                print(f"  ❌ test 5: {r[:80]}")
                failed += 1

            # Test 6: bad velocity
            r = await mcp_opendaw_create_hemiola(pattern="3:2", primary_velocity=2.0, unit_index=1)
            if "Error" in r:
                print("  ✅ test 6: bad velocity rejected")
                passed += 1
            else:
                print(f"  ❌ test 6: {r[:80]}")
                failed += 1

            # Test 7: bad pitch
            r = await mcp_opendaw_create_hemiola(pattern="3:2", primary_pitch=128, unit_index=1)
            if "Error" in r:
                print("  ✅ test 7: bad pitch rejected")
                passed += 1
            else:
                print(f"  ❌ test 7: {r[:80]}")
                failed += 1

            # Test 8: bad duration
            r = await mcp_opendaw_create_hemiola(pattern="3:2", duration=0.01, unit_index=1)
            if "Error" in r:
                print("  ✅ test 8: bad duration rejected")
                passed += 1
            else:
                print(f"  ❌ test 8: {r[:80]}")
                failed += 1

            print(f"\n{'='*40}")
            print(f"create_hemiola E2E: {passed}/{passed+failed}")
            return failed == 0

        import asyncio
        ok = asyncio.run(run())
        sys.exit(0 if ok else 1)
    finally:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=5)

if __name__ == "__main__":
    main()

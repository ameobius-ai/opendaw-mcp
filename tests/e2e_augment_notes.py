#!/usr/bin/env python3
"""E2E test for augment_notes transformation tool."""
import sys, os, time, subprocess, json, signal

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault("OPENDAW_URL", "http://localhost:5174")
os.environ.setdefault("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", "/snap/bin/chromium")

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
        from server import (
            bridge,
            mcp_opendaw_create_synth_track,
            mcp_opendaw_create_melody,
            mcp_opendaw_augment_notes,
        )

        async def run():
            await bridge.start()

            # Setup
            r = await mcp_opendaw_create_synth_track(name="Augment Test", synth_type="vaporisateur")
            r = await mcp_opendaw_create_melody(
                pattern="1 2 3 4 5",
                root="C",
                scale="major",
                unit_index=1,
                track_index=0,
            )
            print(f"  setup: melody — {r[:80]}")

            passed = 0
            failed = 0

            # Test 1: augmentation x2 (scale mode)
            r = await mcp_opendaw_augment_notes(factor=2.0, unit_index=1, track_index=0, region_index=0, mode="scale")
            d = json.loads(r) if r.strip().startswith("{") else {}
            if d.get("success") and d.get("notes_augmented", 0) > 0 and d.get("factor") == 2.0:
                print(f"  ✅ test 1: augmentation x2 scale — {d['notes_augmented']} notes")
                passed += 1
            else:
                print(f"  ❌ test 1: {r[:120]}")
                failed += 1

            # Verify durations doubled — recreate melody first
            await mcp_opendaw_create_melody(
                pattern="1 2 3",
                root="C",
                scale="major",
                unit_index=1,
                track_index=0,
                start_beat=100,
            )
            # Test 2: diminution x0.5 (scale mode)
            r = await mcp_opendaw_augment_notes(factor=0.5, unit_index=1, track_index=0, region_index=-1, mode="scale")
            d = json.loads(r) if r.strip().startswith("{") else {}
            if d.get("success") and d.get("factor") == 0.5:
                print(f"  ✅ test 2: diminution x0.5 scale — {d.get('notes_augmented', 0)} notes")
                passed += 1
            else:
                print(f"  ❌ test 2: {r[:120]}")
                failed += 1

            # Test 3: stretch mode (duration only, no position change)
            r = await mcp_opendaw_augment_notes(factor=1.5, unit_index=1, track_index=0, region_index=-1, mode="stretch")
            d = json.loads(r) if r.strip().startswith("{") else {}
            if d.get("success") and d.get("mode") == "stretch":
                print(f"  ✅ test 3: stretch mode — {d.get('notes_augmented', 0)} notes")
                passed += 1
            else:
                print(f"  ❌ test 3: {r[:120]}")
                failed += 1

            # Test 4: all regions (region_index=-1)
            r = await mcp_opendaw_augment_notes(factor=1.0, unit_index=1, track_index=0, region_index=-1, mode="scale")
            d = json.loads(r) if r.strip().startswith("{") else {}
            if d.get("success") and d.get("factor") == 1.0:
                print(f"  ✅ test 4: factor=1.0 (no-op) — {d.get('notes_augmented', 0)} notes")
                passed += 1
            else:
                print(f"  ❌ test 4: {r[:120]}")
                failed += 1

            # Test 5: bad factor (too small)
            r = await mcp_opendaw_augment_notes(factor=0.1, unit_index=1, track_index=0, region_index=0)
            if "Error" in r:
                print("  ✅ test 5: bad factor (0.1) rejected")
                passed += 1
            else:
                print(f"  ❌ test 5: {r[:80]}")
                failed += 1

            # Test 6: bad factor (too large)
            r = await mcp_opendaw_augment_notes(factor=5.0, unit_index=1, track_index=0, region_index=0)
            if "Error" in r:
                print("  ✅ test 6: bad factor (5.0) rejected")
                passed += 1
            else:
                print(f"  ❌ test 6: {r[:80]}")
                failed += 1

            # Test 7: bad mode
            r = await mcp_opendaw_augment_notes(factor=2.0, unit_index=1, track_index=0, region_index=0, mode="wobble")
            if "Error" in r:
                print("  ✅ test 7: bad mode rejected")
                passed += 1
            else:
                print(f"  ❌ test 7: {r[:80]}")
                failed += 1

            # Test 8: non-existent AU
            r = await mcp_opendaw_augment_notes(factor=2.0, unit_index=99, track_index=0, region_index=0)
            d = json.loads(r) if r.strip().startswith("{") else {}
            if d.get("error"):
                print("  ✅ test 8: non-existent AU error handled")
                passed += 1
            else:
                print(f"  ❌ test 8: {r[:80]}")
                failed += 1

            print(f"\n{'='*40}")
            print(f"augment_notes E2E: {passed}/{passed+failed}")
            return failed == 0

        import asyncio
        ok = asyncio.run(run())
        sys.exit(0 if ok else 1)
    finally:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=5)


if __name__ == "__main__":
    main()

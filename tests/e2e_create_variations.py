"""E2E test for create_variations orchestration tool."""

import asyncio
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", "/snap/bin/chromium")
VITE_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "headless-daw"))


def main():
    subprocess.run(["pkill", "-f", "vite.*5174"], capture_output=True)
    time.sleep(1)
    vite_bin = os.path.join(VITE_DIR, "node_modules", ".bin", "vite")
    proc = subprocess.Popen(
        [vite_bin, "--port", "5174"],
        cwd=VITE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        env={**os.environ, "NODE_OPTIONS": ""},
    )
    time.sleep(8)

    passed = 0
    failed = 0

    try:
        from server import (
            mcp_opendaw_create_synth_track,
            mcp_opendaw_create_note_track,
            mcp_opendaw_create_melody,
            mcp_opendaw_create_variations,
        )

        async def run():
            nonlocal passed, failed
            from server import bridge as global_bridge
            bridge = global_bridge
            await bridge.start()

            # Setup: synth + note track
            await mcp_opendaw_create_synth_track("Source", "vaporisateur")
            await mcp_opendaw_create_note_track(0)

            # Create source melody
            r1 = await mcp_opendaw_create_melody(
                scale="minor", root="A", pattern="1 2 3 5 4 3 2 1",
                unit_index=0, track_index=0,
            )
            if "success" in r1.lower() or "notes" in r1.lower():
                passed += 1
            else:
                failed += 1

            # Test 1: basic variations
            r2 = await mcp_opendaw_create_variations(
                source_unit=0, source_track=0, source_region=0,
                variations="transpose:5,invert,reverse,augment:2",
            )
            data2 = json.loads(r2) if r2.strip().startswith("{") else {}
            if data2.get("success") and data2.get("variations", 0) >= 3:
                passed += 1
            else:
                failed += 1

            # Test 2: octave shifts
            r3 = await mcp_opendaw_create_variations(
                source_unit=0, source_track=0, source_region=0,
                variations="octave_up,octave_down",
                start_beat=32,
            )
            data3 = json.loads(r3) if r3.strip().startswith("{") else {}
            if data3.get("success") and data3.get("variations", 0) == 2:
                passed += 1
            else:
                failed += 1

            # Test 3: diminish
            r4 = await mcp_opendaw_create_variations(
                source_unit=0, source_track=0, source_region=0,
                variations="diminish:2,fragment",
                start_beat=48,
            )
            data4 = json.loads(r4) if r4.strip().startswith("{") else {}
            if data4.get("success"):
                passed += 1
            else:
                failed += 1

            # Test 4: single transpose
            r5 = await mcp_opendaw_create_variations(
                source_unit=0, source_track=0,
                variations="transpose:7",
                start_beat=64,
            )
            data5 = json.loads(r5) if r5.strip().startswith("{") else {}
            if data5.get("success") and data5.get("variations", 0) == 1:
                passed += 1
            else:
                failed += 1

            # Test 5: empty variations error
            r6 = await mcp_opendaw_create_variations(
                source_unit=0, source_track=0, variations="",
            )
            if "Error" in r6:
                passed += 1
            else:
                failed += 1

            # Test 6: too many variations error
            many = ",".join(["transpose:1"] * 20)
            r7 = await mcp_opendaw_create_variations(
                source_unit=0, source_track=0, variations=many,
            )
            if "Error" in r7:
                passed += 1
            else:
                failed += 1

            # Test 7: invert with axis
            r8 = await mcp_opendaw_create_variations(
                source_unit=0, source_track=0,
                variations="invert:64",
                start_beat=72,
            )
            data8 = json.loads(r8) if r8.strip().startswith("{") else {}
            if data8.get("success"):
                passed += 1
            else:
                failed += 1

            # Test 8: invalid source AU
            r9 = await mcp_opendaw_create_variations(
                source_unit=99, source_track=0, variations="transpose:1",
            )
            if "error" in r9.lower() or "Error" in r9:
                passed += 1
            else:
                failed += 1

            await bridge.stop()
            print(f"create_variations E2E: {passed}/{passed + failed}")
            return failed == 0

        ok = asyncio.run(run())
        sys.exit(0 if ok else 1)
    except Exception as e:
        print(f"EXCEPTION: {e}")
        failed += 1
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    print(f"create_variations E2E: {passed}/{passed + failed}")


if __name__ == "__main__":
    main()

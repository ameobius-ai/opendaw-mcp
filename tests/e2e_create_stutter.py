"""E2E test for create_stutter orchestration tool."""

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
            mcp_opendaw_create_stutter,
        )

        async def run():
            nonlocal passed, failed
            from server import bridge as global_bridge
            bridge = global_bridge
            await bridge.start()

            await mcp_opendaw_create_synth_track("Stutter", "vaporisateur")
            await mcp_opendaw_create_note_track(0)

            # Test 1: basic accelerate stutter
            r1 = await mcp_opendaw_create_stutter(
                pitches="60",
                pattern="accelerate",
                repeat_count=16,
                unit_index=0, track_index=0,
            )
            data1 = json.loads(r1) if r1.strip().startswith("{") else {}
            if data1.get("success") and data1.get("total_notes", 0) > 0:
                passed += 1
            else:
                print(f"  DEBUG t1: {r1[:200]}")
                failed += 1

            # Test 2: constant pattern at 32nd notes
            r2 = await mcp_opendaw_create_stutter(
                pitches="64,67,71",
                pattern="constant",
                rate="32nd",
                repeat_count=8,
                unit_index=0, track_index=0,
                start_beat=8,
            )
            data2 = json.loads(r2) if r2.strip().startswith("{") else {}
            if data2.get("success"):
                passed += 1
            else:
                failed += 1

            # Test 3: ping_pong pattern with gate
            r3 = await mcp_opendaw_create_stutter(
                pitches="72",
                pattern="ping_pong",
                gate=0.7,
                repeat_count=12,
                unit_index=0, track_index=0,
                start_beat=16,
            )
            data3 = json.loads(r3) if r3.strip().startswith("{") else {}
            if data3.get("success") and data3.get("notes_after_gate", 99) <= 12:
                passed += 1
            else:
                failed += 1

            # Test 4: build velocity ramp with accent
            r4 = await mcp_opendaw_create_stutter(
                pitches="48",
                pattern="decelerate",
                velocity_ramp="build",
                accent_pattern="1_e_and_a",
                repeat_count=20,
                unit_index=0, track_index=0,
                start_beat=24,
            )
            data4 = json.loads(r4) if r4.strip().startswith("{") else {}
            if data4.get("success"):
                passed += 1
            else:
                failed += 1

            # Test 5: pitch jitter
            r5 = await mcp_opendaw_create_stutter(
                pitches="60",
                pattern="random",
                pitch_jitter=5,
                repeat_count=10,
                unit_index=0, track_index=0,
                start_beat=32,
            )
            data5 = json.loads(r5) if r5.strip().startswith("{") else {}
            if data5.get("success"):
                passed += 1
            else:
                failed += 1

            # Test 6: invalid pitches
            r6 = await mcp_opendaw_create_stutter(pitches="abc")
            if "Error" in r6:
                passed += 1
            else:
                failed += 1

            # Test 7: invalid pattern
            r7 = await mcp_opendaw_create_stutter(pattern="bogus")
            if "Error" in r7:
                passed += 1
            else:
                failed += 1

            # Test 8: repeat_count out of bounds
            r8 = await mcp_opendaw_create_stutter(repeat_count=2)
            if "Error" in r8:
                passed += 1
            else:
                failed += 1

            await bridge.stop()
            print(f"create_stutter E2E: {passed}/{passed + failed}")
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

    print(f"create_stutter E2E: {passed}/{passed + failed}")


if __name__ == "__main__":
    main()

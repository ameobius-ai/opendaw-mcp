"""E2E test for create_motif_development orchestration tool."""

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
            mcp_opendaw_create_motif_development,
        )

        async def run():
            nonlocal passed, failed
            from server import bridge as global_bridge
            bridge = global_bridge
            await bridge.start()

            await mcp_opendaw_create_synth_track("Motif", "vaporisateur")
            await mcp_opendaw_create_note_track(0)

            # Test 1: basic development
            r1 = await mcp_opendaw_create_motif_development(
                motif="1,1,1,2",
                scale="minor", root="A",
                steps="statement,sequence_up,fragment,invert,cadence",
                unit_index=0, track_index=0,
            )
            data1 = json.loads(r1) if r1.strip().startswith("{") else {}
            if data1.get("success") and data1.get("notes_created", 0) > 0:
                passed += 1
            else:
                failed += 1

            # Test 2: MIDI pitches
            r2 = await mcp_opendaw_create_motif_development(
                motif="60,60,60,62",
                steps="statement,octave_up,octave_down,cadence",
                unit_index=0, track_index=0,
                start_beat=32,
            )
            data2 = json.loads(r2) if r2.strip().startswith("{") else {}
            if data2.get("success"):
                passed += 1
            else:
                failed += 1

            # Test 3: expand + compress
            r3 = await mcp_opendaw_create_motif_development(
                motif="1,3,5,4",
                steps="statement,expand,compress,cadence",
                unit_index=0, track_index=0,
                start_beat=64,
            )
            data3 = json.loads(r3) if r3.strip().startswith("{") else {}
            if data3.get("success"):
                passed += 1
            else:
                failed += 1

            # Test 4: fragment_end
            r4 = await mcp_opendaw_create_motif_development(
                motif="1,2,3,4,5,6",
                steps="statement,fragment,fragment_end,cadence",
                unit_index=0, track_index=0,
                start_beat=96,
            )
            data4 = json.loads(r4) if r4.strip().startswith("{") else {}
            if data4.get("success"):
                passed += 1
            else:
                failed += 1

            # Test 5: invalid root
            r5 = await mcp_opendaw_create_motif_development(
                motif="1,2,3", root="X",
            )
            if "Error" in r5:
                passed += 1
            else:
                failed += 1

            # Test 6: invalid motif (too short)
            r6 = await mcp_opendaw_create_motif_development(
                motif="1",
            )
            if "Error" in r6:
                passed += 1
            else:
                failed += 1

            # Test 7: invalid stage
            r7 = await mcp_opendaw_create_motif_development(
                motif="1,2,3", steps="statement,bogus_stage",
            )
            if "Error" in r7:
                passed += 1
            else:
                failed += 1

            # Test 8: too many stages
            many = ",".join(["statement"] * 25)
            r8 = await mcp_opendaw_create_motif_development(
                motif="1,2,3", steps=many,
            )
            if "Error" in r8:
                passed += 1
            else:
                failed += 1

            await bridge.stop()
            print(f"create_motif_development E2E: {passed}/{passed + failed}")
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

    print(f"create_motif_development E2E: {passed}/{passed + failed}")


if __name__ == "__main__":
    main()

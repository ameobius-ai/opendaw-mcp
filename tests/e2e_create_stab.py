#!/usr/bin/env python3
"""E2E test for create_stab — rhythmic chord stabs (house/disco/funk)."""
import asyncio, json, subprocess, sys, os, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

VITE_PORT = 5174
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(SCRIPT_DIR)
HEADLESS_DIR = os.path.join(os.path.dirname(REPO_DIR), "headless-daw")
os.environ["PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"] = "/snap/bin/chromium"


def run_test():
    vite = subprocess.Popen(
        ["npx", "vite", "--port", str(VITE_PORT), "--strictPort"],
        cwd=HEADLESS_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(8)

    try:
        from server import (
            bridge,
            mcp_opendaw_create_synth_track,
            mcp_opendaw_create_stab,
            mcp_opendaw_list_notes,
        )

        async def test():
            await bridge.start()

            # 1. Create synth track
            r = await mcp_opendaw_create_synth_track("stab_test", "vaporisateur")
            data = json.loads(r)
            print(f"1. Create synth track: {data}")
            assert data.get("success"), f"Failed: {data}"
            ui = data["unit_index"]

            # 2. House off-beat stabs — Cm7
            r2 = await mcp_opendaw_create_stab(
                chords='[["C","min7"]]',
                rhythm="x-x-x-x-",
                unit_index=ui,
                track_index=0,
                start_beat=0,
                octave=4,
                velocity=0.85,
                length_beats=4,
                stab_duration=0.5,
            )
            data2 = json.loads(r2)
            print(f"2. House off-beat Cm7 stabs: {data2}")
            assert data2.get("success"), f"Stab failed: {data2}"
            assert data2["total_notes"] == 16, f"Expected 16 notes (4 stabs × 4-note chord), got {data2['total_notes']}"
            assert data2["stabs"] == 4, f"Expected 4 stabs, got {data2['stabs']}"
            assert data2["chords_used"] == 1
            print(f"   {data2['total_notes']} notes, 4 stabs × Cm7 ✅")

            # 3. Verify notes exist
            r3 = await mcp_opendaw_list_notes(unit_index=ui, track_index=0, region_index=0)
            data3 = json.loads(r3)
            print(f"3. Verify notes: {len(data3.get('notes', []))} notes found")
            assert len(data3.get("notes", [])) >= 16, f"Expected >=16 notes, got {len(data3.get('notes', []))}"
            print("   Notes verified ✅")

            # 4. Funky pattern with ghost notes — cycling F7 and Cm7
            r4 = await mcp_opendaw_create_stab(
                chords='[["F","dom7"],["C","min7"]]',
                rhythm="x..x.xx-",
                unit_index=ui,
                track_index=0,
                start_beat=4,
                octave=4,
                velocity=0.9,
                length_beats=4,
                stab_duration=0.375,
            )
            data4 = json.loads(r4)
            print(f"4. Funky ghost stabs F7/Cm7: {data4}")
            assert data4.get("success"), f"Funky stab failed: {data4}"
            # rhythm "x..x.xx-": 7 hits (x, ., x, ., x, x, x) — skip = 1
            # x=4notes + .=4notes(ghost) + x=4notes + .=4notes(ghost) + x=4notes + x=4notes + x=4notes = 28
            assert data4["total_notes"] == 28, f"Expected 28 notes, got {data4['total_notes']}"
            assert data4["chords_used"] == 2, f"Expected 2 chords, got {data4['chords_used']}"
            print(f"   {data4['total_notes']} notes, 5 stabs + 2 ghost, F7/Cm7 cycling ✅")

            # 5. All-rests error
            r5 = await mcp_opendaw_create_stab(
                chords='[["C","min7"]]',
                rhythm="--------",
                unit_index=ui,
            )
            print(f"5. All-rests error: {r5[:100]}")
            assert "Error" in r5 or "error" in r5, f"Expected error, got: {r5}"
            print("   Error caught ✅")

            # 6. Invalid rhythm char error
            r6 = await mcp_opendaw_create_stab(
                chords='[["C","min7"]]',
                rhythm="x-x-o-x-",
                unit_index=ui,
            )
            print(f"6. Invalid rhythm error: {r6[:100]}")
            assert "Error" in r6 or "error" in r6, f"Expected error, got: {r6}"
            print("   Error caught ✅")

            await bridge.stop()
            print("\n✅ All stab tests passed!")
            return True

        return asyncio.run(test())

    finally:
        vite.terminate()
        vite.wait()


if __name__ == "__main__":
    ok = run_test()
    sys.exit(0 if ok else 1)

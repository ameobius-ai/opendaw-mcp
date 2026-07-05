"""E2E test: create_riser — ascending pitch sweep for build-up transitions."""
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
            mcp_opendaw_create_riser,
            mcp_opendaw_list_notes,
        )

        async def test():
            await bridge.start()

            # 1. Create synth track
            r = await mcp_opendaw_create_synth_track("riser_test", "vaporisateur")
            data = json.loads(r)
            print(f"1. Create synth track: {data}")
            assert data.get("success"), f"Failed: {data}"
            ui = data["unit_index"]

            # 2. Create riser
            r2 = await mcp_opendaw_create_riser(
                unit_index=ui,
                start_beat=0,
                length_beats=4,
                start_pitch=36,
                end_pitch=84,
                steps=32,
                curve="exp",
                velocity=0.7,
            )
            data2 = json.loads(r2)
            print(f"2. Create riser: {data2}")
            assert data2.get("success"), f"Riser failed: {data2}"
            assert data2["total_notes"] == 32, f"Expected 32 notes, got {data2['total_notes']}"
            assert data2["start_pitch"] == 36
            assert data2["end_pitch"] == 84
            assert data2["curve"] == "exp"
            print("   32 notes, pitch 36→84, exp curve ✅")

            # 3. Verify notes
            r3 = await mcp_opendaw_list_notes(unit_index=ui, track_index=0, region_index=0)
            notes = json.loads(r3).get("notes", [])
            print(f"3. Notes: {len(notes)} notes")
            assert len(notes) == 32, f"Expected 32 notes, got {len(notes)}"
            pitches = [n["pitch"] for n in notes]
            assert pitches[0] == 36, f"First pitch should be 36, got {pitches[0]}"
            assert pitches[-1] == 84, f"Last pitch should be 84, got {pitches[-1]}"
            # exp curve: pitches should accelerate upward
            assert pitches[-1] > pitches[-2] > pitches[-10], "Pitches should be ascending"
            print(f"   Pitch range: {pitches[0]}→{pitches[-1]}, ascending ✅")

            # 4. Test linear curve
            r4 = await mcp_opendaw_create_riser(
                unit_index=ui,
                start_beat=8,
                length_beats=2,
                start_pitch=48,
                end_pitch=72,
                steps=16,
                curve="linear",
                velocity=0.5,
            )
            data4 = json.loads(r4)
            print(f"4. Linear riser: {data4}")
            assert data4.get("success"), f"Linear riser failed: {data4}"
            assert data4["total_notes"] == 16
            print("   16 notes, linear curve ✅")

            # 5. Error handling
            r5 = await mcp_opendaw_create_riser(
                unit_index=ui, start_pitch=200, end_pitch=84,
            )
            assert "Error" in r5, "Should reject pitch > 127"
            print("5. Error handling: pitch > 127 rejected ✅")

            print("\n=== ALL RISER E2E TESTS PASSED ===")
            return True

        result = asyncio.run(test())
        return result
    finally:
        vite.terminate()
        try:
            vite.wait(timeout=5)
        except subprocess.TimeoutExpired:
            vite.kill()


if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)

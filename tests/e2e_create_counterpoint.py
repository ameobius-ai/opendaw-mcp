"""E2E test: create_counterpoint — contrary motion counter-melody.

Creates an ascending melody, generates counterpoint, verifies contrary motion.
"""
import json
import subprocess
import sys
import time
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

VITE_PORT = 5174
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(SCRIPT_DIR)
HEADLESS_DIR = os.path.join(os.path.dirname(REPO_DIR), "headless-daw")


def run_test():
    vite = subprocess.Popen(
        ["npx", "vite", "--port", str(VITE_PORT), "--strictPort"],
        cwd=HEADLESS_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(6)

    try:
        from server import bridge, mcp_opendaw_create_synth_track, mcp_opendaw_create_melody, \
            mcp_opendaw_create_counterpoint, mcp_opendaw_list_notes

        import asyncio

        async def test():
            await bridge.start()

            # 1. Create ascending melody: C D E F G A B C5
            r = await mcp_opendaw_create_synth_track("melody", "vaporisateur")
            data = json.loads(r)
            ui, ti = data["unit_index"], data["track_index"]
            print(f"✓ Created melody track: unit={ui}, track={ti}")

            r = await mcp_opendaw_create_melody(
                scale="major", root="C",
                pattern="1 2 3 4 5 6 7 + 1",
                unit_index=ui, track_index=ti,
            )
            data = json.loads(r)
            assert data.get("success"), f"create_melody failed: {data}"

            r = await mcp_opendaw_list_notes(unit_index=ui, track_index=ti, region_index=0)
            notes = json.loads(r).get("notes", [])
            melody_pitches = [n["pitch"] for n in notes]
            print(f"✓ Melody pitches: {melody_pitches}")
            # C major ascending: [60, 62, 64, 65, 67, 69, 71, 72]
            assert melody_pitches == [60, 62, 64, 65, 67, 69, 71, 72], \
                f"Expected ascending C major, got {melody_pitches}"

            # 2. Create counterpoint with default interval=7 (fifth below center)
            r = await mcp_opendaw_create_counterpoint(
                unit_index=ui, track_index=ti, region_index=0,
                interval=7,
            )
            data = json.loads(r)
            assert data.get("success"), f"create_counterpoint failed: {data}"
            print(f"✓ Counterpoint created: {data.get('counterpoint_notes_created', 0)} notes")
            print(f"  Center pitch: {data.get('center_pitch')}")
            print(f"  Sample pitches: {data.get('sample_pitches')}")

            # Read counterpoint notes
            cp_ui = data["target_unit_index"]
            r = await mcp_opendaw_list_notes(unit_index=cp_ui, track_index=0, region_index=0)
            cp_notes = json.loads(r).get("notes", [])
            cp_pitches = [n["pitch"] for n in cp_notes]
            print(f"  Counterpoint pitches: {cp_pitches}")

            # Verify contrary motion: ascending melody → descending counterpoint
            # Melody goes up: [60, 62, 64, 65, 67, 69, 71, 72]
            # Center = avg(60,72) - 7 = 66 - 7 = 59
            # CP = 2*59 - melody = [58, 56, 54, 53, 51, 49, 47, 46]
            center = data["center_pitch"]
            expected_cp = [2 * center - p for p in melody_pitches]
            assert cp_pitches == expected_cp, \
                f"Counterpoint mismatch: expected {expected_cp}, got {cp_pitches}"
            print(f"✓ Counterpoint mirrors melody around center={center}")

            # Verify contrary motion: melody ascending, counterpoint descending
            melody_direction = "up" if melody_pitches[-1] > melody_pitches[0] else "down"
            cp_direction = "down" if cp_pitches[-1] < cp_pitches[0] else "up"
            assert melody_direction == "up" and cp_direction == "down", \
                f"Expected contrary motion: melody up, CP down. Got: melody {melody_direction}, CP {cp_direction}"
            print("✓ Contrary motion verified: melody up → counterpoint down!")

            # 3. Error handling
            r = await mcp_opendaw_create_counterpoint(
                unit_index=ui, track_index=ti, region_index=0,
                interval=100,
            )
            assert "Error" in r, "Should reject interval > 48"
            print("✓ Error handling: interval > 48 rejected")

            print("\n=== ALL COUNTERPOINT E2E TESTS PASSED ===")
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

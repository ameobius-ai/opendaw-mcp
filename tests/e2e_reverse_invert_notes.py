"""E2E test: reverse_notes + invert_notes — melodic variation tools.

Creates a melody, reverses it, then inverts it. Verifies pitch/position transformations.
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
            mcp_opendaw_reverse_notes, mcp_opendaw_invert_notes, mcp_opendaw_list_notes

        import asyncio

        async def test():
            await bridge.start()

            # 1. Create melody: ascending C major
            r = await mcp_opendaw_create_synth_track("test_reverse", "vaporisateur")
            data = json.loads(r)
            ui, ti = data["unit_index"], data["track_index"]
            print(f"✓ Created track: unit={ui}, track={ti}")

            r = await mcp_opendaw_create_melody(
                scale="major", root="C",
                pattern="1 2 3 4 5",
                unit_index=ui, track_index=ti,
            )
            data = json.loads(r)
            assert data.get("success"), f"create_melody failed: {data}"

            r = await mcp_opendaw_list_notes(unit_index=ui, track_index=ti, region_index=0)
            notes = json.loads(r).get("notes", [])
            pitches_before = [n["pitch"] for n in notes]
            positions_before = [n["position_beats"] for n in notes]
            print(f"✓ Before reverse: pitches={pitches_before}, positions={positions_before}")
            # C major ascending: C4=60, D4=62, E4=64, F4=65, G4=67
            assert pitches_before == [60, 62, 64, 65, 67], f"Expected ascending C major, got {pitches_before}"

            # 2. Invert notes around C4=60
            r = await mcp_opendaw_invert_notes(unit_index=ui, track_index=ti, region_index=0, axis=60)
            data = json.loads(r)
            assert data.get("success"), f"invert_notes failed: {data}"
            print(f"✓ Inverted {data.get('notes_inverted', 0)} notes around axis=60")

            r = await mcp_opendaw_list_notes(unit_index=ui, track_index=ti, region_index=0)
            notes_after = json.loads(r).get("notes", [])
            pitches_inverted = [n["pitch"] for n in notes_after]
            print(f"  Inverted pitches: {pitches_inverted}")
            # Inversion around 60: 60→60, 62→58, 64→56, 65→55, 67→53
            expected_inverted = [60, 58, 56, 55, 53]
            assert pitches_inverted == expected_inverted, \
                f"Inversion mismatch: expected {expected_inverted}, got {pitches_inverted}"
            print("✓ Inversion correct!")

            # 3. Invert back (should restore originals)
            r = await mcp_opendaw_invert_notes(unit_index=ui, track_index=ti, region_index=0, axis=60)
            r = await mcp_opendaw_list_notes(unit_index=ui, track_index=ti, region_index=0)
            pitches_restored = [n["pitch"] for n in json.loads(r).get("notes", [])]
            assert pitches_restored == pitches_before, \
                f"Double inversion should restore originals: {pitches_restored}"
            print(f"✓ Double inversion restores originals: {pitches_restored}")

            # 4. Test invert error handling
            r = await mcp_opendaw_invert_notes(unit_index=ui, track_index=ti, axis=200)
            assert "Error" in r, "Should reject axis > 127"
            print("✓ Error handling: axis > 127 rejected")

            # 5. Reverse notes — create a new melody for position testing
            r2 = await mcp_opendaw_create_synth_track("test_reverse2", "vaporisateur")
            d2 = json.loads(r2)
            ui2, ti2 = d2["unit_index"], d2["track_index"]
            await mcp_opendaw_create_melody(
                scale="major", root="C",
                pattern="1 2 3 4 5 6 7 + 1",
                unit_index=ui2, track_index=ti2,
            )
            r = await mcp_opendaw_list_notes(unit_index=ui2, track_index=ti2, region_index=0)
            notes2 = json.loads(r).get("notes", [])
            pos2_before = [n["position_beats"] for n in notes2]
            pitches2_before = [n["pitch"] for n in notes2]
            print(f"✓ Reverse test melody: pitches={pitches2_before}, positions={pos2_before}")

            r = await mcp_opendaw_reverse_notes(unit_index=ui2, track_index=ti2, region_index=0)
            data = json.loads(r)
            assert data.get("success"), f"reverse_notes failed: {data}"
            print(f"✓ Reversed {data.get('notes_reversed', 0)} notes")

            r = await mcp_opendaw_list_notes(unit_index=ui2, track_index=ti2, region_index=0)
            notes2_after = json.loads(r).get("notes", [])
            pos2_after = [n["position_beats"] for n in notes2_after]
            print(f"  Positions after reverse: {pos2_after}")

            # After reverse, positions should be different from original
            assert pos2_after != pos2_before, "Positions should change after reverse"
            print("✓ Positions changed after reverse!")

            print("\n=== ALL REVERSE/INVERT E2E TESTS PASSED ===")
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

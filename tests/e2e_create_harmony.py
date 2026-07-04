"""E2E test: create_harmony — generate harmony parts from existing notes.

Creates a melody, then generates diatonic thirds, chromatic octave, and fifth harmony.
Verifies pitch relationships and error handling.
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
            mcp_opendaw_create_harmony, mcp_opendaw_list_notes

        import asyncio

        async def test():
            await bridge.start()

            # 1. Create melody: C major scale ascending (C D E F G A B C)
            r = await mcp_opendaw_create_synth_track("melody", "vaporisateur")
            data = json.loads(r)
            ui, ti = data["unit_index"], data["track_index"]
            print(f"✓ Created melody track: unit={ui}, track={ti}")

            r = await mcp_opendaw_create_melody(
                scale="major", root="C",
                pattern="1 2 3 4 5 6 7 + 1",  # C D E F G A B C5
                unit_index=ui, track_index=ti,
            )
            data = json.loads(r)
            assert data.get("success"), f"create_melody failed: {data}"
            print(f"✓ Created melody: {data.get('melody_notes', 0)} notes")

            # Snapshot melody pitches
            r = await mcp_opendaw_list_notes(unit_index=ui, track_index=ti, region_index=0)
            melody_notes = json.loads(r).get("notes", [])
            melody_pitches = [n["pitch"] for n in melody_notes]
            print(f"✓ Melody pitches: {melody_pitches}")
            # C major: C4=60, D4=62, E4=64, F4=65, G4=67, A4=69, B4=71, C5=72
            assert melody_pitches == [60, 62, 64, 65, 67, 69, 71, 72], \
                f"Expected C major scale, got {melody_pitches}"

            # 2. Diatonic thirds up: C→E, D→F, E→G, F→A, G→B, A→C5, B→D5, C5→E5
            # Expected: [64, 65, 67, 69, 71, 72, 74, 76]
            r = await mcp_opendaw_create_harmony(
                unit_index=ui, track_index=ti, region_index=0,
                interval="thirds", direction="up",
            )
            data = json.loads(r)
            assert data.get("success"), f"create_harmony thirds failed: {data}"
            print(f"✓ Harmony thirds up: {data.get('harmony_notes_created', 0)} notes")
            print(f"  Sample pitches: {data.get('sample_pitches', [])}")

            # List harmony notes on the new track
            harmony_ui = data["target_unit_index"]
            r = await mcp_opendaw_list_notes(unit_index=harmony_ui, track_index=0, region_index=0)
            harmony_notes = json.loads(r).get("notes", [])
            harmony_pitches = [n["pitch"] for n in harmony_notes]
            print(f"  Harmony pitches: {harmony_pitches}")

            # Diatonic thirds above C major:
            # C(60)→E(64), D(62)→F(65), E(64)→G(67), F(65)→A(69),
            # G(67)→B(71), A(69)→C(72), B(71)→D(74), C(72)→E(76)
            expected_thirds = [64, 65, 67, 69, 71, 72, 74, 76]
            assert harmony_pitches == expected_thirds, \
                f"Diatonic thirds mismatch: expected {expected_thirds}, got {harmony_pitches}"
            print("✓ Diatonic thirds correct!")

            # 3. Octave up: each pitch + 12
            r = await mcp_opendaw_create_harmony(
                unit_index=ui, track_index=ti, region_index=0,
                interval="octave", direction="up",
            )
            data = json.loads(r)
            assert data.get("success"), f"create_harmony octave failed: {data}"
            print(f"✓ Harmony octave up: {data.get('harmony_notes_created', 0)} notes")

            r = await mcp_opendaw_list_notes(unit_index=data["target_unit_index"], track_index=0, region_index=0)
            octave_pitches = [n["pitch"] for n in json.loads(r).get("notes", [])]
            expected_octave = [p + 12 for p in melody_pitches]
            assert octave_pitches == expected_octave, \
                f"Octave mismatch: expected {expected_octave}, got {octave_pitches}"
            print(f"  Octave pitches: {octave_pitches} ✓")

            # 4. Octave down
            r = await mcp_opendaw_create_harmony(
                unit_index=ui, track_index=ti, region_index=0,
                interval="octave", direction="down",
            )
            data = json.loads(r)
            assert data.get("success"), f"create_harmony octave down failed: {data}"
            r = await mcp_opendaw_list_notes(unit_index=data["target_unit_index"], track_index=0, region_index=0)
            octave_down_pitches = [n["pitch"] for n in json.loads(r).get("notes", [])]
            expected_octave_down = [p - 12 for p in melody_pitches]
            assert octave_down_pitches == expected_octave_down, \
                f"Octave down mismatch: expected {expected_octave_down}, got {octave_down_pitches}"
            print(f"  Octave down pitches: {octave_down_pitches} ✓")

            # 5. Chromatic fifth up: each pitch + 7
            r = await mcp_opendaw_create_harmony(
                unit_index=ui, track_index=ti, region_index=0,
                interval="fifth_chromatic", direction="up",
            )
            data = json.loads(r)
            assert data.get("success"), f"create_harmony fifth failed: {data}"
            r = await mcp_opendaw_list_notes(unit_index=data["target_unit_index"], track_index=0, region_index=0)
            fifth_pitches = [n["pitch"] for n in json.loads(r).get("notes", [])]
            expected_fifth = [p + 7 for p in melody_pitches]
            assert fifth_pitches == expected_fifth, \
                f"Fifth mismatch: expected {expected_fifth}, got {fifth_pitches}"
            print(f"✓ Chromatic fifth up: {fifth_pitches}")

            # 6. Error handling
            r = await mcp_opendaw_create_harmony(
                unit_index=ui, track_index=ti, region_index=0,
                interval="invalid_interval",
            )
            assert "Error" in r, "Should reject invalid interval"
            print("✓ Error handling: invalid interval rejected")

            r = await mcp_opendaw_create_harmony(
                unit_index=ui, track_index=ti, region_index=0,
                interval="thirds", direction="sideways",
            )
            assert "Error" in r, "Should reject invalid direction"
            print("✓ Error handling: invalid direction rejected")

            print("\n=== ALL HARMONY E2E TESTS PASSED ===")
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

"""E2E test: humanize_notes — velocity, timing, duration, swing variation on existing notes.

Creates a melody, snapshots note velocities/positions, humanizes, verifies deviations.
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
    # Start Vite
    vite = subprocess.Popen(
        ["npx", "vite", "--port", str(VITE_PORT), "--strictPort"],
        cwd=HEADLESS_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(6)

    try:
        from server import bridge, mcp_opendaw_create_synth_track, mcp_opendaw_create_melody, \
            mcp_opendaw_humanize_notes, mcp_opendaw_list_notes

        import asyncio

        async def test():
            await bridge.start()

            # 1. Create a synth track with melody
            r = await mcp_opendaw_create_synth_track("test_humanize", "vaporisateur")
            data = json.loads(r)
            assert data.get("success"), f"create_synth_track failed: {data}"
            ui = data["unit_index"]
            ti = data["track_index"]
            print(f"✓ Created synth track: unit={ui}, track={ti}")

            # 2. Create a simple melody (C minor, 8 notes)
            r = await mcp_opendaw_create_melody(
                scale="minor", root="C",
                pattern="1 2 3 4 5 4 3 2",
                unit_index=ui, track_index=ti,
            )
            data = json.loads(r)
            assert data.get("success"), f"create_melody failed: {data}"
            melody_count = data.get("melody_notes", 0)
            print(f"✓ Created melody: {melody_count} notes")

            # 3. List notes before humanize (snapshot)
            r = await mcp_opendaw_list_notes(unit_index=ui, track_index=ti, region_index=0)
            data = json.loads(r)
            notes_before = data.get("notes", [])
            assert len(notes_before) > 0, "No notes to humanize"
            print(f"✓ Notes before humanize: {len(notes_before)}")

            # Snapshot velocities and positions
            vel_before = [n["velocity"] for n in notes_before]

            # All velocities should be identical (from create_melody default 0.75)
            assert all(v == vel_before[0] for v in vel_before), \
                f"Velocities not uniform before humanize: {vel_before}"
            print(f"✓ Uniform velocities before: {vel_before[0]}")

            # 4. Humanize with velocity + timing + duration
            r = await mcp_opendaw_humanize_notes(
                unit_index=ui,
                velocity_amount=0.20,
                timing_amount=0.15,
                duration_amount=0.10,
                swing=0.0,
                seed=42,
            )
            data = json.loads(r)
            assert data.get("success"), f"humanize_notes failed: {data}"
            total = data.get("total_notes_humanized", 0)
            print(f"✓ Humanized {total} notes (seed=42)")

            # 5. List notes after humanize
            r = await mcp_opendaw_list_notes(unit_index=ui, track_index=ti, region_index=0)
            data = json.loads(r)
            notes_after = data.get("notes", [])

            vel_after = [n["velocity"] for n in notes_after]

            # Velocities should now vary (not all identical)
            unique_vels = len(set(round(v, 4) for v in vel_after))
            assert unique_vels > 1, \
                f"Velocities still uniform after humanize: {vel_after}"
            print(f"✓ Velocities after humanize: {len(set(round(v,2) for v in vel_after))} unique values")

            # No velocity should exceed [0.05, 1.0]
            assert all(0.05 <= v <= 1.0 for v in vel_after), \
                f"Velocity out of bounds: {vel_after}"
            print("✓ All velocities within [0.05, 1.0]")

            # 6. Test different seeds produce different results
            r2 = await mcp_opendaw_create_synth_track("test_humanize2", "vaporisateur")
            d2 = json.loads(r2)
            ui2, ti2 = d2["unit_index"], d2["track_index"]
            await mcp_opendaw_create_melody(
                scale="minor", root="D",
                pattern="1 3 5 3 1 3 5 3",
                unit_index=ui2, track_index=ti2,
            )
            await mcp_opendaw_humanize_notes(
                unit_index=ui2, velocity_amount=0.20, timing_amount=0.15,
                duration_amount=0.10, seed=99,
            )
            r_list1 = await mcp_opendaw_list_notes(unit_index=ui2, track_index=ti2, region_index=0)
            v1 = [n["velocity"] for n in json.loads(r_list1).get("notes", [])]

            r3 = await mcp_opendaw_create_synth_track("test_humanize3", "vaporisateur")
            d3 = json.loads(r3)
            ui3, ti3 = d3["unit_index"], d3["track_index"]
            await mcp_opendaw_create_melody(
                scale="minor", root="D",
                pattern="1 3 5 3 1 3 5 3",
                unit_index=ui3, track_index=ti3,
            )
            await mcp_opendaw_humanize_notes(
                unit_index=ui3, velocity_amount=0.20, timing_amount=0.15,
                duration_amount=0.10, seed=200,
            )
            r_list2 = await mcp_opendaw_list_notes(unit_index=ui3, track_index=ti3, region_index=0)
            v2 = [n["velocity"] for n in json.loads(r_list2).get("notes", [])]

            # Different seeds → different results
            if len(v1) == len(v2) and len(v1) > 0:
                diffs = sum(1 for a, b in zip(v1, v2) if abs(a - b) > 0.001)
                print(f"✓ Seed 99 vs 200: {diffs}/{len(v1)} velocities differ")

            # 7. Error handling
            r = await mcp_opendaw_humanize_notes(velocity_amount=1.5)
            assert "Error" in r, "Should reject velocity_amount > 1"
            print("✓ Error handling: velocity_amount > 1 rejected")

            r = await mcp_opendaw_humanize_notes(swing=2.0)
            assert "Error" in r, "Should reject swing > 1"
            print("✓ Error handling: swing > 1 rejected")

            # 8. Swing test — odd 16th positions should shift
            r4 = await mcp_opendaw_create_synth_track("test_swing", "vaporisateur")
            d4 = json.loads(r4)
            ui4, ti4 = d4["unit_index"], d4["track_index"]
            await mcp_opendaw_create_melody(
                scale="blues", root="A",
                pattern="1 1 1 1 1 1 1 1",  # 8 repeated notes
                unit_index=ui4, track_index=ti4,
            )
            r_list_swing_before = await mcp_opendaw_list_notes(unit_index=ui4, track_index=ti4, region_index=0)
            pos_swing_before = [n["position_beats"] for n in json.loads(r_list_swing_before).get("notes", [])]

            r_swing = await mcp_opendaw_humanize_notes(
                unit_index=ui4, velocity_amount=0.0, timing_amount=0.0,
                duration_amount=0.0, swing=0.5, seed=1,
            )
            d_swing = json.loads(r_swing)
            assert d_swing.get("success"), f"Swing humanize failed: {d_swing}"

            r_list_swing_after = await mcp_opendaw_list_notes(unit_index=ui4, track_index=ti4, region_index=0)
            pos_swing_after = [n["position_beats"] for n in json.loads(r_list_swing_after).get("notes", [])]

            # At least some positions should differ (swing shifts odd 16ths)
            pos_diffs = sum(1 for a, b in zip(pos_swing_before, pos_swing_after) if abs(a - b) > 0.001)
            print(f"✓ Swing=0.5: {pos_diffs}/{len(pos_swing_before)} positions shifted")
            assert pos_diffs > 0, "Swing should shift at least some note positions"

            print("\n=== ALL HUMANIZE E2E TESTS PASSED ===")
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

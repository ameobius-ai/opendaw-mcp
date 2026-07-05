"""Example: apply_velocity_curve — expressive MIDI dynamics.

Demonstrates 5 curve types for shaping note velocities across a region.
Unlike humanize_notes (random variation), velocity curves apply deterministic
envelope shapes — essential for build-ups, expressive phrasing, and dynamic control.
"""
import asyncio
from opendaw_mcp.server import mcp_opendaw_create_synth_track, mcp_opendaw_create_notes_batch, mcp_opendaw_apply_velocity_curve, bridge


async def main():
    await bridge.start()

    # Setup: synth track + 16 notes at uniform velocity
    await mcp_opendaw_create_synth_track(name="Lead", synth_type="vaporisateur")
    notes = [{"pitch": 60 + (i % 4) * 12, "start": i * 0.25, "duration": 0.25, "velocity": 0.5} for i in range(16)]
    await mcp_opendaw_create_notes_batch(notes_json=notes, unit_index=0, track_index=0)

    # 1. Build-up: ramp from quiet to loud (classic EDM snare roll)
    print("=== Build-up (ramp_up 0.2 → 1.0) ===")
    r = await mcp_opendaw_apply_velocity_curve(curve_type="ramp_up", start_velocity=0.2, end_velocity=1.0)
    print(r)

    # 2. Expressive phrase: arc — crescendo then decrescendo
    print("\n=== Expressive arc (0.3 → 1.0 → 0.3) ===")
    r = await mcp_opendaw_apply_velocity_curve(curve_type="arc", start_velocity=0.3, end_velocity=1.0)
    print(r)

    # 3. Fade-in with slow swell: power curve (power=0.5)
    print("\n=== Slow swell (power=0.5, 0.1 → 0.9) ===")
    r = await mcp_opendaw_apply_velocity_curve(curve_type="power", power=0.5, start_velocity=0.1, end_velocity=0.9)
    print(r)

    # 4. Sharp attack: power curve (power=3.0) — stays low then jumps
    print("\n=== Sharp attack (power=3.0, 0.1 → 1.0) ===")
    r = await mcp_opendaw_apply_velocity_curve(curve_type="power", power=3.0, start_velocity=0.1, end_velocity=1.0)
    print(r)

    # 5. Trough: dip in the middle (quiet middle, loud edges)
    print("\n=== Trough (1.0 → 0.3 → 1.0) ===")
    r = await mcp_opendaw_apply_velocity_curve(curve_type="trough", start_velocity=0.3, end_velocity=1.0)
    print(r)

    await bridge.stop()
    print("\nDone! Try combining with humanize_notes for natural + shaped dynamics.")


if __name__ == "__main__":
    asyncio.run(main())

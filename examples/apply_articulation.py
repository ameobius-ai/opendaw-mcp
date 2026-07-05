"""Example: apply_articulation — staccato, legato, tenuto, accent.

Demonstrates 4 articulation types that reshape note durations and velocities
to change phrasing character. Essential for expressive MIDI programming.
"""
import asyncio
from opendaw_mcp.server import mcp_opendaw_create_synth_track, mcp_opendaw_create_notes_batch, mcp_opendaw_apply_articulation, bridge


async def main():
    await bridge.start()

    # Setup: synth + 8 notes at 16th grid, uniform duration and velocity
    await mcp_opendaw_create_synth_track(name="Lead", synth_type="vaporisateur")
    notes = [{"pitch": 60, "start": i * 0.25, "duration": 0.25, "velocity": 0.5} for i in range(8)]
    await mcp_opendaw_create_notes_batch(notes_json=notes, unit_index=0, track_index=0)

    # 1. Staccato: crisp, detached (30% of slot)
    print("=== Staccato (amount=0.3) ===")
    r = await mcp_opendaw_apply_articulation(articulation="staccato", amount=0.3)
    print(r)

    # Reset durations
    notes_reset = [{"pitch": 60, "start": i * 0.25, "duration": 0.25, "velocity": 0.5} for i in range(8)]
    await mcp_opendaw_create_notes_batch(notes_json=notes_reset, unit_index=0, track_index=0)

    # 2. Legato: smooth, connected (95% fill)
    print("\n=== Legato (amount=0.95) ===")
    r = await mcp_opendaw_apply_articulation(articulation="legato", amount=0.95)
    print(r)

    # 3. Tenuto: full slot, no gap
    print("\n=== Tenuto ===")
    r = await mcp_opendaw_apply_articulation(articulation="tenuto")
    print(r)

    # 4. Accent: boost downbeats
    print("\n=== Accent (amount=0.8) ===")
    r = await mcp_opendaw_apply_articulation(articulation="accent", amount=0.8)
    print(r)

    await bridge.stop()
    print("\nDone! Combine with apply_velocity_curve for full dynamic + articulation control.")


if __name__ == "__main__":
    asyncio.run(main())

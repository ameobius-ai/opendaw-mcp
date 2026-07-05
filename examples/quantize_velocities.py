"""quantize_velocities — snap note velocities to discrete stepped levels.

Demonstrates MPC-style 16-level velocity quantization on a note track.
Creates a drum-like pattern with humanized velocities, then snaps them
to 4 levels (pp / p / mf / f) for clean dynamic tiers.
"""
import asyncio
from server import mcp_opendaw_create_note_track, mcp_opendaw_create_notes_batch
from server import mcp_opendaw_quantize_velocities, mcp_opendaw_list_tracks


async def main():
    # 1. list tracks to find the unit index
    tracks = await mcp_opendaw_list_tracks()
    print("Tracks:", tracks[:200])

    # 2. create a note track
    result = await mcp_opendaw_create_note_track(unit_index=0, name="drums")
    print("Created note track:", result[:200])

    # 3. create notes with varied velocities (simulating humanized drums)
    notes = [
        {"pitch": 36, "position": 0,    "duration": 480, "velocity": 0.92},  # kick
        {"pitch": 38, "position": 480,  "duration": 240, "velocity": 0.78},  # snare
        {"pitch": 42, "position": 240,  "duration": 120, "velocity": 0.45},  # hat
        {"pitch": 36, "position": 960,  "duration": 480, "velocity": 0.88},  # kick
        {"pitch": 42, "position": 720,  "duration": 120, "velocity": 0.52},  # hat
        {"pitch": 38, "position": 1440, "duration": 240, "velocity": 0.81},  # snare
        {"pitch": 42, "position": 1200, "duration": 120, "velocity": 0.38},  # hat
        {"pitch": 42, "position": 1680, "duration": 120, "velocity": 0.61},  # hat
    ]
    batch = await mcp_opendaw_create_notes_batch(
        unit_index=0, track_index=0, notes_json=json.dumps(notes)
    )
    print("Created notes:", batch[:200])

    # 4. quantize velocities to 4 levels (pp / p / mf / f)
    result = await mcp_opendaw_quantize_velocities(
        unit_index=0, track_index=0, levels=4, mode="snap"
    )
    print("Quantized to 4 levels:", result[:300])

    # 5. try 16-level MPC style
    result2 = await mcp_opendaw_quantize_velocities(
        unit_index=0, track_index=0, levels=16, mode="snap"
    )
    print("Quantized to 16 levels:", result2[:300])


if __name__ == "__main__":
    import json
    asyncio.run(main())

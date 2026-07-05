"""invert_chord_notes — chord inversion at a specific beat position.

Demonstrates inverting a C major chord from root position to
1st inversion (E in bass) and then to 2nd inversion (G in bass).
"""
import asyncio
from server import (
    mcp_opendaw_create_note_track,
    mcp_opendaw_create_chord_pads,
    mcp_opendaw_invert_chord_notes,
    mcp_opendaw_list_tracks,
)


async def main():
    # 1. list tracks
    tracks = await mcp_opendaw_list_tracks()
    print("Tracks:", tracks[:200])

    # 2. create a note track
    result = await mcp_opendaw_create_note_track(unit_index=0, name="chords")
    print("Created track:", result[:200])

    # 3. create chord pads: C-G-Am-F (each 4 beats)
    chords = await mcp_opendaw_create_chord_pads(
        chords="C-G-Am-F", unit_index=0, track_index=0, chord_duration=4
    )
    print("Chord pads:", chords[:200])

    # 4. invert the C chord at beat 0 → 1st inversion (E in bass)
    inv1 = await mcp_opendaw_invert_chord_notes(
        unit_index=0, track_index=0, region_index=0,
        chord_position=0, inversion=1, direction="up"
    )
    print("1st inversion:", inv1[:300])

    # 5. invert the G chord at beat 4 → 2nd inversion (D in bass)
    inv2 = await mcp_opendaw_invert_chord_notes(
        unit_index=0, track_index=0, region_index=0,
        chord_position=4, inversion=2, direction="up"
    )
    print("2nd inversion:", inv2[:300])

    # 6. drop voicing on Am at beat 8 (top note down)
    inv3 = await mcp_opendaw_invert_chord_notes(
        unit_index=0, track_index=0, region_index=0,
        chord_position=8, inversion=1, direction="down"
    )
    print("Drop voicing:", inv3[:300])


if __name__ == "__main__":
    asyncio.run(main())

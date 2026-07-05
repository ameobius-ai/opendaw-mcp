"""humanize_pitch — add micro-detune (cents) for intonation humanization.

This example demonstrates how to make programmed MIDI feel more natural
by adding per-note cent offsets. Real instruments and vocals never play
perfectly in tune — there's always slight pitch drift.

humanize_pitch complements humanize_notes:
- humanize_notes: velocity + timing + duration variation
- humanize_pitch: pitch micro-detune (cents)

Pipeline:
1. Create a synth track with some notes
2. Apply humanize_pitch for string warmth
3. Combine with humanize_notes for full humanization
"""

import asyncio
from opendaw_mcp.server import mcp_opendaw_humanize_pitch, mcp_opendaw_humanize_notes, mcp_opendaw_create_synth_track, mcp_opendaw_create_note


async def main():
    # 1. Create a synth track (strings patch)
    print("Creating string synth track...")
    result = await mcp_opendaw_create_synth_track("Strings", "vaporisateur")
    print(result)

    # 2. Add some notes — a simple C major arpeggio
    print("\nAdding C major arpeggio notes...")
    for pitch, beat in [(60, 0), (64, 0.5), (67, 1.0), (72, 1.5)]:
        await mcp_opendaw_create_note(
            track_index=0, pitch=pitch, start_beat=beat,
            duration_beats=0.5, velocity=0.7, unit_index=0
        )

    # 3. Apply pitch humanization — subtle string warmth
    print("\nApplying pitch humanization (cents_depth=4, seed=7)...")
    result = await mcp_opendaw_humanize_pitch(
        unit_index=0, track_index=0,
        cents_depth=4,  # subtle ±4 cents
        bias=0,         # centered
        seed=7,
    )
    print(result)

    # 4. Also apply velocity/timing humanization for full effect
    print("\nApplying velocity/timing humanization...")
    result = await mcp_opendaw_humanize_notes(
        unit_index=0, track_index=0,
        velocity_amount=0.10,
        timing_amount=0.08,
        duration_amount=0.05,
        seed=7,
    )
    print(result)

    # 5. Try a detuned brass preset
    print("\n--- Detuned brass preset ---")
    print("humanize_pitch(unit_index=0, track_index=1, cents_depth=12, bias=-3)")
    print("  → 12 cents depth with -3 bias (flat tendency, typical brass)")


if __name__ == "__main__":
    asyncio.run(main())

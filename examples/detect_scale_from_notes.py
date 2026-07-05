"""Detect the musical scale/key from MIDI notes in a DAW region.

Unlike detect_key (which analyses WAV audio), this works directly on MIDI
note data — no audio file needed. Uses pitch class histogram + Pearson
correlation against 15 scale profiles, testing all 12 roots (180 combos).

Pipeline:
1. detect_scale_from_notes → find the scale of existing MIDI
2. force_scale_notes → snap any out-of-scale notes
3. diatonic_transpose_notes → transpose within the detected scale
4. generate_melody → generate new material in the same scale
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import (
    mcp_opendaw_detect_scale_from_notes,
    mcp_opendaw_force_scale_notes,
    mcp_opendaw_diatonic_transpose_notes,
)


async def main():
    # Step 1: Detect the scale from existing notes
    print("=== Detecting scale from MIDI notes ===")
    result = await mcp_opendaw_detect_scale_from_notes(
        unit_index=0,
        track_index=0,
        region_index=-2,  # all regions on track
    )
    print(result)

    # The result includes:
    # - best_match: {scale, root, correlation}
    # - alternatives: top 5 other scale candidates
    # - pitch_class_histogram: 12-bin distribution
    # - confidence: high/medium/low

    # Step 2: Force all notes to the detected scale
    # (Parse the best_match from result to get root and scale)
    print("\n=== Forcing notes to detected scale ===")
    forced = await mcp_opendaw_force_scale_notes(
        unit_index=0,
        track_index=0,
        root_note="A",
        scale="natural_minor",
    )
    print(forced)

    # Step 3: Transpose within the scale
    print("\n=== Diatonic transposition ===")
    transposed = await mcp_opendaw_diatonic_transpose_notes(
        unit_index=0,
        track_index=0,
        steps=2,
        root_note="A",
        scale="natural_minor",
    )
    print(transposed)


if __name__ == "__main__":
    asyncio.run(main())

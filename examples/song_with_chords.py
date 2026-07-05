"""Song + chord progression — harmonic movement over a full track.

Demonstrates adding a chord progression layer on top of a song built
with create_song_with_variations. The song builder creates rhythm and
melody (all sections share the same root), then create_chord_pads adds
harmonic movement (different chords per section).

Pipeline:
1. create_song_with_variations — 36-bar DnB song (6 sections, mix + humanize + master)
2. create_chord_pads — i-VI-III-VII in A minor (Am-F-C-G), 4 bars per chord
3. render_full_song — auto-detect length, export WAV

The chord pads play on track 2 (harmony track), creating harmonic color
changes that the arrangement alone can't provide.

Usage:
    source venv/bin/activate
    python examples/song_with_chords.py
"""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from server import (
    bridge,
    mcp_opendaw_create_song_with_variations,
    mcp_opendaw_create_chord_pads,
    mcp_opendaw_render_full_song,
)


async def main():
    print("Starting DAW bridge...")
    await bridge.start()
    print("Bridge ready.\n")

    # === STEP 1: Build the song (rhythm + melody + mix + master) ===
    print("=== STEP 1: create_song_with_variations('dnb') ===")
    song = await mcp_opendaw_create_song_with_variations(
        genre="dnb",
        apply_mix=True,
        apply_humanize=True,
        apply_master=True,
    )
    song_data = json.loads(song) if isinstance(song, str) else song
    print(f"Song: {song_data.get('total_bars')} bars, "
          f"{song_data.get('total_notes')} notes")
    print(f"Structure: {song_data.get('structure')}\n")

    # === STEP 2: Add chord progression (harmony layer) ===
    # i-VI-III-VII in A minor = Am-F-C-G
    # This is the same progression used in synthwave and trance
    # 4 bars per chord × 4 chords = 16 bars of harmonic movement
    # Place on track 2 (harmony track), octave 3 (pad range)
    print("=== STEP 2: create_chord_pads('Am-F-C-G') ===")
    chords = await mcp_opendaw_create_chord_pads(
        progression="Am-F-C-G",
        bars_per_chord=4,
        octave=3,
        velocity=0.55,   # soft pad, doesn't compete with drums
        track_index=2,
        note_duration=3.8,  # almost full bar with small gap
    )
    chord_data = json.loads(chords) if isinstance(chords, str) else chords
    print(f"Chords: {chord_data.get('chord_count')} chords, "
          f"{chord_data.get('total_bars')} bars, "
          f"{chord_data.get('total_notes')} pad notes")
    for c in chord_data.get("chords", []):
        print(f"  {c['chord']:8s} at beat {c['start_beat']:4.0f}  "
              f"pitches={c['pitches']}")
    print()

    # === STEP 3: Render everything ===
    print("=== STEP 3: render_full_song() ===")
    render = await mcp_opendaw_render_full_song(
        filename="dnb_with_chords",
        tail_beats=4,
    )
    render_data = json.loads(render) if isinstance(render, str) else render
    print(f"Rendered: {render_data.get('total_beats')} beats, "
          f"{render_data.get('regions_scanned')} regions")
    print(f"File: {render_data.get('filepath')}")
    print(f"Size: {render_data.get('file_size_mb')} MB\n")

    print("✓ Done — 3 calls: song + chords + render.")
    print("  The chord pads add harmonic movement that the")
    print("  arrangement alone (single root) can't provide.")

    await bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())

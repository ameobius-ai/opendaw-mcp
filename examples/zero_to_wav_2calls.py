"""Zero-to-WAV in 2 calls — the simplest full production pipeline.

Demonstrates the minimal path from empty project to finished track:
1. create_song_with_variations — builds a 36-bar song with 6 varied sections
2. render_full_song — auto-detects length, exports WAV

That's it. No manual beat counting, no per-track note creation, no
individual effect chaining. The song builder handles:
- 14 genre arrangements (dnb/house/trap/techno/dubstep/synthwave/trance/disco/
  afrobeat/rock/jazz/pop/funk/reggae)
- 12 section presets (full/drums_only/drums_bass/full_busy/breakdown/
  melody_invert/melody_reverse/melody_octave_up/melody_transposeN/
  bass_octave_up/bass_sub/fade/drop)
- Optional mix + humanize + master (all built-in)
- Real musical variation between sections (drum density, bass octave,
  melody transforms, track exclusion)

Usage:
    source venv/bin/activate
    python examples/zero_to_wav_2calls.py
"""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from server import (
    bridge,
    mcp_opendaw_create_song_with_variations,
    mcp_opendaw_render_full_song,
    mcp_opendaw_get_project_state,
)


async def main():
    # Start the DAW bridge
    print("Starting DAW bridge...")
    await bridge.start()
    print("Bridge ready.")

    # Show empty project state
    state = await mcp_opendaw_get_project_state()
    state_data = json.loads(state) if isinstance(state, str) else state
    print(f"Initial state: {state_data.get('tracks', 0)} tracks")

    # === CALL 1: Build a complete song ===
    print("\n=== CALL 1: create_song_with_variations('dnb') ===")
    result = await mcp_opendaw_create_song_with_variations(
        genre="dnb",
        # Default sections: intro:4:0.5:drums_only,verse1:8:0.8:full,
        # chorus:8:1.0:full_busy,verse2:8:0.8:melody_transpose5,
        # bridge:4:0.6:breakdown,outro:4:0.4:fade
        # = 36 bars with 6 varied sections
        apply_mix=True,       # genre-aware mix (comp/EQ/sat/reverb/sidechain)
        apply_humanize=True,  # genre-aware humanize (DnB = tight timing 0.03)
        apply_master=True,    # mastering chain (loud, -14 LUFS)
    )
    song_data = json.loads(result) if isinstance(result, str) else result
    print(f"Song built: {song_data.get('total_bars')} bars, "
          f"{song_data.get('section_count')} sections, "
          f"{song_data.get('total_notes')} notes")
    print(f"Structure: {song_data.get('structure')}")
    print(f"Pipeline: {song_data.get('pipeline_steps')}")

    # === CALL 2: Render to WAV ===
    print("\n=== CALL 2: render_full_song() ===")
    render = await mcp_opendaw_render_full_song(
        filename="dnb_full_song",
        tail_beats=4,  # 1 bar tail for reverb/delay
    )
    render_data = json.loads(render) if isinstance(render, str) else render
    print(f"Rendered: {render_data.get('detected_length_beats')} beats detected "
          f"+ {render_data.get('tail_beats')} tail = "
          f"{render_data.get('total_beats')} total")
    print(f"Regions scanned: {render_data.get('regions_scanned')}")
    print(f"File: {render_data.get('filepath')}")
    print(f"Size: {render_data.get('file_size_mb')} MB")
    print(f"Has audio: {render_data.get('has_audio')}")

    # Show final state
    state2 = await mcp_opendaw_get_project_state()
    state2_data = json.loads(state2) if isinstance(state2, str) else state2
    print(f"\nFinal state: {state2_data.get('tracks', 0)} tracks")

    print("\n✓ Done — 2 calls, empty project to finished WAV.")

    # Stop bridge
    await bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())

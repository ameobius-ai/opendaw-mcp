"""Custom song structure — 5 sections with hand-picked variations.

Demonstrates building a song section by section using
create_arrangement_variation. Each section gets specific musical
transforms — not presets, but hand-tuned parameters.

This is the "producer approach": you decide exactly what each section
sounds like, rather than using the song builder's presets.

Structure:
  intro (4 bars)  — drums only, sparse, low energy
  verse  (8 bars) — full arrangement, normal
  chorus (8 bars) — busy drums, octave-up bass, full energy
  bridge (4 bars) — sparse drums, inverted melody, no bass
  outro  (8 bars) — fade, no melody, sparse

Usage:
    source venv/bin/activate
    python examples/custom_sections.py
"""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from server import (
    bridge,
    mcp_opendaw_create_arrangement_variation,
    mcp_opendaw_apply_genre_mix,
    mcp_opendaw_apply_genre_humanization,
    mcp_opendaw_add_mastering_chain,
    mcp_opendaw_render_full_song,
)


async def main():
    print("Starting DAW bridge...")
    await bridge.start()
    print("Bridge ready.\n")

    # Define sections: (name, bars, velocity, start_beat, params)
    sections = [
        ("intro",  4, 0.45, 0,   {"drum_density": 0.3, "include_bass": False, "include_harmony": False, "include_melody": False}),
        ("verse",  8, 0.75, 16,  {"drum_density": 1.0, "include_bass": True,  "include_harmony": True,  "include_melody": True}),
        ("chorus", 8, 1.0,  48,  {"drum_density": 1.5, "bass_octave_shift": 1, "include_harmony": True,  "include_melody": True}),
        ("bridge", 4, 0.55, 80,  {"drum_density": 0.3, "include_bass": False, "melody_transform": "invert", "include_harmony": True}),
        ("outro",  8, 0.35, 96,  {"drum_density": 0.4, "include_bass": True,  "include_harmony": False, "include_melody": False}),
    ]

    total_bars = sum(s[1] for s in sections)
    print(f"Building {total_bars}-bar song with {len(sections)} custom sections:\n")

    for name, bars, vel, beat, params in sections:
        print(f"  {name:8s} bars={bars} vel={vel} beat={beat} {params}")
        result = await mcp_opendaw_create_arrangement_variation(
            genre="house",
            section_name=name,
            bars=bars,
            velocity=vel,
            start_beat=beat,
            **params,
        )
        data = json.loads(result) if isinstance(result, str) else result
        transforms = data.get("transforms", [])
        print(f"           → {data.get('notes_after', 0)} notes, transforms: {transforms}")

    print(f"\n{'='*60}")
    print("Post-processing pipeline:\n")

    # Mix
    print("  apply_genre_mix('house')...")
    mix = await mcp_opendaw_apply_genre_mix(genre="house")
    mix_data = json.loads(mix) if isinstance(mix, str) else mix
    print(f"  → {mix_data.get('effects_added', 0)} effects added")

    # Humanize
    print("  apply_genre_humanization('house')...")
    hum = await mcp_opendaw_apply_genre_humanization(genre="house")
    hum_data = json.loads(hum) if isinstance(hum, str) else hum
    print(f"  → {hum_data.get('tracks_humanized', 0)} tracks humanized")

    # Master
    print("  add_mastering_chain(loud, -14 LUFS)...")
    await mcp_opendaw_add_mastering_chain(target_lufs=-14, style="loud")
    print("  → mastering chain added")

    # Render
    print("\n  render_full_song()...")
    render = await mcp_opendaw_render_full_song(filename="custom_house")
    render_data = json.loads(render) if isinstance(render, str) else render
    print(f"  → {render_data.get('total_beats')} beats, "
          f"file: {render_data.get('filepath')}")

    print(f"\n✓ Done — {total_bars}-bar custom house track.")
    print("  Each section was hand-tuned with specific transforms.")
    print("  Total: 5 variation calls + 3 pipeline calls + 1 render = 9 calls.")

    await bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())

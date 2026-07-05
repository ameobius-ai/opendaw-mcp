"""Multi-section modulated song: verse→chorus→bridge→outro with key changes.

This example shows how to build a complete song with key modulation
between sections — all in one call. Each section has its own chord
progression, length, and energy level.

Default structure:
  verse  — Am-F-C-G   — 8 bars — energy 0.7 (A minor)
  chorus — C-G-Am-F   — 8 bars — energy 1.0 (C major, relative major)
  bridge — F-C-Dm-G   — 4 bars — energy 0.6 (F major, up a fourth)
  outro  — Am-F-C-G   — 4 bars — energy 0.5 (return to A minor)

Total: 24 bars, 4 key centers, auto-calculated beat positions.
"""
import asyncio
from server import (
    mcp_opendaw_create_modulated_song,
    mcp_opendaw_apply_genre_mix,
    mcp_opendaw_render_full_song,
)


async def main():
    # 1. Build multi-section modulated song (one call, 4 sections)
    r1 = await mcp_opendaw_create_modulated_song(
        sections="verse:Am-F-C-G:8:0.7,chorus:C-G-Am-F:8:1.0,bridge:F-C-Dm-G:4:0.6,outro:Am-F-C-G:4:0.5",
        arp_pattern="up",
        bass_pattern="root",
        melody_pattern="chord_tones",
        counter_melody_pattern="contrary",
        velocity=0.7,
    )
    print("Modulated song:", r1)

    # 2. Mix
    r2 = await mcp_opendaw_apply_genre_mix(genre="synthwave", unit_index=0)
    print("Mix:", r2)

    # 3. Render
    r3 = await mcp_opendaw_render_full_song()
    print("Render:", r3)


if __name__ == "__main__":
    asyncio.run(main())

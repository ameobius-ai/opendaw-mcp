"""Example: create a riff, hook, lick, and turnaround in sequence.

Demonstrates the melodic vocabulary pipeline:
  riff → hook → lick → turnaround → etude

Each tool generates genre-specific melodic content.
"""
import asyncio
import json
from server import (
    mcp_opendaw_create_riff,
    mcp_opendaw_create_hook,
    mcp_opendaw_create_lick,
    mcp_opendaw_create_turnaround,
    mcp_opendaw_create_etude,
)


async def main():
    # 1. Riff — song identity (E minor pentatonic, rock)
    print("=== RIFF (rock, E minor pentatonic, 2 bars) ===")
    result = json.loads(await mcp_opendaw_create_riff(
        riff_type="rock",
        key_root="E",
        scale_type="minor_pentatonic",
        bars=2,
        octave=3,
    ))
    print(f"  notes: {result.get('notes_generated', 'N/A')}")
    print(f"  characteristics: {result.get('characteristics', '')}")

    # 2. Hook — earworm melody (C major, pop, 2 bars)
    print("\n=== HOOK (pop, C major, 2 bars) ===")
    result = json.loads(await mcp_opendaw_create_hook(
        hook_type="pop",
        key_root="C",
        scale_type="major",
        bars=2,
        octave=4,
    ))
    print(f"  notes: {result.get('notes_generated', 'N/A')}")
    print(f"  characteristics: {result.get('characteristics', '')}")

    # 3. Lick — vocabulary phrase (A minor, bebop, 1 bar)
    print("\n=== LICK (bebop, A minor, 1 bar) ===")
    result = json.loads(await mcp_opendaw_create_lick(
        lick_type="bebop",
        key_root="A",
        scale_type="minor",
        octave=4,
    ))
    print(f"  notes: {result.get('notes_generated', 'N/A')}")
    print(f"  characteristics: {result.get('characteristics', '')}")

    # 4. Turnaround — resolution (C major, jazz, 2 bars)
    print("\n=== TURNAROUND (jazz, C major, 2 bars) ===")
    result = json.loads(await mcp_opendaw_create_turnaround(
        turnaround_type="jazz",
        key_root="C",
        scale_type="major",
        octave=4,
    ))
    print(f"  notes: {result.get('notes_generated', 'N/A')}")
    print(f"  characteristics: {result.get('characteristics', '')}")

    # 5. Etude — technical study (C major, scale, 8 bars)
    print("\n=== ETUDE (scale, C major, 8 bars) ===")
    result = json.loads(await mcp_opendaw_create_etude(
        etude_type="scale",
        key_root="C",
        scale_type="major",
        bars=8,
        octave=4,
    ))
    print(f"  notes: {result.get('notes_generated', 'N/A')}")
    print(f"  characteristics: {result.get('characteristics', '')}")

    print("\n✓ Melodic vocabulary pipeline complete")


if __name__ == "__main__":
    asyncio.run(main())

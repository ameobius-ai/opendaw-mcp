"""Reharmonization — transform a chord progression with substitution techniques.

This example shows how to use reharmonize_progression to enrich a simple
chord progression with jazz and classical substitution techniques.

Usage:
    python reharmonization.py
"""

import asyncio
import json
from opendaw_mcp.server import (
    mcp_opendaw_reharmonize_progression,
)


async def main():
    # Original: ii-V-I in C major (jazz standard)
    original = "Dm7-G7-Cmaj7"

    # 1. Tritone substitution: G7 → Db7 (guide tones shared)
    result_tt = await mcp_opendaw_reharmonize_progression(
        progression=original,
        technique="tritone_sub",
        intensity="medium",
    )
    data = json.loads(result_tt)
    print("=== Tritone Substitution ===")
    print(f"Original:  {data['source_progression']}")
    print(f"Reharmonized: {data['reharmonized_progression']}")
    for m in data["chord_mapping"]:
        if not m.get("kept"):
            print(f"  {m['explanation']}")

    # 2. Modal interchange on pop progression
    pop_orig = "C-G-Am-F"
    result_mi = await mcp_opendaw_reharmonize_progression(
        progression=pop_orig,
        technique="modal_interchange",
        intensity="heavy",
    )
    data_mi = json.loads(result_mi)
    print("\n=== Modal Interchange ===")
    print(f"Original:  {data_mi['source_progression']}")
    print(f"Reharmonized: {data_mi['reharmonized_progression']}")
    for m in data_mi["chord_mapping"]:
        if not m.get("kept"):
            print(f"  {m['explanation']}")

    # 3. Secondary dominants for jazz coloring
    jazz_orig = "C-Am-Dm-G7"
    result_sd = await mcp_opendaw_reharmonize_progression(
        progression=jazz_orig,
        technique="secondary_dominant",
        intensity="medium",
    )
    data_sd = json.loads(result_sd)
    print("\n=== Secondary Dominants ===")
    print(f"Original:  {data_sd['source_progression']}")
    print(f"Reharmonized: {data_sd['reharmonized_progression']}")
    for m in data_sd["chord_mapping"]:
        if not m.get("kept"):
            print(f"  {m['explanation']}")

    # 4. Use reharmonized result with voice-led pads
    reharmonized = data_mi["reharmonized_progression"]
    print("\n=== Voice-Led Pads on Reharmonized Progression ===")
    print(f"Progression: {reharmonized}")
    # result = await mcp_opendaw_create_voice_led_progression(
    #     progression=reharmonized,
    #     octave=3,
    #     track_index=2,
    # )


if __name__ == "__main__":
    asyncio.run(main())

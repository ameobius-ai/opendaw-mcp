"""Example: Ground bass — repeating ostinato with developing melody.

create_ground_bass creates a basso ostinato: a short bass pattern that
repeats throughout while a melody above it changes character per cycle.
"""

import asyncio
from opendaw_mcp.server import mcp_opendaw_create_ground_bass


async def main():
    # 1. Baroque style — descending stepwise (Purcell's Dido's Lament vibe)
    print("=== Baroque Ground Bass ===")
    result = await mcp_opendaw_create_ground_bass(
        bass_pattern="A2 A2 E2 E2 F2 F2 E2 E2",
        bass_rhythm="1 1 1 1 1 1 1 1",
        repeats=8, melody_style="baroque"
    )
    print(result[:300])

    # 2. Film tension — dissonant crescendo
    print("\n=== Film Tension Ground Bass ===")
    result = await mcp_opendaw_create_ground_bass(
        bass_pattern="D2 D2 A2 A2",
        bass_rhythm="2 2 2 2",
        repeats=12, melody_style="film_tension"
    )
    print(result[:300])

    # 3. Modal jazz vamp — Miles Davis / Kind of Blue
    print("\n=== Modal Ground Bass ===")
    result = await mcp_opendaw_create_ground_bass(
        bass_pattern="D2 A2 D2 A2",
        bass_rhythm="2 2 2 2",
        repeats=16, melody_style="modal"
    )
    print(result[:300])


if __name__ == "__main__":
    asyncio.run(main())

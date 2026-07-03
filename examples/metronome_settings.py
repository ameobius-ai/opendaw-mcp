"""Example: Configure metronome for recording with count-in.

Uses the dedicated set_metronome tool to enable click,
set volume, and choose sixteenth-note subdivision.
"""
import asyncio
import sys

sys.path.insert(0, ".")

from server import mcp  # noqa: E402


async def main() -> None:
    # Enable metronome at moderate volume with sixteenth-note clicks
    result = await mcp.call_tool("set_metronome", {
        "enabled": True,
        "gain": 0.6,
        "beat_subdivision": 4,  # 1=quarter, 2=eighths, 4=sixteenths
    })
    print(f"Metronome: {result}")


if __name__ == "__main__":
    asyncio.run(main())

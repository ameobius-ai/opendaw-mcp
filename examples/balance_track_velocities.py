"""Balance velocities across multiple tracks — MIDI mix leveling.

Sets relative velocity levels across multiple note tracks so they sit
correctly in the mix. Uses presets for common genre balances, or custom
target velocities for precise control.

Presets assume track order: drums, bass, harmony/pads, lead/vocal.
Adjust track_indices to match your actual track order.
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import mcp_opendaw_balance_track_velocities


async def main():
    # Hip-hop / rock / electronic: drums forward
    print("=== Drums forward (hip-hop/rock/electronic) ===")
    result = await mcp_opendaw_balance_track_velocities(
        unit_index=0,
        track_indices="0,1,2,3",  # drums, bass, harmony, lead
        preset="drums_forward",
    )
    print(result)

    # Pop / ballad: vocal forward
    print("\n=== Vocal forward (pop/ballad) ===")
    result2 = await mcp_opendaw_balance_track_velocities(
        unit_index=0,
        track_indices="0,1,2,3",
        preset="vocal_forward",
    )
    print(result2)

    # Custom: precise control
    print("\n=== Custom balance ===")
    result3 = await mcp_opendaw_balance_track_velocities(
        unit_index=0,
        track_indices="0,1,2,3",
        preset="custom",
        target_velocities="0.9,0.85,0.55,0.75",
    )
    print(result3)


if __name__ == "__main__":
    asyncio.run(main())

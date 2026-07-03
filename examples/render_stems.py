"""
Example: Render stems and full mix with LUFS targeting.

Shows how to:
- Render individual stems (per-AU exports)
- Render the full mix
- Target streaming LUFS levels (-14 for Spotify/YouTube)
"""

import asyncio
import json
import server

async def main():
    await server.bridge.start()
    print("Bridge started")

    # 1. Get project info
    result = await server.mcp_opendaw_get_project_duration()
    duration = json.loads(result)
    print(f"Project duration: {duration}")

    # 2. Render individual stems
    # Get all AUs
    result = await server.mcp_opendaw_get_full_project_state()
    state = json.loads(result)
    aus = state.get("audio_units", [])

    for i, au in enumerate(aus):
        result = await server.mcp_opendaw_render_stems(
            unit_index=i,
            filename=f"stem_{au.get('label', f'unit{i}')}.wav",
            target_lufs=-14.0
        )
        data = json.loads(result)
        print(f"Stem {i} ({au.get('label', '?')}): {data}")

    # 3. Render full mix
    result = await server.mcp_opendaw_render_mix(
        filename="full_mix.wav",
        target_lufs=-14.0
    )
    data = json.loads(result)
    print(f"Full mix: {data}")

    print("\nRendering complete!")
    print(f"Rendered {len(aus)} stems + 1 full mix at -14 LUFS")

    await server.bridge.stop()

if __name__ == "__main__":
    asyncio.run(main())

"""
Example: Render stems and full mix with LUFS targeting.

Shows how to:
- Render individual stems (per-AU exports)
- Target streaming LUFS levels (-14 for Spotify/YouTube)
- Auto-gain to match loudness targets
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

    # 2. Start the engine (required for rendering)
    await server.mcp_opendaw_start_engine()
    print("Engine started")

    # 3. Export individual stems
    # export_stems(filename_prefix, sample_rate)
    result = await server.mcp_opendaw_export_stems("stem", 48000)
    stems_data = json.loads(result)
    print(f"Stems exported: {stems_data}")

    # 4. Measure LUFS on the exported mix
    # measure_lufs(filename)
    mix_file = stems_data.get("mix_file") or stems_data.get("files", [{}])[0].get("path", "")
    if mix_file:
        result = await server.mcp_opendaw_measure_lufs(mix_file)
        lufs_data = json.loads(result)
        print(f"LUFS measurement: {lufs_data}")

        # 5. Auto-gain to -14 LUFS (Spotify target)
        # auto_gain(target_lufs, filename, sample_rate, max_iterations)
        result = await server.mcp_opendaw_auto_gain("-14", mix_file, 48000, "10")
        print(f"Auto-gain to -14 LUFS: {json.loads(result)}")
    else:
        print("No mix file found for LUFS measurement")

    print("\nRendering complete!")
    print("Stems exported + LUFS measured + auto-gain applied")

    await server.bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())

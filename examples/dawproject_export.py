#!/usr/bin/env python3
"""Example: Export project to .dawproject format and re-import.

Demonstrates cross-DAW workflow: openDAW → .dawproject → Bitwig/Ableton → .dawproject → openDAW
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from server import bridge, mcp_opendaw_create_synth_track, mcp_opendaw_export_dawproject, mcp_opendaw_import_dawproject


async def main():
    await bridge.start()

    # Create a simple project
    print("Creating synth track...")
    r = await mcp_opendaw_create_synth_track(track_name="Bass", waveform="sawtooth")
    print(f"  {r[:100]}")

    # Export to .dawproject
    print("\nExporting to .dawproject...")
    r = await mcp_opendaw_export_dawproject("my_project")
    print(f"  {r}")

    # Import it back
    filepath = "/tmp/opendaw-exports/my_project.dawproject"
    if os.path.exists(filepath):
        print(f"\nImporting {filepath}...")
        r = await mcp_opendaw_import_dawproject(filepath)
        print(f"  {r}")

    await bridge.stop()
    print("\nDone! Cross-DAW round-trip complete.")


if __name__ == "__main__":
    asyncio.run(main())

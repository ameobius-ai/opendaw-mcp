"""Render a project and convert to MP3/FLAC in one step.

Demonstrates:
- create_synth_track + create_note_track + create_note
- render_full (WAV)
- convert_audio (WAV → MP3, WAV → FLAC)
- render_full_format (render + convert in one call)

Usage: python render_convert.py
"""
import asyncio
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from server import bridge, mcp


def _result(r):
    """Unwrap MCP call_tool result to dict."""
    if isinstance(r, tuple):
        return json.loads(r[0][0].text)
    if isinstance(r, str):
        return json.loads(r)
    return r


async def main():
    await bridge.start()
    print("=== Render + Convert Example ===\n")

    # 1. Create a synth track
    r = await mcp.call_tool("mcp_opendaw_create_synth_track",
                            {"name": "bass", "synth_type": "Vaporisateur"})
    d = _result(r)
    ui = d.get("unit_index", 1)
    print(f"Created synth track: unit_index={ui}")

    # 2. Create note track + add a note
    await mcp.call_tool("mcp_opendaw_create_note_track", {"unit_index": ui})
    await mcp.call_tool("mcp_opendaw_create_note",
                        {"track_index": 0, "pitch": 36, "start_beat": 0,
                         "duration_beats": 4, "velocity": 0.8, "unit_index": ui})
    print("Added bass note (C2, 4 beats)")

    # 3. Render to WAV first
    r = await mcp.call_tool("mcp_opendaw_render_full",
                            {"filename": "bass_wav", "sample_rate": 48000})
    d = _result(r)
    print(f"\nRendered WAV: {d.get('file_size_mb', '?')}MB, has_audio={d.get('has_audio')}")

    # 4. Convert to MP3
    r = await mcp.call_tool("mcp_opendaw_convert_audio",
                            {"filename": "bass_wav", "format": "mp3", "bitrate": "320k"})
    d = _result(r)
    print(f"Converted MP3: {d.get('output_size_mb', '?')}MB (ratio: {d.get('compression_ratio', '?')})")

    # 5. Convert to FLAC
    r = await mcp.call_tool("mcp_opendaw_convert_audio",
                            {"filename": "bass_wav", "format": "flac"})
    d = _result(r)
    print(f"Converted FLAC: {d.get('output_size_mb', '?')}MB (ratio: {d.get('compression_ratio', '?')})")

    # 6. One-step render + convert
    r = await mcp.call_tool("mcp_opendaw_render_full_format",
                            {"filename": "bass_one_step", "sample_rate": 48000, "format": "mp3"})
    d = _result(r)
    conv = d.get("conversion", {}) if isinstance(d, dict) else {}
    print(f"\nOne-step render+convert MP3: {conv.get('output_size_mb', '?')}MB")

    # 7. Verify all files
    print("\n=== Exported files ===")
    export_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "exports")
    for f in sorted(os.listdir(export_dir)):
        if f.startswith("bass"):
            size = os.path.getsize(os.path.join(export_dir, f))
            print(f"  {f}: {size / 1024:.0f}KB")

    await bridge.stop()
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())

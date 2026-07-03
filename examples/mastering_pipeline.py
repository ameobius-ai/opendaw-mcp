"""
Mastering Pipeline Example

Demonstrates a complete mastering workflow:
1. Render the full mix to WAV
2. Measure integrated LUFS and true peak
3. Auto-adjust gain to hit a target LUFS
4. Render stems for delivery
5. Convert to MP3 for preview

This is a real-world mastering chain that an AI agent can run
end-to-end without human intervention.
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import server


async def main():
    bridge = server.bridge

    # ─── Setup ──────────────────────────────────────────────
    print("=== Mastering Pipeline ===\n")

    # Check project state
    state = await server.mcp_opendaw_get_project_info()
    info = json.loads(state)
    if "error" in info:
        print(f"Error: {info['error']}")
        return
    print(f"Project: {info.get('bpm', '?')} BPM, {info.get('track_count', 0)} tracks")

    # ─── Step 1: Render full mix ────────────────────────────
    print("\n[1/5] Rendering full mix to WAV (48kHz)...")
    render = json.loads(await server.mcp_opendaw_render_full(
        filename="pre_master",
        sample_rate=48000
    ))
    if "error" in render:
        print(f"  Render failed: {render['error']}")
        return
    print(f"  Rendered: {render.get('file_path', 'unknown')}")

    # ─── Step 2: Measure LUFS ───────────────────────────────
    print("\n[2/5] Measuring integrated LUFS...")
    lufs = json.loads(await server.mcp_opendaw_measure_lufs(
        filename="pre_master"
    ))
    if "error" in lufs:
        print(f"  LUFS measurement failed: {lufs['error']}")
        return
    integrated = lufs.get("integrated_lufs", "?")
    true_peak = lufs.get("true_peak_db", "?")
    print(f"  Integrated LUFS: {integrated}")
    print(f"  True Peak: {true_peak} dB")

    # ─── Step 3: Auto-gain to target ────────────────────────
    target_lufs = -14.0  # Spotify/YouTube standard
    print(f"\n[3/5] Auto-adjusting gain to {target_lufs} LUFS...")
    gain = json.loads(await server.mcp_opendaw_auto_gain(
        filename="pre_master",
        target_lufs=target_lufs
    ))
    if "error" in gain:
        print(f"  Auto-gain failed: {gain['error']}")
        return
    print(f"  Adjusted by {gain.get('gain_adjustment_db', '?')} dB")
    print(f"  New LUFS: {gain.get('new_lufs', '?')}")

    # ─── Step 4: Export stems ───────────────────────────────
    print("\n[4/5] Exporting stems for delivery...")
    stems = json.loads(await server.mcp_opendaw_export_stems(
        filename_prefix="stem",
        sample_rate=48000
    ))
    if "error" in stems:
        print(f"  Stem export failed: {stems['error']}")
    else:
        stem_count = stems.get("stem_count", 0)
        print(f"  Exported {stem_count} stems")

    # ─── Step 5: Convert to MP3 for preview ─────────────────
    print("\n[5/5] Converting master to MP3 (320kbps)...")
    mp3 = json.loads(await server.mcp_opendaw_convert_audio(
        filename="pre_master",
        format="mp3",
        bitrate="320k"
    ))
    if "error" in mp3:
        print(f"  Conversion failed: {mp3['error']}")
    else:
        print(f"  MP3: {mp3.get('output_file', 'created')}")

    print("\n=== Mastering complete ===")


if __name__ == "__main__":
    asyncio.run(main())

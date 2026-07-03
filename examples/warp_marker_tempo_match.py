"""Warp marker tempo matching example.

Demonstrates creating, updating, and deleting warp markers on a
time-stretched audio region to match it to a target tempo.

Usage:
    source venv/bin/activate
    python examples/warp_marker_tempo_match.py
"""

import asyncio
import json
import struct
import wave
import io
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from server import (
    bridge,
    mcp_opendaw_load_audio,
    mcp_opendaw_create_audio_track,
    mcp_opendaw_create_time_stretched_region,
    mcp_opendaw_list_warp_markers,
    mcp_opendaw_create_warp_marker,
    mcp_opendaw_update_warp_marker,
    mcp_opendaw_delete_warp_marker,
)


def make_test_wav(path: str, duration: float = 4.0, sr: int = 44100):
    """Create a simple decaying tone WAV for testing."""
    n = int(sr * duration)
    buf = io.BytesIO()
    with wave.open(buf, "w") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        for i in range(n):
            # 220Hz sine with decay
            t = i / sr
            val = int(16000 * 0.7 ** (t * 2) * 0.5 * (i / sr))
            w.writeframesraw(struct.pack("<hh", val, val))
    buf.seek(0)
    with open(path, "wb") as f:
        f.write(buf.read())


async def main():
    print("Starting bridge...")
    await bridge.start()
    print("Bridge ready\n")

    # 1. Create test audio
    wav_path = "/tmp/warp_test_tone.wav"
    make_test_wav(wav_path, duration=4.0)
    print(f"Created test WAV: {wav_path}")

    # 2. Load into DAW
    r = await mcp_opendaw_load_audio(wav_path, "tempo_test")
    data = json.loads(r)
    sample_id = data["id"]
    print(f"Loaded audio: id={sample_id}, duration={data['duration']}s")

    # 3. Create audio track + time-stretched region
    await mcp_opendaw_create_audio_track()
    r = await mcp_opendaw_create_time_stretched_region(
        sample_id, unit_index=0, start_beat=0, track_index=0,
        playback_rate=1.0, transient_mode="transient", bpm=120
    )
    print(f"Created stretched region: {r}")

    # 4. List existing warp markers (should have 2 anchors)
    r = await mcp_opendaw_list_warp_markers(0, 0, 0)
    data = json.loads(r)
    print(f"\nInitial warp markers ({data['marker_count']}):")
    for m in data["warp_markers"]:
        anchor = " [ANCHOR]" if m["is_anchor"] else ""
        print(f"  pos={m['position']}ppqn  sec={m['seconds']}s{anchor}")

    # 5. Add a warp marker at beat 1 → 0.75s (tempo drift point)
    r = await mcp_opendaw_create_warp_marker(0, 0, 0, position_beats=1.0, seconds=0.75)
    data = json.loads(r)
    print(f"\nCreated warp marker at beat 1, 0.75s → {data['marker_count']} markers")

    # 6. Add another at beat 2 → 1.6s
    r = await mcp_opendaw_create_warp_marker(0, 0, 0, position_beats=2.0, seconds=1.6)
    data = json.loads(r)
    print(f"Created warp marker at beat 2, 1.6s → {data['marker_count']} markers")

    # 7. Update marker 1 (beat 1) to 0.8s
    r = await mcp_opendaw_update_warp_marker(0, 0, 0, marker_index=1, seconds=0.8)
    data = json.loads(r)
    print(f"Updated marker 1 → pos={data['position']}ppqn sec={data['seconds']}s")

    # 8. List all markers
    r = await mcp_opendaw_list_warp_markers(0, 0, 0)
    data = json.loads(r)
    print(f"\nFinal warp markers ({data['marker_count']}):")
    for m in data["warp_markers"]:
        anchor = " [ANCHOR]" if m["is_anchor"] else ""
        print(f"  pos={m['position']}ppqn  sec={m['seconds']}s{anchor}")

    # 9. Clean up — delete non-anchor markers
    for i in [2, 1]:  # delete in reverse to keep indices stable
        r = await mcp_opendaw_delete_warp_marker(0, 0, 0, marker_index=i)
        data = json.loads(r)
        if data.get("success"):
            print(f"Deleted marker {i} → {data['remaining_markers']} remaining")

    print("\nWarp marker tempo matching demo complete ✅")


if __name__ == "__main__":
    asyncio.run(main())

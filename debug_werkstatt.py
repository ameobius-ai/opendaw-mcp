#!/usr/bin/env python3
"""Debug: why does Werkstatt give silence?

Test variations:
1. Single track + Werkstatt on unit 1
2. Two tracks + Werkstatt on unit 1
3. Single track + Werkstatt on master (unit 0)
4. Single track + built-in effect (Reverb) on unit 1
"""
import asyncio, json, sys, os, numpy as np
from scipy.io import wavfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["OPENDAW_URL"] = "http://[::1]:5174"

from server import (
    mcp_opendaw_load_audio, mcp_opendaw_create_instrument_track,
    mcp_opendaw_place_audio_region, mcp_opendaw_render_full,
    mcp_opendaw_set_track_volume, mcp_opendaw_add_effect,
)
from opendaw_mcp.bridge import HeadlessDawBridge

def _parse(r):
    if isinstance(r, str):
        try: return json.loads(r)
        except: return {"error": r}
    return r

async def render_no_fx(bridge):
    """Baseline: no effects."""
    load_d = _parse(await mcp_opendaw_load_audio(file_path="/tmp/ssl_test_tone.wav", name="test"))
    sid = load_d["id"]
    track_d = _parse(await mcp_opendaw_create_instrument_track(name="test"))
    uid = track_d["unit_index"]
    tid = track_d.get("track_index", 0)
    await mcp_opendaw_place_audio_region(sample_id=sid, unit_index=uid, start_beat=0.0, track_index=tid)
    await mcp_opendaw_set_track_volume(unit_index=uid, volume_db=-3.0)
    r = _parse(await mcp_opendaw_render_full(filename="debug_no_fx", sample_rate=48000))
    return r

async def render_with_reverb(bridge):
    """Built-in Reverb effect (not Werkstatt)."""
    load_d = _parse(await mcp_opendaw_load_audio(file_path="/tmp/ssl_test_tone.wav", name="test2"))
    sid = load_d["id"]
    track_d = _parse(await mcp_opendaw_create_instrument_track(name="test2"))
    uid = track_d["unit_index"]
    tid = track_d.get("track_index", 0)
    await mcp_opendaw_place_audio_region(sample_id=sid, unit_index=uid, start_beat=0.0, track_index=tid)
    await mcp_opendaw_set_track_volume(unit_index=uid, volume_db=-3.0)
    # Add built-in Reverb
    add_d = _parse(await mcp_opendaw_add_effect(effect_type="Reverb", unit_index=uid))
    print(f"  Reverb added: {add_d.get('success', False)}, idx={add_d.get('effect_index')}")
    r = _parse(await mcp_opendaw_render_full(filename="debug_reverb", sample_rate=48000))
    return r

async def main():
    sr = 48000; dur = 5.0
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    mono = 0.3 * np.sin(2 * np.pi * 440 * t)
    stereo = np.stack([mono, mono * 0.95], axis=1)
    wavfile.write("/tmp/ssl_test_tone.wav", sr, (stereo * 32767).astype(np.int16))

    bridge = HeadlessDawBridge()
    bridge.daw_url = "http://[::1]:5174"
    await bridge.start()
    print("Bridge ready.\n")

    print("=== Test 1: No effects (baseline) ===")
    r1 = await render_no_fx(bridge)
    if r1 and r1.get("success"):
        print(f"  max_sample={r1.get('max_sample', 0):.4f} has_audio={r1.get('has_audio')}")
    else:
        print(f"  ❌ {r1}")

    print("\n=== Test 2: Built-in Reverb ===")
    r2 = await render_with_reverb(bridge)
    if r2 and r2.get("success"):
        print(f"  max_sample={r2.get('max_sample', 0):.4f} has_audio={r2.get('has_audio')}")
    else:
        print(f"  ❌ {r2}")

    await bridge.stop()
    print("\n=== DONE ===")

if __name__ == "__main__":
    asyncio.run(main())

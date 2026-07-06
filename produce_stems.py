#!/usr/bin/env python3
"""Universal stem production pipeline for openDAW.

Loads external WAV stems, applies mixing + mastering chain, renders to WAV.
Uses MCP tool functions directly from server.py — proven working pattern.

Usage:
  venv/bin/python produce_stems.py

Edit STEMS, EFFECTS, MASTERING, OUTPUT_NAME sections below.
All calls in one asyncio.run() — bridge state persists.
NO start_engine before render — OfflineEngineRenderer manages its own engine.
"""
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["OPENDAW_URL"] = "http://[::1]:5174"

from server import (
    mcp_opendaw_load_audio,
    mcp_opendaw_create_instrument_track,
    mcp_opendaw_place_audio_region,
    mcp_opendaw_add_effect,
    mcp_opendaw_set_effect_parameter,
    mcp_opendaw_set_track_volume,
    mcp_opendaw_set_track_panning,
    mcp_opendaw_render_full,
)
from opendaw_mcp.bridge import HeadlessDawBridge

# === EDIT THIS SECTION ===
STEMS_DIR = "/mnt/c/Users/admin/Downloads"

STEMS = [
    # (name, file_path, volume_db, panning, muted)
    ("anchor",  f"{STEMS_DIR}/Last Light of Summer.wav",                  -6.0,  0.0,  True),
    ("vocal_1", f"{STEMS_DIR}/Last Light of Summer (Lead Vocal).wav",      -2.0, -0.3, False),
    ("vocal_2", f"{STEMS_DIR}/Last Light of Summer (Lead Vocal)(1).wav",   -3.0,  0.3, False),
    ("acoustic",f"{STEMS_DIR}/Last Light of Summer (Acoustic Guitar).wav", -4.0, -0.2, False),
    ("guitar",  f"{STEMS_DIR}/Last Light of Summer (Guitar).wav",          -5.0,  0.25, False),
    ("bass",    f"{STEMS_DIR}/Last Light of Summer (Bass).wav",            -3.0,  0.0, False),
    ("drums",   f"{STEMS_DIR}/Last Light of Summer (Drum Kit).wav",        -4.0,  0.0, False),
]

# Effects: (stem_index, effect_type, {param: value})
# stem_index = position in STEMS list (0=anchor, 1=vocal_1, ...)
EFFECTS = [
    (1, "Compressor", {"threshold": -18, "ratio": 3, "attack": 0.003, "release": 0.25}),
    (2, "Compressor", {"threshold": -18, "ratio": 3, "attack": 0.003, "release": 0.25}),
    (6, "Compressor", {"threshold": -12, "ratio": 4, "attack": 0.001, "release": 0.15}),
    (1, "Reverb",     {"wet": 0.35, "dry": 0.8}),
    (2, "Reverb",     {"wet": 0.35, "dry": 0.8}),
    (3, "Reverb",     {"wet": 0.20, "dry": 0.8}),
]

# Mastering on primary bus (unit 0)
MASTERING = [
    ("Maximizer", {"ceiling": -1.0, "gain": 2.0}),
]

OUTPUT_NAME = "last_light_of_summer"
OUTPUT_DESKTOP = True  # copy to Windows Desktop after render
# === END EDIT SECTION ===


def _parse(r):
    """Parse MCP tool result to dict."""
    if isinstance(r, str):
        try:
            return json.loads(r)
        except (json.JSONDecodeError, ValueError):
            return {"error": r}
    return r


async def main():
    print("Starting bridge...")
    bridge = HeadlessDawBridge()
    bridge.daw_url = "http://[::1]:5174"
    await bridge.start()
    print("Bridge ready.\n")

    # Step 1: Load stems
    print(f"=== Step 1: Load {len(STEMS)} stems ===")
    unit_indices = []
    for i, (name, path, vol, pan, muted) in enumerate(STEMS):
        print(f"  [{i+1}/{len(STEMS)}] {name}:")

        load_d = _parse(await mcp_opendaw_load_audio(file_path=path, name=name))
        if not load_d or not load_d.get("success"):
            print(f"    load ❌ {load_d}")
            unit_indices.append(None)
            continue
        sample_id = load_d["id"]

        track_d = _parse(await mcp_opendaw_create_instrument_track(name=name))
        if not track_d or not track_d.get("success"):
            print(f"    track ❌ {track_d}")
            unit_indices.append(None)
            continue
        uid = track_d["unit_index"]
        tid = track_d["track_index"]
        unit_indices.append(uid)

        place_d = _parse(await mcp_opendaw_place_audio_region(
            sample_id=sample_id, unit_index=uid, start_beat=0.0, track_index=tid
        ))
        if not place_d or not place_d.get("success"):
            print(f"    region ❌ {place_d}")
            continue

        await mcp_opendaw_set_track_volume(unit_index=uid, volume_db=vol)
        await mcp_opendaw_set_track_panning(unit_index=uid, panning=pan)
        print(f"    ✅ unit {uid}, {load_d.get('duration', 0):.1f}s, vol={vol}dB, pan={pan}")

    # Step 2: Effects
    print(f"\n=== Step 2: Add {len(EFFECTS)} effects ===")
    for stem_idx, effect_type, params in EFFECTS:
        if stem_idx >= len(unit_indices) or unit_indices[stem_idx] is None:
            continue
        uid = unit_indices[stem_idx]
        add_d = _parse(await mcp_opendaw_add_effect(effect_type=effect_type, unit_index=uid))
        if add_d and add_d.get("success"):
            fx_idx = add_d.get("effect_index", 0)
            for pname, value in params.items():
                await mcp_opendaw_set_effect_parameter(uid, fx_idx, pname, value)
            print(f"  unit {uid}: {effect_type} ✅")
        else:
            print(f"  unit {uid}: {effect_type} ❌ {add_d}")

    # Step 3: Mastering
    print("\n=== Step 3: Mastering on primary bus ===")
    for effect_type, params in MASTERING:
        add_d = _parse(await mcp_opendaw_add_effect(effect_type=effect_type, unit_index=0))
        if add_d and add_d.get("success"):
            fx_idx = add_d.get("effect_index", 0)
            for pname, value in params.items():
                await mcp_opendaw_set_effect_parameter(0, fx_idx, pname, value)
            print(f"  {effect_type} ✅")
        else:
            print(f"  {effect_type} ❌ {add_d}")

    # Step 4: Render (NO start_engine!)
    print("\n=== Step 4: Render ===")
    render_d = _parse(await mcp_opendaw_render_full(filename=OUTPUT_NAME, sample_rate=48000))
    if render_d and render_d.get("success"):
        dur = render_d.get("samples", 0) / render_d.get("sample_rate", 48000)
        size_mb = render_d.get("size", 0) / 1048576
        print(f"  ✅ Duration: {dur:.1f}s, Size: {size_mb:.1f}MB")
        print(f"  Has audio: {render_d.get('has_audio')}, Max sample: {render_d.get('max_sample', 0):.4f}")
        filepath = render_d.get("filepath", "")
        if filepath:
            print(f"  File: {filepath}")
            if OUTPUT_DESKTOP:
                import shutil
                desktop_path = f"/mnt/c/Users/admin/Desktop/{OUTPUT_NAME}.wav"
                shutil.copy2(filepath, desktop_path)
                print(f"  Copied to: {desktop_path}")
    else:
        print(f"  ❌ {render_d}")

    await bridge.stop()
    print("\n=== DONE ===")


if __name__ == "__main__":
    asyncio.run(main())

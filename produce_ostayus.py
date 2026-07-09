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
    mcp_opendaw_set_script_device_code,
    mcp_opendaw_set_script_param,
    mcp_opendaw_render_full,
)
from opendaw_mcp.bridge import HeadlessDawBridge

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts")


def _load_script(name):
    """Load a Werkstatt DSP script by name (without werkstatt_ prefix and .js suffix)."""
    path = os.path.join(SCRIPTS_DIR, f"werkstatt_{name}.js")
    with open(path, "r") as f:
        return f.read()

# === EDIT THIS SECTION ===
STEMS_DIR = "/mnt/c/Users/admin/Downloads"

STEMS = [
    # (name, file_path, volume_db, panning, muted)
    # Post-rock: vocal doubles L/R, guitar doubles hard L/R, bass +3dB foundation
    # Analysis: vocal -18 LUFS, guitar -18.9, bass -23.5 (needs boost), drums -21.8
    # vocal_1/vocal_2 are doubles — pan L/R, vocal_2 quieter
    # guitar_1/guitar_2 are doubles — hard pan
    ("anchor",  f"{STEMS_DIR}/Остаюсь с солью.wav",                       -10.0,  0.0,  True),
    ("vocal_1", f"{STEMS_DIR}/Остаюсь с солью (Lead Vocal).wav",          -2.0,  -0.5, False),   # L
    ("vocal_2", f"{STEMS_DIR}/Остаюсь с солью (Lead Vocal)(1).wav",       -4.0,   0.5, False),   # R, quieter
    ("guitar_1",f"{STEMS_DIR}/Остаюсь с солью (Guitar).wav",              -3.0,  -0.85, False),  # hard L
    ("guitar_2",f"{STEMS_DIR}/Остаюсь с солью (Guitar)(1).wav",           -3.0,   0.85, False),  # hard R
    ("bass",    f"{STEMS_DIR}/Остаюсь с солью (Bass).wav",                 0.0,   0.0, False),   # foundation +3dB
    ("drums",   f"{STEMS_DIR}/Остаюсь с солью (Drum Kit).wav",            -4.0,   0.0, False),   # center
]

# Effects: (stem_index, effect_type, {param: value})
# stem_index = position in STEMS list (0=anchor, 1=vocal_1, ...)
# Post-rock premix v4: removed de-esser + guitar paraeq (killed body)
# Kept: bass paraeq (fundamental), vocal comp, drum comp, reverb
EFFECTS = [
    # Vocals: compressor only (de-esser removed — killed vocal body)
    (1, "Compressor", {"threshold": -22, "ratio": 4, "attack": 0.005, "release": 0.3}),
    (2, "Compressor", {"threshold": -22, "ratio": 4, "attack": 0.005, "release": 0.3}),
    # Bass: ParaEQ — boost 80Hz + cut 250Hz (mud). No HPF — keeps sub fundamental
    (5, "Werkstatt", {"__script__": "paraeq", "hp_freq": 20, "band1_freq": 80, "band1_gain": 3.0, "band1_q": 1.0,
                       "band2_freq": 250, "band2_gain": -2.0, "band2_q": 1.2,
                       "band3_freq": 5000, "band3_gain": 0.0, "band3_q": 1.0}),
    # Drums: compressor for punch
    (6, "Compressor", {"threshold": -15, "ratio": 4, "attack": 0.002, "release": 0.12}),
    # Reverb — post-rock BIG space
    (1, "Reverb", {"wet": 0.40, "dry": 0.7}),
    (2, "Reverb", {"wet": 0.40, "dry": 0.7}),
    (3, "Reverb", {"wet": 0.25, "dry": 0.8}),
    (4, "Reverb", {"wet": 0.25, "dry": 0.8}),
]

# Mastering on primary bus (unit 0)
# SSL bus comp (fixed 2026-07-08) + Maximizer
MASTERING = [
    ("Werkstatt", {"__script__": "ssl_bus_comp", "threshold": 0.4, "ratio": 0.3, "attack": 0.3, "release": 0.3, "makeup": 0.4, "mix": 0.6, "auto_release": 1.0}),
    ("Maximizer", {"ceiling": -0.5, "gain": 0.0}),
]

OUTPUT_NAME = "ostayus_solyu"
OUTPUT_DESKTOP = True  # copy to Windows Desktop after render
FAST_SECONDS = 30  # 0 = full render, >0 = trim output to first N seconds (for quick iteration)
# === END EDIT SECTION ===


def _parse(r):
    """Parse MCP tool result to dict."""
    if isinstance(r, str):
        try:
            return json.loads(r)
        except (json.JSONDecodeError, ValueError):
            return {"error": r}
    return r


def preflight_check_werkstatt():
    """Validate all Werkstatt scripts referenced in EFFECTS before render."""
    import subprocess, sys as _sys
    scripts_dir = os.path.join(os.path.dirname(__file__), "scripts")
    checked = set()
    for _, etype, params in EFFECTS:
        if etype == "Werkstatt" and "__script__" in params:
            script_name = params["__script__"]
            matches = [f for f in os.listdir(scripts_dir) if script_name in f and f.endswith(".js")]
            for m in matches:
                if m not in checked:
                    checked.add(m)
                    path = os.path.join(scripts_dir, m)
                    # inline validation (faster than subprocess)
                    import re
                    NUM = r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?'
                    VALID = re.compile(rf'^//\s*@param\s+(\w+)\s+({NUM})\s+({NUM})\s+({NUM})(?:\s+(\w+))?(?:\s+(.+))?$')
                    with open(path) as f:
                        lines = f.readlines()
                    in_header = False
                    errors = []
                    for i, line in enumerate(lines, 1):
                        line = line.rstrip("\n")
                        if "@werkstatt" in line or "@apparat" in line:
                            in_header = True
                            continue
                        if not in_header: continue
                        if line.strip() and not line.strip().startswith("//"): break
                        if "@param" not in line: continue
                        if not VALID.match(line):
                            errors.append(f"    line {i}: {line.strip()}")
                    if errors:
                        print(f"  ⛔ {m}: malformed @param:")
                        for e in errors:
                            print(e)
                        print(f"  Run: venv/bin/python autofix_params.py --check {script_name}")
                        return False
    return True


async def main():
    print("Starting bridge...")
    bridge = HeadlessDawBridge()
    bridge.daw_url = "http://[::1]:5174"
    await bridge.start()
    print("Bridge ready.\n")

    # Step 0: Pre-flight validation of Werkstatt scripts
    if EFFECTS:
        print("=== Step 0: Pre-flight Werkstatt validation ===")
        if not preflight_check_werkstatt():
            print("  Fix malformed scripts before rendering. Aborting.")
            await bridge.stop()
            sys.exit(1)
        print("  All Werkstatt scripts valid ✅\n")

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
        if not add_d or not add_d.get("success"):
            print(f"  unit {uid}: {effect_type} ❌ {add_d}")
            continue
        fx_idx = add_d.get("effect_index", 0)

        # Werkstatt: load script, set code, then set params
        if effect_type == "Werkstatt" and "__script__" in params:
            script_name = params.pop("__script__")
            code = _load_script(script_name)
            code_d = _parse(await mcp_opendaw_set_script_device_code(
                device_type="werkstatt", unit_index=uid, device_index=fx_idx, code=code
            ))
            if not code_d or not code_d.get("success"):
                print(f"  unit {uid}: {script_name} code ❌ {code_d}")
                continue
            # Set params via set_script_param
            for pname, value in params.items():
                await mcp_opendaw_set_script_param("werkstatt", uid, fx_idx, pname, value)
            print(f"  unit {uid}: {script_name} ✅")
        else:
            # Regular effect: set params via set_effect_parameter
            for pname, value in params.items():
                await mcp_opendaw_set_effect_parameter(uid, fx_idx, pname, value)
            print(f"  unit {uid}: {effect_type} ✅")

    # Step 3: Mastering
    print("\n=== Step 3: Mastering on primary bus ===")
    for effect_type, params in MASTERING:
        add_d = _parse(await mcp_opendaw_add_effect(effect_type=effect_type, unit_index=0))
        if not add_d or not add_d.get("success"):
            print(f"  {effect_type} ❌ {add_d}")
            continue
        fx_idx = add_d.get("effect_index", 0)

        # Werkstatt: load script, set code, then set params
        if effect_type == "Werkstatt" and "__script__" in params:
            script_name = params.pop("__script__")
            code = _load_script(script_name)
            code_d = _parse(await mcp_opendaw_set_script_device_code(
                device_type="werkstatt", unit_index=0, device_index=fx_idx, code=code
            ))
            if not code_d or not code_d.get("success"):
                print(f"  {script_name} code ❌ {code_d}")
                continue
            for pname, value in params.items():
                await mcp_opendaw_set_script_param("werkstatt", 0, fx_idx, pname, value)
            print(f"  {script_name} ✅")
        else:
            for pname, value in params.items():
                await mcp_opendaw_set_effect_parameter(0, fx_idx, pname, value)
            print(f"  {effect_type} ✅")

    # Step 4: Render (NO start_engine!)
    print("\n=== Step 4: Render ===")
    render_d = _parse(await mcp_opendaw_render_full(filename=OUTPUT_NAME, sample_rate=48000))
    if render_d and render_d.get("success"):
        dur = render_d.get("samples", 0) / render_d.get("sample_rate", 48000)
        size_mb = render_d.get("size", 0) / 1048576
        max_sample = render_d.get("max_sample", 0)
        has_audio = render_d.get("has_audio", False)
        print(f"  ✅ Duration: {dur:.1f}s, Size: {size_mb:.1f}MB")
        print(f"  Has audio: {has_audio}, Max sample: {max_sample:.4f}")

        # ─── FAST RENDER TRIM ───────────────────────────────────
        # If FAST_SECONDS > 0, trim output to first N seconds for quick iteration
        filepath = render_d.get("filepath", "")
        if filepath and FAST_SECONDS > 0:
            from scipy.io import wavfile as _wav
            import numpy as _np
            _sr, _data = _wav.read(filepath)
            if _data.dtype == _np.int16: _data = _data.astype(_np.float32) / 32768.0
            elif _data.dtype != _np.float32: _data = _data.astype(_np.float32)
            _cut = int(FAST_SECONDS * _sr)
            if _data.shape[0] > _cut:
                _data = _data[:_cut]
                _wav.write(filepath, _sr, _data)
                print(f"  ✂️ Trimmed to first {FAST_SECONDS}s ({_cut} samples)")
                render_d["samples"] = _cut
                render_d["max_sample"] = float(_np.max(_np.abs(_data))) if _data.size > 0 else 0.0
                render_d["has_audio"] = bool(_np.max(_np.abs(_data)) > 0.001) if _data.size > 0 else False
                max_sample = render_d["max_sample"]
                has_audio = render_d["has_audio"]

        # ─── SILENT RENDER GUARD ───────────────────────────────
        # Detect empty/quiet output — usually means a broken effect killed the signal
        # Fail fast instead of silently shipping silence
        if not has_audio or max_sample < 0.001:
            print(f"\n  ⛔ SILENT RENDER DETECTED — max_sample={max_sample:.6f}")
            print(f"  This usually means:")
            print(f"    - A Werkstatt script failed silently on the master bus")
            print(f"    - A paraeq/EQ parameter is out of range")
            print(f"    - A compressor threshold is too aggressive")
            print(f"  Check effect chain — remove suspicious effects and re-render.")
            print(f"  Output file NOT copied to Desktop (preventing silent delivery).")
            await bridge.stop()
            sys.exit(1)

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

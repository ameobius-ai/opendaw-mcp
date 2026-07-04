"""Suno generation → openDAW enhancement — end-to-end AI music pipeline.

This is the flagship integration example:
1. Generate a track with Suno (via chirp_generate MCP tool)
2. Download the audio
3. Load it into openDAW
4. Add mastering effects (Werkstatt tape sat + lookahead comp)
5. Measure LUFS for streaming platforms
6. Render the enhanced mix

This connects two AI music tools: Suno (generation) → openDAW (production).

Requirements:
    - openDAW Vite dev server on localhost:5174
    - Suno API access — join https://discord.gg/kRpauM54vn to get chirp API access
    - Internet connection for Suno generation

Usage:
    source venv/bin/activate
    python examples/suno_generate_to_opendaw.py

    # With custom prompt
    python examples/suno_generate_to_opendaw.py --prompt "dark coldwave, 90 BPM, minor key, analog synths"
"""

import asyncio
import json
import sys
import os
import argparse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from server import (
    bridge,
    mcp_opendaw_get_project_state,
    mcp_opendaw_create_audio_track,
    mcp_opendaw_load_audio,
    mcp_opendaw_create_audio_clip,
    mcp_opendaw_add_effect,
    mcp_opendaw_set_script_device_code,
    mcp_opendaw_set_script_param,
    mcp_opendaw_set_bpm,
    mcp_opendaw_render_full,
    mcp_opendaw_measure_lufs,
    mcp_opendaw_export_stems,
)

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
EXPORT_DIR = os.environ.get("OPENDAW_EXPORT_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "exports"))


def load_script(name: str) -> str:
    with open(os.path.join(SCRIPTS_DIR, name)) as f:
        return f.read()


def download_audio(url: str, dest_path: str) -> bool:
    """Download audio from URL to local file."""
    try:
        urllib.request.urlretrieve(url, dest_path)
        return os.path.exists(dest_path) and os.path.getsize(dest_path) > 0
    except Exception as e:
        print(f"  Download failed: {e}")
        return False


async def generate_with_suno(prompt: str, style: str = "") -> dict | None:
    """Generate a track with Suno via the chirp_generate tool.

    Returns dict with audio_url, title, lyric, or None on failure.
    """
    try:
        # Import chirp_generate from the MCP tools available in this environment
        # In production, this would be called via the MCP protocol
        print(f"  Prompt: {prompt}")
        if style:
            print(f"  Style: {style}")

        # Use chirp_generate directly (available in Hermes environment)
        from chirp_generate import chirp_generate  # type: ignore

        kwargs = {
            "prompt": prompt,
            "model": "sun/chirp-v5",
            "instrumental": False,
        }
        if style:
            kwargs["style"] = style

        result = await chirp_generate(**kwargs)
        if result and isinstance(result, dict):
            # chirp_generate returns a list of variations
            variations = result.get("variations", result.get("songs", []))
            if isinstance(variations, list) and variations:
                v = variations[0]
                return {
                    "audio_url": v.get("audio_url", ""),
                    "title": v.get("title", "suno_track"),
                    "lyric": v.get("lyric", ""),
                    "image_url": v.get("image_url", ""),
                }
        return None
    except ImportError:
        print("  (chirp_generate not available — using placeholder)")
        return None
    except Exception as e:
        print(f"  Suno generation error: {e}")
        return None


async def main():
    parser = argparse.ArgumentParser(description="Suno → openDAW end-to-end pipeline")
    parser.add_argument("--prompt", default="dark coldwave, analog synths, 90 BPM, minor key, atmospheric",
                        help="Suno generation prompt")
    parser.add_argument("--style", default="coldwave, darkwave, post-punk, analog synthesizers, reverb",
                        help="Suno style tags")
    parser.add_argument("--bpm", type=int, default=90, help="BPM for openDAW project")
    parser.add_argument("--skip-suno", action="store_true", help="Skip Suno generation, use local file")
    parser.add_argument("--audio-file", help="Local audio file to use instead of Suno")
    args = parser.parse_args()

    print("=" * 60)
    print("Suno Generation → openDAW Enhancement Pipeline")
    print("=" * 60)

    await bridge.start()

    audio_path = args.audio_file

    # ─── 1. Generate with Suno ───────────────────────────────
    if not args.skip_suno and not audio_path:
        print("\n[1/6] Generating track with Suno...")
        suno_result = await generate_with_suno(args.prompt, args.style)
        if suno_result and suno_result.get("audio_url"):
            print(f"  Generated: {suno_result['title']}")
            # Download the audio
            audio_path = os.path.join(EXPORT_DIR, f"{suno_result['title']}.mp3")
            os.makedirs(EXPORT_DIR, exist_ok=True)
            if download_audio(suno_result["audio_url"], audio_path):
                print(f"  Downloaded to: {audio_path}")
            else:
                print("  Download failed — continuing without audio")
                audio_path = None
        else:
            print("  Suno generation not available — continuing in demo mode")
            audio_path = None
    elif audio_file := args.audio_file:
        print(f"\n[1/6] Using local file: {audio_file}")
    else:
        print("\n[1/6] Skipping Suno generation (--skip-suno)")

    # ─── 2. Set up project ───────────────────────────────────
    print(f"\n[2/6] Setting up openDAW project at {args.bpm} BPM...")
    state = json.loads(await mcp_opendaw_get_project_state())
    print(f"  Project: {state.get('track_count', 0)} tracks")

    await mcp_opendaw_set_bpm(bpm=args.bpm)
    print(f"  BPM: {args.bpm}")

    # ─── 3. Load audio + create track ────────────────────────
    sample_id = None
    unit_idx = 0  # primary audio unit
    if audio_path and os.path.exists(audio_path):
        print("\n[3/6] Loading audio into openDAW...")
        result = json.loads(await mcp_opendaw_load_audio(file_path=audio_path, name="suno_track"))
        if result.get("success"):
            sample_id = result["id"]
            print(f"  Loaded: {result['name']} ({result.get('duration', 0):.1f}s)")

            track = json.loads(await mcp_opendaw_create_audio_track())
            track_idx = track.get("track_index", 0)
            print(f"  Track created: index {track_idx}")

            clip = json.loads(await mcp_opendaw_create_audio_clip(
                sample_id=sample_id, unit_index=unit_idx,
                clip_index=0, track_index=track_idx, bpm=args.bpm
            ))
            print(f"  Clip placed: {'OK' if clip.get('success') else clip.get('error', 'issue')}")
        else:
            print(f"  Load failed: {result.get('error', 'unknown')}")
    else:
        print("\n[3/6] Skipping audio load (no file)")

    # ─── 4. Mastering chain ──────────────────────────────────
    print("\n[4/6] Adding mastering chain...")
    # Werkstatt DarkSat — tape saturation for analog warmth
    sat = json.loads(await mcp_opendaw_add_effect(unit_index=unit_idx, effect_type="Werkstatt"))
    if sat.get("success"):
        fx_idx = sat.get("effect_index", 0)
        await mcp_opendaw_set_script_device_code(
            device_type="werkstatt", unit_index=unit_idx,
            device_index=fx_idx, code=load_script("werkstatt_darksat.js")
        )
        await mcp_opendaw_set_script_param("werkstatt", unit_idx, fx_idx, "drive", 0.3)
        await mcp_opendaw_set_script_param("werkstatt", unit_idx, fx_idx, "tone", 0.5)
        await mcp_opendaw_set_script_param("werkstatt", unit_idx, fx_idx, "mix", 0.6)
        await mcp_opendaw_set_script_param("werkstatt", unit_idx, fx_idx, "output", -1)
        print("  ✅ DarkSat tape saturation: drive=0.3, mix=0.6")

    # Werkstatt Lookahead — transparent compression
    comp = json.loads(await mcp_opendaw_add_effect(unit_index=unit_idx, effect_type="Werkstatt"))
    if comp.get("success"):
        fx_idx = comp.get("effect_index", 1)
        await mcp_opendaw_set_script_device_code(
            device_type="werkstatt", unit_index=unit_idx,
            device_index=fx_idx, code=load_script("werkstatt_lookahead.js")
        )
        await mcp_opendaw_set_script_param("werkstatt", unit_idx, fx_idx, "threshold", -14)
        await mcp_opendaw_set_script_param("werkstatt", unit_idx, fx_idx, "ratio", 3)
        await mcp_opendaw_set_script_param("werkstatt", unit_idx, fx_idx, "attack", 0.005)
        await mcp_opendaw_set_script_param("werkstatt", unit_idx, fx_idx, "release", 0.15)
        await mcp_opendaw_set_script_param("werkstatt", unit_idx, fx_idx, "makeup", 3)
        await mcp_opendaw_set_script_param("werkstatt", unit_idx, fx_idx, "mix", 1)
        print("  ✅ Lookahead compressor: thresh=-14dB, ratio=3:1, makeup=+3dB")

    # ─── 5. Measure LUFS ─────────────────────────────────────
    print("\n[5/6] Measuring LUFS...")
    lufs = json.loads(await mcp_opendaw_measure_lufs())
    if lufs.get("success") or "lufs" in lufs:
        lufs_val = lufs.get("lufs", lufs.get("lufs_integrated", "?"))
        true_peak = lufs.get("true_peak_db", "?")
        print(f"  LUFS: {lufs_val} dB, True Peak: {true_peak} dB")
        if isinstance(lufs_val, (int, float)):
            if lufs_val > -14:
                print("  ⚠️  Above Spotify target (-14 LUFS) — may need attenuation")
            elif lufs_val < -18:
                print("  ⚠️  Below streaming minimum — may need makeup gain")
            else:
                print("  ✅ Within streaming range (-14 to -18 LUFS)")

    # ─── 6. Render + export ──────────────────────────────────
    print("\n[6/6] Rendering enhanced mix...")
    render = json.loads(await mcp_opendaw_render_full(filename="suno_enhanced", sample_rate=48000))
    if render.get("success"):
        print(f"  ✅ Rendered: {render.get('file_path', 'unknown')}")
    else:
        print(f"  Render: {render.get('error', 'check engine')}")

    stems = json.loads(await mcp_opendaw_export_stems(filename="suno_stems", sample_rate=48000))
    if stems.get("success"):
        print(f"  ✅ Stems: {stems.get('stem_count', 0)} exported")

    await bridge.stop()
    print("\n" + "=" * 60)
    print("Pipeline complete!")
    print("=" * 60)
    print("\nWorkflow: Suno (generation) → openDAW (production)")
    print("  1. Suno generated the track")
    print("  2. openDAW loaded it as an audio clip")
    print("  3. Tape saturation added analog warmth")
    print("  4. Lookahead compression provided transparent leveling")
    print("  5. LUFS measured for streaming compliance")
    print("  6. Enhanced mix rendered + stems exported")


if __name__ == "__main__":
    asyncio.run(main())

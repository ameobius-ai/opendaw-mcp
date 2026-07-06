#!/usr/bin/env python3
"""E2E render test with real stems: Last Light of Summer.

Uses MCP tools directly: create_instrument_track, load_audio, place_audio_region,
apply_mix_preset, render_full. Tests the render timeout fix.
"""

import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server import (
    bridge,
    mcp_opendaw_create_instrument_track,
    mcp_opendaw_load_audio,
    mcp_opendaw_place_audio_region,
    mcp_opendaw_apply_mix_preset,
    mcp_opendaw_render_full,
    mcp_opendaw_get_project_info,
)

STEMS = [
    {"name": "Acoustic Guitar", "file": "/home/ameobius/projects/creative-studio/agent-daw/headless-daw/public/stems_last_light/Last Light of Summer (Acoustic Guitar).wav"},
    {"name": "Bass", "file": "/home/ameobius/projects/creative-studio/agent-daw/headless-daw/public/stems_last_light/Last Light of Summer (Bass).wav"},
    {"name": "Drum Kit", "file": "/home/ameobius/projects/creative-studio/agent-daw/headless-daw/public/stems_last_light/Last Light of Summer (Drum Kit).wav"},
    {"name": "Guitar", "file": "/home/ameobius/projects/creative-studio/agent-daw/headless-daw/public/stems_last_light/Last Light of Summer (Guitar).wav"},
    {"name": "Lead Vocal", "file": "/home/ameobius/projects/creative-studio/agent-daw/headless-daw/public/stems_last_light/Last Light of Summer (Lead Vocal).wav"},
    {"name": "Lead Vocal 2", "file": "/home/ameobius/projects/creative-studio/agent-daw/headless-daw/public/stems_last_light/Last Light of Summer (Lead Vocal)(1).wav"},
]

MIX = [
    {"pan": -0.3, "vol_db": -3.0},
    {"pan": 0.0, "vol_db": -6.0},
    {"pan": 0.0, "vol_db": -4.0},
    {"pan": 0.3, "vol_db": -5.0},
    {"pan": -0.15, "vol_db": 0.0},
    {"pan": 0.15, "vol_db": -2.0},
]


async def main():
    print("Starting bridge...")
    if bridge.page is None:
        await bridge.start()
    print("Bridge ready!")

    # Phase 1: Create 6 instrument tracks (Tape device — plays audio regions)
    print("\n=== Phase 1: Create 6 instrument tracks ===")
    track_indices = []
    for i, stem in enumerate(STEMS):
        result = await mcp_opendaw_create_instrument_track(stem["name"])
        data = json.loads(result) if isinstance(result, str) else result
        unit_idx = data.get("unit_index", i) if isinstance(data, dict) else i
        track_idx = data.get("track_index", 0) if isinstance(data, dict) else 0
        track_indices.append({"unit": unit_idx, "track": track_idx})
        print(f"  Track {i}: {stem['name']} → unit={unit_idx}, track={track_idx}")

    # Phase 2: Load audio files
    print("\n=== Phase 2: Load audio ===")
    sample_ids = []
    for i, stem in enumerate(STEMS):
        result = await mcp_opendaw_load_audio(stem["file"], stem["name"])
        data = json.loads(result) if isinstance(result, str) else result
        sample_id = data.get("id") if isinstance(data, dict) else None
        duration = data.get("duration") if isinstance(data, dict) else None
        sample_ids.append(sample_id)
        print(f"  Stem {i}: {stem['name']} → id={sample_id}, dur={duration}s")

    # Phase 3: Place audio regions
    print("\n=== Phase 3: Place regions ===")
    for i, stem in enumerate(STEMS):
        ti = track_indices[i]
        sample_id = sample_ids[i]
        if not sample_id:
            print(f"  Region {i}: SKIP — no sample_id")
            continue
        result = await mcp_opendaw_place_audio_region(
            sample_id, ti["unit"], 0.0, ti["track"]
        )
        data = json.loads(result) if isinstance(result, str) else result
        print(f"  Region {i}: {stem['name']} → {data}")

    # Phase 4: Apply mix (pan + volume)
    print("\n=== Phase 4: Apply mix ===")
    for i, settings in enumerate(MIX):
        pan = settings["pan"]
        vol_db = settings["vol_db"]
        ti = track_indices[i]
        unit_idx = ti["unit"]
        result = await bridge.evaluate(f"""async () => {{
            const h = window.DAW_HELPERS;
            const auBox = h.auBox({unit_idx});
            h.modify(() => {{
                if (auBox.panning) auBox.panning.setValue({pan});
                if (auBox.volume) auBox.volume.setValue({vol_db});
            }});
            return {{
                pan: auBox.panning?.getValue?.() ?? null,
                volume: auBox.volume?.getValue?.() ?? null,
            }};
        }}""")
        print(f"  AU {unit_idx}: pan={pan}, vol={vol_db}dB → {result}")

    # Phase 5: Check project state
    print("\n=== Phase 5: Project state ===")
    state = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        const aus = h.allAUs();
        const lastPPQN = h.project.lastRegionAction ? h.project.lastRegionAction() : 0;
        const beats = lastPPQN / h.ppqn.Quarter;
        return {
            au_count: aus.length,
            last_beat: beats,
            bpm: h.project.timelineBox.bpm.getValue(),
        };
    }""")
    print(f"  State: {state}")

    # Phase 6: RENDER
    print("\n=== Phase 6: RENDER ===")
    t0 = time.time()
    render_result = await mcp_opendaw_render_full("last_light_of_summer_mix", 48000)
    elapsed = time.time() - t0

    render_data = json.loads(render_result) if isinstance(render_result, str) else render_result
    print(f"\n  Render completed in {elapsed:.1f}s")
    print(f"  Result: {json.dumps(render_data, indent=2)}")

    if isinstance(render_data, dict) and render_data.get("success"):
        has_audio = render_data.get("has_audio", False)
        filepath = render_data.get("filepath")
        size_mb = render_data.get("file_size_mb", 0)
        print(f"\n  WAV: {filepath} ({size_mb} MB)")
        print(f"  Has audio: {has_audio}")
        print(f"  Max sample: {render_data.get('max_sample')}")
        if has_audio:
            print("  ✅ RENDER SUCCESS — audio present in output")
        else:
            print("  ❌ RENDER — no audio in output")
    else:
        print(f"\n  RENDER ERROR: {render_data}")

    await bridge.stop()
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())

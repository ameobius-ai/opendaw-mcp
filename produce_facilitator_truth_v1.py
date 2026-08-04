#!/usr/bin/env python3
"""Facilitator Truth one-shot stem mix.

Pipeline fixes vs broken MCP session:
- fresh bridge + page.reload (clean box graph / master AU)
- NO start_engine before render
- NO transfer_audiounit / add_mastering_chain (corrupt indices)
- dual instr + dual vox via double import_audio_to_tracks
- master Revamp HS + Maximizer only on unit 0 (output)
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("OPENDAW_URL", "http://127.0.0.1:5174")

from server import (
    mcp_opendaw_import_audio_to_tracks,
    mcp_opendaw_set_bpm,
    mcp_opendaw_set_track_volume,
    mcp_opendaw_set_track_panning,
    mcp_opendaw_add_effect,
    mcp_opendaw_set_revamp_filter,
    mcp_opendaw_set_effect_parameter,
    mcp_opendaw_render_full,
    mcp_opendaw_get_project_state,
    mcp_opendaw_reset_project,
)
from opendaw_mcp.bridge import HeadlessDawBridge
import server as server_mod

STEMS = "/tmp/facilitator_truth"
BPM = 108
OUT = "facilitator_truth_mix_v1"


def _parse(r):
    if isinstance(r, str):
        try:
            return json.loads(r)
        except (json.JSONDecodeError, ValueError):
            return {"raw": r}
    return r if isinstance(r, dict) else {"raw": r}


async def hard_reload():
    """Reload headless page so Project + master AU are fresh."""
    b = server_mod.bridge
    if b.page is None:
        await b.start()
    print("reloading page…")
    await b.page.reload(timeout=30000)
    await b.page.wait_for_function(
        "(typeof window.DAW !== 'undefined'"
        " || (window.opendaw && window.opendaw.service && window.opendaw.service.project)"
        " || typeof window.DAW_project !== 'undefined')"
        " && typeof window.DAW_NoteEventBox !== 'undefined'",
        timeout=60000,
    )
    # re-inject helpers if start() already did once
    await b.start() if False else None
    # force helper reinject: clear flag then re-run start injection path
    await b.page.evaluate("() => { try { delete window.DAW_HELPERS; } catch(e) {} }")
    # re-call bridge start injection by evaluating the same wait + reinject via start internals
    # simplest: stop+start fresh browser
    try:
        await b.stop()
    except Exception:
        pass
    await b.start()
    print("bridge ready")


async def main():
    print("=== Facilitator Truth v1 clean rebuild ===")
    await hard_reload()

    st = _parse(await mcp_opendaw_get_project_state())
    print("state after reload:", json.dumps(st)[:300])

    rst = _parse(await mcp_opendaw_reset_project())
    print("reset:", rst)
    st2 = _parse(await mcp_opendaw_get_project_state())
    n = len(st2.get("audioUnits") or [])
    print("units after reset:", n)
    if n == 0:
        print("NO master AU — reload again hard")
        await hard_reload()
        st2 = _parse(await mcp_opendaw_get_project_state())
        n = len(st2.get("audioUnits") or [])
        print("units after 2nd reload:", n)

    await mcp_opendaw_set_bpm(bpm=BPM)

    # Import order: drums, bass, instr L, instr R, vox L, vox R
    files = [
        ("drums", f"{STEMS}/drums.wav"),
        ("bass", f"{STEMS}/bass.wav"),
        ("instr_L", f"{STEMS}/instrumentals.wav"),
        ("instr_R", f"{STEMS}/instrumentals.wav"),
        ("vox_L", f"{STEMS}/vocals.wav"),
        ("vox_R", f"{STEMS}/vocals.wav"),
    ]
    units = {}
    for name, path in files:
        r = _parse(await mcp_opendaw_import_audio_to_tracks(
            file_path=path, mode="", bpm=BPM, start_beat=0.0
        ))
        uid = r.get("unit_index")
        if uid is None and "result" in r:
            try:
                inner = json.loads(r["result"]) if isinstance(r["result"], str) else r["result"]
                uid = inner.get("unit_index")
                r = inner
            except Exception:
                pass
        print(f"  import {name}: unit={uid} ok={r.get('imported')}")
        if uid is None:
            raise SystemExit(f"import failed {name}: {r}")
        units[name] = int(uid)

    # levels + pan
    layout = {
        "drums":  (2.5, 0.0),
        "bass":   (-2.0, 0.0),
        "instr_L": (-4.0, -0.55),
        "instr_R": (-4.0, 0.55),
        "vox_L":  (1.5, -0.35),
        "vox_R":  (1.5, 0.35),
    }
    for name, (vol, pan) in layout.items():
        uid = units[name]
        await mcp_opendaw_set_track_volume(unit_index=uid, volume_db=vol)
        await mcp_opendaw_set_track_panning(unit_index=uid, panning=pan)
        print(f"  mix {name} u{uid}: {vol}dB pan {pan}")

    # stem EQ
    # bass LS -2.5@100
    b = units["bass"]
    await mcp_opendaw_add_effect(unit_index=b, effect_type="Revamp")
    await mcp_opendaw_set_revamp_filter(
        unit_index=b, effect_index=0, section="lowshelf",
        enabled=True, frequency=100, gain=-2.5, q=0.7
    )
    # instr low-mid cut
    for key in ("instr_L", "instr_R"):
        u = units[key]
        await mcp_opendaw_add_effect(unit_index=u, effect_type="Revamp")
        await mcp_opendaw_set_revamp_filter(
            unit_index=u, effect_index=0, section="lowbell",
            enabled=True, frequency=250, gain=-1.5, q=1.0
        )
    # vox presence HS
    for key in ("vox_L", "vox_R"):
        u = units[key]
        await mcp_opendaw_add_effect(unit_index=u, effect_type="Revamp")
        await mcp_opendaw_set_revamp_filter(
            unit_index=u, effect_index=0, section="highshelf",
            enabled=True, frequency=3500, gain=2.5, q=0.7
        )
    print("  stem eq ok")

    # master on unit 0 ONLY if it's empty output (no audio track)
    st3 = _parse(await mcp_opendaw_get_project_state())
    aus = st3.get("audioUnits") or []
    print("pre-master state units:", len(aus))
    master_u = 0
    # if unit 0 has a track, master AU was lost — put lim on last unit is wrong;
    # try add to 0 anyway only if no track content expected
    u0 = aus[0] if aus else {}
    has_track0 = bool(u0.get("tracks"))
    if has_track0 and units.get("drums") == 0:
        print("WARN: unit0 is drums (no separate master). applying master chain on unit0 drums bus path = wrong")
        print("skipping unit-local master; will post-process with ffmpeg loudnorm after render")
        master_ok = False
    else:
        await mcp_opendaw_add_effect(unit_index=master_u, effect_type="Revamp")
        await mcp_opendaw_set_revamp_filter(
            unit_index=master_u, effect_index=0, section="highshelf",
            enabled=True, frequency=10000, gain=3.0, q=0.7
        )
        await mcp_opendaw_add_effect(unit_index=master_u, effect_type="Maximizer")
        await mcp_opendaw_set_effect_parameter(
            unit_index=master_u, effect_index=1, parameter_name="threshold", value=-1.5
        )
        master_ok = True
        print("  master HS+lim on unit", master_u)

    print("render (no start_engine)…")
    rend = _parse(await mcp_opendaw_render_full(filename=OUT, sample_rate=48000))
    if "result" in rend and isinstance(rend["result"], str):
        try:
            rend = json.loads(rend["result"])
        except Exception:
            pass
    print("render:", json.dumps(rend)[:500])
    if not rend.get("success"):
        raise SystemExit(2)
    print("filepath:", rend.get("filepath"))
    print("max_sample:", rend.get("max_sample"), "master_ok:", master_ok)


if __name__ == "__main__":
    asyncio.run(main())

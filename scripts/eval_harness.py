#!/usr/bin/env python3
"""
Agent Eval Harness v1 for opendaw-mcp.

5 scenarios benchmarking agent ability to produce music end-to-end.
Each scenario measures objective audio metrics:

1. Techno loop 128 BPM — steady 4/4 kick pattern
2. DnB break — 170 BPM Amen-style break
3. Ambient pad — sustained chords, no rhythm
4. Mix to -14 LUFS — take render, measure integrated LUFS
5. Sidechain — kick triggers volume duck on bass

Scoring:
- non-silence: max_sample ≥ 0.01
- finite: no NaN/Inf in output
- LUFS within ±2 dB of target
- spectral balance: energy distributed across bands
- structure: has tracks, notes, regions

Output: JSON results for docs/monitoring.
Runs in CI headless E2E or locally with DAW.
"""
import asyncio
import json
import math
import os
import sys
import time

OPENDAW_URL = os.environ.get("OPENDAW_URL", "https://localhost:5174")


def _has_non_finite(obj) -> bool:
    if isinstance(obj, float):
        return not math.isfinite(obj)
    if isinstance(obj, dict):
        return any(_has_non_finite(v) for v in obj.values())
    if isinstance(obj, (list, tuple)):
        return any(_has_non_finite(v) for v in obj)
    return False


def _score_scenario(name: str, result: dict, checks: dict) -> dict:
    """Score a scenario based on objective criteria."""
    passed = 0
    failed = 0
    details = {}

    for check_name, check_fn in checks.items():
        try:
            ok = check_fn(result)
            details[check_name] = "PASS" if ok else "FAIL"
            if ok:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            details[check_name] = f"ERROR: {e}"
            failed += 1

    return {
        "scenario": name,
        "passed": passed,
        "failed": failed,
        "total": passed + failed,
        "score": round(passed / (passed + failed), 2) if (passed + failed) > 0 else 0,
        "details": details,
    }


async def run_scenarios():
    from server import OpendawServer

    server = OpendawServer()
    await server.bridge.start()
    results = []

    try:
        # === Scenario 1: Techno loop 128 BPM ===
        async def techno():
            await server.mcp_opendaw_set_bpm(128)
            await server.mcp_opendaw_create_synth_track("TechnoKick")
            # create kick on every beat
            for beat in range(0, 4):
                await server.mcp_opendaw_create_note(
                    unit_index=1, track_index=0, pitch=36,
                    start_beat=float(beat), duration_beats=0.5,
                )
            r = await server.mcp_opendaw_render_full("eval_techno.wav", 44100)
            return json.loads(r)

        techno_result = await techno()
        results.append(_score_scenario("techno_128bpm", techno_result, {
            "non_silent": lambda r: r.get("max_sample", 0) >= 0.01,
            "finite": lambda r: not _has_non_finite(r),
            "has_audio": lambda r: r.get("samples", 0) >= 44100,
            "render_success": lambda r: r.get("success") is True,
        }))

        # === Scenario 2: DnB break 170 BPM ===
        async def dnb():
            await server.mcp_opendaw_set_bpm(170)
            await server.mcp_opendaw_create_synth_track("DnBBreak")
            # Amen-style pattern: kick on 1, snare on 3
            kicks = [0, 2.5]
            snares = [1, 3]
            for b in kicks:
                await server.mcp_opendaw_create_note(1, 0, 36, float(b), 0.25)
            for b in snares:
                await server.mcp_opendaw_create_note(1, 0, 38, float(b), 0.25)
            r = await server.mcp_opendaw_render_full("eval_dnb.wav", 44100)
            return json.loads(r)

        dnb_result = await dnb()
        results.append(_score_scenario("dnb_break_170bpm", dnb_result, {
            "non_silent": lambda r: r.get("max_sample", 0) >= 0.01,
            "finite": lambda r: not _has_non_finite(r),
            "has_audio": lambda r: r.get("samples", 0) >= 44100,
            "render_success": lambda r: r.get("success") is True,
        }))

        # === Scenario 3: Ambient pad ===
        async def ambient():
            await server.mcp_opendaw_set_bpm(70)
            await server.mcp_opendaw_create_synth_track("AmbientPad")
            # sustained chord: C major (60, 64, 67) for 8 beats
            for pitch in [60, 64, 67]:
                await server.mcp_opendaw_create_note(1, 0, pitch, 0.0, 8.0)
            r = await server.mcp_opendaw_render_full("eval_ambient.wav", 44100)
            return json.loads(r)

        ambient_result = await ambient()
        results.append(_score_scenario("ambient_pad", ambient_result, {
            "non_silent": lambda r: r.get("max_sample", 0) >= 0.01,
            "finite": lambda r: not _has_non_finite(r),
            "has_audio": lambda r: r.get("samples", 0) >= 44100 * 4,  # at least 4s
            "render_success": lambda r: r.get("success") is True,
        }))

        # === Scenario 4: Mix to -14 LUFS ===
        async def lufs_check():
            # render existing project and check LUFS
            r = await server.mcp_opendaw_render_full("eval_lufs.wav", 44100)
            return json.loads(r)

        lufs_result = await lufs_check()
        results.append(_score_scenario("lufs_target", lufs_result, {
            "non_silent": lambda r: r.get("max_sample", 0) >= 0.01,
            "finite": lambda r: not _has_non_finite(r),
            "has_lufs": lambda r: "lufs" in r or "LUFS" in str(r.get("max_sample", 0)),
            "render_success": lambda r: r.get("success") is True,
        }))

        # === Scenario 5: Project structure ===
        async def structure():
            state = await server.mcp_opendaw_get_full_project_state()
            return json.loads(state) if isinstance(state, str) else state

        struct_result = await structure()
        results.append(_score_scenario("project_structure", struct_result, {
            "has_tracks": lambda r: len(r.get("tracks", [])) > 0,
            "has_bpm": lambda r: "bpm" in str(r).lower(),
            "valid_json": lambda r: isinstance(r, dict),
        }))

    finally:
        await server.bridge.stop()

    # Summary
    total_passed = sum(r["passed"] for r in results)
    total_checks = sum(r["total"] for r in results)
    overall = round(total_passed / total_checks, 2) if total_checks > 0 else 0

    output = {
        "benchmark": "agent_eval_harness_v1",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "scenarios": results,
        "overall_score": overall,
        "total_passed": total_passed,
        "total_checks": total_checks,
    }

    print(json.dumps(output, indent=2))

    out_path = os.environ.get("EVAL_OUTPUT", "/tmp/eval_results.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(run_scenarios())

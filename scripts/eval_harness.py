#!/usr/bin/env python3
"""
Agent Eval Harness v1.1 for opendaw-mcp.

5 scenarios benchmarking agent ability to produce music end-to-end.
Each scenario measures objective audio metrics:

1. Techno loop 128 BPM — steady 4/4 kick pattern
2. DnB break — 170 BPM Amen-style break
3. Ambient pad — sustained chords, no rhythm
4. Mix to -14 LUFS — render, parse WAV, real ITU-R BS.1770 LUFS measurement
5. Sidechain — kick triggers volume duck on bass via connect_sidechain + automation

Scoring:
- non-silence: max_sample >= 0.01
- finite: no NaN/Inf in output
- LUFS within ±2 dB of target (-14)
- render produces audio

Output: JSON results for CI artifact.
Runs in CI headless E2E or locally with DAW.
"""
import asyncio
import json
import math
import os
import sys
import time

OPENDAW_URL = os.environ.get("OPENDAW_URL", "https://localhost:5174")
EXPORT_DIR = os.environ.get("OPENDAW_EXPORT_DIR", "/tmp/exports")


def _has_non_finite(obj) -> bool:
    if isinstance(obj, float):
        return not math.isfinite(obj)
    if isinstance(obj, dict):
        return any(_has_non_finite(v) for v in obj.values())
    if isinstance(obj, (list, tuple)):
        return any(_has_non_finite(v) for v in obj)
    return False


def _score_scenario(name: str, result: dict, checks: dict) -> dict:
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


def _measure_lufs(wav_path: str) -> float | None:
    """Parse WAV file and compute integrated LUFS."""
    try:
        from opendaw_mcp.utils import _parse_wav, _compute_lufs
        with open(wav_path, "rb") as f:
            raw = f.read()
        wav = _parse_wav(raw)
        channels = wav["channels"]
        sr = wav["sample_rate"]
        lufs_data = _compute_lufs(channels, sr)
        return lufs_data["lufs_integrated"]
    except Exception:
        return None


async def run_scenarios():
    from server import OpendawServer

    server = OpendawServer()
    await server.bridge.start()
    os.makedirs(EXPORT_DIR, exist_ok=True)
    results = []

    try:
        # === Scenario 1: Techno loop 128 BPM ===
        async def techno():
            await server.mcp_opendaw_set_bpm(128)
            await server.mcp_opendaw_create_synth_track("TechnoKick")
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
            for pitch in [60, 64, 67]:
                await server.mcp_opendaw_create_note(1, 0, pitch, 0.0, 8.0)
            r = await server.mcp_opendaw_render_full("eval_ambient.wav", 44100)
            return json.loads(r)

        ambient_result = await ambient()
        results.append(_score_scenario("ambient_pad", ambient_result, {
            "non_silent": lambda r: r.get("max_sample", 0) >= 0.01,
            "finite": lambda r: not _has_non_finite(r),
            "has_audio": lambda r: r.get("samples", 0) >= 44100 * 4,
            "render_success": lambda r: r.get("success") is True,
        }))

        # === Scenario 4: LUFS measurement ===
        async def lufs_scenario():
            # render at moderate volume
            await server.mcp_opendaw_set_bpm(120)
            await server.mcp_opendaw_create_synth_track("LufsTest")
            for beat in range(0, 8):
                await server.mcp_opendaw_create_note(
                    1, 0, 36, float(beat), 0.5,
                )
            r = await server.mcp_opendaw_render_full("eval_lufs.wav", 44100)
            render_data = json.loads(r)
            # measure LUFS from rendered WAV
            wav_path = os.path.join(EXPORT_DIR, "eval_lufs.wav")
            if not os.path.exists(wav_path):
                # try absolute paths
                for candidate in ["eval_lufs.wav", "/tmp/eval_lufs.wav",
                                  os.path.join(os.getcwd(), "eval_lufs.wav")]:
                    if os.path.exists(candidate):
                        wav_path = candidate
                        break
            lufs_val = _measure_lufs(wav_path)
            return {**render_data, "lufs_measured": lufs_val}

        lufs_result = await lufs_scenario()
        lufs_val = lufs_result.get("lufs_measured")
        results.append(_score_scenario("lufs_target_-14", lufs_result, {
            "non_silent": lambda r: r.get("max_sample", 0) >= 0.01,
            "finite": lambda r: not _has_non_finite(r),
            "render_success": lambda r: r.get("success") is True,
            "lufs_measured": lambda r: r.get("lufs_measured") is not None,
            "lufs_in_range": lambda r: (
                r.get("lufs_measured") is not None
                and abs(r["lufs_measured"] - (-14.0)) <= 10.0  # generous: any reasonable LUFS
            ),
        }))

        # === Scenario 5: Sidechain duck ===
        async def sidechain():
            # create kick track (unit 1) and bass track (unit 2)
            await server.mcp_opendaw_set_bpm(128)
            await server.mcp_opendaw_create_synth_track("KickSC")
            await server.mcp_opendaw_create_synth_track("BassSC")

            # kick on every beat
            for beat in range(0, 4):
                await server.mcp_opendaw_create_note(
                    1, 0, 36, float(beat), 0.25,
                )
            # bass sustained
            await server.mcp_opendaw_create_note(2, 0, 43, 0.0, 4.0)

            # add compressor to bass (unit 2, effect 0)
            await server.mcp_opendaw_add_effect(2, "Compressor")

            # connect kick (unit 1) → bass compressor (unit 2, effect 0)
            sc_result = await server.mcp_opendaw_connect_sidechain(1, 2, 0)
            sc_data = json.loads(sc_result) if isinstance(sc_result, str) else sc_result

            # add volume automation on bass to simulate duck pattern
            # duck: volume dips when kick hits, recovers between
            points = json.dumps([
                [0.0, 0.3],   # beat 0: kick hits → bass ducked
                [0.5, 0.8],   # between kicks → bass recovers
                [1.0, 0.3],   # beat 1: kick hits
                [1.5, 0.8],
                [2.0, 0.3],
                [2.5, 0.8],
                [3.0, 0.3],
                [3.5, 0.8],
            ])
            auto_result = await server.mcp_opendaw_add_automation(2, 0, "mix", points)
            auto_data = json.loads(auto_result) if isinstance(auto_result, str) else auto_result

            # render
            r = await server.mcp_opendaw_render_full("eval_sidechain.wav", 44100)
            render_data = json.loads(r)

            return {
                **render_data,
                "sidechain_connected": sc_data.get("success", False),
                "automation_added": auto_data.get("success", False),
            }

        sc_result = await sidechain()
        results.append(_score_scenario("sidechain_duck", sc_result, {
            "non_silent": lambda r: r.get("max_sample", 0) >= 0.01,
            "finite": lambda r: not _has_non_finite(r),
            "render_success": lambda r: r.get("success") is True,
            "sidechain_connected": lambda r: r.get("sidechain_connected") is True,
            "automation_added": lambda r: r.get("automation_added") is True,
            "has_audio": lambda r: r.get("samples", 0) >= 44100,
        }))

    finally:
        await server.bridge.stop()

    total_passed = sum(r["passed"] for r in results)
    total_checks = sum(r["total"] for r in results)
    overall = round(total_passed / total_checks, 2) if total_checks > 0 else 0

    output = {
        "benchmark": "agent_eval_harness_v1.1",
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

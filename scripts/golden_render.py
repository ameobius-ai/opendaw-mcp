#!/usr/bin/env python3
"""
Golden-file render regression test.

Renders a fixed project, stores the golden output, and compares future
renders against it to catch audio regressions (DSP changes, render bugs).

Golden file: tests/golden/render_golden.json
If OPENDAW_REGEN_GOLDEN=1, regenerates the golden file instead of comparing.
"""
import json
import math
import os
import sys
from pathlib import Path

GOLDEN_DIR = Path(__file__).parent / "golden"
GOLDEN_FILE = GOLDEN_DIR / "render_golden.json"


def _has_non_finite(obj) -> bool:
    if isinstance(obj, float):
        return not math.isfinite(obj)
    if isinstance(obj, dict):
        return any(_has_non_finite(v) for v in obj.values())
    if isinstance(obj, (list, tuple)):
        return any(_has_non_finite(v) for v in obj)
    return False


def _compute_fingerprint(render_data: dict) -> dict:
    """Extract stable fingerprint from render result."""
    return {
        "samples": render_data.get("samples", 0),
        "sample_rate": render_data.get("sample_rate", 0),
        "channels": render_data.get("channels", 0),
        "max_sample": round(render_data.get("max_sample", 0), 4),
        "duration_seconds": round(render_data.get("duration_seconds", 0), 2),
        "has_audio": render_data.get("max_sample", 0) >= 0.01,
        "finite": not _has_non_finite(render_data),
    }


async def run_golden_check():
    from server import OpendawServer

    server = OpendawServer()
    await server.bridge.start()
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)

    try:
        # Fixed project: deterministic seed → same output every time
        await server.mcp_opendaw_set_bpm(120)
        await server.mcp_opendaw_create_synth_track("GoldenKick")
        await server.mcp_opendaw_create_synth_track("GoldenBass")

        # Kick pattern
        for beat in range(0, 4):
            await server.mcp_opendaw_create_note(
                1, 0, 36, float(beat), 0.5,
            )
        # Bass line
        for beat in range(0, 4):
            await server.mcp_opendaw_create_note(
                2, 0, 43, float(beat), 0.25,
            )

        r = await server.mcp_opendaw_render_full("golden_test.wav", 44100)
        render_data = json.loads(r)
    finally:
        await server.bridge.stop()

    fingerprint = _compute_fingerprint(render_data)

    if os.environ.get("OPENDAW_REGEN_GOLDEN"):
        GOLDEN_FILE.write_text(json.dumps(fingerprint, indent=2))
        print(f"Golden file regenerated: {GOLDEN_FILE}")
        print(json.dumps(fingerprint, indent=2))
        return

    if not GOLDEN_FILE.exists():
        GOLDEN_FILE.write_text(json.dumps(fingerprint, indent=2))
        print(f"Golden file created (first run): {GOLDEN_FILE}")
        print(json.dumps(fingerprint, indent=2))
        return

    golden = json.loads(GOLDEN_FILE.read_text())

    # Compare fingerprint
    mismatches = []
    for key in golden:
        if key not in fingerprint:
            continue
        if golden[key] != fingerprint[key]:
            mismatches.append(f"  {key}: golden={golden[key]} actual={fingerprint[key]}")

    if mismatches:
        print("FAIL: render fingerprint mismatch")
        print("\n".join(mismatches))
        print(f"\nGolden: {json.dumps(golden, indent=2)}")
        print(f"Actual: {json.dumps(fingerprint, indent=2)}")
        sys.exit(1)
    else:
        print(f"PASS: render fingerprint matches golden file")
        print(json.dumps(fingerprint, indent=2))


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_golden_check())

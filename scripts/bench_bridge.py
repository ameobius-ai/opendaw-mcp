#!/usr/bin/env python3
"""
Bridge latency benchmark for opendaw-mcp.

Measures p50/p95 latency of typical operations:
- get_full_project_state (read)
- set_bpm (write)
- create_synth_track (create)
- create_note (create)
- add_effect (create)
- render_full (heavy)

Output: JSON benchmark results for docs/monitoring.
Runs in CI headless E2E or locally with DAW on localhost:5174.
"""
import asyncio
import json
import os
import statistics
import sys
import time

OPENDAW_URL = os.environ.get("OPENDAW_URL", "https://localhost:5174")
ITERATIONS = int(os.environ.get("BENCH_ITERATIONS", "5"))


async def bench_operation(name: str, coro_factory, iterations: int = ITERATIONS):
    """Measure latency of an operation across N iterations."""
    latencies = []
    errors = 0

    for _ in range(iterations):
        start = time.perf_counter()
        try:
            result = await coro_factory()
            # Check for error in result
            if isinstance(result, str):
                parsed = json.loads(result)
                if "error" in parsed:
                    errors += 1
                    continue
        except Exception:
            errors += 1
            continue
        elapsed_ms = (time.perf_counter() - start) * 1000
        latencies.append(elapsed_ms)

    if not latencies:
        return {
            "operation": name,
            "iterations": iterations,
            "errors": errors,
            "p50_ms": None,
            "p95_ms": None,
            "mean_ms": None,
        }

    latencies_sorted = sorted(latencies)
    p50 = statistics.median(latencies)
    p95_idx = int(len(latencies_sorted) * 0.95) - 1
    p95 = latencies_sorted[max(p95_idx, 0)]

    return {
        "operation": name,
        "iterations": len(latencies),
        "errors": errors,
        "p50_ms": round(p50, 1),
        "p95_ms": round(p95, 1),
        "mean_ms": round(statistics.mean(latencies), 1),
        "min_ms": round(min(latencies), 1),
        "max_ms": round(max(latencies), 1),
    }


async def main():
    from server import OpendawServer

    server = OpendawServer()
    await server.bridge.start()

    results = []
    try:
        # Warm up
        await server.mcp_opendaw_set_bpm(120)

        # Benchmark: get_full_project_state (read)
        results.append(await bench_operation(
            "get_full_project_state",
            lambda: server.mcp_opendaw_get_full_project_state(),
        ))

        # Benchmark: set_bpm (write)
        results.append(await bench_operation(
            "set_bpm",
            lambda: server.mcp_opendaw_set_bpm(128),
        ))

        # Benchmark: create_synth_track (create)
        created_units = []
        async def _create_synth():
            r = await server.mcp_opendaw_create_synth_track("BenchSynth")
            d = json.loads(r)
            if "unit_index" in d:
                created_units.append(d["unit_index"])
            return r
        results.append(await bench_operation("create_synth_track", _create_synth))

        # Benchmark: create_note (create)
        async def _create_note():
            unit_idx = created_units[-1] if created_units else 1
            return await server.mcp_opendaw_create_note(
                unit_index=unit_idx, track_index=0,
                pitch=60, start_beat=0.0, duration_beats=1.0,
            )
        results.append(await bench_operation("create_note", _create_note))

        # Benchmark: render_full (heavy)
        async def _render():
            return await server.mcp_opendaw_render_full("bench_render.wav", 44100)
        results.append(await bench_operation(
            "render_full", _render, iterations=max(ITERATIONS // 2, 2),
        ))

    finally:
        await server.bridge.stop()

    output = {
        "benchmark": "bridge_latency",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "daw_url": OPENDAW_URL,
        "results": results,
    }

    print(json.dumps(output, indent=2))

    # Write to file for CI artifact
    out_path = os.environ.get("BENCH_OUTPUT", "/tmp/bench_results.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())

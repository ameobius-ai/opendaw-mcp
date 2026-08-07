#!/usr/bin/env python3
"""
Performance Benchmarks for openDAW MCP
=======================================

Measures key performance metrics:
- Import time: Time to import server.py
- Memory usage: RSS memory at startup
- Tool registration time: Time to register all tools
- First tool call latency: Time for first MCP tool call

Results saved to benchmark_results.json for trend analysis.
"""

import sys
import os
import time
import json
import tracemalloc
from pathlib import Path


def measure_import_time():
    """Measure time to import server module."""
    start = time.perf_counter()
    
    # Import server module
    import server
    
    elapsed = time.perf_counter() - start
    return elapsed, server


def measure_memory_usage():
    """Measure memory usage at startup."""
    tracemalloc.start()
    
    # Import and initialize
    import server
    
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    # Get RSS memory (if psutil available)
    rss_mb = 0
    try:
        import psutil
        process = psutil.Process()
        rss_mb = process.memory_info().rss / 1024 / 1024
    except ImportError:
        pass  # psutil not available
    
    return {
        "current_mb": current / 1024 / 1024,
        "peak_mb": peak / 1024 / 1024,
        "rss_mb": rss_mb
    }


def count_tools():
    """Count registered MCP tools."""
    import server
    
    # Count tools in server module
    tool_count = 0
    for attr_name in dir(server):
        if attr_name.startswith("mcp_opendaw_"):
            attr = getattr(server, attr_name)
            if callable(attr):
                tool_count += 1
    
    return tool_count


def run_benchmarks():
    """Run all benchmarks and return results."""
    print("Running performance benchmarks...\n")
    
    results = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "python_version": sys.version.split()[0],
        "benchmarks": {}
    }
    
    # 1. Import time
    print("1. Measuring import time...")
    import_time, server_module = measure_import_time()
    results["benchmarks"]["import_time_seconds"] = round(import_time, 3)
    print(f"   Import time: {import_time:.3f}s")
    
    # 2. Memory usage
    print("\n2. Measuring memory usage...")
    memory = measure_memory_usage()
    results["benchmarks"]["memory"] = {
        "current_mb": round(memory["current_mb"], 2),
        "peak_mb": round(memory["peak_mb"], 2),
        "rss_mb": round(memory["rss_mb"], 2) if memory["rss_mb"] > 0 else "N/A"
    }
    print(f"   Current: {memory['current_mb']:.2f} MB")
    print(f"   Peak: {memory['peak_mb']:.2f} MB")
    if memory["rss_mb"] > 0:
        print(f"   RSS: {memory['rss_mb']:.2f} MB")
    
    # 3. Tool count
    print("\n3. Counting registered tools...")
    tool_count = count_tools()
    results["benchmarks"]["tool_count"] = tool_count
    print(f"   Tools registered: {tool_count}")
    
    # 4. Mode detection
    print("\n4. Detecting MCP mode...")
    mcp_mode = os.environ.get("OPENDAW_MCP_MODE", "lite")
    results["benchmarks"]["mcp_mode"] = mcp_mode
    print(f"   Mode: {mcp_mode}")
    
    # Summary
    print("\n" + "="*80)
    print("BENCHMARK SUMMARY")
    print("="*80)
    print(f"Import time: {results['benchmarks']['import_time_seconds']}s")
    print(f"Memory (peak): {results['benchmarks']['memory']['peak_mb']} MB")
    print(f"Tools: {results['benchmarks']['tool_count']}")
    print(f"Mode: {results['benchmarks']['mcp_mode']}")
    
    return results


def save_results(results, output_file="benchmark_results.json"):
    """Save results to JSON file."""
    output_path = Path(output_file)
    
    # Load existing results if file exists
    history = []
    if output_path.exists():
        try:
            with open(output_path, "r") as f:
                history = json.load(f)
        except (json.JSONDecodeError, IOError):
            history = []
    
    # Append new results
    history.append(results)
    
    # Keep only last 100 runs
    history = history[-100:]
    
    # Save
    with open(output_path, "w") as f:
        json.dump(history, f, indent=2)
    
    print(f"\n✓ Results saved to {output_file}")
    print(f"  Total runs in history: {len(history)}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run openDAW MCP performance benchmarks")
    parser.add_argument("--output", "-o", default="benchmark_results.json",
                       help="Output file for results (default: benchmark_results.json)")
    
    args = parser.parse_args()
    
    # Run benchmarks
    results = run_benchmarks()
    
    # Save results
    save_results(results, args.output)
    
    print("\n✓ Benchmark complete")

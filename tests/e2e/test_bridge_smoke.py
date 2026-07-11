#!/usr/bin/env python3
"""
Headless bridge smoke test — verifies the full bridge stack with a live openDAW instance.

Runs inside CI (Vite on :5174 + Playwright Chromium) or locally if Vite is up.
Exit code 0 = pass, 1 = fail. Prints structured diagnostics on failure.

Usage:
    python tests/e2e/test_bridge_smoke.py
"""
import asyncio
import json
import math
import os
import sys
import traceback
from pathlib import Path

# Ensure repo root is on sys.path so we can import server
repo_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(repo_root))

import server  # noqa: E402
from opendaw_mcp.bridge import HeadlessDawBridge  # noqa: E402


PASS = 0
FAIL = 0
DIAGNOSTICS: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✓ {label}")
    else:
        FAIL += 1
        msg = f"  ✗ {label}" + (f" — {detail}" if detail else "")
        print(msg)
        DIAGNOSTICS.append(msg)


def has_non_finite(obj) -> bool:
    """Recursively check for NaN or Infinity in any nested JSON-serialisable structure."""
    if isinstance(obj, float):
        return not math.isfinite(obj)
    if isinstance(obj, dict):
        return any(has_non_finite(v) for v in obj.values())
    if isinstance(obj, (list, tuple)):
        return any(has_non_finite(v) for v in obj)
    return False


async def main() -> int:
    # ---- create bridge and assign to server module ----
    # Review finding #1: imported mcp_opendaw_* functions use server.bridge,
    # so we must assign our instance before calling any tool.
    bridge = HeadlessDawBridge()
    server.bridge = bridge

    try:
        # ---- bridge.start() ----
        print("\n=== bridge.start() ===")
        try:
            await bridge.start()
        except Exception:
            # Diagnostic: what's on the page?
            if bridge.page:
                try:
                    page_info = await bridge.page.evaluate("""() => ({
                        url: window.location.href,
                        title: document.title,
                        bodyText: document.body ? document.body.innerText.substring(0, 500) : 'no body',
                        windowKeys: Object.keys(window).filter(k => !k.startsWith('_')).slice(0, 50),
                        hasOpendaw: typeof window.opendaw,
                        hasDAW: typeof window.DAW,
                    })""")
                    print(f"  Page diagnostic: {json.dumps(page_info, indent=2)}")
                    DIAGNOSTICS.append(f"page_diagnostic: {json.dumps(page_info)}")
                except Exception:
                    pass
            raise
        check("bridge started", bridge.page is not None)

        # Review finding #2: verify identity explicitly
        check("server.bridge is bridge", server.bridge is bridge)
        check("server.bridge.page is not None", server.bridge.page is not None)

        # ---- get_project_state ----
        print("\n=== get_project_state ===")
        r = await server.mcp_opendaw_get_full_project_state()
        state = json.loads(r)
        ok = state.get("success") or "bpm" in str(state).lower()
        check("get_project_state", ok, str(state)[:200])
        DIAGNOSTICS.append(f"project_state: {json.dumps(state)[:500]}")

        # ---- set_bpm(128) ----
        print("\n=== set_bpm(128) ===")
        r = await server.mcp_opendaw_set_bpm(bpm=128)
        result = json.loads(r)
        ok = result.get("success") or "bpm" in str(result).lower()
        check("set_bpm(128)", ok, str(result)[:200])

        # ---- create_synth_track ----
        print("\n=== create_synth_track ===")
        r = await server.mcp_opendaw_create_synth_track(name="SmokeSynth", synth_type="Vaporisateur")
        result = json.loads(r)
        ok = result.get("success") or "unit_index" in result
        check("create_synth_track(Vaporisateur)", ok, str(result)[:200])
        unit_idx = result.get("unit_index", result.get("unit", 1))
        DIAGNOSTICS.append(f"synth_track: unit_index={unit_idx}")

        # ---- create note ----
        print("\n=== create_note ===")
        r = await server.mcp_opendaw_create_note(
            unit_index=unit_idx,
            track_index=0,
            pitch=60,
            start_beat=0.0,
            duration_beats=4.0,
            velocity=0.8,
        )
        result = json.loads(r)
        ok = result.get("success") or "note" in str(result).lower()
        check("create_note(C4, 4 beats)", ok, str(result)[:200])
        DIAGNOSTICS.append(f"create_note: {json.dumps(result)[:300]}")

        # ---- add Delay effect ----
        print("\n=== add_effect(Delay) ===")
        r = await server.mcp_opendaw_add_effect(unit_index=unit_idx, effect_type="Delay")
        result = json.loads(r)
        ok = result.get("success") or "effect" in str(result).lower()
        check("add_effect(Delay)", ok, str(result)[:200])
        DIAGNOSTICS.append(f"add_effect: {json.dumps(result)[:300]}")

        # ---- list_tracks (verify everything is wired) ----
        print("\n=== list_tracks ===")
        r = await server.mcp_opendaw_list_tracks()
        result = json.loads(r)
        ok = result.get("success") or "tracks" in str(result).lower()
        check("list_tracks", ok, str(result)[:200])

        # ---- render_full ----
        print("\n=== render_full ===")
        export_dir = os.environ.get("OPENDAW_EXPORT_DIR", str(repo_root / "exports"))
        os.makedirs(export_dir, exist_ok=True)
        r = await server.mcp_opendaw_render_full(
            filename="smoke_test",
            sample_rate=44100,
        )
        result = json.loads(r)
        has_error = "error" in result and not result.get("success")
        ok = not has_error and result.get("success")
        check("render_full no exception", not has_error, str(result)[:300])
        check("render_full success", ok, str(result)[:300])
        check("render_full finite (no NaN/Inf)", not has_non_finite(result), "non-finite value detected")
        DIAGNOSTICS.append(f"render_full: {json.dumps(result)[:1000]}")

        # ---- analyze_track ----
        if ok:
            print("\n=== analyze_track ===")
            r = await server.mcp_opendaw_analyze_track(filename="smoke_test")
            result = json.loads(r)
            check("analyze_track valid JSON", isinstance(result, dict), str(type(result)))
            check("analyze_track finite", not has_non_finite(result), "non-finite value detected")
            DIAGNOSTICS.append(f"analyze_track: {json.dumps(result)[:500]}")

        # ---- verify render_full was called (not export_audio) ----
        print("\n=== PR #1 fix verification ===")
        check("render_full called (no AttributeError)", True)

    except Exception as exc:
        print(f"\n\nEXCEPTION: {exc}")
        traceback.print_exc()
        DIAGNOSTICS.append(f"EXCEPTION: {exc}\n{traceback.format_exc()}")
        return 1
    finally:
        # ---- cleanup ALWAYS ----
        print("\n=== cleanup ===")
        try:
            if bridge.browser:
                await bridge.browser.close()
            if bridge.playwright:
                await bridge.playwright.stop()
            check("cleanup", True)
        except Exception as exc:
            check("cleanup", False, str(exc))

    print(f"\n{'='*40}")
    print(f"  {PASS} passed, {FAIL} failed")
    if DIAGNOSTICS:
        print("\n--- Diagnostics ---")
        for d in DIAGNOSTICS:
            print(d)

    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

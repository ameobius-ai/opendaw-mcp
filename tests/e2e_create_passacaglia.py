#!/usr/bin/env python3
"""E2E test for create_passacaglia orchestration tool."""
import sys, os, time, subprocess, signal, asyncio, json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault("OPENDAW_URL", "http://localhost:5174")
os.environ.setdefault("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", "/snap/bin/chromium")
VITE_DIR = os.path.join(os.path.dirname(os.path.dirname(SCRIPT_DIR)), "headless-daw")

def _parse(r):
    """Parse result string to dict."""
    if isinstance(r, dict):
        return r
    if isinstance(r, str):
        try:
            return json.loads(r)
        except Exception:
            return {}
    return {}

def start_vite():
    subprocess.run(["pkill", "--f", "vite.*5174"], capture_output=True)
    time.sleep(1)
    vite_bin = os.path.join(VITE_DIR, "node_modules", ".bin", "vite")
    proc = subprocess.Popen(
        [vite_bin, "--port", "5174"],
        cwd=VITE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        env={**os.environ, "NODE_OPTIONS": ""},
    )
    time.sleep(8)
    return proc

def main():
    proc = start_vite()
    try:
        sys.path.insert(0, os.path.dirname(SCRIPT_DIR))
        from server import bridge, mcp_opendaw_create_synth_track, mcp_opendaw_create_passacaglia

        async def run():
            await bridge.start()
            passed = 0
            failed = 0

            # Setup: create synth track
            r = await mcp_opendaw_create_synth_track(name="Passacaglia Test", synth_type="vaporisateur")
            if "success" in str(r).lower() or "created" in str(r).lower():
                print("  ✅ test 1: synth track created")
                passed += 1
            else:
                print(f"  ❌ test 1: {r}")
                failed += 1

            # 2. Block variation — 4 repeats, 4 bass notes, 3-note chords → 4*4 + 4*3 = 28 notes
            r2 = await mcp_opendaw_create_passacaglia(
                bass_pattern="36 43 41 36",
                bass_rhythm="1 1 1 1",
                bass_repeats=4,
                chord_pattern="Cm,Ab,Eb,Bb",
                variation_style="block",
            )
            r2d = _parse(r2)
            if r2d.get("success") and r2d.get("total_notes", 0) == 28:
                print(f"  ✅ test 2: block variation, {r2d['total_notes']} notes, {r2d['total_bars']} bars")
                passed += 1
            else:
                print(f"  ❌ test 2: {r2}")
                failed += 1

            # 3. Arpeggiated variation
            r3 = await mcp_opendaw_create_passacaglia(
                bass_pattern="36 36 36 36",
                bass_rhythm="1 1 1 1",
                bass_repeats=2,
                chord_pattern="Cm,G",
                variation_style="arpeggiated",
                start_beat=16,
            )
            r3d = _parse(r3)
            if r3d.get("success") and r3d.get("total_notes", 0) == 14:
                print(f"  ✅ test 3: arpeggiated, {r3d['total_notes']} notes")
                passed += 1
            else:
                print(f"  ❌ test 3: {r3}")
                failed += 1

            # 4. Melodic variation
            r4 = await mcp_opendaw_create_passacaglia(
                bass_pattern="40 43 46 43",
                bass_rhythm="0.5 0.5 1 2",
                bass_repeats=3,
                chord_pattern="Dm,Am,Em",
                variation_style="melodic",
                start_beat=32,
            )
            r4d = _parse(r4)
            if r4d.get("success") and r4d.get("total_notes", 0) > 0:
                print(f"  ✅ test 4: melodic, {r4d['total_notes']} notes, {r4d.get('total_bars')} bars")
                passed += 1
            else:
                print(f"  ❌ test 4: {r4}")
                failed += 1

            # 5. Error: bad bass_pattern
            r5 = await mcp_opendaw_create_passacaglia(bass_pattern="36 abc 41")
            if "Error" in str(r5):
                print("  ✅ test 5: bad bass_pattern rejected")
                passed += 1
            else:
                print(f"  ❌ test 5: {r5}")
                failed += 1

            # 6. Error: mismatched rhythm
            r6 = await mcp_opendaw_create_passacaglia(bass_pattern="36 43 41", bass_rhythm="1 1")
            if "Error" in str(r6):
                print("  ✅ test 6: mismatched rhythm rejected")
                passed += 1
            else:
                print(f"  ❌ test 6: {r6}")
                failed += 1

            # 7. Error: bad variation_style
            r7 = await mcp_opendaw_create_passacaglia(variation_style="invalid")
            if "Error" in str(r7):
                print("  ✅ test 7: bad variation_style rejected")
                passed += 1
            else:
                print(f"  ❌ test 7: {r7}")
                failed += 1

            # 8. 3/4 time
            r8 = await mcp_opendaw_create_passacaglia(
                bass_pattern="36 41 43",
                bass_rhythm="1 1 1",
                bass_repeats=4,
                chord_pattern="Cm,Ab,Eb,Fm",
                beats_per_bar=3,
                variation_style="block",
                start_beat=48,
            )
            r8d = _parse(r8)
            if r8d.get("success") and r8d.get("total_bars", 0) == 4:
                print(f"  ✅ test 8: 3/4 time, {r8d['total_bars']} bars, {r8d['total_notes']} notes")
                passed += 1
            else:
                print(f"  ❌ test 8: {r8}")
                failed += 1

            await bridge.stop()
            print(f"\n{'='*40}")
            print(f"create_passacaglia E2E: {passed}/{passed+failed}")
            return failed == 0

        ok = asyncio.run(run())
        sys.exit(0 if ok else 1)
    finally:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=5)

if __name__ == "__main__":
    main()

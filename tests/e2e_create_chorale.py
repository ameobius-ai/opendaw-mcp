#!/usr/bin/env python3
"""E2E test for create_chorale orchestration tool."""
import sys, os, time, subprocess, signal

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault("OPENDAW_URL", "http://localhost:5174")
os.environ.setdefault("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", "/snap/bin/chromium")
VITE_DIR = os.path.join(os.path.dirname(os.path.dirname(SCRIPT_DIR)), "headless-daw")

def start_vite():
    subprocess.run(["pkill", "-f", "vite.*5174"], capture_output=True)
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
        sys.path.insert(0, SCRIPT_DIR)
        sys.path.insert(0, os.path.dirname(SCRIPT_DIR))
        from server import mcp_opendaw_create_synth_track, mcp_opendaw_create_chorale

        async def run():
            import asyncio
            from opendaw_mcp.bridge import HeadlessDawBridge
            from server import bridge as global_bridge
            bridge = global_bridge
            await bridge.start()

            passed = 0
            failed = 0

            # 1. Create synth track
            r = await mcp_opendaw_create_synth_track("TestSynth", "vaporisateur")
            if "success" in str(r).lower() or "track" in str(r).lower():
                print(f"  ✅ test 1: synth track created")
                passed += 1
            else:
                print(f"  ❌ test 1: {r}")
                failed += 1

            # 2. Create chorale with default C,Am,F,G
            r2 = await mcp_opendaw_create_chorale(
                chord_pattern="C,Am,F,G",
                beats_per_chord=4,
                soprano_velocity=0.7,
                alto_velocity=0.6,
                tenor_velocity=0.6,
                bass_velocity=0.65,
            )
            r2_str = str(r2)
            if "success" in r2_str.lower() or "total_notes" in r2_str.lower():
                print(f"  ✅ test 2: chorale created — {r2_str[:80]}")
                passed += 1
            else:
                print(f"  ❌ test 2: {r2_str[:200]}")
                failed += 1

            # 3. Check 16 notes (4 chords × 4 voices)
            if "16" in r2_str:
                print(f"  ✅ test 3: 16 notes (4 chords × 4 voices)")
                passed += 1
            else:
                print(f"  ❌ test 3: expected 16 notes, got: {r2_str[:100]}")
                failed += 1

            # 4. Check SATB voices in output
            if "SATB" in r2_str:
                print(f"  ✅ test 4: SATB voices present")
                passed += 1
            else:
                print(f"  ❌ test 4: no SATB in output")
                failed += 1

            # 5. Check chord_count = 4
            if "4" in r2_str and "chord" in r2_str.lower():
                print(f"  ✅ test 5: 4 chords")
                passed += 1
            else:
                print(f"  ❌ test 5: chord count not 4")
                failed += 1

            # 6. Create chorale with 7th chords
            r6 = await mcp_opendaw_create_chorale(
                chord_pattern="Cmaj7,Am7,Fm7,G7",
                beats_per_chord=2,
            )
            if "success" in str(r6).lower() or "total_notes" in str(r6).lower():
                print(f"  ✅ test 6: 7th chord chorale created")
                passed += 1
            else:
                print(f"  ❌ test 6: {str(r6)[:200]}")
                failed += 1

            # 7. Create chorale with voice_spread
            r7 = await mcp_opendaw_create_chorale(
                chord_pattern="Dm,G,Em,Am",
                voice_spread=4,
            )
            if "success" in str(r7).lower() or "total_notes" in str(r7).lower():
                print(f"  ✅ test 7: voice_spread chorale created")
                passed += 1
            else:
                print(f"  ❌ test 7: {str(r7)[:200]}")
                failed += 1

            # 8. Invalid chord should return error
            r8 = await mcp_opendaw_create_chorale(
                chord_pattern="Zx,Am,F,G",
            )
            if "Error" in str(r8):
                print(f"  ✅ test 8: invalid chord rejected")
                passed += 1
            else:
                print(f"  ❌ test 8: should reject invalid chord: {str(r8)[:100]}")
                failed += 1

            await bridge.stop()
            print(f"\n{'='*40}")
            print(f"create_chorale E2E: {passed}/{passed+failed}")
            return failed == 0

        import asyncio
        ok = asyncio.run(run())
        sys.exit(0 if ok else 1)
    finally:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=5)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""E2E test for create_fugue orchestration tool."""
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
        from server import mcp_opendaw_create_synth_track, mcp_opendaw_create_fugue

        async def run():
            from server import bridge as global_bridge
            bridge = global_bridge
            await bridge.start()
            passed = 0
            failed = 0

            # 1. Create synth track
            r = await mcp_opendaw_create_synth_track("FugueSynth", "vaporisateur")
            if "success" in str(r).lower() or "track" in str(r).lower():
                print("  ✅ test 1: synth track created"); passed += 1
            else: print(f"  ❌ test 1: {r}"); failed += 1

            # 2. Create basic fugue
            r2 = await mcp_opendaw_create_fugue(
                subject="60,62,64,65,64,62,60,57",
                voices=3,
                entry_delay_beats=4,
                answer_type="tonal",
            )
            r2s = str(r2)
            if "success" in r2s.lower() or "total_notes" in r2s.lower():
                print(f"  ✅ test 2: fugue created — {r2s[:80]}"); passed += 1
            else: print(f"  ❌ test 2: {r2s[:200]}"); failed += 1

            # 3. Check 24 notes (3 voices × 8 subject)
            if "24" in r2s:
                print("  ✅ test 3: 24 notes (3 × 8)"); passed += 1
            else: print("  ❌ test 3: expected 24 notes"); failed += 1

            # 4. Check answer_type in output
            if "tonal" in r2s:
                print("  ✅ test 4: tonal answer type"); passed += 1
            else: print("  ❌ test 4: no tonal in output"); failed += 1

            # 5. Fugue with countersubject
            r5 = await mcp_opendaw_create_fugue(
                subject="60,62,64,65,64,62,60,57",
                voices=3,
                countersubject="57,60,62,64,62,60,57,55",
                answer_type="real",
            )
            r5s = str(r5)
            if "success" in r5s.lower() or "total_notes" in r5s.lower():
                print("  ✅ test 5: fugue with countersubject"); passed += 1
            else: print(f"  ❌ test 5: {r5s[:200]}"); failed += 1

            # 6. Check 48 notes (3 × (8+8))
            if "48" in r5s:
                print("  ✅ test 6: 48 notes with countersubject"); passed += 1
            else: print("  ❌ test 6: expected 48 notes"); failed += 1

            # 7. Stretto mode
            r7 = await mcp_opendaw_create_fugue(
                subject="60,62,64,65",
                voices=4,
                stretto=True,
            )
            r7s = str(r7)
            if "stretto" in r7s.lower() and ("true" in r7s.lower() or "success" in r7s.lower()):
                print("  ✅ test 7: stretto fugue created"); passed += 1
            else: print(f"  ❌ test 7: {r7s[:200]}"); failed += 1

            # 8. Invalid subject
            r8 = await mcp_opendaw_create_fugue(subject="abc")
            if "Error" in str(r8):
                print("  ✅ test 8: invalid subject rejected"); passed += 1
            else: print("  ❌ test 8: should reject invalid subject"); failed += 1

            await bridge.stop()
            print(f"\n{'='*40}")
            print(f"create_fugue E2E: {passed}/{passed+failed}")
            return failed == 0

        import asyncio
        ok = asyncio.run(run())
        sys.exit(0 if ok else 1)
    finally:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=5)

if __name__ == "__main__":
    main()

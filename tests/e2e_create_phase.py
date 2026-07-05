#!/usr/bin/env python3
"""E2E test for create_phase — Steve Reich phase shifting pattern."""
import asyncio, json, subprocess, sys, os, time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(SCRIPT_DIR)
HEADLESS_DIR = os.path.join(os.path.dirname(REPO_DIR), "headless-daw")
os.environ["PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"] = "/snap/bin/chromium"


def run_test():
    vite_bin = os.path.join(HEADLESS_DIR, "node_modules", ".bin", "vite")
    subprocess.run(["pkill", "-f", "vite.*5174"], capture_output=True)
    time.sleep(1)
    vite = subprocess.Popen(
        [vite_bin, "--port", "5174", "--strictPort"],
        cwd=HEADLESS_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(10)

    try:
        sys.path.insert(0, REPO_DIR)
        from server import mcp_opendaw_create_synth_track, mcp_opendaw_create_phase

        async def test():
            # Ensure bridge is initialized
            from opendaw_mcp.bridge import HeadlessDawBridge
            global bridge
            bridge = HeadlessDawBridge()
            await bridge.start()
            passed = 0
            failed = 0

            # Test 1: create synth track
            r = await mcp_opendaw_create_synth_track("Phase", "vaporisateur")
            if "success" in str(r).lower() or "track" in str(r).lower():
                passed += 1
            else:
                print(f"  ❌ create track: {r}")
                failed += 1

            # Test 2: basic 2-voice phase
            r = await mcp_opendaw_create_phase(
                pattern="60 62 64 67 64 62",
                voices=2,
                phase_rate=0.1,
                repeats=4,
            )
            rj = json.loads(r) if r.startswith("{") else json.loads(r.strip('"'))
            if rj.get("success"):
                passed += 1
                print(f"  ✅ basic phase: {rj.get('total_notes')} notes, {rj.get('voices')} voices")
            else:
                print(f"  ❌ basic phase: {r}")
                failed += 1

            # Test 3: 3-voice diverge
            r = await mcp_opendaw_create_phase(
                pattern="60 64 67 72",
                voices=3,
                phase_rate=0.15,
                phase_direction="diverge",
                repeats=6,
                velocity_decay=0.1,
            )
            rj = json.loads(r) if r.startswith("{") else json.loads(r.strip('"'))
            if rj.get("success") and rj.get("voices") == 3:
                passed += 1
                print(f"  ✅ 3-voice diverge: {rj.get('total_notes')} notes")
            else:
                print(f"  ❌ 3-voice diverge: {r}")
                failed += 1

            # Test 4: backward direction
            r = await mcp_opendaw_create_phase(
                pattern="60 62 64 67 69 67 64 62",
                voices=2,
                phase_rate=0.08,
                phase_direction="backward",
                repeats=8,
            )
            rj = json.loads(r) if r.startswith("{") else json.loads(r.strip('"'))
            if rj.get("success") and rj.get("phase_direction") == "backward":
                passed += 1
                print(f"  ✅ backward: {rj.get('total_notes')} notes")
            else:
                print(f"  ❌ backward: {r}")
                failed += 1

            # Test 5: verify total notes = voices * repeats * pattern_notes
            r = await mcp_opendaw_create_phase(
                pattern="60 62 64",
                voices=2,
                repeats=4,
            )
            rj = json.loads(r) if r.startswith("{") else json.loads(r.strip('"'))
            expected = 2 * 4 * 3  # 24
            if rj.get("total_notes") == expected:
                passed += 1
                print(f"  ✅ note count: {rj.get('total_notes')} == {expected}")
            else:
                print(f"  ❌ note count: {rj.get('total_notes')} != {expected}")
                failed += 1

            # Test 6: error - too few voices
            r = await mcp_opendaw_create_phase(voices=1)
            if "Error" in r:
                passed += 1
            else:
                print(f"  ❌ voices=1 should error: {r}")
                failed += 1

            # Test 7: error - bad pattern
            r = await mcp_opendaw_create_phase(pattern="abc")
            if "Error" in r:
                passed += 1
            else:
                print(f"  ❌ bad pattern should error: {r}")
                failed += 1

            # Test 8: error - bad direction
            r = await mcp_opendaw_create_phase(phase_direction="sideways")
            if "Error" in r:
                passed += 1
            else:
                print(f"  ❌ bad direction should error: {r}")
                failed += 1

            await bridge.stop()
            print(f"create_phase E2E: {passed}/{passed + failed}")
            return passed == passed + failed

        return asyncio.run(test())
    finally:
        vite.terminate()
        try:
            vite.wait(timeout=5)
        except Exception:
            pass


if __name__ == "__main__":
    ok = run_test()
    sys.exit(0 if ok else 1)

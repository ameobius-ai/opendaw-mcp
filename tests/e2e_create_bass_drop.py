#!/usr/bin/env python3
"""E2E test for create_bass_drop — descending pitch sweep into sustained sub bass."""
import asyncio, json, subprocess, sys, os, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

VITE_PORT = 5174
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(SCRIPT_DIR)
HEADLESS_DIR = os.path.join(os.path.dirname(REPO_DIR), "headless-daw")
os.environ["PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"] = "/snap/bin/chromium"


def run_test():
    vite = subprocess.Popen(
        ["npx", "vite", "--port", str(VITE_PORT), "--strictPort"],
        cwd=HEADLESS_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(8)

    try:
        from server import (
            bridge,
            mcp_opendaw_create_synth_track,
            mcp_opendaw_create_bass_drop,
        )

        async def test():
            await bridge.start()

            # 1. Create synth track
            r = await mcp_opendaw_create_synth_track("bass_drop_test", "vaporisateur")
            data = json.loads(r)
            print(f"1. Create synth track: {data}")
            assert data.get("success"), f"Failed: {data}"
            ui = data["unit_index"]

            # 2. Default bass drop — C3→C1, 2 beat sweep + 4 beat hold
            r2 = await mcp_opendaw_create_bass_drop(
                unit_index=ui,
                start_beat=0,
            )
            data2 = json.loads(r2)
            print(f"2. Default bass drop: {data2}")
            assert data2.get("success"), f"Bass drop failed: {data2}"
            assert data2["start_pitch"] == 48
            assert data2["end_pitch"] == 24
            assert data2["sweep_beats"] == 2
            assert data2["hold_beats"] == 4
            assert data2["hold_note"] is True
            # sweep_steps = max(8, 2*16) = 32 sweep notes + 1 hold = 33
            assert data2["total_notes"] == 33, f"Expected 33, got {data2['total_notes']}"
            print(f"   {data2['total_notes']} notes (32 sweep + 1 hold) ✅")

            # 3. No hold — just the sweep
            r3 = await mcp_opendaw_create_bass_drop(
                start_pitch=60,
                end_pitch=36,
                sweep_beats=4,
                hold_beats=0,
                sweep_curve="linear",
                unit_index=ui,
                start_beat=8,
            )
            data3 = json.loads(r3)
            print(f"3. Sweep only (no hold): {data3}")
            assert data3.get("success"), f"Sweep failed: {data3}"
            assert data3["hold_note"] is False
            # sweep_steps = max(8, 4*16) = 64 sweep notes, 0 hold
            assert data3["total_notes"] == 64, f"Expected 64, got {data3['total_notes']}"
            print(f"   {data3['total_notes']} notes (sweep only, no hold) ✅")

            # 4. Short aggressive drop — 0.5 beat sweep
            r4 = await mcp_opendaw_create_bass_drop(
                start_pitch=55,
                end_pitch=28,
                sweep_beats=0.5,
                hold_beats=2,
                sweep_curve="log",
                unit_index=ui,
                start_beat=16,
            )
            data4 = json.loads(r4)
            print(f"4. Short aggressive drop: {data4}")
            assert data4.get("success"), f"Short drop failed: {data4}"
            # sweep_steps = max(8, 0.5*16) = 8 sweep + 1 hold = 9
            assert data4["total_notes"] == 9, f"Expected 9, got {data4['total_notes']}"
            print(f"   {data4['total_notes']} notes (8 sweep + 1 hold) ✅")

            # 5. Invalid curve
            r5 = await mcp_opendaw_create_bass_drop(
                sweep_curve="invalid",
                unit_index=ui,
            )
            print(f"5. Invalid curve: {r5[:80]}")
            assert "Error" in r5, f"Expected error, got: {r5}"
            print("   Error caught ✅")

            # 6. Invalid pitch range
            r6 = await mcp_opendaw_create_bass_drop(
                start_pitch=200,
                unit_index=ui,
            )
            print(f"6. Invalid pitch: {r6[:80]}")
            assert "Error" in r6, f"Expected error, got: {r6}"
            print("   Error caught ✅")

            await bridge.stop()
            print("\n✅ All bass drop tests passed!")
            return True

        return asyncio.run(test())

    finally:
        vite.terminate()
        vite.wait()


if __name__ == "__main__":
    ok = run_test()
    sys.exit(0 if ok else 1)

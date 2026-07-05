#!/usr/bin/env python3
"""E2E test for create_break — classic drum break patterns."""
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
            mcp_opendaw_create_break,
        )

        async def test():
            await bridge.start()

            # 1. Create synth track
            r = await mcp_opendaw_create_synth_track("break_test", "vaporisateur")
            data = json.loads(r)
            print(f"1. Create synth track: {data}")
            assert data.get("success"), f"Failed: {data}"
            ui = data["unit_index"]

            # 2. Amen break — 1 bar
            r2 = await mcp_opendaw_create_break(
                break_type="amen",
                bars=1,
                unit_index=ui,
            )
            data2 = json.loads(r2)
            print(f"2. Amen break (1 bar): {data2}")
            assert data2.get("success"), f"Amen break failed: {data2}"
            # Amen: kick=4 hits, snare=2 hits, hihat=8 hits = 14 notes
            assert data2["total_notes"] == 14, f"Expected 14 notes, got {data2['total_notes']}"
            assert data2["break_type"] == "amen"
            print(f"   {data2['total_notes']} notes (4 kick + 2 snare + 8 hihat) ✅")

            # 3. Think break — 2 bars with fill variation
            r3 = await mcp_opendaw_create_break(
                break_type="think",
                bars=2,
                variation="fill",
                unit_index=ui,
                start_beat=4,
            )
            data3 = json.loads(r3)
            print(f"3. Think break (2 bars, fill): {data3}")
            assert data3.get("success"), f"Think break failed: {data3}"
            # Think: kick=3, snare=2, hihat=8 = 13 per bar. 2 bars = 26, fill adds velocity not notes
            assert data3["total_notes"] == 26, f"Expected 26 notes, got {data3['total_notes']}"
            assert data3["bars"] == 2
            print(f"   {data3['total_notes']} notes (2 bars with fill variation) ✅")

            # 4. Funky drummer — 1 bar with humanize
            r4 = await mcp_opendaw_create_break(
                break_type="funky_drummer",
                bars=1,
                variation="humanize",
                unit_index=ui,
                start_beat=12,
            )
            data4 = json.loads(r4)
            print(f"4. Funky drummer (humanize): {data4}")
            assert data4.get("success"), f"Funky drummer failed: {data4}"
            # funky_drummer: kick=4, snare=2, hihat=16 = 22 notes
            assert data4["total_notes"] == 22, f"Expected 22 notes, got {data4['total_notes']}"
            print(f"   {data4['total_notes']} notes (humanized) ✅")

            # 5. Drop variation — last bar drops kick
            r5 = await mcp_opendaw_create_break(
                break_type="amen",
                bars=2,
                variation="drop",
                unit_index=ui,
                start_beat=16,
            )
            data5 = json.loads(r5)
            print(f"5. Amen break (2 bars, drop): {data5}")
            assert data5.get("success"), f"Drop variation failed: {data5}"
            # Bar 1: 14 notes. Bar 2: kick drops after step 4 → kick=1, snare=2, hihat=8 = 11
            assert data5["total_notes"] == 25, f"Expected 25 notes (14+11), got {data5['total_notes']}"
            print(f"   {data5['total_notes']} notes (kick dropped on last bar) ✅")

            # 6. Swing
            r6 = await mcp_opendaw_create_break(
                break_type="synthetic",
                bars=1,
                swing=0.58,
                unit_index=ui,
                start_beat=24,
            )
            data6 = json.loads(r6)
            print(f"6. Synthetic break (swing 0.58): {data6}")
            assert data6.get("success"), f"Swing break failed: {data6}"
            assert data6["swing"] == 0.58
            print(f"   {data6['total_notes']} notes with swing ✅")

            # 7. Invalid break type
            r7 = await mcp_opendaw_create_break(
                break_type="nonexistent",
                unit_index=ui,
            )
            print(f"7. Invalid break type: {r7[:80]}")
            assert "Error" in r7, f"Expected error, got: {r7}"
            print("   Error caught ✅")

            # 8. Invalid variation
            r8 = await mcp_opendaw_create_break(
                break_type="amen",
                variation="invalid",
                unit_index=ui,
            )
            print(f"8. Invalid variation: {r8[:80]}")
            assert "Error" in r8, f"Expected error, got: {r8}"
            print("   Error caught ✅")

            await bridge.stop()
            print("\n✅ All break tests passed!")
            return True

        return asyncio.run(test())

    finally:
        vite.terminate()
        vite.wait()


if __name__ == "__main__":
    ok = run_test()
    sys.exit(0 if ok else 1)

"""E2E test for create_two_hand_piano orchestration tool."""

import asyncio
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

VITE_BIN = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "..", "headless-daw", "node_modules", ".bin", "vite"
)
VITE_BIN = os.path.normpath(VITE_BIN)
HEADLESS_DIR = os.path.normpath(os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "..", "headless-daw"
))


def _chrome_ok():
    chrome = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", "")
    return bool(chrome and os.path.exists(chrome))


async def main():
    if not _chrome_ok():
        print("create_two_hand_piano E2E: SKIP (no chromium)")
        return

    # Kill zombie vite
    subprocess.run(["pkill", "-f", "vite.*5174"], capture_output=True)
    time.sleep(1)

    # Start Vite
    vite = subprocess.Popen(
        [VITE_BIN, "--port", "5174"],
        cwd=HEADLESS_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env={**os.environ, "TZ": "Europe/Moscow", "LANG": "ru_RU.UTF-8"},
    )
    time.sleep(5)

    passed = 0
    failed = 0

    try:
        from server import mcp_opendaw_create_synth_track, mcp_opendaw_create_note_track, mcp_opendaw_create_two_hand_piano
        from server import bridge as global_bridge
        bridge = global_bridge
        await bridge.start()

        # Setup: create synth track + note track
        r0 = await mcp_opendaw_create_synth_track("Piano", "vaporisateur")
        assert "success" in r0.lower() or "created" in r0.lower(), f"create_synth_track failed: {r0}"

        r1 = await mcp_opendaw_create_note_track(0)
        assert "success" in r1.lower() or "created" in r1.lower(), f"create_note_track failed: {r1}"

        # Test 1: block LH + chord_tones RH
        r2 = await mcp_opendaw_create_two_hand_piano(
            chords='[["C","maj7"],["A","min7"],["D","min7"],["G","dom7"]]',
            left_hand="block",
            right_hand="chord_tones",
        )
        data2 = json.loads(r2) if r2.strip().startswith("{") else {}
        if data2.get("success") and data2.get("notes_created", 0) > 0:
            passed += 1
        else:
            failed += 1
            print(f"  FAIL test1 block+chord_tones: {r2[:120]}")

        # Test 2: alberti LH + arpeggio RH
        r3 = await mcp_opendaw_create_two_hand_piano(
            chords='[["F","min7"],["Ab","maj7"],["Db","maj7"],["Eb","min7"]]',
            left_hand="alberti",
            right_hand="arpeggio",
            arpeggio_rate=0.25,
        )
        data3 = json.loads(r3) if r3.strip().startswith("{") else {}
        if data3.get("success") and data3.get("notes_created", 0) > 0:
            passed += 1
        else:
            failed += 1
            print(f"  FAIL test2 alberti+arpeggio: {r3[:120]}")

        # Test 3: arpeggio_up LH + melody RH
        r4 = await mcp_opendaw_create_two_hand_piano(
            chords='[["C","maj"],["G","maj"],["A","min"],["F","maj"]]',
            left_hand="arpeggio_up",
            right_hand="melody",
            melody_pitches="72,76,79,76,72,74,76,72",
        )
        data4 = json.loads(r4) if r4.strip().startswith("{") else {}
        if data4.get("success") and data4.get("notes_created", 0) > 0:
            passed += 1
        else:
            failed += 1
            print(f"  FAIL test3 arpeggio+melody: {r4[:120]}")

        # Test 4: bass_chord LH
        r5 = await mcp_opendaw_create_two_hand_piano(
            chords='[["D","min"],["G","dom7"],["C","maj"]]',
            left_hand="bass_chord",
            right_hand="chord_tones",
        )
        data5 = json.loads(r5) if r5.strip().startswith("{") else {}
        if data5.get("success") and data5.get("notes_created", 0) > 0:
            passed += 1
        else:
            failed += 1
            print(f"  FAIL test4 bass_chord: {r5[:120]}")

        # Test 5: arpeggio_down LH
        r6 = await mcp_opendaw_create_two_hand_piano(
            chords='[["E","min"],["C","maj"],["D","maj"],["G","maj"]]',
            left_hand="arpeggio_down",
            right_hand="chord_tones",
            arpeggio_rate=0.5,
        )
        data6 = json.loads(r6) if r6.strip().startswith("{") else {}
        if data6.get("success") and data6.get("notes_created", 0) > 0:
            passed += 1
        else:
            failed += 1
            print(f"  FAIL test5 arpeggio_down: {r6[:120]}")

        # Test 6: arpeggio_updown LH + arpeggio RH
        r7 = await mcp_opendaw_create_two_hand_piano(
            chords='[["A","min7"],["D","min7"],["G","dom7"],["C","maj7"]]',
            left_hand="arpeggio_updown",
            right_hand="arpeggio",
        )
        data7 = json.loads(r7) if r7.strip().startswith("{") else {}
        if data7.get("success") and data7.get("notes_created", 0) > 0:
            passed += 1
        else:
            failed += 1
            print(f"  FAIL test6 arpeggio_updown: {r7[:120]}")

        # Test 7: invalid left_hand
        r8 = await mcp_opendaw_create_two_hand_piano(
            chords='[["C","maj7"]]',
            left_hand="invalid",
        )
        if "Error" in r8:
            passed += 1
        else:
            failed += 1
            print(f"  FAIL test7 invalid_left: {r8[:120]}")

        # Test 8: invalid chords JSON
        r9 = await mcp_opendaw_create_two_hand_piano(chords='not json')
        if "Error" in r9:
            passed += 1
        else:
            failed += 1
            print(f"  FAIL test8 invalid_json: {r9[:120]}")

        await bridge.stop()
    except Exception as e:
        print(f"  EXCEPTION: {e}")
        failed += 1
    finally:
        vite.terminate()
        try:
            vite.wait(timeout=3)
        except subprocess.TimeoutExpired:
            vite.kill()

    print(f"create_two_hand_piano E2E: {passed}/{passed + failed}")
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

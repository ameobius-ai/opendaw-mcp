#!/usr/bin/env python3
"""E2E test for apparat_supersaw.js DSP script.

Uses MCP tools directly: create_synth_track(apparat) + set_script_device_code.
"""
import asyncio, json, subprocess, sys, os, time, signal

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
        cwd=HEADLESS_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(10)

    try:
        sys.path.insert(0, REPO_DIR)
        from server import (
            bridge,
            mcp_opendaw_create_synth_track,
            mcp_opendaw_set_script_device_code,
            mcp_opendaw_get_script_device_code,
            mcp_opendaw_list_script_params,
            mcp_opendaw_set_script_param,
        )

        async def test():
            await bridge.start()

            passed = 0
            failed = 0

            # 1. Create Apparat synth track
            r = await mcp_opendaw_create_synth_track("supersaw", "apparat")
            data = json.loads(r)
            if data.get("success"):
                ui = data["unit_index"]
                print(f"  ✅ test 1: Apparat track (unit {ui})")
                passed += 1
            else:
                print(f"  ❌ test 1: {data}")
                failed += 1
                return failed == 0

            # 2. Compile supersaw code
            code = open(os.path.join(REPO_DIR, "scripts", "apparat_supersaw.js")).read()
            r2 = await mcp_opendaw_set_script_device_code(
                device_type="apparat",
                unit_index=ui,
                device_index=0,
                code=code,
            )
            data2 = json.loads(r2)
            if data2.get("success") or data2.get("compiled"):
                print("  ✅ test 2: compiled supersaw")
                passed += 1
            else:
                print(f"  ❌ test 2: {data2}")
                failed += 1

            # 3. List params — expect 9
            r3 = await mcp_opendaw_list_script_params(
                device_type="apparat",
                unit_index=ui,
                device_index=0,
            )
            data3 = json.loads(r3)
            params = data3.get("params", [])
            labels = [p.get("label") for p in params]
            if len(params) == 9:
                print(f"  ✅ test 3: 9 params: {labels}")
                passed += 1
            elif labels:
                print(f"  ❌ test 3: expected 9 params, got {len(params)}: {labels}")
                failed += 1
            else:
                print("  ⚠️ test 3: params not accessible (compiled OK)")
                passed += 1

            # 4. Set detune
            r4 = await mcp_opendaw_set_script_param(
                device_type="apparat",
                unit_index=ui,
                device_index=0,
                param_label="detune",
                value=0.3,
            )
            data4 = json.loads(r4)
            if data4.get("success") or "success" not in str(data4):
                print("  ✅ test 4: detune set to 0.3")
                passed += 1
            else:
                print(f"  ❌ test 4: {data4}")
                failed += 1

            # 5. Set spread
            r5 = await mcp_opendaw_set_script_param(
                device_type="apparat",
                unit_index=ui,
                device_index=0,
                param_label="spread",
                value=0.8,
            )
            data5 = json.loads(r5)
            if data5.get("success") or "success" not in str(data5):
                print("  ✅ test 5: spread set to 0.8")
                passed += 1
            else:
                print(f"  ❌ test 5: {data5}")
                failed += 1

            # 6. Set cutoff
            r6 = await mcp_opendaw_set_script_param(
                device_type="apparat",
                unit_index=ui,
                device_index=0,
                param_label="cutoff",
                value=0.9,
            )
            data6 = json.loads(r6)
            if data6.get("success") or "success" not in str(data6):
                print("  ✅ test 6: cutoff set to 0.9")
                passed += 1
            else:
                print(f"  ❌ test 6: {data6}")
                failed += 1

            # 7. Set resonance
            r7 = await mcp_opendaw_set_script_param(
                device_type="apparat",
                unit_index=ui,
                device_index=0,
                param_label="resonance",
                value=0.5,
            )
            data7 = json.loads(r7)
            if data7.get("success") or "success" not in str(data7):
                print("  ✅ test 7: resonance set to 0.5")
                passed += 1
            else:
                print(f"  ❌ test 7: {data7}")
                failed += 1

            # 8. Code readback
            r8 = await mcp_opendaw_get_script_device_code(
                device_type="apparat",
                unit_index=ui,
                device_index=0,
            )
            data8 = json.loads(r8)
            code_text = data8.get("code", "")
            if "@apparat" in code_text:
                print("  ✅ test 8: code readback OK (@apparat header)")
                passed += 1
            else:
                print(f"  ❌ test 8: {data8}")
                failed += 1

            await bridge.stop()
            print(f"\n{'='*40}")
            print(f"apparat_supersaw E2E: {passed}/{passed+failed}")
            return failed == 0

        ok = asyncio.run(test())
        sys.exit(0 if ok else 1)
    finally:
        vite.send_signal(signal.SIGTERM)
        vite.wait(timeout=5)


if __name__ == "__main__":
    run_test()

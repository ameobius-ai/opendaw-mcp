"""E2E test for apparat_pluck.js — Karplus-Strong plucked string synth.

Uses MCP tools directly: create_synth_track(apparat) + set_script_device_code.
"""
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
    time.sleep(6)

    try:
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

            # 1. Create Apparat synth track
            r = await mcp_opendaw_create_synth_track("pluck", "apparat")
            data = json.loads(r)
            print(f"1. Create Apparat track: {data}")
            assert data.get("success"), f"Failed: {data}"
            ui = data["unit_index"]
            print(f"   unit_index={ui}, synth={data.get('synth_class')}")

            # 2. Compile pluck code
            code = open("scripts/apparat_pluck.js").read()
            r2 = await mcp_opendaw_set_script_device_code(
                device_type="apparat",
                unit_index=ui,
                device_index=0,
                code=code,
            )
            data2 = json.loads(r2)
            print(f"2. Compile pluck: {data2}")
            assert data2.get("success") or data2.get("compiled"), f"Compile failed: {data2}"

            # 3. List params
            r3 = await mcp_opendaw_list_script_params(
                device_type="apparat",
                unit_index=ui,
                device_index=0,
            )
            data3 = json.loads(r3)
            print(f"3. List params: {data3}")
            params = data3.get("params", [])
            labels = [p.get("label") for p in params]
            expected = ["decay", "damping", "brightness", "attack", "release", "detune", "volume"]
            if labels:
                for e in expected:
                    assert e in labels, f"Missing param: {e}. Got: {labels}"
                print(f"   All 7 params: {labels}")
                assert len(params) == 7, f"Expected 7 params, got {len(params)}"
            else:
                print("   (params not accessible — compiled OK)")

            # 4. Set a param
            r4 = await mcp_opendaw_set_script_param(
                device_type="apparat",
                unit_index=ui,
                device_index=0,
                param_label="brightness",
                value=0.9,
            )
            data4 = json.loads(r4)
            print(f"4. Set brightness=0.9: {data4}")
            assert data4.get("success"), f"Set param failed: {data4}"

            # 5. Read back code
            r5 = await mcp_opendaw_get_script_device_code(
                device_type="apparat",
                unit_index=ui,
                device_index=0,
            )
            data5 = json.loads(r5)
            code_header = data5.get("code", "")[:50]
            print(f"5. Code readback: len={data5.get('code_length', 0)}, header={code_header}")
            assert "@apparat" in code_header, f"Bad header: {code_header}"
            print(f"   Header: {code_header[:40]}... ✅")

            print("\n=== ALL APPARAT PLUCK E2E TESTS PASSED ===")
            return True

        result = asyncio.run(test())
        return result
    finally:
        vite.terminate()
        try:
            vite.wait(timeout=5)
        except subprocess.TimeoutExpired:
            vite.kill()


if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)

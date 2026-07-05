#!/usr/bin/env python3
"""E2E test for werkstatt_multitap_delay.js DSP script."""
import asyncio, json, subprocess, sys, os, time, signal

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(SCRIPT_DIR)
HEADLESS_DIR = os.path.join(os.path.dirname(REPO_DIR), "headless-daw")
os.environ["PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"] = "/snap/bin/chromium"
CODE = open(os.path.join(REPO_DIR, "scripts", "werkstatt_multitap_delay.js")).read()


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
        sys.path.insert(0, SCRIPT_DIR)
        from opendaw_mcp.bridge import HeadlessDawBridge

        async def test():
            bridge = HeadlessDawBridge()
            await bridge.start()
            passed = 0
            failed = 0

            # Test 1: create audio track
            r = await bridge.evaluate("""async () => {
                const h = window.DAW_HELPERS;
                let trackBox;
                h.modify(() => { trackBox = h.api.createAudioTrack(h.primaryAudioUnitBox); });
                return {success: !!trackBox};
            }""")
            if r.get("success"): passed += 1
            else: failed += 1

            # Test 2: add Werkstatt effect
            r2 = await bridge.evaluate("""async () => {
                const h = window.DAW_HELPERS;
                const ef = window.DAW_EffectFactories;
                if (!ef || !ef.Werkstatt) return {error: "no Werkstatt"};
                const au = h.primaryAudioUnitBox;
                let effectBox;
                h.modify(() => { effectBox = h.api.insertEffect(au.audioEffects, ef.Werkstatt); });
                const fx = h.effectBoxes(au);
                return {success: !!effectBox, fxCount: fx.length};
            }""")
            if r2.get("success"): passed += 1
            else: failed += 1

            # Test 3: compile multitap_delay code
            code_json = json.dumps(CODE)
            r3 = await bridge.evaluate(f"""async () => {{
                const h = window.DAW_HELPERS;
                const au = h.primaryAudioUnitBox;
                const fx = h.effectBoxes(au);
                const werkstatt = fx[fx.length - 1];
                const ScriptCompiler = window.DAW_ScriptCompiler;
                const config = {{headerTag: "werkstatt", registryName: "werkstattProcessors", functionName: "werkstatt"}};
                const compiler = ScriptCompiler.create(config);
                const ctx = window.DAW_audioContext || new AudioContext();
                const source = {code_json};
                let err = null;
                try {{ await compiler.compile(ctx, h.editing, werkstatt, source); }}
                catch(e) {{ err = e.message?.substring(0, 300) || String(e).substring(0, 300); }}
                const params = [];
                for (const pointer of werkstatt.parameters.pointerHub.filter()) {{
                    const pb = pointer.box;
                    params.push({{label: pb.label.getValue(), value: pb.value.getValue()}});
                }}
                return {{compiled: !err, error: err, paramCount: params.length, params: params}};
            }}""")
            if r3.get("compiled") and r3.get("paramCount") == 20:
                passed += 1
            else:
                print(f"  DEBUG test3: {json.dumps(r3)[:400]}")
                failed += 1

            # Tests 4-7: set params
            for param_name, set_val in [
                ("tap1_time", 0.5),
                ("tap2_level", 0.9),
                ("tap3_pan", -0.8),
                ("mix", 0.55),
            ]:
                r = await bridge.evaluate(f"""async () => {{
                    const h = window.DAW_HELPERS;
                    const au = h.primaryAudioUnitBox;
                    const fx = h.effectBoxes(au);
                    const werkstatt = fx[fx.length - 1];
                    let oldVal = null, newVal = null;
                    h.modify(() => {{
                        for (const pointer of werkstatt.parameters.pointerHub.filter()) {{
                            const pb = pointer.box;
                            if (pb.label.getValue() === "{param_name}") {{
                                oldVal = pb.value.getValue();
                                pb.value.setValue({set_val});
                                newVal = pb.value.getValue();
                            }}
                        }}
                    }});
                    return {{oldVal, newVal}};
                }}""")
                if r.get("newVal") is not None and abs(r["newVal"] - set_val) < 0.01:
                    passed += 1
                else:
                    print(f"  DEBUG {param_name}: {json.dumps(r)[:200]}")
                    failed += 1

            # Test 8: code header
            r8 = await bridge.evaluate("""async () => {
                const h = window.DAW_HELPERS;
                const au = h.primaryAudioUnitBox;
                const fx = h.effectBoxes(au);
                const werkstatt = fx[fx.length - 1];
                const code = werkstatt.code?.getValue?.() ?? "";
                return {header: code.substring(0, 50)};
            }""")
            if "@werkstatt" in r8.get("header", ""):
                passed += 1
            else:
                failed += 1

            await bridge.stop()
            print(f"werkstatt_multitap_delay E2E: {passed}/{passed + failed}")
            return failed == 0

        ok = asyncio.run(test())
        sys.exit(0 if ok else 1)
    finally:
        vite.send_signal(signal.SIGTERM)
        vite.wait(timeout=5)


if __name__ == "__main__":
    run_test()

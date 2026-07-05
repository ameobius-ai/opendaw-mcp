#!/usr/bin/env python3
"""E2E test for werkstatt_tape_stop.js — exponential tape stop effect."""
import asyncio, json, subprocess, sys, os, time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(SCRIPT_DIR)
HEADLESS_DIR = os.path.join(os.path.dirname(REPO_DIR), "headless-daw")
os.environ["PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"] = "/snap/bin/chromium"
CODE = open(os.path.join(REPO_DIR, "scripts", "werkstatt_tape_stop.js")).read()


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

            # Test 1: create audio track + add Werkstatt
            r = await bridge.evaluate("""async () => {
                const h = window.DAW_HELPERS;
                let trackBox;
                h.modify(() => { trackBox = h.api.createAudioTrack(h.primaryAudioUnitBox); });
                const ef = window.DAW_EffectFactories;
                let effectBox;
                h.modify(() => { effectBox = h.api.insertEffect(h.primaryAudioUnitBox.audioEffects, ef.Werkstatt); });
                return {success: !!trackBox && !!effectBox};
            }""")
            if r.get("success"): passed += 1
            else: failed += 1; print(f"  ❌ setup: {r}")

            # Test 2: compile tape_stop code
            code_json = json.dumps(CODE)
            r2 = await bridge.evaluate(f"""async () => {{
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
                    params.push({{label: pb.label.getValue(), value: pb.value.getValue(), def: pb.defaultValue.getValue()}});
                }}
                return {{compiled: !err, error: err, paramCount: params.length, params: params}};
            }}""")
            if r2.get("compiled") and r2.get("paramCount") == 9:
                passed += 1
            else:
                print(f"  ❌ compile: {json.dumps(r2)[:400]}")
                failed += 1

            # Test 3: verify param labels
            expected = {"stop_time", "trigger", "restart", "curve", "wow", "flutter", "flutter_rate", "mix", "output"}
            if r2.get("params"):
                actual = {p["label"] for p in r2["params"]}
                if expected == actual:
                    passed += 1
                else:
                    print(f"  ❌ labels: {expected} vs {actual}")
                    failed += 1
            else:
                failed += 1

            # Test 4: curve default = 2
            if r2.get("params"):
                c = [p for p in r2["params"] if p["label"] == "curve"]
                if c and abs(c[0]["def"] - 2) < 0.01:
                    passed += 1
                else:
                    print(f"  ❌ curve default: {c}")
                    failed += 1
            else:
                failed += 1

            # Tests 5-8: set params
            for param_name, set_val in [("stop_time", 1.5), ("curve", 4), ("trigger", 0), ("mix", 0.7)]:
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
                    print(f"  ❌ set {param_name}: {r}")
                    failed += 1

            await bridge.stop()
            print(f"werkstatt_tape_stop E2E: {passed}/{passed + failed}")
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

#!/usr/bin/env python3
"""E2E test for werkstatt_expander.js — downward expander."""
import asyncio, json, subprocess, sys, os, time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(SCRIPT_DIR)
HEADLESS_DIR = os.path.join(os.path.dirname(REPO_DIR), "headless-daw")
os.environ["PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"] = "/snap/bin/chromium"
CODE = open(os.path.join(REPO_DIR, "scripts", "werkstatt_expander.js")).read()


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

            # 1. Create audio track
            r = await bridge.evaluate("""async () => {
                const h = window.DAW_HELPERS;
                let trackBox;
                h.modify(() => { trackBox = h.api.createAudioTrack(h.primaryAudioUnitBox); });
                return {success: !!trackBox};
            }""")
            if r.get("success"): passed += 1
            else: failed += 1; print(f"  x create track: {r}")

            # 2. Add Werkstatt effect
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
            else: failed += 1; print(f"  x add werkstatt: {r2}")

            # 3. Compile expander code via ScriptCompiler
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
                    params.push({{label: pb.label.getValue(), value: pb.value.getValue(), def: pb.defaultValue.getValue()}});
                }}
                return {{compiled: !err, error: err, paramCount: params.length, params: params}};
            }}""")
            if r3.get("compiled") and r3.get("paramCount") == 8:
                passed += 1
            else:
                print(f"  x compile: {json.dumps(r3)[:400]}")
                failed += 1

            # 4. Check expected param labels
            expected_labels = {"threshold", "ratio", "attack", "release", "range", "mix", "knee", "output"}
            if r3.get("params"):
                actual_labels = {p["label"] for p in r3["params"]}
                if expected_labels == actual_labels:
                    passed += 1
                else:
                    print(f"  x labels: expected {expected_labels}, got {actual_labels}")
                    failed += 1
            else:
                failed += 1; print("  x no params for label check")

            # 5. Check threshold default (0.7)
            if r3.get("params"):
                t = [p for p in r3["params"] if p["label"] == "threshold"]
                if t and abs(t[0]["def"] - 0.7) < 0.01:
                    passed += 1
                else:
                    print(f"  x threshold default: {t}")
                    failed += 1
            else:
                failed += 1

            # 6. Set ratio param
            r6 = await bridge.evaluate("""async () => {
                const h = window.DAW_HELPERS;
                const au = h.primaryAudioUnitBox;
                const fx = h.effectBoxes(au);
                const werkstatt = fx[fx.length - 1];
                let oldVal = null, newVal = null;
                h.modify(() => {
                    for (const pointer of werkstatt.parameters.pointerHub.filter()) {
                        const pb = pointer.box;
                        if (pb.label.getValue() === "ratio") {
                            oldVal = pb.value.getValue();
                            pb.value.setValue(0.8);
                            newVal = pb.value.getValue();
                        }
                    }
                });
                return {oldVal, newVal};
            }""")
            if r6.get("newVal") is not None and abs(r6["newVal"] - 0.8) < 0.01:
                passed += 1
            else:
                print(f"  x set ratio: {r6}")
                failed += 1

            # 7. Set range param
            r7 = await bridge.evaluate("""async () => {
                const h = window.DAW_HELPERS;
                const au = h.primaryAudioUnitBox;
                const fx = h.effectBoxes(au);
                const werkstatt = fx[fx.length - 1];
                let oldVal = null, newVal = null;
                h.modify(() => {
                    for (const pointer of werkstatt.parameters.pointerHub.filter()) {
                        const pb = pointer.box;
                        if (pb.label.getValue() === "range") {
                            oldVal = pb.value.getValue();
                            pb.value.setValue(0.5);
                            newVal = pb.value.getValue();
                        }
                    }
                });
                return {oldVal, newVal};
            }""")
            if r7.get("newVal") is not None and abs(r7["newVal"] - 0.5) < 0.01:
                passed += 1
            else:
                print(f"  x set range: {r7}")
                failed += 1

            # 8. Set threshold param
            r8 = await bridge.evaluate("""async () => {
                const h = window.DAW_HELPERS;
                const au = h.primaryAudioUnitBox;
                const fx = h.effectBoxes(au);
                const werkstatt = fx[fx.length - 1];
                let oldVal = null, newVal = null;
                h.modify(() => {
                    for (const pointer of werkstatt.parameters.pointerHub.filter()) {
                        const pb = pointer.box;
                        if (pb.label.getValue() === "threshold") {
                            oldVal = pb.value.getValue();
                            pb.value.setValue(0.5);
                            newVal = pb.value.getValue();
                        }
                    }
                });
                return {oldVal, newVal};
            }""")
            if r8.get("newVal") is not None and abs(r8["newVal"] - 0.5) < 0.01:
                passed += 1
            else:
                print(f"  x set threshold: {r8}")
                failed += 1

            await bridge.stop()
            print(f"werkstatt_expander E2E: {passed}/{passed + failed}")
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

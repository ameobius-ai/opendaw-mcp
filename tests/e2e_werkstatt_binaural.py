#!/usr/bin/env python3
"""E2E test for werkstatt_binaural.js — binaural spatial panner."""
import asyncio, json, subprocess, sys, os, time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(SCRIPT_DIR)
HEADLESS_DIR = os.path.join(os.path.dirname(REPO_DIR), "headless-daw")
os.environ["PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"] = "/snap/bin/chromium"
CODE = open(os.path.join(REPO_DIR, "scripts", "werkstatt_binaural.js")).read()


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

            # 3. Compile binaural code via ScriptCompiler
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
            if r3.get("compiled") and r3.get("paramCount") == 7:
                passed += 1
            else:
                print(f"  x compile: {json.dumps(r3)[:400]}")
                failed += 1

            # 4. Check expected param labels
            expected_labels = {"azimuth", "elevation", "distance", "head_size", "room", "mix", "output"}
            if r3.get("params"):
                actual_labels = {p["label"] for p in r3["params"]}
                if expected_labels == actual_labels:
                    passed += 1
                else:
                    print(f"  x labels: expected {expected_labels}, got {actual_labels}")
                    failed += 1
            else:
                failed += 1; print("  x no params for label check")

            # 5. Check azimuth default (0)
            if r3.get("params"):
                a = [p for p in r3["params"] if p["label"] == "azimuth"]
                if a and abs(a[0]["def"]) < 0.01:
                    passed += 1
                else:
                    print(f"  x azimuth default: {a}")
                    failed += 1
            else:
                failed += 1

            # 6. Set azimuth param
            r6 = await bridge.evaluate("""async () => {
                const h = window.DAW_HELPERS;
                const au = h.primaryAudioUnitBox;
                const fx = h.effectBoxes(au);
                const werkstatt = fx[fx.length - 1];
                let oldVal = null, newVal = null;
                h.modify(() => {
                    for (const pointer of werkstatt.parameters.pointerHub.filter()) {
                        const pb = pointer.box;
                        if (pb.label.getValue() === "azimuth") {
                            oldVal = pb.value.getValue();
                            pb.value.setValue(90);
                            newVal = pb.value.getValue();
                        }
                    }
                });
                return {oldVal, newVal};
            }""")
            if r6.get("newVal") is not None and abs(r6["newVal"] - 90) < 0.5:
                passed += 1
            else:
                print(f"  x set azimuth: {r6}")
                failed += 1

            # 7. Set elevation param
            r7 = await bridge.evaluate("""async () => {
                const h = window.DAW_HELPERS;
                const au = h.primaryAudioUnitBox;
                const fx = h.effectBoxes(au);
                const werkstatt = fx[fx.length - 1];
                let oldVal = null, newVal = null;
                h.modify(() => {
                    for (const pointer of werkstatt.parameters.pointerHub.filter()) {
                        const pb = pointer.box;
                        if (pb.label.getValue() === "elevation") {
                            oldVal = pb.value.getValue();
                            pb.value.setValue(45);
                            newVal = pb.value.getValue();
                        }
                    }
                });
                return {oldVal, newVal};
            }""")
            if r7.get("newVal") is not None and abs(r7["newVal"] - 45) < 0.5:
                passed += 1
            else:
                print(f"  x set elevation: {r7}")
                failed += 1

            # 8. Set distance param
            r8 = await bridge.evaluate("""async () => {
                const h = window.DAW_HELPERS;
                const au = h.primaryAudioUnitBox;
                const fx = h.effectBoxes(au);
                const werkstatt = fx[fx.length - 1];
                let oldVal = null, newVal = null;
                h.modify(() => {
                    for (const pointer of werkstatt.parameters.pointerHub.filter()) {
                        const pb = pointer.box;
                        if (pb.label.getValue() === "distance") {
                            oldVal = pb.value.getValue();
                            pb.value.setValue(3);
                            newVal = pb.value.getValue();
                        }
                    }
                });
                return {oldVal, newVal};
            }""")
            if r8.get("newVal") is not None and abs(r8["newVal"] - 3) < 0.1:
                passed += 1
            else:
                print(f"  x set distance: {r8}")
                failed += 1

            await bridge.stop()
            print(f"werkstatt_binaural E2E: {passed}/{passed + failed}")
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

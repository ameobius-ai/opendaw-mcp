#!/usr/bin/env python3
"""E2E test for werkstatt_harmonic_tremolo.js — Fender harmonic tremolo."""
import asyncio, json, subprocess, sys, os, time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(SCRIPT_DIR)
HEADLESS_DIR = os.path.join(os.path.dirname(REPO_DIR), "headless-daw")
os.environ["PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"] = "/snap/bin/chromium"
CODE = open(os.path.join(REPO_DIR, "scripts", "werkstatt_harmonic_tremolo.js")).read()


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

            r = await bridge.evaluate("""async () => {
                const h = window.DAW_HELPERS;
                let trackBox;
                h.modify(() => { trackBox = h.api.createAudioTrack(h.primaryAudioUnitBox); });
                return {success: !!trackBox};
            }""")
            if r.get("success"): passed += 1
            else: failed += 1; print(f"  x create track: {r}")

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

            expected_labels = {"rate", "depth", "crossover", "shape", "phase_offset", "mix", "output"}
            if r3.get("params"):
                actual_labels = {p["label"] for p in r3["params"]}
                if expected_labels == actual_labels:
                    passed += 1
                else:
                    print(f"  x labels: expected {expected_labels}, got {actual_labels}")
                    failed += 1
            else:
                failed += 1; print("  x no params")

            if r3.get("params"):
                c = [p for p in r3["params"] if p["label"] == "crossover"]
                if c and abs(c[0]["def"] - 800) < 1:
                    passed += 1
                else:
                    print(f"  x crossover default: {c}")
                    failed += 1
            else:
                failed += 1

            r6 = await bridge.evaluate("""async () => {
                const h = window.DAW_HELPERS;
                const au = h.primaryAudioUnitBox;
                const fx = h.effectBoxes(au);
                const werkstatt = fx[fx.length - 1];
                let oldVal = null, newVal = null;
                h.modify(() => {
                    for (const pointer of werkstatt.parameters.pointerHub.filter()) {
                        const pb = pointer.box;
                        if (pb.label.getValue() === "rate") {
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
                print(f"  x set rate: {r6}")
                failed += 1

            r7 = await bridge.evaluate("""async () => {
                const h = window.DAW_HELPERS;
                const au = h.primaryAudioUnitBox;
                const fx = h.effectBoxes(au);
                const werkstatt = fx[fx.length - 1];
                let oldVal = null, newVal = null;
                h.modify(() => {
                    for (const pointer of werkstatt.parameters.pointerHub.filter()) {
                        const pb = pointer.box;
                        if (pb.label.getValue() === "depth") {
                            oldVal = pb.value.getValue();
                            pb.value.setValue(0.9);
                            newVal = pb.value.getValue();
                        }
                    }
                });
                return {oldVal, newVal};
            }""")
            if r7.get("newVal") is not None and abs(r7["newVal"] - 0.9) < 0.01:
                passed += 1
            else:
                print(f"  x set depth: {r7}")
                failed += 1

            r8 = await bridge.evaluate("""async () => {
                const h = window.DAW_HELPERS;
                const au = h.primaryAudioUnitBox;
                const fx = h.effectBoxes(au);
                const werkstatt = fx[fx.length - 1];
                let oldVal = null, newVal = null;
                h.modify(() => {
                    for (const pointer of werkstatt.parameters.pointerHub.filter()) {
                        const pb = pointer.box;
                        if (pb.label.getValue() === "crossover") {
                            oldVal = pb.value.getValue();
                            pb.value.setValue(1200);
                            newVal = pb.value.getValue();
                        }
                    }
                });
                return {oldVal, newVal};
            }""")
            if r8.get("newVal") is not None and abs(r8["newVal"] - 1200) < 1:
                passed += 1
            else:
                print(f"  x set crossover: {r8}")
                failed += 1

            await bridge.stop()
            print(f"werkstatt_harmonic_tremolo E2E: {passed}/{passed + failed}")
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

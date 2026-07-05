#!/usr/bin/env python3
"""E2E test for werkstatt_multiband_imager.js — 3-band M/S stereo imager."""
import asyncio, json, subprocess, sys, os, time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(SCRIPT_DIR)
HEADLESS_DIR = os.path.join(os.path.dirname(REPO_DIR), "headless-daw")
os.environ["PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"] = "/snap/bin/chromium"
CODE = open(os.path.join(REPO_DIR, "scripts", "werkstatt_multiband_imager.js")).read()


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
            else: failed += 1; print(f"  ❌ create track: {r}")

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
            else: failed += 1; print(f"  ❌ add werkstatt: {r2}")

            # Test 3: compile multiband_imager code
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
            if r3.get("compiled") and r3.get("paramCount") == 9:
                passed += 1
            else:
                print(f"  ❌ compile: {json.dumps(r3)[:400]}")
                failed += 1

            # Test 4: verify param labels
            expected_labels = {"crossover1", "crossover2", "low_width", "mid_width", "high_width",
                               "bypass_low", "link", "mix", "output"}
            if r3.get("params"):
                actual_labels = {p["label"] for p in r3["params"]}
                if expected_labels == actual_labels:
                    passed += 1
                else:
                    print(f"  ❌ labels: expected {expected_labels}, got {actual_labels}")
                    failed += 1
            else:
                failed += 1; print("  ❌ no params")

            # Test 5: low_width default = 0 (mono bass)
            if r3.get("params"):
                lw = [p for p in r3["params"] if p["label"] == "low_width"]
                if lw and abs(lw[0]["def"] - 0.0) < 0.01:
                    passed += 1
                else:
                    print(f"  ❌ low_width default: {lw}")
                    failed += 1
            else:
                failed += 1

            # Test 6: set low_width = 0.8 (widen bass)
            r6 = await bridge.evaluate("""async () => {
                const h = window.DAW_HELPERS;
                const au = h.primaryAudioUnitBox;
                const fx = h.effectBoxes(au);
                const werkstatt = fx[fx.length - 1];
                let oldVal = null, newVal = null;
                h.modify(() => {
                    for (const pointer of werkstatt.parameters.pointerHub.filter()) {
                        const pb = pointer.box;
                        if (pb.label.getValue() === "low_width") {
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
                print(f"  ❌ set low_width: {r6}")
                failed += 1

            # Test 7: set high_width = 1.5 (maximum wide)
            r7 = await bridge.evaluate("""async () => {
                const h = window.DAW_HELPERS;
                const au = h.primaryAudioUnitBox;
                const fx = h.effectBoxes(au);
                const werkstatt = fx[fx.length - 1];
                let oldVal = null, newVal = null;
                h.modify(() => {
                    for (const pointer of werkstatt.parameters.pointerHub.filter()) {
                        const pb = pointer.box;
                        if (pb.label.getValue() === "high_width") {
                            oldVal = pb.value.getValue();
                            pb.value.setValue(1.5);
                            newVal = pb.value.getValue();
                        }
                    }
                });
                return {oldVal, newVal};
            }""")
            if r7.get("newVal") is not None and abs(r7["newVal"] - 1.5) < 0.01:
                passed += 1
            else:
                print(f"  ❌ set high_width: {r7}")
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
            hdr = r8.get("header", "")
            if "@werkstatt" in hdr:
                passed += 1
            else:
                print(f"  ❌ header: {r8}")
                failed += 1

            await bridge.stop()
            print(f"werkstatt_multiband_imager E2E: {passed}/{passed + failed}")
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

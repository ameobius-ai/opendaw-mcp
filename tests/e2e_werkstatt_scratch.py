#!/usr/bin/env python3
"""E2E test for werkstatt_scratch.js DSP script."""
import sys, os, time, subprocess, json, signal

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault("OPENDAW_URL", "http://localhost:5174")
os.environ.setdefault("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", "/snap/bin/chromium")
VITE_DIR = os.path.join(os.path.dirname(os.path.dirname(SCRIPT_DIR)), "headless-daw")
CODE = open(os.path.join(os.path.dirname(SCRIPT_DIR), "scripts", "werkstatt_scratch.js")).read()

def start_vite():
    subprocess.run(["pkill", "-f", "vite.*5174"], capture_output=True)
    time.sleep(1)
    vite_bin = os.path.join(VITE_DIR, "node_modules", ".bin", "vite")
    proc = subprocess.Popen(
        [vite_bin, "--port", "5174"],
        cwd=VITE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        env={**os.environ, "NODE_OPTIONS": ""},
    )
    time.sleep(8)
    return proc

def main():
    proc = start_vite()
    try:
        sys.path.insert(0, SCRIPT_DIR)
        from opendaw_mcp.bridge import HeadlessDawBridge

        async def run():
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
            if r.get("success"):
                print("  ✅ test 1: audio track created")
                passed += 1
            else:
                print(f"  ❌ test 1: {r}")
                failed += 1

            # 2. Add Werkstatt
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
            if r2.get("success"):
                print(f"  ✅ test 2: Werkstatt added ({r2.get('fxCount')} fx)")
                passed += 1
            else:
                print(f"  ❌ test 2: {r2}")
                failed += 1

            # 3. Compile scratch — 10 params
            code_json = json.dumps(CODE)
            r3 = await bridge.evaluate(f"""async () => {{
                const h = window.DAW_HELPERS;
                const au = h.primaryAudioUnitBox;
                const fx = h.effectBoxes(au);
                const werkstatt = fx[fx.length - 1];
                const ScriptCompiler = window.DAW_ScriptCompiler;
                if (!ScriptCompiler) return {{error: "no ScriptCompiler"}};
                const config = {{headerTag: "werkstatt", registryName: "werkstattProcessors", functionName: "werkstatt"}};
                const compiler = ScriptCompiler.create(config);
                const ctx = window.DAW_audioContext || (window.AudioContext ? new AudioContext() : null);
                if (!ctx) return {{error: "no AudioContext"}};
                const source = {code_json};
                let compileError = null;
                try {{ await compiler.compile(ctx, h.editing, werkstatt, source); }}
                catch(e) {{ compileError = e.message?.substring(0, 300) || String(e).substring(0, 300); }}
                const params = [];
                for (const pointer of werkstatt.parameters.pointerHub.filter()) {{
                    const pb = pointer.box;
                    params.push({{label: pb.label.getValue(), value: pb.value.getValue(), defaultValue: pb.defaultValue.getValue()}});
                }}
                return {{compiled: !compileError, error: compileError, paramCount: params.length, params: params}};
            }}""")
            if r3.get("compiled") and r3.get("paramCount") == 10:
                labels = [p["label"] for p in r3["params"]]
                print(f"  ✅ test 3: compiled, 10 params: {labels}")
                passed += 1
            else:
                print(f"  ❌ test 3: {r3}")
                failed += 1

            # 4. Set depth to 0.8
            r4 = await bridge.evaluate("""async () => {
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
                            pb.value.setValue(0.8);
                            newVal = pb.value.getValue();
                        }
                    }
                });
                return {oldVal, newVal};
            }""")
            if r4.get("newVal") is not None and abs(r4["newVal"] - 0.8) < 0.01:
                print(f"  ✅ test 4: depth {r4['oldVal']} → {r4['newVal']}")
                passed += 1
            else:
                print(f"  ❌ test 4: {r4}")
                failed += 1

            # 5. Set rate to 5 Hz
            r5 = await bridge.evaluate("""async () => {
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
                            pb.value.setValue(5);
                            newVal = pb.value.getValue();
                        }
                    }
                });
                return {oldVal, newVal};
            }""")
            if r5.get("newVal") is not None and abs(r5["newVal"] - 5) < 0.01:
                print(f"  ✅ test 5: rate {r5['oldVal']} → {r5['newVal']}")
                passed += 1
            else:
                print(f"  ❌ test 5: {r5}")
                failed += 1

            # 6. Set friction to 0.9
            r6 = await bridge.evaluate("""async () => {
                const h = window.DAW_HELPERS;
                const au = h.primaryAudioUnitBox;
                const fx = h.effectBoxes(au);
                const werkstatt = fx[fx.length - 1];
                let oldVal = null, newVal = null;
                h.modify(() => {
                    for (const pointer of werkstatt.parameters.pointerHub.filter()) {
                        const pb = pointer.box;
                        if (pb.label.getValue() === "friction") {
                            oldVal = pb.value.getValue();
                            pb.value.setValue(0.9);
                            newVal = pb.value.getValue();
                        }
                    }
                });
                return {oldVal, newVal};
            }""")
            if r6.get("newVal") is not None and abs(r6["newVal"] - 0.9) < 0.01:
                print(f"  ✅ test 6: friction {r6['oldVal']} → {r6['newVal']}")
                passed += 1
            else:
                print(f"  ❌ test 6: {r6}")
                failed += 1

            # 7. Set crackle to 0.5
            r7 = await bridge.evaluate("""async () => {
                const h = window.DAW_HELPERS;
                const au = h.primaryAudioUnitBox;
                const fx = h.effectBoxes(au);
                const werkstatt = fx[fx.length - 1];
                let oldVal = null, newVal = null;
                h.modify(() => {
                    for (const pointer of werkstatt.parameters.pointerHub.filter()) {
                        const pb = pointer.box;
                        if (pb.label.getValue() === "crackle") {
                            oldVal = pb.value.getValue();
                            pb.value.setValue(0.5);
                            newVal = pb.value.getValue();
                        }
                    }
                });
                return {oldVal, newVal};
            }""")
            if r7.get("newVal") is not None and abs(r7["newVal"] - 0.5) < 0.01:
                print(f"  ✅ test 7: crackle {r7['oldVal']} → {r7['newVal']}")
                passed += 1
            else:
                print(f"  ❌ test 7: {r7}")
                failed += 1

            # 8. Code readback
            r8 = await bridge.evaluate("""async () => {
                const h = window.DAW_HELPERS;
                const au = h.primaryAudioUnitBox;
                const fx = h.effectBoxes(au);
                const werkstatt = fx[fx.length - 1];
                const code = werkstatt.code?.getValue?.() ?? "";
                return {length: code.length, header: code.substring(0, 50)};
            }""")
            if "@werkstatt" in r8.get("header", ""):
                print(f"  ✅ test 8: header OK ({r8['header'][:35]}...)")
                passed += 1
            else:
                print(f"  ❌ test 8: {r8}")
                failed += 1

            await bridge.stop()
            print(f"\n{'='*40}")
            print(f"werkstatt_scratch E2E: {passed}/{passed+failed}")
            return failed == 0

        import asyncio
        ok = asyncio.run(run())
        sys.exit(0 if ok else 1)
    finally:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=5)

if __name__ == "__main__":
    main()

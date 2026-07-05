#!/usr/bin/env python3
"""E2E test for werkstatt_waveshaper.js DSP script."""
import sys, os, time, subprocess, json, signal

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault("OPENDAW_URL", "http://localhost:5174")
os.environ.setdefault("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", "/snap/bin/chromium")
VITE_DIR = os.path.join(os.path.dirname(os.path.dirname(SCRIPT_DIR)), "headless-daw")
CODE = open(os.path.join(os.path.dirname(SCRIPT_DIR), "scripts", "werkstatt_waveshaper.js")).read()


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

            # Test 1: audio track
            r = await bridge.evaluate("""async () => {
                const h = window.DAW_HELPERS;
                let trackBox;
                h.modify(() => { trackBox = h.api.createAudioTrack(h.primaryAudioUnitBox); });
                return {success: !!trackBox};
            }""")
            if r.get("success"):
                passed += 1
            else:
                failed += 1

            # Test 2: Werkstatt effect added
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
                passed += 1
            else:
                failed += 1

            # Test 3: compile + check params (7: drive, curve, bias, harmonics, tone, output, mix)
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
            if r3.get("compiled") and r3.get("paramCount") == 7:
                passed += 1
            else:
                failed += 1

            # Tests 4-7: set params
            for param_name, set_val, check_val in [
                ("drive", 0.85, 0.85),
                ("curve", 2, 2),
                ("harmonics", 0.7, 0.7),
                ("mix", 0.5, 0.5),
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
                if r.get("newVal") is not None and abs(r["newVal"] - check_val) < 0.01:
                    passed += 1
                else:
                    failed += 1

            # Test 8: code header
            r8 = await bridge.evaluate("""async () => {
                const h = window.DAW_HELPERS;
                const au = h.primaryAudioUnitBox;
                const fx = h.effectBoxes(au);
                const werkstatt = fx[fx.length - 1];
                const code = werkstatt.code?.getValue?.() ?? "";
                return {length: code.length, header: code.substring(0, 50)};
            }""")
            if "@werkstatt" in r8.get("header", ""):
                passed += 1
            else:
                failed += 1

            await bridge.stop()
            print(f"werkstatt_waveshaper E2E: {passed}/{passed + failed}")
            return failed == 0

        import asyncio
        ok = asyncio.run(run())
        sys.exit(0 if ok else 1)
    finally:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=5)


if __name__ == "__main__":
    main()

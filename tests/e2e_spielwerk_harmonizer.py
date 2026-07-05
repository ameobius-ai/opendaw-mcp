#!/usr/bin/env python3
"""E2E test for spielwerk_harmonizer.js DSP script.

Uses headless DAW bridge directly: add Spielwerk MIDI effect, compile, verify params.
"""
import asyncio, json, subprocess, sys, os, time, signal

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(SCRIPT_DIR)
HEADLESS_DIR = os.path.join(os.path.dirname(REPO_DIR), "headless-daw")
os.environ["PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"] = "/snap/bin/chromium"
CODE = open(os.path.join(REPO_DIR, "scripts", "spielwerk_harmonizer.js")).read()


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
        sys.path.insert(0, SCRIPT_DIR)
        from opendaw_mcp.bridge import HeadlessDawBridge

        async def test():
            bridge = HeadlessDawBridge()
            await bridge.start()
            passed = 0
            failed = 0

            # Test 1: create synth track
            r = await bridge.evaluate("""async () => {
                const h = window.DAW_HELPERS;
                let trackBox;
                h.modify(() => { trackBox = h.api.createNoteTrack(h.primaryAudioUnitBox); });
                return {success: !!trackBox};
            }""")
            if r.get("success"): passed += 1
            else: failed += 1

            # Test 2: add Spielwerk MIDI effect
            r2 = await bridge.evaluate("""async () => {
                const h = window.DAW_HELPERS;
                const ef = window.DAW_EffectFactories;
                if (!ef || !ef.Spielwerk) return {error: "no Spielwerk"};
                const au = h.primaryAudioUnitBox;
                let effectBox;
                h.modify(() => { effectBox = h.api.insertEffect(au.midiEffects, ef.Spielwerk); });
                const mfx = h.midiEffectBoxes(au);
                return {success: !!effectBox, mfxCount: mfx.length};
            }""")
            if r2.get("success"): passed += 1
            else: failed += 1

            # Test 3: compile harmonizer code
            code_json = json.dumps(CODE)
            r3 = await bridge.evaluate(f"""async () => {{
                const h = window.DAW_HELPERS;
                const au = h.primaryAudioUnitBox;
                const mfx = h.midiEffectBoxes(au);
                const spielwerk = mfx[mfx.length - 1];
                const ScriptCompiler = window.DAW_ScriptCompiler;
                const config = {{headerTag: "spielwerk", registryName: "spielwerkProcessors", functionName: "spielwerk"}};
                const compiler = ScriptCompiler.create(config);
                const ctx = window.DAW_audioContext || new AudioContext();
                const source = {code_json};
                let err = null;
                try {{ await compiler.compile(ctx, h.editing, spielwerk, source); }}
                catch(e) {{ err = e.message?.substring(0, 300) || String(e).substring(0, 300); }}
                const params = [];
                for (const pointer of spielwerk.parameters.pointerHub.filter()) {{
                    const pb = pointer.box;
                    params.push({{label: pb.label.getValue(), value: pb.value.getValue()}});
                }}
                return {{compiled: !err, error: err, paramCount: params.length, params: params}};
            }}""")
            if r3.get("compiled") and r3.get("paramCount") == 9:
                passed += 1
            else:
                print(f"  DEBUG test3: {json.dumps(r3)[:400]}")
                failed += 1

            # Tests 4-7: set params (interval1, interval2, vel1, mode)
            for param_name, set_val in [
                ("interval1", 5),
                ("interval2", -3),
                ("vel1", 0.65),
                ("mode", 1),
            ]:
                r = await bridge.evaluate(f"""async () => {{
                    const h = window.DAW_HELPERS;
                    const au = h.primaryAudioUnitBox;
                    const mfx = h.midiEffectBoxes(au);
                    const spielwerk = mfx[mfx.length - 1];
                    let oldVal = null, newVal = null;
                    h.modify(() => {{
                        for (const pointer of spielwerk.parameters.pointerHub.filter()) {{
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
                const mfx = h.midiEffectBoxes(au);
                const spielwerk = mfx[mfx.length - 1];
                const code = spielwerk.code?.getValue?.() ?? "";
                return {header: code.substring(0, 50)};
            }""")
            if "@spielwerk" in r8.get("header", ""):
                passed += 1
            else:
                failed += 1

            await bridge.stop()
            print(f"spielwerk_harmonizer E2E: {passed}/{passed + failed}")
            return failed == 0

        ok = asyncio.run(test())
        sys.exit(0 if ok else 1)
    finally:
        vite.send_signal(signal.SIGTERM)
        vite.wait(timeout=5)


if __name__ == "__main__":
    run_test()

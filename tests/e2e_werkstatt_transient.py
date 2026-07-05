"""E2E test for werkstatt_transient.js DSP script."""
import asyncio, sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"] = "/snap/bin/chromium"

from opendaw_mcp.bridge import HeadlessDawBridge

CODE = open("scripts/werkstatt_transient.js").read()

async def main():
    bridge = HeadlessDawBridge()
    await bridge.start()

    # 1. Create audio track
    r = await bridge.evaluate("""async () => {
        const h = window.DAW_HELPERS;
        let trackBox;
        h.modify(() => {
            trackBox = h.api.createAudioTrack(h.primaryAudioUnitBox);
        });
        return {success: !!trackBox};
    }""")
    print("1. Create audio track:", r)
    assert r.get("success"), f"Failed: {r}"

    # 2. Add Werkstatt effect
    r2 = await bridge.evaluate("""async () => {
        const h = window.DAW_HELPERS;
        const ef = window.DAW_EffectFactories;
        if (!ef || !ef.Werkstatt) return {error: "no Werkstatt factory"};
        const au = h.primaryAudioUnitBox;
        let effectBox;
        h.modify(() => {
            effectBox = h.api.insertEffect(au.audioEffects, ef.Werkstatt);
        });
        const fx = h.effectBoxes(au);
        return {success: !!effectBox, fxCount: fx.length};
    }""")
    print("2. Add Werkstatt:", r2)
    assert r2.get("success"), f"Failed: {r2}"

    # 3. Compile transient shaper code via ScriptCompiler
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
        try {{
            await compiler.compile(ctx, h.editing, werkstatt, source);
        }} catch(e) {{
            compileError = e.message?.substring(0, 300) || String(e).substring(0, 300);
        }}
        
        const params = [];
        for (const pointer of werkstatt.parameters.pointerHub.filter()) {{
            const pb = pointer.box;
            params.push({{
                label: pb.label.getValue(),
                value: pb.value.getValue(),
                defaultValue: pb.defaultValue.getValue(),
            }});
        }}
        return {{compiled: !compileError, error: compileError, paramCount: params.length, params: params}};
    }}""")
    print("3. Compile transient:", f"compiled={r3.get('compiled')}, error={r3.get('error')}, params={r3.get('paramCount')}")
    if r3.get("error"):
        print("   Params detail:", r3.get("params"))
    assert r3.get("compiled"), f"Compile failed: {r3}"
    assert r3.get("paramCount") == 4, f"Expected 4 params, got {r3.get('paramCount')}"
    
    labels = [p["label"] for p in r3["params"]]
    expected = ["attack", "sustain", "mix", "output"]
    for e in expected:
        assert e in labels, f"Missing param: {e}. Got: {labels}"
    print("   All 4 params:", labels)
    
    # 4. Set attack param
    r4 = await bridge.evaluate("""async () => {
        const h = window.DAW_HELPERS;
        const au = h.primaryAudioUnitBox;
        const fx = h.effectBoxes(au);
        const werkstatt = fx[fx.length - 1];
        let oldVal = null, newVal = null;
        h.modify(() => {
            for (const pointer of werkstatt.parameters.pointerHub.filter()) {
                const pb = pointer.box;
                if (pb.label.getValue() === "attack") {
                    oldVal = pb.value.getValue();
                    pb.value.setValue(0.8);
                    newVal = pb.value.getValue();
                }
            }
        });
        return {oldVal, newVal};
    }""")
    print("4. Set attack:", r4)
    assert abs(r4["newVal"] - 0.8) < 0.01, f"attack not set: {r4}"
    print(f"   attack {r4['oldVal']} → {r4['newVal']} ✅")
    
    # 5. Set sustain param
    r5 = await bridge.evaluate("""async () => {
        const h = window.DAW_HELPERS;
        const au = h.primaryAudioUnitBox;
        const fx = h.effectBoxes(au);
        const werkstatt = fx[fx.length - 1];
        let oldVal = null, newVal = null;
        h.modify(() => {
            for (const pointer of werkstatt.parameters.pointerHub.filter()) {
                const pb = pointer.box;
                if (pb.label.getValue() === "sustain") {
                    oldVal = pb.value.getValue();
                    pb.value.setValue(0.3);
                    newVal = pb.value.getValue();
                }
            }
        });
        return {oldVal, newVal};
    }""")
    print("5. Set sustain:", r5)
    assert abs(r5["newVal"] - 0.3) < 0.01, f"sustain not set: {r5}"
    print(f"   sustain {r5['oldVal']} → {r5['newVal']} ✅")
    
    # 6. Read back code header
    r6 = await bridge.evaluate("""async () => {
        const h = window.DAW_HELPERS;
        const au = h.primaryAudioUnitBox;
        const fx = h.effectBoxes(au);
        const werkstatt = fx[fx.length - 1];
        const code = werkstatt.code?.getValue?.() ?? "";
        return {length: code.length, header: code.substring(0, 50)};
    }""")
    print("6. Code readback:", r6)
    assert "@werkstatt" in r6["header"], f"Bad header: {r6}"
    print(f"   Header: {r6['header'][:40]}... ✅")
    
    await bridge.stop()
    print("\n=== ALL E2E TESTS PASSED ===")

asyncio.run(main())

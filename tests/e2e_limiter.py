"""E2E test for werkstatt_limiter.js — brickwall limiter."""
import asyncio, sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"] = "/snap/bin/chromium"

from opendaw_mcp.bridge import HeadlessDawBridge

CODE = open("scripts/werkstatt_limiter.js").read()

async def main():
    bridge = HeadlessDawBridge()
    await bridge.start()

    r = await bridge.evaluate("""async () => {
        const h = window.DAW_HELPERS;
        h.modify(() => { h.api.createAudioTrack(h.primaryAudioUnitBox); });
        const ef = window.DAW_EffectFactories;
        if (!ef || !ef.Werkstatt) return {error: "no Werkstatt"};
        const au = h.primaryAudioUnitBox;
        h.modify(() => { h.api.insertEffect(au.audioEffects, ef.Werkstatt); });
        return {success: true};
    }""")
    print("1. Setup:", r)
    assert r.get("success")

    code_json = json.dumps(CODE)
    r2 = await bridge.evaluate(f"""async () => {{
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
        let compileError = null;
        try {{ await compiler.compile(ctx, h.editing, werkstatt, {code_json}); }}
        catch(e) {{ compileError = e.message?.substring(0, 300) || String(e).substring(0, 300); }}
        const params = [];
        for (const pointer of werkstatt.parameters.pointerHub.filter()) {{
            const pb = pointer.box;
            params.push({{label: pb.label.getValue(), value: pb.value.getValue(), defaultValue: pb.defaultValue.getValue()}});
        }}
        return {{compiled: !compileError, error: compileError, paramCount: params.length, params: params}};
    }}""")
    print(f"2. Compile: compiled={r2.get('compiled')}, error={r2.get('error')}, params={r2.get('paramCount')}")
    assert r2.get("compiled"), f"Compile failed: {r2}"
    assert r2.get("paramCount") == 5, f"Expected 5 params, got {r2.get('paramCount')}"
    
    labels = [p["label"] for p in r2["params"]]
    expected = ["ceiling", "release", "lookahead", "dither", "mix"]
    for e in expected:
        assert e in labels, f"Missing param: {e}. Got: {labels}"
    print(f"   All 5 params: {labels}")
    
    # Set ceiling
    r3 = await bridge.evaluate("""async () => {
        const h = window.DAW_HELPERS;
        const au = h.primaryAudioUnitBox;
        const fx = h.effectBoxes(au);
        const werkstatt = fx[fx.length - 1];
        let oldVal = null, newVal = null;
        h.modify(() => {
            for (const pointer of werkstatt.parameters.pointerHub.filter()) {
                const pb = pointer.box;
                if (pb.label.getValue() === "ceiling") {
                    oldVal = pb.value.getValue();
                    pb.value.setValue(0.8);
                    newVal = pb.value.getValue();
                }
            }
        });
        return {oldVal, newVal};
    }""")
    print("3. Set ceiling:", r3)
    assert abs(r3["newVal"] - 0.8) < 0.01, f"ceiling not set: {r3}"
    print(f"   ceiling {r3['oldVal']} → {r3['newVal']} ✅")
    
    # Set lookahead
    r4 = await bridge.evaluate("""async () => {
        const h = window.DAW_HELPERS;
        const au = h.primaryAudioUnitBox;
        const fx = h.effectBoxes(au);
        const werkstatt = fx[fx.length - 1];
        let oldVal = null, newVal = null;
        h.modify(() => {
            for (const pointer of werkstatt.parameters.pointerHub.filter()) {
                const pb = pointer.box;
                if (pb.label.getValue() === "lookahead") {
                    oldVal = pb.value.getValue();
                    pb.value.setValue(0.9);
                    newVal = pb.value.getValue();
                }
            }
        });
        return {oldVal, newVal};
    }""")
    print("4. Set lookahead:", r4)
    assert abs(r4["newVal"] - 0.9) < 0.01, f"lookahead not set: {r4}"
    print(f"   lookahead {r4['oldVal']} → {r4['newVal']} ✅")
    
    # Code readback
    r5 = await bridge.evaluate("""async () => {
        const h = window.DAW_HELPERS;
        const au = h.primaryAudioUnitBox;
        const fx = h.effectBoxes(au);
        const werkstatt = fx[fx.length - 1];
        const code = werkstatt.code?.getValue?.() ?? "";
        return {header: code.substring(0, 50)};
    }""")
    print("5. Code header:", r5)
    assert "@werkstatt" in r5["header"], f"Bad header: {r5}"
    print("   Header OK ✅")
    
    await bridge.stop()
    print("\n=== ALL E2E TESTS PASSED ===")

asyncio.run(main())

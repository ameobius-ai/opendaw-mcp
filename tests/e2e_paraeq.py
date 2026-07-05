"""E2E test for werkstatt_paraeq.js — parametric EQ with 3 bands + HP + LP."""
import asyncio, sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"] = "/snap/bin/chromium"

from opendaw_mcp.bridge import HeadlessDawBridge

CODE = open("scripts/werkstatt_paraeq.js").read()

async def main():
    bridge = HeadlessDawBridge()
    await bridge.start()

    # 1. Create audio track + Werkstatt
    r = await bridge.evaluate("""async () => {
        const h = window.DAW_HELPERS;
        h.modify(() => { h.api.createAudioTrack(h.primaryAudioUnitBox); });
        const ef = window.DAW_EffectFactories;
        if (!ef || !ef.Werkstatt) return {error: "no Werkstatt factory"};
        const au = h.primaryAudioUnitBox;
        h.modify(() => { h.api.insertEffect(au.audioEffects, ef.Werkstatt); });
        const fx = h.effectBoxes(au);
        return {success: true, fxCount: fx.length};
    }""")
    print("1. Setup:", r)
    assert r.get("success"), f"Failed: {r}"

    # 2. Compile paraeq code
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
        try {{
            await compiler.compile(ctx, h.editing, werkstatt, {code_json});
        }} catch(e) {{
            compileError = e.message?.substring(0, 300) || String(e).substring(0, 300);
        }}
        
        const params = [];
        for (const pointer of werkstatt.parameters.pointerHub.filter()) {{
            const pb = pointer.box;
            params.push({{label: pb.label.getValue(), value: pb.value.getValue(), defaultValue: pb.defaultValue.getValue()}});
        }}
        return {{compiled: !compileError, error: compileError, paramCount: params.length, params: params}};
    }}""")
    print(f"2. Compile: compiled={r2.get('compiled')}, error={r2.get('error')}, params={r2.get('paramCount')}")
    assert r2.get("compiled"), f"Compile failed: {r2}"
    assert r2.get("paramCount") == 12, f"Expected 12 params, got {r2.get('paramCount')}: {r2.get('params')}"
    
    labels = [p["label"] for p in r2["params"]]
    expected = ["band1_freq", "band1_gain", "band1_q", "band2_freq", "band2_gain", "band2_q",
                "band3_freq", "band3_gain", "band3_q", "hp_freq", "lp_freq", "mix"]
    for e in expected:
        assert e in labels, f"Missing param: {e}. Got: {labels}"
    print(f"   All 12 params: {labels}")
    
    # 3. Set band1_gain (boost low shelf)
    r3 = await bridge.evaluate("""async () => {
        const h = window.DAW_HELPERS;
        const au = h.primaryAudioUnitBox;
        const fx = h.effectBoxes(au);
        const werkstatt = fx[fx.length - 1];
        let oldVal = null, newVal = null;
        h.modify(() => {
            for (const pointer of werkstatt.parameters.pointerHub.filter()) {
                const pb = pointer.box;
                if (pb.label.getValue() === "band1_gain") {
                    oldVal = pb.value.getValue();
                    pb.value.setValue(6.0);
                    newVal = pb.value.getValue();
                }
            }
        });
        return {oldVal, newVal};
    }""")
    print("3. Set band1_gain:", r3)
    assert abs(r3["newVal"] - 6.0) < 0.01, f"band1_gain not set: {r3}"
    print(f"   band1_gain {r3['oldVal']} → {r3['newVal']} ✅")
    
    # 4. Set band2_q (narrow Q)
    r4 = await bridge.evaluate("""async () => {
        const h = window.DAW_HELPERS;
        const au = h.primaryAudioUnitBox;
        const fx = h.effectBoxes(au);
        const werkstatt = fx[fx.length - 1];
        let oldVal = null, newVal = null;
        h.modify(() => {
            for (const pointer of werkstatt.parameters.pointerHub.filter()) {
                const pb = pointer.box;
                if (pb.label.getValue() === "band2_q") {
                    oldVal = pb.value.getValue();
                    pb.value.setValue(3.5);
                    newVal = pb.value.getValue();
                }
            }
        });
        return {oldVal, newVal};
    }""")
    print("4. Set band2_q:", r4)
    assert abs(r4["newVal"] - 3.5) < 0.01, f"band2_q not set: {r4}"
    print(f"   band2_q {r4['oldVal']} → {r4['newVal']} ✅")
    
    # 5. Code readback
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

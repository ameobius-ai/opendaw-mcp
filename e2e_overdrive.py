#!/usr/bin/env python3
"""E2E test: werkstatt_overdrive DSP script — compile via ScriptCompiler, verify params."""
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from opendaw_mcp.bridge import HeadlessDawBridge


async def main():
    bridge = HeadlessDawBridge()
    await bridge.start()

    script_path = os.path.join(os.path.dirname(__file__), "scripts", "werkstatt_overdrive.js")
    with open(script_path, "r") as f:
        code = f.read()

    print(f"=== Script loaded: {len(code)} bytes ===")
    print(f"Header: {code.split(chr(10))[0]}")

    # Step 1: Add Werkstatt effect
    print("\n=== Step 1: Add Werkstatt effect ===")
    r = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        const ef = window.DAW_EffectFactories;
        const factory = ef.AudioNamed["Werkstatt"];
        if (!factory) return { error: "Werkstatt factory not found" };

        h.modify(() => {
            const au = h.allAUBoxes()[0];
            if (!au) return;
            h.api.insertEffect(au.audioEffects, factory);
        });

        const au = h.allAUBoxes()[0];
        const fxs = h.effectBoxes(au);
        return { effect_count: fxs.length, werkstatt_index: fxs.length - 1 };
    }""")
    print(f"Werkstatt added: {r}")
    assert not r.get("error"), f"Failed: {r}"
    werkstatt_idx = r.get("werkstatt_index", 0)

    # Step 2: Compile via ScriptCompiler
    print(f"\n=== Step 2: Compile code ({len(code)} bytes) ===")
    code_json = json.dumps(code)
    r = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const au = h.allAUBoxes()[0];
        const fxs = h.effectBoxes(au);
        const device = fxs[{werkstatt_idx}];
        if (!device) return {{ error: "Device not found" }};

        const ScriptCompiler = window.DAW_ScriptCompiler;
        if (!ScriptCompiler) return {{ error: "ScriptCompiler not available" }};

        const config = {{headerTag: "werkstatt", registryName: "werkstattProcessors", functionName: "werkstatt"}};
        const compiler = ScriptCompiler.create(config);
        const ctx = window.DAW_audioContext || new AudioContext();

        const source = {code_json};
        let compileError = null;
        try {{
            await compiler.compile(ctx, h.editing, device, source);
        }} catch(e) {{
            compileError = e.message?.substring(0, 300) || String(e).substring(0, 300);
        }}

        const params = [];
        for (const pointer of device.parameters.pointerHub.filter()) {{
            const pb = pointer.box;
            params.push({{
                label: pb.label.getValue(),
                value: pb.value.getValue(),
                defaultValue: pb.defaultValue.getValue(),
            }});
        }}

        return {{
            success: compileError === null,
            code_length: device.code.getValue().length,
            params_created: params.length,
            params: params,
            compile_error: compileError,
        }};
    }}""")
    print(f"Compile result: {json.dumps(r, indent=2)}")

    assert r.get("success"), f"Compile failed: {r.get('compile_error')}"
    assert r.get("code_length", 0) > 2000, f"Code too short: {r.get('code_length')}"
    assert r.get("params_created") == 5, f"Expected 5 params, got {r.get('params_created')}"
    print(f"✅ Compiled: {r.get('code_length')} bytes, {r.get('params_created')} params")

    param_names = [p["label"] for p in r.get("params", [])]
    expected = ["drive", "tone", "level", "bias", "dry"]
    assert param_names == expected, f"Param names mismatch: {param_names} vs {expected}"
    print(f"✅ Params: {param_names}")

    # Verify defaults (float32 tolerance)
    defaults = {p["label"]: p["defaultValue"] for p in r.get("params", [])}
    assert abs(defaults["drive"] - 0.4) < 0.01, f"drive default should be ~0.4, got {defaults['drive']}"
    assert abs(defaults["tone"] - 0.5) < 0.01, f"tone default should be ~0.5, got {defaults['tone']}"
    assert abs(defaults["level"] - 0.8) < 0.01, f"level default should be ~0.8, got {defaults['level']}"
    assert abs(defaults["dry"] - 0) < 0.01, f"dry default should be ~0, got {defaults['dry']}"
    print(f"✅ Defaults verified: drive={defaults['drive']}, tone={defaults['tone']}, level={defaults['level']}")

    # Step 3: set_param — drive to 0.8
    print("\n=== Step 3: set_param (drive → 0.8) ===")
    r = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const au = h.allAUBoxes()[0];
        const fxs = h.effectBoxes(au);
        const device = fxs[{werkstatt_idx}];
        let oldVal = 0, newVal = 0;

        h.modify(() => {{
            for (const pointer of device.parameters.pointerHub.filter()) {{
                const pb = pointer.box;
                if (pb.label.getValue() === 'drive') {{
                    oldVal = pb.value.getValue();
                    pb.value.setValue(0.8);
                    newVal = pb.value.getValue();
                }}
            }}
        }});

        return {{ param: 'drive', old: oldVal, new: newVal }};
    }}""")
    print(f"set_param: {r.get('old')} → {r.get('new')}")
    assert abs(r.get("old", 0) - 0.4) < 0.01, f"Default drive should be ~0.4, got {r.get('old')}"
    assert abs(r.get("new", 0) - 0.8) < 0.01, f"New drive should be ~0.8, got {r.get('new')}"
    print("✅ set_param verified")

    # Step 4: set_param — dry blend to 0.3 (parallel overdrive)
    print("\n=== Step 4: set_param (dry → 0.3) ===")
    r = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const au = h.allAUBoxes()[0];
        const fxs = h.effectBoxes(au);
        const device = fxs[{werkstatt_idx}];
        let oldVal = 0, newVal = 0;

        h.modify(() => {{
            for (const pointer of device.parameters.pointerHub.filter()) {{
                const pb = pointer.box;
                if (pb.label.getValue() === 'dry') {{
                    oldVal = pb.value.getValue();
                    pb.value.setValue(0.3);
                    newVal = pb.value.getValue();
                }}
            }}
        }});

        return {{ param: 'dry', old: oldVal, new: newVal }};
    }}""")
    print(f"set_param: {r.get('old')} → {r.get('new')}")
    assert abs(r.get("old", 0) - 0) < 0.01, f"Default dry should be ~0, got {r.get('old')}"
    assert abs(r.get("new", 0) - 0.3) < 0.01, f"New dry should be ~0.3, got {r.get('new')}"
    print("✅ parallel blend enabled (dry=0.3)")

    await bridge.stop()
    print("\n=== ALL E2E TESTS PASSED ===")


if __name__ == "__main__":
    asyncio.run(main())

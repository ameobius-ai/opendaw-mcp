#!/usr/bin/env python3
"""E2E test: werkstatt_stereo_delay DSP script — compile via MCP tools, verify params."""
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from opendaw_mcp.bridge import HeadlessDawBridge


async def main():
    bridge = HeadlessDawBridge()
    await bridge.start()

    # Read the script
    script_path = os.path.join(os.path.dirname(__file__), "scripts", "werkstatt_stereo_delay.js")
    with open(script_path, "r") as f:
        code = f.read()

    print(f"=== Script loaded: {len(code)} bytes ===")
    print(f"Header: {code.split(chr(10))[0]}")

    # Step 1: Add Werkstatt effect to AU 0
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
    assert not r.get("error"), f"Failed to add Werkstatt: {r}"
    werkstatt_idx = r.get("werkstatt_index", 0)

    # Step 2: Compile code via ScriptCompiler
    print(f"\n=== Step 2: Compile code ({len(code)} bytes) ===")
    code_json = json.dumps(code)
    r = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const au = h.allAUBoxes()[0];
        const fxs = h.effectBoxes(au);
        const device = fxs[{werkstatt_idx}];
        if (!device) return {{ error: "Device not found at index {werkstatt_idx}" }};

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

        // Read back params
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
    assert r.get("code_length", 0) > 2500, f"Code too short after compile: {r.get('code_length')}"
    assert r.get("params_created") == 6, f"Expected 6 params, got {r.get('params_created')}"
    print(f"✅ Compiled: {r.get('code_length')} bytes, {r.get('params_created')} params")

    # Verify param names
    param_names = [p["label"] for p in r.get("params", [])]
    expected = ["time_l", "time_r", "feedback", "tone", "mix", "pingpong"]
    assert param_names == expected, f"Param names mismatch: {param_names} vs {expected}"
    print(f"✅ Params: {param_names}")

    # Verify default values (float32 precision tolerance)
    defaults = {p["label"]: p["defaultValue"] for p in r.get("params", [])}
    assert abs(defaults["time_l"] - 350) < 1, f"time_l default should be ~350, got {defaults['time_l']}"
    assert abs(defaults["time_r"] - 450) < 1, f"time_r default should be ~450, got {defaults['time_r']}"
    assert abs(defaults["feedback"] - 0.35) < 0.01, f"feedback default should be ~0.35, got {defaults['feedback']}"
    assert abs(defaults["pingpong"] - 0) < 0.01, f"pingpong default should be ~0, got {defaults['pingpong']}"
    print(f"✅ Defaults verified: time_l={defaults['time_l']}, time_r={defaults['time_r']}, feedback={defaults['feedback']}")

    # Step 3: Set param — change feedback to 0.6
    print("\n=== Step 3: set_param (feedback → 0.6) ===")
    r = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const au = h.allAUBoxes()[0];
        const fxs = h.effectBoxes(au);
        const device = fxs[{werkstatt_idx}];
        let oldVal = 0, newVal = 0;

        h.modify(() => {{
            for (const pointer of device.parameters.pointerHub.filter()) {{
                const pb = pointer.box;
                if (pb.label.getValue() === 'feedback') {{
                    oldVal = pb.value.getValue();
                    pb.value.setValue(0.6);
                    newVal = pb.value.getValue();
                }}
            }}
        }});

        return {{ param: 'feedback', old: oldVal, new: newVal }};
    }}""")
    print(f"set_param: {r.get('old')} → {r.get('new')}")
    assert abs(r.get("old", 0) - 0.35) < 0.01, f"Default feedback should be ~0.35, got {r.get('old')}"
    assert abs(r.get("new", 0) - 0.6) < 0.01, f"New feedback should be ~0.6, got {r.get('new')}"
    print("✅ set_param verified")

    # Step 4: Set pingpong to 1 (enable ping-pong)
    print("\n=== Step 4: set_param (pingpong → 1.0) ===")
    r = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const au = h.allAUBoxes()[0];
        const fxs = h.effectBoxes(au);
        const device = fxs[{werkstatt_idx}];
        let oldVal = 0, newVal = 0;

        h.modify(() => {{
            for (const pointer of device.parameters.pointerHub.filter()) {{
                const pb = pointer.box;
                if (pb.label.getValue() === 'pingpong') {{
                    oldVal = pb.value.getValue();
                    pb.value.setValue(1.0);
                    newVal = pb.value.getValue();
                }}
            }}
        }});

        return {{ param: 'pingpong', old: oldVal, new: newVal }};
    }}""")
    print(f"set_param: {r.get('old')} → {r.get('new')}")
    assert abs(r.get("old", 0) - 0) < 0.01, f"Default pingpong should be ~0, got {r.get('old')}"
    assert abs(r.get("new", 0) - 1.0) < 0.01, f"New pingpong should be ~1.0, got {r.get('new')}"
    print("✅ pingpong enabled")

    await bridge.stop()
    print("\n=== ALL E2E TESTS PASSED ===")


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""Generate .opb preset files for openDAW Werkstatt scripts.

Uses headless DAW bridge to:
1. Create a Werkstatt audio effect
2. Compile the script code into it
3. Encode as preset via PresetEncoder.encodeEffects
4. Package as .opb bundle (ZIP: version, meta.json, preset.odp)
"""

import asyncio
import base64
import io
import json
import os
import sys
import time
import uuid
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from server import HeadlessDawBridge

DAW_URL = "http://localhost:5174"

# 5 selected Werkstatt presets — most universally useful DSP effects
PRESETS = [
    {
        "name": "Dark Saturation",
        "description": "Tape-style saturation with drive, bias, tone and dry/wet mix. DC-blocked tanh waveshaper with shelving tone control.",
        "script_file": "werkstatt_darksat.js",
        "label": "Dark Saturation",
    },
    {
        "name": "Plate Reverb",
        "description": "Schroeder plate reverb: 4 comb filters + 2 allpass per channel. Stereo decorrelated with M/S width control and predelay.",
        "script_file": "werkstatt_reverb.js",
        "label": "Plate Reverb",
    },
    {
        "name": "Cold Fold Distortion",
        "description": "Wavefolding distortion with bitcrush and sample-rate reduction. Drive into mirror-fold, then quantize and slew.",
        "script_file": "werkstatt_coldfold.js",
        "label": "Cold Fold Distortion",
    },
    {
        "name": "Stereo Phaser",
        "description": "6-stage stereo phaser with LFO modulation. Quadrature L/R phases for wide stereo image.",
        "script_file": "werkstatt_phaser.js",
        "label": "Stereo Phaser",
    },
    {
        "name": "Stereo Chorus",
        "description": "Modulated delay chorus with 90° offset L/R LFOs. Fractional delay read with feedback for thick stereo width.",
        "script_file": "werkstatt_chorus.js",
        "label": "Stereo Chorus",
    },
]

SCRIPTS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "openDAW", "examples", "werkstatt"
)
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "presets")


async def generate_preset(bridge: HeadlessDawBridge, preset: dict) -> bytes:
    """Generate a .opb bundle for one Werkstatt preset."""
    script_path = os.path.join(SCRIPTS_DIR, preset["script_file"])
    with open(script_path, "r") as f:
        code = f.read()

    code_b64 = base64.b64encode(code.encode("utf-8")).decode("ascii")
    label = preset["label"]

    # Use DAW_HELPERS + DAW globals to create effect, compile code, encode preset
    js = f"""
    async () => {{
        const h = window.DAW_HELPERS;
        const p = window.DAW;
        const EF = window.DAW_EffectFactories;
        const PE = window.DAW_PresetEncoder;
        const SC = window.DAW_ScriptCompiler;

        // Get first non-output AU
        const units = h.allAUBoxes();
        let au = units.find(u => u.type?.getValue?.() !== 3);
        if (!au) au = units[0];

        // Step 1: Add Werkstatt effect (in modify block)
        let effectBox;
        h.modify(() => {{
            effectBox = h.api.insertEffect(au.audioEffects, EF.Werkstatt);
        }});
        if (!effectBox) {{ throw new Error("insertEffect returned no box"); }}

        // Step 2: Set label (in modify block)
        h.modify(() => {{
            effectBox.label.setValue({json.dumps(label)});
        }});

        // Step 3: Compile script — ScriptCompiler.create() + compile()
        // compile() calls editing.modify() internally
        const config = {{headerTag: "werkstatt", registryName: "werkstattProcessors", functionName: "werkstatt"}};
        const compiler = SC.create(config);
        const ctx = window.DAW_audioContext;
        const code = atob("{code_b64}");
        await compiler.compile(ctx, h.editing, effectBox, code);

        // Step 4: Encode as audio-effect preset (ChainKind.Audio = 1)
        const presetBytes = PE.encodeEffects([effectBox], 1);
        const bytes = new Uint8Array(presetBytes);
        let binary = "";
        for (let i = 0; i < bytes.length; i++) {{
            binary += String.fromCharCode(bytes[i]);
        }}
        return btoa(binary);
    }}
    """

    result = await bridge.evaluate(js)
    if isinstance(result, dict) and result.get("error"):
        raise RuntimeError(f"Bridge error for {preset['name']}: {result['error']}")

    preset_b64 = result  # result is the base64 string returned from JS
    if not preset_b64 or not isinstance(preset_b64, str):
        raise RuntimeError(f"No result from bridge for {preset['name']}")

    preset_bytes = base64.b64decode(preset_b64)

    # Build .opb bundle (ZIP: version, meta.json, preset.odp)
    now = int(time.time() * 1000)
    meta = {
        "category": "audio-effect",
        "uuid": str(uuid.uuid4()),
        "name": preset["name"],
        "device": "Werkstatt",
        "description": preset["description"],
        "created": now,
        "modified": now,
    }

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("version", "1")
        zf.writestr("meta.json", json.dumps(meta, indent=2))
        zf.writestr("preset.odp", preset_bytes)

    return buf.getvalue()


async def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    bridge = HeadlessDawBridge()
    print("Starting bridge...")
    await bridge.start()
    print("Bridge ready.")

    for preset in PRESETS:
        print(f"\nGenerating: {preset['name']}...")
        try:
            opb_data = await generate_preset(bridge, preset)
            filename = preset["name"].replace(" ", "_") + ".opb"
            filepath = os.path.join(OUTPUT_DIR, filename)
            with open(filepath, "wb") as f:
                f.write(opb_data)
            print(f"  OK {filename} ({len(opb_data)} bytes)")
        except Exception as e:
            print(f"  FAILED: {e}")

    await bridge.stop()
    print(f"\nDone. Presets saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    asyncio.run(main())

"""Preset management demo — save and load Werkstatt effect presets.

This example demonstrates:
1. Creating a track with a Werkstatt effect
2. Compiling a custom DSP script into the Werkstatt
3. Saving the effect chain as a .opb preset file
4. Loading the preset back into a different project

Prerequisites:
- Vite dev server running (headless-daw on port 5174)
- opendaw-mcp installed: pip install opendaw-mcp
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from server import HeadlessDawBridge

DAW_URL = os.environ.get("OPENDAW_URL", "http://localhost:5174")

# A simple tape saturation script for the Werkstatt device
SATURATION_SCRIPT = """// @werkstatt demo_saturation 1 1
// @param drive 0.5 0 1 linear %
// @param mix 0.8 0 1 linear %
// @param output 0 0 1 linear %
class Processor {
    drive = 0.5
    mix = 0.8
    output = 0
    paramChanged(label, value) {
        if (label === "drive") this.drive = value
        else if (label === "mix") this.mix = value
        else if (label === "output") this.output = value
    }
    process(io, block) {
        const outGain = Math.pow(10, this.output * 0.4 - 0.2)
        for (let i = block.s0; i < block.s1; i++) {
            for (let ch = 0; ch < io.out.length; ch++) {
                const src = io.src[ch] || io.src[0]
                const dry = src[i]
                const wet = Math.tanh(dry * (1 + this.drive * 5)) * outGain
                io.out[ch][i] = dry * (1 - this.mix) + wet * this.mix
            }
        }
    }
}
"""


async def main():
    bridge = HeadlessDawBridge()
    print("Connecting to DAW...")
    await bridge.start()
    print("Connected.\n")

    # Step 1: Create a synth track
    print("=== Step 1: Create instrument track ===")
    result = await bridge.call_tool("mcp_opendaw_create_synth", {
        "unit_index": -1,
        "instrument_type": "Vaporisateur",
    })
    print(f"Created synth: {result[:80]}...")

    # Step 2: Add Werkstatt effect
    print("\n=== Step 2: Add Werkstatt effect ===")
    result = await bridge.call_tool("mcp_opendaw_add_effect", {
        "unit_index": 0,
        "effect_type": "Werkstatt",
    })
    print(f"Added Werkstatt: {result[:80]}...")

    # Step 3: Compile saturation script into Werkstatt
    print("\n=== Step 3: Compile DSP script ===")
    result = await bridge.call_tool("mcp_opendaw_set_script_device_code", {
        "unit_index": 0,
        "effect_index": 0,
        "code": SATURATION_SCRIPT,
    })
    print(f"Compiled: {result[:80]}...")

    # Step 4: Tweak parameters
    print("\n=== Step 4: Set parameters ===")
    result = await bridge.call_tool("mcp_opendaw_set_script_param", {
        "unit_index": 0,
        "effect_index": 0,
        "param_name": "drive",
        "value": 0.85,
    })
    print(f"Set drive=0.85: {result[:80]}...")

    result = await bridge.call_tool("mcp_opendaw_set_script_param", {
        "unit_index": 0,
        "effect_index": 0,
        "param_name": "mix",
        "value": 1.0,
    })
    print(f"Set mix=1.0: {result[:80]}...")

    # Step 5: Save as .opb preset
    print("\n=== Step 5: Save effect preset ===")
    preset_path = os.path.join(os.path.dirname(__file__), "..", "my_saturation.opb")
    result = await bridge.call_tool("mcp_opendaw_save_effect_preset", {
        "unit_index": 0,
        "filename": preset_path,
    })
    print(f"Saved preset: {result}")

    # Verify file exists
    if os.path.exists(preset_path):
        size = os.path.getsize(preset_path)
        print(f"  File: {preset_path} ({size} bytes)")
    else:
        print(f"  WARNING: File not found at {preset_path}")

    # Step 6: Load preset back (simulates importing into a new project)
    print("\n=== Step 6: Load effect preset ===")
    result = await bridge.call_tool("mcp_opendaw_load_effect_preset", {
        "filename": preset_path,
    })
    print(f"Loaded preset: {result}")

    # Step 7: Verify loaded parameters
    print("\n=== Step 7: Verify loaded parameters ===")
    result = await bridge.call_tool("mcp_opendaw_list_script_params", {
        "unit_index": 0,
        "effect_index": 0,
    })
    print(f"Original Werkstatt params: {result[:120]}...")

    await bridge.stop()
    print("\n=== Done! ===")
    print(f"Preset saved to: {preset_path}")
    print("You can share the .opb file with other openDAW users.")
    print("Drag and drop it onto openDAW to import.")


if __name__ == "__main__":
    asyncio.run(main())

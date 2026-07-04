#!/usr/bin/env python3
"""
Device-Specific Parameters Demo

Demonstrates the v1.9.0 + v1.9.1 device-specific parameter tools:
- NeuralAmp model loading (bypasses popup-based Tone3000 Select Flow)
- Vocoder modulator source + band count
- Compressor boolean params (lookahead, automakeup, autoattack, autorelease)
- Gate inverse
- Crusher bits
- Fold oversampling

This example creates a guitar-style chain: Compressor → NeuralAmp → Crusher → Fold
and a separate Vocoder demo, showing all non-float parameter types.
"""
import asyncio
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from server import bridge


async def main():
    await bridge.start()
    print("=== Device-Specific Parameters Demo ===\n")

    # ─── Guitar Chain: Compressor → NeuralAmp → Crusher → Fold ───
    print("--- Guitar FX Chain ---")

    # 1. Compressor with lookahead + auto features
    from server import mcp_opendaw_add_effect
    from server import mcp_opendaw_set_effect_parameter_bool

    r = await mcp_opendaw_add_effect(unit_index=0, effect_type='Compressor')
    print(f"1. Compressor added: {r}")

    # Enable lookahead for transient preservation
    r = await mcp_opendaw_set_effect_parameter_bool(
        unit_index=0, effect_index=1, parameter_name='lookahead', value=True)
    print(f"   lookahead=true: {r}")

    # Auto-makeup off (we'll set output manually)
    r = await mcp_opendaw_set_effect_parameter_bool(
        unit_index=0, effect_index=1, parameter_name='automakeup', value=False)
    print(f"   automakeup=false: {r}")

    # Auto attack/release on
    r = await mcp_opendaw_set_effect_parameter_bool(
        unit_index=0, effect_index=1, parameter_name='autoattack', value=True)
    print(f"   autoattack=true: {r}")

    r = await mcp_opendaw_set_effect_parameter_bool(
        unit_index=0, effect_index=1, parameter_name='autorelease', value=True)
    print(f"   autorelease=true: {r}")

    # 2. NeuralAmp with model loading
    from server import mcp_opendaw_set_neuralamp_model, mcp_opendaw_get_neuralamp_model

    r = await mcp_opendaw_add_effect(unit_index=0, effect_type='NeuralAmp')
    print(f"\n2. NeuralAmp added: {r}")

    # Load a minimal NAM model (in real use, load actual Tone3000 model JSON)
    nam_model = json.dumps({
        "version": "0.1",
        "architecture": "WaveNet",
        "config": {
            "layers": 5,
            "channels": 16,
            "kernel_size": 3,
            "dilation": [1, 2, 4, 8, 16]
        },
        "weights": []  # Real models have actual weights here
    })
    r = await mcp_opendaw_set_neuralamp_model(
        unit_index=0, effect_index=2, model_json=nam_model, label="My Amp", pack_id="custom")
    print(f"   model loaded: {r}")

    # Set mono to false (stereo processing)
    r = await mcp_opendaw_set_effect_parameter_bool(
        unit_index=0, effect_index=2, parameter_name='mono', value=False)
    print(f"   mono=false (stereo): {r}")

    # Verify model
    r = await mcp_opendaw_get_neuralamp_model(unit_index=0, effect_index=2)
    print(f"   model verify: {r}")

    # 3. Crusher for lo-fi bitcrush
    from server import mcp_opendaw_set_crusher_bits

    r = await mcp_opendaw_add_effect(unit_index=0, effect_type='Crusher')
    print(f"\n3. Crusher added: {r}")

    r = await mcp_opendaw_set_crusher_bits(
        unit_index=0, effect_index=3, bits=12)
    print(f"   bits=12 (subtle crush): {r}")

    # 4. Fold for harmonic saturation
    from server import mcp_opendaw_set_fold_oversampling

    r = await mcp_opendaw_add_effect(unit_index=0, effect_type='Fold')
    print(f"\n4. Fold added: {r}")

    r = await mcp_opendaw_set_fold_oversampling(
        unit_index=0, effect_index=4, oversampling=2)
    print(f"   oversampling=2 (4x, alias-free): {r}")

    # ─── Vocoder Demo ───
    print("\n--- Vocoder Demo ---")

    from server import mcp_opendaw_set_vocoder_modulator_source, mcp_opendaw_set_vocoder_band_count
    from server import mcp_opendaw_remove_effect

    # Remove guitar chain effects to clean up
    for i in [4, 3, 2, 1]:
        await mcp_opendaw_remove_effect(unit_index=0, effect_index=i)

    r = await mcp_opendaw_add_effect(unit_index=0, effect_type='Vocoder')
    print(f"Vocoder added: {r}")

    r = await mcp_opendaw_set_vocoder_band_count(
        unit_index=0, effect_index=1, band_count=32)
    print(f"   band_count=32 (high resolution): {r}")

    r = await mcp_opendaw_set_vocoder_modulator_source(
        unit_index=0, effect_index=1, source='noise-pink')
    print(f"   modulator=noise-pink: {r}")

    # Switch to white noise
    r = await mcp_opendaw_set_vocoder_modulator_source(
        unit_index=0, effect_index=1, source='noise-white')
    print(f"   modulator=noise-white: {r}")

    # ─── Summary ───
    print("\n=== Summary ===")
    print("v1.9.0 tools: set_neuralamp_model, set_vocoder_modulator_source,")
    print("              set_vocoder_band_count, set_fold_oversampling, set_crusher_bits")
    print("v1.9.1 tools: set_effect_parameter_bool, set_effect_parameter_int")
    print("All device-specific non-float parameter types now covered.")

    await bridge.stop()
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())

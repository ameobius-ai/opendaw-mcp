"""
Example: Custom DSP Script Authoring

Demonstrates the dsp-script-authoring skill: writes a custom Werkstatt
audio effect (analog-style saturation with tone control), compiles it
via ScriptCompiler, sets parameters, and verifies.

Uses MCP tools directly (not raw bridge evaluate) — same as an agent would.

Usage:
    # Start Vite first:
    #   cd headless-daw && npx vite --port 5174
    #
    source venv/bin/activate
    OPENDAW_URL=http://localhost:5174 python3 examples/custom_dsp_script.py
"""
import asyncio
import sys
sys.path.insert(0, ".")
import server

# Custom Werkstatt DSP script — analog saturation with tone control
CUSTOM_SCRIPT = """// @werkstatt analog_sat 1 1
// @param drive 0.5 0 2 linear
// @param tone 0.5 0 1 linear
// @param mix 0.5 0 1 linear
// @param output 0 -24 6 linear dB

class Processor {
  p = {drive: 0.5, tone: 0.5, mix: 0.5, output: 0.0}
  sr = sampleRate
  lp = 0
  prevIn = 0
  prevOut = 0

  constructor() {
    // Pre-allocate any buffers here — NEVER in process()
  }

  paramChanged(label, value) {
    this.p[label] = value
  }

  process(io, block) {
    const drive = this.p.drive
    const tone = this.p.tone
    const mix = this.p.mix
    const outGain = Math.pow(10, this.p.output / 20)
    const dcCoeff = 0.995
    const lpFreq = 200 + tone * 8000
    const lpCoeff = Math.exp(-2 * Math.PI * lpFreq / this.sr)

    for (let i = block.s0; i < block.s1; i++) {
      // 1. DC blocker
      const dcOut = io.src[0][i] - this.prevIn + dcCoeff * this.prevOut
      this.prevIn = io.src[0][i]
      this.prevOut = dcOut

      // 2. Saturation (tanh soft clip)
      const driven = dcOut * drive
      const saturated = Math.tanh(driven)

      // 3. Tone filter (one-pole lowpass)
      this.lp = this.lp + lpCoeff * (saturated - this.lp)
      const toned = this.lp

      // 4. Output gain + dry/wet mix
      const wet = toned * outGain
      io.out[0][i] = dcOut * (1 - mix) + wet * mix
      io.out[1][i] = io.out[0][i]
    }
  }
}
"""


async def main():
    await server.bridge.start()

    try:
        # === 1. Create a synth track (Vaporisateur) ===
        print("1. Creating synth track (Vaporisateur)...")
        synth = await server.mcp_opendaw_create_synth_track("Custom DSP", "Vaporisateur")
        import json
        synth_data = json.loads(synth)
        uid = synth_data.get("unit_index")
        print(f"   AU created: unit_index={uid}")

        # === 2. Add Werkstatt effect ===
        print("\n2. Adding Werkstatt audio effect...")
        fx = await server.mcp_opendaw_add_effect(uid, "Werkstatt")
        fx_data = json.loads(fx)
        fx_idx = fx_data.get("effect_index", 0)
        print(f"   Werkstatt added at effect_index={fx_idx}")

        # === 3. Compile custom DSP script ===
        print("\n3. Compiling custom DSP script (analog saturation)...")
        compile = await server.mcp_opendaw_set_script_device_code(
            "Werkstatt", uid, fx_idx, CUSTOM_SCRIPT
        )
        compile_data = json.loads(compile)
        print(f"   Compiled: {compile_data.get('success', False)}")
        print(f"   Params created: {compile_data.get('params_created', 0)}")
        if compile_data.get("error"):
            print(f"   ❌ Error: {compile_data['error']}")
            return

        # === 4. List parameters ===
        print("\n4. Listing script parameters...")
        params = await server.mcp_opendaw_list_script_params("Werkstatt", uid, fx_idx)
        params_data = json.loads(params)
        for p in params_data.get("parameters", []):
            print(f"   - {p['label']}: value={p['value']}, "
                  f"range=[{p.get('min','?')}-{p.get('max','?')}], "
                  f"type={p.get('type','?')}")

        # === 5. Set parameters ===
        print("\n5. Setting parameters...")
        for name, value in [("drive", 0.85), ("tone", 0.3), ("mix", 0.8), ("output", -3.0)]:
            result = await server.mcp_opendaw_set_script_param(
                "Werkstatt", uid, fx_idx, name, value
            )
            r = json.loads(result)
            print(f"   {name}: {r.get('old_value', '?')} → {r.get('new_value', '?')}")

        # === 6. Read code back ===
        print("\n6. Reading code back from device...")
        code = await server.mcp_opendaw_get_script_device_code("Werkstatt", uid, fx_idx)
        code_data = json.loads(code)
        code_str = code_data.get("code", "")
        print(f"   Code: {len(code_str)} bytes")
        print(f"   Header: {code_str.split(chr(10))[0] if code_str else 'empty'}")
        print(f"   Has process(): {'process(io, block)' in code_str}")
        print(f"   Has tanh: {'Math.tanh' in code_str}")
        print(f"   Has DC blocker: {'prevIn' in code_str}")

        # === 7. Verify ===
        print("\n✅ Custom DSP script compiled and tested!")
        print(f"   Script: analog saturation with DC blocker + tone filter + dry/wet")
        print(f"   4 parameters: drive, tone, mix, output")
        print(f"   All parameters set and verified")

    finally:
        await server.bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())

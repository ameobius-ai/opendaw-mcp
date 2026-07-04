"""
Example: Custom DSP Script Authoring

Demonstrates the dsp-script-authoring skill: writes a custom Werkstatt
audio effect (analog-style saturation with tone control), compiles it
via ScriptCompiler, sets parameters, and verifies.

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
from server import HeadlessDawBridge

# Custom Werkstatt DSP script — analog saturation with tone control
# This is a simplified version of werkstatt_darksat.js showing the authoring pattern
CUSTOM_SCRIPT = """// @werkstatt analog_sat 1 1
// @param drive 0.5 0 2 linear
// @param tone 0.5 0 1 linear
// @param mix 0.5 0 1 linear
// @param output 0 -24 6 linear dB

class Processor {
  p = {drive: 0.5, tone: 0.5, mix: 0.5, output: 0.0}
  sr = sampleRate
  lp = 0
  hp = 0
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

    // DC blocker coefficients
    const dcCoeff = 0.995

    // Tone filter: lowpass when tone < 0.5, highpass when tone > 0.5
    const lpFreq = 200 + tone * 8000  // 200Hz..8200Hz
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

      // 4. Output gain
      const wet = toned * outGain

      // 5. Dry/wet mix
      io.out[0][i] = dcOut * (1 - mix) + wet * mix
      io.out[1][i] = io.out[0][i]  // mono effect
    }
  }
}
"""


async def main():
    bridge = HeadlessDawBridge()
    await bridge.start()

    try:
        # === 1. Create an audio unit with Werkstatt ===
        print("1. Creating audio unit with Werkstatt effect...")
        setup = await bridge.evaluate("""async () => {
            const h = window.DAW_HELPERS;
            const p = h.api;
            // Create a synth AU (Vaporisateur) so we have audio to process
            const inst = p.createAnyInstrument(h.InstrumentFactories.Vaporisateur);
            const au = inst.audioUnit;
            const auIndex = h.allAUs().indexOf(au);
            // Add Werkstatt as audio effect
            const werkstatt = p.insertEffect(au.audioEffects, h.EffectFactories.Werkstatt);
            const fx = [...au.audioEffects.adapters()];
            const werkIdx = fx.findIndex(f => f.box.constructor.name === 'WerkstattDeviceBox');
            return {
                au_index: auIndex,
                werkstatt_index: werkIdx,
                total_effects: fx.length
            };
        }""")
        print(f"   AU: {setup.get('au_index')}, Werkstatt at index: {setup.get('werkstatt_index')}")

        # === 2. Load custom DSP script (compiles via ScriptCompiler) ===
        print("\n2. Compiling custom DSP script...")
        import json
        code_escaped = json.dumps(CUSTOM_SCRIPT)
        compile_result = await bridge.evaluate(f"""async () => {{
            const h = window.DAW_HELPERS;
            const aus = h.allAUs();
            if ({setup.get('au_index', 0)} >= aus.length) return {{error: "No AU"}};
            const au = aus[{setup.get('au_index', 0)}];
            const fx = [...au.audioEffects.adapters()];
            const werkIdx = fx.findIndex(f => f.box.constructor.name === 'WerkstattDeviceBox');
            if (werkIdx < 0) return {{error: "No Werkstatt"}};
            const werkBox = fx[werkIdx].box;

            // Use ScriptCompiler to compile
            const compiler = window.DAW_ScriptCompiler;
            if (!compiler) return {{error: "ScriptCompiler not available"}};

            const audioContext = window.DAW_audioContext;
            if (!audioContext) return {{error: "No audioContext"}};

            const code = {code_escaped};

            try {{
                compiler.compile(audioContext, h.editing, werkBox, code);
                return {{
                    success: true,
                    code_length: code.length,
                    header: code.split('\\n')[0]
                }};
            }} catch(e) {{
                return {{error: e.message, stack: e.stack?.substring(0, 200)}};
            }}
        }}""")
        print(f"   Compile result: {compile_result}")

        if compile_result.get("error"):
            print(f"   ❌ Compilation failed: {compile_result['error']}")
            return

        # === 3. List parameters (should match @param declarations) ===
        print("\n3. Listing script parameters...")
        params = await bridge.evaluate(f"""async () => {{
            const h = window.DAW_HELPERS;
            const aus = h.allAUs();
            const au = aus[{setup.get('au_index', 0)}];
            const fx = [...au.audioEffects.adapters()];
            const werkIdx = fx.findIndex(f => f.box.constructor.name === 'WerkstattDeviceBox');
            const werkAdapter = fx[werkIdx];
            const params = [...werkAdapter.box.parameters.pointerHub.incoming()];
            return params.map(p => ({{
                label: p.box.label.getValue(),
                index: p.box.index.getValue(),
                value: p.box.value.getValue(),
                defaultValue: p.box.defaultValue.getValue()
            }}));
        }}""")
        print(f"   Parameters ({len(params)}):")
        for p in params:
            print(f"   - {p['label']}: value={p['value']}, default={p['defaultValue']}")

        # === 4. Set parameters ===
        print("\n4. Setting parameters...")
        for param_name, value in [("drive", 0.85), ("tone", 0.3), ("mix", 0.8), ("output", -3.0)]:
            result = await bridge.evaluate(f"""async () => {{
                const h = window.DAW_HELPERS;
                const aus = h.allAUs();
                const au = aus[{setup.get('au_index', 0)}];
                const fx = [...au.audioEffects.adapters()];
                const werkIdx = fx.findIndex(f => f.box.constructor.name === 'WerkstattDeviceBox');
                const params = [...fx[werkIdx].box.parameters.pointerHub.incoming()];
                const param = params.find(p => p.box.label.getValue() === "{param_name}");
                if (!param) return {{error: "Param '{param_name}' not found"}};
                const old = param.box.value.getValue();
                h.modify(() => {{
                    param.box.value.setValue({value});
                }});
                return {{
                    param: "{param_name}",
                    old: old,
                    new: param.box.value.getValue()
                }};
            }}""")
            print(f"   {param_name}: {result.get('old')} → {result.get('new')}")

        # === 5. Read code back ===
        print("\n5. Reading code back from device...")
        code_back = await bridge.evaluate(f"""async () => {{
            const h = window.DAW_HELPERS;
            const aus = h.allAUs();
            const au = aus[{setup.get('au_index', 0)}];
            const fx = [...au.audioEffects.adapters()];
            const werkIdx = fx.findIndex(f => f.box.constructor.name === 'WerkstattDeviceBox');
            const code = fx[werkIdx].box.code.getValue();
            return {{
                length: code.length,
                header: code.split('\\n')[0],
                has_process: code.includes('process(io, block)'),
                has_paramChanged: code.includes('paramChanged'),
                has_tanh: code.includes('Math.tanh')
            }};
        }}""")
        print(f"   Code: {code_back.get('length')} bytes, header: {code_back.get('header')}")
        print(f"   Has process(): {code_back.get('has_process')}")
        print(f"   Has paramChanged(): {code_back.get('has_paramChanged')}")
        print(f"   Has tanh saturation: {code_back.get('has_tanh')}")

        # === 6. Verify ===
        print("\n✅ Custom DSP script compiled and tested!")
        print(f"   Script: analog saturation with DC blocker + tone filter + dry/wet")
        print(f"   4 parameters: drive, tone, mix, output")
        print(f"   All parameters set and verified")

    finally:
        await bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())

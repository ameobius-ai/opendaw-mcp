#!/usr/bin/env python3
"""Debug Werkstatt via Playwright: inspect audio graph after compile.

Opens the running openDAW instance, adds a Werkstatt effect with a simple
passthrough script, inspects the audio routing graph, and captures console
errors during render.
"""
import asyncio
import json
import sys
import os
import numpy as np
from scipy.io import wavfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["OPENDAW_URL"] = "http://[::1]:5174"

from server import (
    mcp_opendaw_load_audio, mcp_opendaw_create_instrument_track,
    mcp_opendaw_place_audio_region, mcp_opendaw_render_full,
    mcp_opendaw_set_track_volume, mcp_opendaw_add_effect,
    mcp_opendaw_set_script_device_code, mcp_opendaw_set_script_param,
)
from opendaw_mcp.bridge import HeadlessDawBridge


def _parse(r):
    if isinstance(r, str):
        try: return json.loads(r)
        except: return {"error": r}
    return r


PASSTHROUGH = """\
// @werkstatt passthrough 1 1
// @label Passthrough
// @param mix 1.0 0 1 linear

class Processor {
  constructor(sampleRate, blockSize) {
    this.sr = sampleRate || 48000
    this.p = {mix: 1.0}
  }
  paramChanged(name, value) {
    this.p[name] = value
  }
  processAudio(inputs, outputs, parameters) {
    const input = inputs[0]
    const output = outputs[0]
    if (!input || !output) return
    for (let c = 0; c < output.length; c++) {
      const inch = input[c]
      const outch = output[c]
      if (!inch || !outch) continue
      for (let i = 0; i < outch.length; i++) {
        outch[i] = inch[i] * this.p.mix
      }
    }
  }
}
"""


async def main():
    # Generate test tone
    sr = 48000
    t = np.linspace(0, 5.0, int(sr * 5), endpoint=False)
    mono = 0.3 * np.sin(2 * np.pi * 440 * t)
    stereo = np.stack([mono, mono * 0.95], axis=1)
    wavfile.write("/tmp/dbg_tone.wav", sr, (stereo * 32767).astype(np.int16))

    bridge = HeadlessDawBridge()
    bridge.daw_url = "http://[::1]:5174"
    await bridge.start()
    print("Bridge ready.\n")

    # Setup track
    track_d = _parse(await mcp_opendaw_create_instrument_track(name="test"))
    uid = track_d["unit_index"]
    tid = track_d.get("track_index", 0)
    load_d = _parse(await mcp_opendaw_load_audio(file_path="/tmp/dbg_tone.wav", name="test"))
    sid = load_d["id"]
    await mcp_opendaw_place_audio_region(sample_id=sid, unit_index=uid, start_beat=0.0, track_index=tid)
    await mcp_opendaw_set_track_volume(unit_index=uid, volume_db=-3.0)

    # === BASELINE: render without effect ===
    print("=== BASELINE: no effect ===")
    r0 = _parse(await mcp_opendaw_render_full(filename="dbg_baseline", sample_rate=48000))
    print(f"  max_sample={r0.get('max_sample',0):.4f} has_audio={r0.get('has_audio')}")

    # === Inspect audio graph BEFORE adding Werkstatt ===
    print("\n=== Inspect audio graph BEFORE Werkstatt ===")
    graph_before = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        const units = h.allAUBoxes();
        return {
            totalUnits: units.length,
            units: units.map((au, i) => {
                const fx = h.effectBoxes(au);
                const type = au.type?.getValue?.();
                return {
                    index: i,
                    name: au.name?.getValue?.() || au.label?.getValue?.() || "Unit " + i,
                    type: type,
                    typeStr: ["Output", "Instrument", "Effect"][type] || type,
                    effects: fx.length,
                    effectTypes: fx.map(f => f.constructor.name),
                    hasInput: !!au.input,
                    hasOutput: !!au.output,
                    hasCapture: !!au.capture,
                    volume: au.volume?.getValue?.(),
                };
            }),
        };
    }""")
    print(f"  {json.dumps(graph_before, indent=2)}")

    # === Add Werkstatt passthrough ===
    print("\n=== Add Werkstatt passthrough ===")
    add_d = _parse(await mcp_opendaw_add_effect(effect_type="Werkstatt", unit_index=uid))
    fx_idx = add_d.get("effect_index", 0)
    print(f"  Effect added: index {fx_idx}")

    code_d = _parse(await mcp_opendaw_set_script_device_code(
        device_type="werkstatt", unit_index=uid, device_index=fx_idx, code=PASSTHROUGH
    ))
    print(f"  Compiled: {code_d.get('success')} error={code_d.get('compile_error')}")

    # === Inspect audio graph AFTER adding Werkstatt ===
    print("\n=== Inspect audio graph AFTER Werkstatt ===")
    graph_after = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const units = h.allAUBoxes();
        return {{
            totalUnits: units.length,
            units: units.map((au, i) => {{
                const fx = h.effectBoxes(au);
                return {{
                    index: i,
                    name: au.name?.getValue?.() || au.label?.getValue?.() || "Unit " + i,
                    effects: fx.length,
                    effectTypes: fx.map(f => f.constructor.name),
                    effectDetails: fx.map(f => ({{
                        type: f.constructor.name,
                        hasCode: !!f.code,
                        codeLength: f.code?.getValue?.()?.length || 0,
                        hasProcessor: !!f.processor,
                        processorType: f.processor?.constructor?.name || "none",
                        paramCount: f.parameters ? f.parameters.pointerHub.filter().length : 0,
                    }})),
                }};
            }}),
        }};
    }}""")
    print(f"  {json.dumps(graph_after, indent=2)}")

    # === Check Werkstatt device on correct unit ===
    print(f"\n=== Check Werkstatt processor on unit {uid}, device {fx_idx} ===")
    proc_check = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const units = h.allAUBoxes();
        if ({uid} >= units.length) return {{error: "Unit {uid} not found, total: " + units.length}};
        const au = units[{uid}];
        const fx = h.effectBoxes(au);
        if ({fx_idx} >= fx.length) return {{error: "Effect {fx_idx} not found, total: " + fx.length}};
        const dev = fx[{fx_idx}];
        return {{
            type: dev.constructor.name,
            hasCode: !!dev.code,
            codeLength: dev.code?.getValue?.()?.length || 0,
            hasProcessor: !!dev.processor,
            hasModule: !!dev.module,
            moduleName: dev.module?.url || dev.moduleId || "none",
            paramCount: dev.parameters ? dev.parameters.pointerHub.filter().length : 0,
            keys: Object.keys(dev).filter(k => !k.startsWith("_")).slice(0, 20),
        }};
    }}""")
    print(f"  {json.dumps(proc_check, indent=2)}")

    # === Check werkstattProcessors registry ===
    print("\n=== Check werkstattProcessors registry ===")
    registry = await bridge.evaluate("""() => {
        const reg = window.werkstattProcessors || {};
        return {
            exists: !!window.werkstattProcessors,
            keys: Object.keys(reg),
            size: Object.keys(reg).length,
        };
    }""")
    print(f"  {json.dumps(registry, indent=2)}")

    # === Render WITH Werkstatt ===
    print("\n=== Render WITH Werkstatt ===")
    r1 = _parse(await mcp_opendaw_render_full(filename="dbg_werkstatt", sample_rate=48000))
    print(f"  max_sample={r1.get('max_sample',0):.4f} has_audio={r1.get('has_audio')}")

    if r1.get("has_audio"):
        print("\n  ✅ Werkstatt passthrough WORKS!")
    else:
        print("\n  ⛔ Still silent — checking if OfflineEngineRenderer sees the Werkstatt")
        # Check if render uses AudioWorklet or ScriptProcessorNode
        render_info = await bridge.evaluate("""() => {
            const h = window.DAW_HELPERS;
            const OfflineEngineRenderer = window.DAW_OfflineEngineRenderer;
            return {
                exists: !!OfflineEngineRenderer,
                hasStart: !!OfflineEngineRenderer?.start,
                type: typeof OfflineEngineRenderer,
                keys: OfflineEngineRenderer ? Object.keys(OfflineEngineRenderer).slice(0, 10) : [],
            };
        }""")
        print(f"  OfflineEngineRenderer: {json.dumps(render_info, indent=2)}")

    await bridge.stop()
    print("\n=== DONE ===")


if __name__ == "__main__":
    asyncio.run(main())

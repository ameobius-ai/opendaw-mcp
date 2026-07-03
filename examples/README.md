# openDAW MCP — Usage Examples

This directory contains example scripts showing how to use the MCP tools to create music programmatically.

## Files

| File | Description |
|------|-------------|
| `create_beat.py` | Create a 4-bar drum beat with Playfield (kick, snare, hi-hat) |
| `create_chord_progression.py` | Create a chord progression with Vaporisateur synth |
| `mix_workflow.py` | Full mixing workflow: set levels, add effects, route sends |
| `render_stems.py` | Render individual stems and full mix with LUFS targeting |
| `automation_sweep.py` | Create filter cutoff automation sweep on a synth |
| `modular_patch.py` | Modular system patch: AU → Gain → Delay → Output with patch cables |
| `full_production_pipeline.py` | Complete track from scratch: synth + drums + DSP + automation + render |
| `full_production_pipeline_v2.py` | Enhanced pipeline with modular routing and scriptable devices |
| `render_convert.py` | Render mix and convert to MP3/FLAC via ffmpeg |
| `instrument_automation.py` | Automate instrument parameters (Vaporisateur filter sweep) |
| `device_specific_params.py` | Control device-specific params (Vocoder, Crusher, Fold, StereoTool) |
| `scriptable_devices_demo.py` | Apparat/Werkstatt/Spielwerk custom DSP scripts |
| `warp_marker_tempo_match.py` | Warp markers for tempo-matching audio regions |
| `dawproject_export.py` | Export to .dawproject format (Bitwig/Ableton/rePitch interop) |
| `mastering_pipeline.py` | Full mastering chain: render → measure LUFS → auto-gain → stems → MP3 |
| `metronome_settings.py` | Configure metronome: enable, gain, subdivision, monophonic mode |

## Prerequisites

```bash
# Terminal 1: Start openDAW
cd openDAW && npm run dev

# Terminal 2: Start MCP server
cd opendaw-mcp
source venv/bin/activate
python server.py
```

## Using with AI Agents

These tools are designed to be called by AI agents via MCP. Here's a typical conversation flow:

1. **Create a project**: `create_note_track` → `create_note_region`
2. **Add notes**: `create_note_event` with positions and pitches
3. **Add instruments**: `create_synth` (Vaporisateur, Nano, etc.)
4. **Add effects**: `add_effect` (Delay, Reverb, Compressor, etc.)
5. **Mix**: `set_track_volume`, `set_effect_parameter`, `create_send`
6. **Render**: `render_stems` or `render_mix`

## Using with Python Directly

```python
import asyncio
import server

async def main():
    # Start the bridge
    await server.bridge.start()
    
    # Create a synth
    result = await server.mcp_opendaw_create_synth("Vaporisateur")
    print(f"Created: {result}")
    
    # Add a delay effect
    result = await server.mcp_opendaw_add_effect(0, "Delay")
    print(f"Added effect: {result}")
    
    # Set delay time
    result = await server.mcp_opendaw_set_effect_parameter(0, 0, "time", 0.5)
    print(f"Set parameter: {result}")
    
    # Stop the bridge
    await server.bridge.stop()

asyncio.run(main())
```

# Examples

36 Python examples covering every aspect of opendaw-mcp. All runnable with a live DAW bridge.

## Genre Templates (8)

Full genre starting points — E2E verified with real note counts.

| Example | Genre | BPM | Key | Description |
|---------|-------|-----|-----|-------------|
| `genre_techno.py` | Techno | 130 | — | Driving 4-on-floor, hypnotic patterns |
| `genre_coldwave.py` | Coldwave | 100 | Am | Dark post-punk, Dattorro + Waveshaper |
| `genre_ambient.py` | Ambient | 70 | C | Pad + bell + texture, long reverbs |
| `genre_hiphop.py` | Hip-hop | 85 | Ab | Boom bap, 808 bass |
| `genre_dnb.py` | DnB | 174 | F | Amen break, reese + sub |
| `genre_house.py` | House | 124 | F | 4-on-floor, off-beat stabs |
| `genre_lofi.py` | Lo-fi | 82 | — | Swung drums, ii-V-I jazz chords |
| `genre_trap.py` | Trap | 145 | F | Fast hi-hat rolls, gliding 808 |

```bash
python examples/genre_house.py
```

## Production Pipelines

| Example | Description |
|---------|-------------|
| `full_production_pipeline.py` | Full track: drums → bass → chords → lead → mix → render |
| `full_production_pipeline_v2.py` | Enhanced pipeline with mastering |
| `mastering_pipeline.py` | LUFS targeting, multiband, true peak control |
| `mix_workflow.py` | Volume, pan, sends, buses, A/B comparison |

## Synth & Instrument Control

| Example | Description |
|---------|-------------|
| `create_beat.py` | Basic drum pattern creation |
| `create_chord_progression.py` | Chord progressions from names |
| `instrument_automation.py` | Automating synth parameters |
| `device_specific_params.py` | Vaporisateur, Waveshaper, Revamp, Tidal |
| `metronome_settings.py` | Metronome configuration |

## Effects & Routing

| Example | Description |
|---------|-------------|
| `modular_patch.py` | Modular system: modules + patch cables |
| `scriptable_devices_demo.py` | Werkstatt/Apparat/Spielwerk scripting |
| `custom_dsp_script.py` | Loading custom JS DSP code |

## Export & Rendering

| Example | Description |
|---------|-------------|
| `render_convert.py` | Render to WAV, convert to MP3/FLAC |
| `render_stems.py` | Per-stem export |
| `dawproject_export.py` | .dawproject export (Bitwig/Ableton compatible) |
| `warp_marker_tempo_match.py` | Warp markers for tempo matching |

## Suno Integration

| Example | Description |
|---------|-------------|
| `suno_to_opendaw.py` | Import a Suno track into openDAW |
| `suno_stems_to_opendaw.py` | Split Suno track → stems → import into DAW |

## Orchestration

| Example | Description |
|---------|-------------|
| `orchestration_demo.py` | All 8 orchestration tools in one demo |
| `automation_sweep.py` | Filter sweeps, volume fades |
| `song_structure_demo.py` | Arrangement markers: intro/verse/chorus/bridge/outro |
| `preset_management.py` | Save/load .opb presets |
| `music_theory_demo.py` | Use shared note/chord/scale data to compute pitches, build progressions |

## Running examples

```bash
# Start the DAW bridge first
cd openDAW/headless-daw && npx vite --port 5174 &

# Run any example
cd opendaw-mcp
source venv/bin/activate
python examples/genre_dnb.py
```

All examples use the `OpendawServer` class and call MCP tools directly:

```python
import asyncio
from opendaw_mcp.server import OpendawServer

async def main():
    server = OpendawServer()
    await server.bridge.start()

    # ... your tool calls here ...

    await server.bridge.stop()

asyncio.run(main())
```

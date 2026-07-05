# Examples

58 Python examples covering every aspect of opendaw-mcp. All runnable with a live DAW bridge.

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
| `create_melody.py` | Melody from scale degrees + rhythmic pattern (14 scales) |
| `create_bassline.py` | Bassline from root + rhythmic pattern (low octave, high velocity) |
| `create_arpeggio.py` | Arpeggios from chord names — 6 patterns, 6 rates |
| `humanize_notes.py` | Humanize MIDI: velocity/timing/duration variation + swing |
| `create_harmony.py` | Generate harmony parts — diatonic + chromatic intervals |
| `create_counterpoint.py` | Counter-melody in contrary motion |
| `reverse_invert_notes.py` | Melodic variation: retrograde + mirror inversion |
| `create_drum_fill.py` | Drum fills/transitions: 5 types, adjustable density |
| `create_ostinato.py` | Repeating melodic pattern as foundation layer |
| `create_crescendo.py` | Crescendo/decrescendo: linear, exp, log curves |
| `apply_swing.py` | Pure swing feel: 16th/8th grid, classic hip-hop groove |
| `create_polyrhythm.py` | Polyrhythms: 3:4, 2:3, 5:7 cross-rhythms |
| `create_scale_run.py` | Ascending/descending scale runs: fills, transitions, build-ups |
| `create_call_response.py` | Call-and-response: antecedent/consequent phrase structure |
| `create_walking_bass.py` | Walking bass over chord progressions: jazz/blues/swing |
| `apply_sidechain.py` | Sidechain ducking: classic house/techno pumping effect |
| `create_ghost_notes.py` | Ghost notes: funk/R&B groove enhancer |
| `apply_velocity_curve.py` | Velocity envelopes: ramp/arc/trough/power curves for expressive dynamics |
| `apply_articulation.py` | Articulation: staccato/legato/tenuto/accent for phrasing character |
| `create_riser.py` | Build-up risers: exp/linear/log pitch sweeps for transitions |
| `create_stab.py` | Rhythmic chord stabs: house off-beat, funky ghost notes, disco 16ths |
| `create_break.py` | Classic drum breaks: Amen, Think, Funky Drummer, with variation + swing |
| `create_chop.py` | Pitch chopping: reverse (Dilla), stutter (glitch), shuffle (Madlib), ping-pong, gate, bass chop |
| `create_trill.py` | Two-note trills: baroque 16th, fast 32nd, slow 8th, jazz triplet, minor 3rd |
| `create_glissando.py` | Scale runs: chromatic, major, pentatonic, descending, whole tone |
| `create_sequence.py` | Transposed repetition: baroque 4th, jazz 2nd, film 5th, fade-out, rising quint |
| `create_pedal_point.py` | Sustained bass under chords: retriggered, sustained, jazz 7ths, slow, waltz |

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

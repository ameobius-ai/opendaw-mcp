# Stems & Presets

4 tools for stem separation and preset management.

## Stem Splitter (2)

| Tool | Description |
|------|-------------|
| `list_split_modes` | List all available stem separation modes with SDR scores |
| `split_stems` | Split an audio file into stems using SOTA models. 7 modes. Optional auto-import |

## Stem separation modes

| Mode | Model | Stems | Best for |
|------|-------|-------|----------|
| `ensemble` | BS-Roformer + HTDemucs | 4 | Best quality, slowest |
| `scnet` | SCNet | 4 | Sparse compression network |
| `bs6` | BS-Roformer 6-stem | 6 | drums/bass/vocals/other/guitar/piano |
| `polarformer` | MelBand Roformer | 4 | Polarized separation |
| `dereverb` | BS-Roformer dereverb | 1 | Remove reverb from a stem |
| `drumsep` | Drum separation | 4+ | Kick/snare/hat/toms |
| `denoise` | MelBand Roformer | 1 | Noise removal |

### Example: split and import

```python
# Split a Suno track into stems
result = await server.mcp_opendaw_split_stems(
    file_path="/path/to/suno_track.wav",
    mode="bs6",
    auto_import=True  # automatically creates audio regions in the DAW
)
# Returns: {"stems": ["drums.wav", "bass.wav", "vocals.wav", ...],
#           "imported_regions": 6}
```

### GPU requirement

Stem separation runs locally on GPU. Models total ~3 GB and are downloaded
on first use. See the `stem-splitter/` directory for setup instructions.

## Preset Management (2)

| Tool | Description |
|------|-------------|
| `save_effect_preset` | Encode an effect chain as a `.opb` preset bundle (ZIP) |
| `load_effect_preset` | Load a `.opb` preset and decode via PresetDecoder |

### .opb format

`.opb` files are ZIP bundles containing:

```
preset.opb (ZIP)
├── version        — preset format version
├── meta.json      — metadata (name, author, description)
└── preset.odp     — raw binary preset data (OPRE magic 0x4F505245)
```

These are drag-and-drop compatible with openDAW's UI.

### Example: save and load presets

```python
# Save a reverb chain as a preset
await server.mcp_opendaw_save_effect_preset(
    unit_index=0,
    output_path="my_reverb.opb",
    name="My Reverb",
    description="Dark plate reverb with pre-delay"
)

# Load it onto another AU
await server.mcp_opendaw_load_effect_preset(
    file_path="my_reverb.opb",
    unit_index=2
)
```

## Engine Control (8)

| Tool | Description |
|------|-------------|
| `capture_realtime` | Capture realtime audio output from the DAW engine |
| `engine_panic` | Send a panic signal — stops all notes immediately |
| `engine_sleep` | Put the audio engine to sleep (suspend processing) |
| `engine_wake` | Wake the audio engine from sleep |
| `get_engine_status` | Real-time status: playing, position, BPM, CPU load, recording |
| `query_loading_complete` | Check if all audio samples are loaded and ready |
| `set_metronome` | Configure metronome (enabled, gain, beat_subdivision) |
| `start_engine` | Start the audio engine (AudioWorklet) after setup |

## MIDI Output (1)

| Tool | Description |
|------|-------------|
| `list_midi_output_devices` | List all MIDI output devices (hardware MIDI outputs) |

## Samples (2)

| Tool | Description |
|------|-------------|
| `get_sample_info` | Get detailed info about an audio sample by UUID |
| `list_samples` | List all audio file samples used in the project |

## Debugging & Control (3)

| Tool | Description |
|------|-------------|
| `evaluate_raw` | Execute arbitrary JavaScript in the DAW V8 context |
| `screenshot_daw` | Take a screenshot of the openDAW UI (base64 PNG) |
| `wait_for_condition` | Wait for a JavaScript condition to evaluate to true |

## Editing (2)

| Tool | Description |
|------|-------------|
| `redo` | Redo the last undone operation |
| `undo` | Undo the last editing operation |

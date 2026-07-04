# Audio Unit Duplication (duplicate_audiounit — tool #126, verified July 2026)

Deep-copies an AU: instrument (same factory + all params), audio effects (same types + all param values), note tracks/regions/events, track volume/panning, AU label/volume.

## The capture.refer() Pitfall (CRITICAL)

**Do NOT attempt AU duplication in a single monolithic `editing.modify()` JS block.** `AudioUnitBox.capture` is a `PointerField` (field index 26) that refuses `refer()` when called inside the same `editing.modify()` transaction as `AudioUnitBox.create()`. The error:

```
{AudioUnitBox:PointerField (capture) <uuid>/26 cannot be pointed to}
```

This happens even if `capture.refer()` is inside the constructor callback of `AudioUnitBox.create()`. It works in `create_synth_track` because that runs in a fresh project context, but adding a second AU with `capture.refer()` in the same transaction as reading the source AU fails.

Other pointer fields on AudioUnitBox (`input`, `output`, `collection`) work fine with `refer()` inside `editing.modify()`. Only `capture` exhibits this behavior — likely because capture has special initialization logic in `graph.stageBox()` that conflicts with late `refer()`.

## Correct Architecture: Python-Orchestrated Multi-Step

Read source state → create new AU via existing tool → copy params → copy effects → copy notes. Each phase is a separate `bridge.evaluate()` call with its own `editing.modify()` block.

### Step 1: Read source AU info
```javascript
() => {
    const p = window.DAW;
    const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({box}) => box);
    const srcAU = units[unit_index];
    // Read: type, label, volume, instrument class name, effects, tracks, notes
    // Instrument: [...srcAU.input.pointerHub.incoming()][0]?.box (NOT .input.targetVertex)
    // Capture: [...srcAU.capture.pointerHub.incoming()][0]?.box (NOT .capture.targetVertex)
    // Notes: region.events.targetVertex.unwrap() → vertex.box || vertex → .events.pointerHub.incoming()
}
```

**PITFALL: `au.input` and `au.capture` are `Field`, not `PointerField` — they have `.pointerHub.incoming()`, NOT `.targetVertex.unwrapOrNull()`.** Using `.targetVertex` on a `Field` throws `Cannot read properties of undefined (reading 'unwrapOrNull')`.

### Step 2-3: Read instrument and effect params
Iterate `inst.fields()` (or `fx.fields()`), check `f.getValue && f.setValue`, read value. Store as `{index, value}` pairs.

### Step 4: Create new AU
Use existing `create_synth_track` / `create_audio_track` MCP tools — they handle capture creation correctly.

### Step 5: Copy instrument params
```python
for p in inst_params:
    await bridge.evaluate(f"""() => {{
        const p = window.DAW;
        const au = [...p.rootBox.audioUnits.pointerHub.incoming()][{new_idx}]?.box;
        const inst = [...au.input.pointerHub.incoming()][0]?.box;
        p.editing.modify(() => {{
            const f = [...inst.fields()][{p['index']}];
            if (f && f.setValue) f.setValue({json.dumps(p['value'])});
        }});
    }}""")
```

### Step 6: Copy effects
Map box class names to factory names, then `add_effect` + copy params:
```python
fx_map = {
    "DelayDeviceBox": "Delay", "ReverbDeviceBox": "Reverb",
    "CompressorDeviceBox": "Compressor",
    # "FilterDeviceBox": "Filter",     # REMOVED from upstream EffectFactories (July 2026)
    # "EqualizerDeviceBox": "Equalizer", # REMOVED from upstream EffectFactories (July 2026)
    "DistortionDeviceBox": "Distortion",
    "ChorusDeviceBox": "Chorus", "PhaserDeviceBox": "Phaser",
    "NoiseGateDeviceBox": "NoiseGate", "TremoloDeviceBox": "Tremolo",
    "WerkstattDeviceBox": "Werkstatt", "SpielwerkDeviceBox": "Spielwerk",
    "StereoToolDeviceBox": "StereoTool", "WaveshaperDeviceBox": "Waveshaper",
    "VocoderDeviceBox": "Vocoder", "NeuralAmpDeviceBox": "NeuralAmp",
}
```

### Step 7: Copy notes
Source notes store position/duration in PPQN (960 per beat). `create_note` takes `start_beat` / `duration_beats`:
```python
pos_beats = note["position"] / 960.0
dur_beats = note["duration"] / 960.0
await mcp_opendaw_create_note(
    track_index=ti, pitch=note["pitch"],
    start_beat=pos_beats, duration_beats=dur_beats,
    velocity=note["velocity"], unit_index=new_idx
)
```

**Note**: `create_note` creates a new NoteRegionBox per note. Source AU may have multiple notes in one region, but the duplicate will have one note per region. This is cosmetic — audio output is identical.

### PITFALL: Sorting audioEffects by index crashes on malformed AudioBusBox

When reading source AU effects, do NOT sort `audioEffects` by `box.index.getValue()`:
```javascript
// WRONG — crashes if a malformed AudioBusBox is in the collection
const effects = [...au.audioEffects.pointerHub.incoming()].map(({box}) => box)
    .sort((a,b) => a.index.getValue() - b.index.getValue());
```
AudioBusBox has no `index` field. If a bus was created by a bad `create_audio_bus` call (bare AudioBusBox without AudioUnitBox), it can leak into `audioEffects` and trigger `AudioBusBox <uuid> has no index field` panic inside `IndexedBox.collectIndexedBoxes`. Filter by class name instead:
```javascript
const effects = [...au.audioEffects.pointerHub.incoming()].map(({box}) => box)
    .filter(e => e.constructor.name.endsWith('DeviceBox'));
```

### PITFALL: Filter/Equalizer removed from upstream EffectFactories (July 2026)

The `fx_map` above already comments these out, but be aware: `EffectFactories.Filter` and `EffectFactories.Equalizer` no longer exist. If `duplicate_audiounit` encounters a `FilterDeviceBox` or `EqualizerDeviceBox` in the source, it will fail to find the factory. These effects were replaced by other processing chains in upstream.

## Verified Test (July 2026)

Source: Vaporisateur + 3 notes (C2, G2, C3) + Delay (delayMusical=480) + Reverb + vol -3dB
Duplicate: unit_index=2, Vaporisateur + 3 notes + Delay + Reverb + vol -3dB ✅

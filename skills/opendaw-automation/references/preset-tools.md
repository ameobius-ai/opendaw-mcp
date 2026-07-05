# Preset Export/Import MCP Tools

## APIs

### PresetEncoder.encode
`PresetEncoder.encode(audioUnitBox, {excludeEffect?, includeTimeline?})` → `ArrayBufferLike`

Serializes AU + all dependencies into binary preset format with header (magic + version).

### PresetDecoder.decode
`PresetDecoder.decode(bytes, ProjectSkeleton)` → `ReadonlyArray<AudioUnitBox>`

Deserializes preset into target project. Creates new AU with instrument, effects, MIDI effects, tracks.

### PresetDecoder.replaceAudioUnit
`PresetDecoder.replaceAudioUnit(bytes, targetAU, {keepMIDIEffects?, keepAudioEffects?, keepTimeline?})` → `Attempt<void, string>`

Replaces existing AU's content from preset. Options to keep MIDI/audio effects or timeline.

### PresetHeader
- `MAGIC_HEADER_OPEN = 0x4F50454E` ("OPEN" in ASCII)
- `FORMAT_VERSION = 2`

## Base64 Transport
ArrayBuffer ↔ base64 for JSON transport:
```js
// Encode
const bytes = new Uint8Array(buffer);
let binary = '';
for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
const base64 = btoa(binary);

// Decode
const binary = atob(b64);
const bytes = new Uint8Array(binary.length);
for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
// Pass bytes.buffer to PresetDecoder.decode
```

## ProjectSkeleton (same as TransferAudioUnits)
```js
{
  boxGraph: p.boxGraph,
  mandatoryBoxes: {
    primaryAudioBusBox: primaryBus,
    rootBox: p.rootBox
  }
}
```

## MCP Tools
- `export_preset(unit_index, include_timeline=False)` → `{preset_b64, size_bytes, unit_type}`
- `import_preset(preset_b64)` → `{new_unit_index, unit_type, effects, effect_names}`
- `replace_from_preset(unit_index, preset_b64, keep_midi_effects=False, keep_audio_effects=False, keep_timeline=False)` → `{success, instrument, effects, effect_names}` or `{error: failureReason}`
- `export_effect_chain(unit_index, effect_type="audio")` → `{preset_b64, size_bytes, effect_count, effect_names}` (effect_type: "audio" or "midi")

## DAW Globals
`DAW_PresetEncoder`, `DAW_PresetDecoder`, `DAW_PresetHeader` added to headless-daw/src/main.ts globals.

## E2E Test Results

### export_preset + import_preset roundtrip
- Source: AU 0 (Vaporisateur + Delay + Reverb)
- Export: 2615 bytes, 3488 base64 chars
- Import: new AU at index 1, instrument, VaporisateurDeviceBox, effects=["Delay","Reverb"]
- Roundtrip preserves instrument type + all effects

### replace_from_preset
- Source preset: Vaporisateur + Delay + Reverb (from export_preset)
- Target: AU 1 (Nano instrument, no effects)
- Replace with keepAudioEffects=true, keepTimeline=true
- Result: instrument changed Nano to Vaporisateur, effects=0 (Nano had none to keep)
- Attempt API: attempt.isSuccess() / attempt.failureReason()
- Pitfall: Source and target must have compatible capture types (MIDI to MIDI, Audio to Audio). Incompatible returns Attempts.err("Cannot replace incompatible instruments").

### export_effect_chain
- Source: AU 0 (Delay + Reverb audio effects)
- Export: 2216 bytes, 2995 base64 chars, effect_names=["Delay","Reverb"]
- Uses PresetEncoder.encodeEffects(effects, ChainKind.Audio=1) or ChainKind.Midi=0
- Wrapper AU created internally (NoopInstrumentBox + CaptureBox), not visible in project

## Pitfalls
- Output unit cannot be exported (filtered by PresetEncoder)
- `include_timeline=False` excludes tracks/regions/notes from preset
- PresetDecoder.decode creates a fresh BoxGraph internally then copies to target — different from TransferAudioUnits which works within same graph
- Large presets (>100KB base64) may hit MCP JSON limits — consider file-based transport for complex AUs

## Not Yet Covered (potential future tools)
- `PresetDecoder.peekHasTimeline` — check if preset contains timeline data (trivial: parse header + scan for TrackBox)
- `PresetEncoder.encode` with `excludeEffect` callback — selective effect exclusion during AU export

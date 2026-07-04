# Upstream Effects — MCP Compatibility & Parameter Reference

Verified July 2026 against upstream/main (post 162-commit sync). All effects in `EffectFactories.AudioNamed` are accessible via `add_effect(effect_type="<Key>")`.

## Effect inventory (15 audio + 5 MIDI)

### Audio effects (AudioNamed)
| Key | Label | Params | Notes |
|-----|-------|--------|-------|
| Compressor | Compressor | — | Sidechain via `connect_sidechain` |
| Crusher | Crusher | — | Bit crusher |
| DattorroReverb | Dattorro Reverb | — | Algorithmic reverb |
| Delay | Delay | 14 | delayMusical, feedback, cross, filter, wet |
| Fold | Fold | — | Wavefolder |
| Reverb | Free Reverb | — | preDelay default 0.001 |
| Gate | Gate | — | Noise gate |
| Maximizer | Maximizer | — | Brickwall limiter, default on Output |
| Revamp | Revamp | — | Graphical EQ |
| **StereoTool** | Stereo Tool | 7 | volume, panning, stereo, invertL, invertR, swap, panningMixing |
| Tidal | Tidal | — | Tremolo & autopan, depth default 0.75 |
| **NeuralAmp** | Tone3000 | — | External effect (model loading via popup — not headless-compatible) |
| **Vocoder** | Vocoder | 11 | carrierMinFreq, carrierMaxFreq, modulatorMinFreq, modulatorMaxFreq, qMin, qMax, envRelease, mix, bandCount, modulatorSource, envAttack, gain |
| **Waveshaper** | Waveshaper | 4 | equation (hardclip), inputGain, outputGain, mix |
| Werkstatt | Werkstatt | — | Scriptable DSP (user JS code) |

### MIDI effects (MidiNamed)
| Key | Label | Notes |
|-----|-------|-------|
| Arpeggio | Arpeggio | Note sequence generator |
| Pitch | Pitch | Pitch shifter |
| Spielwerk | Spielwerk | Scriptable MIDI effect (user JS) |
| Velocity | Velocity | Velocity transformer |
| Zeitgeist | Zeitgeist | Shuffle/groove, creates GrooveShuffleBox |

### Not in AudioNamed
- **Modular** — separate system (`EffectFactories.Modular`), creates ModularBox + ModularAudioInput/Output. Not accessible via `add_effect` (not in `AudioNamed`).

## Verified parameter details

### StereoTool (StereoToolDeviceBox)
```
volume = 0 dB
panning = 0 %
stereo = 0 %
invertL = False
invertR = False
swap = False
panningMixing = 1
```

### Waveshaper (WaveshaperDeviceBox)
```
equation = hardclip    (string param — use set_effect_parameter_string)
inputGain = 0 dB
outputGain = 0 dB
mix = 1 %
```

### Vocoder (VocoderDeviceBox)
```
carrierMinFreq = 100 Hz
carrierMaxFreq = 12000 Hz
modulatorMinFreq = 100 Hz
modulatorMaxFreq = 12000 Hz
qMin = 2
qMax = 20
envRelease = 30 ms
mix = 1 %
bandCount = 16
modulatorSource = noise-pink    (string param)
envAttack = 5 ms
gain = 0 dB
```

## API patterns for reading effect parameters

### Correct: `box.record()` + `field._fieldName`
```javascript
const record = effectBox.record();
for (const [key, field] of Object.entries(record)) {
    const fname = field._fieldName || field.fieldName || key;
    if (skip.has(fname)) continue;  // skip host/index/label/enabled/minimized/sideChain
    if (typeof field.getValue !== 'function') continue;
    const value = field.getValue();
    const unit = field.unit || '';
}
```

### Wrong: `boxAdapters.adapterFor()` — does not exist on `p.api`
The `p.api.boxAdapters` property is not available in headless mode. Use `box.record()` directly.

### Wrong: `box.fields().get(i)` — not the right iteration pattern
Use `box.record()` + `Object.entries()` instead.

## `api.createInstrument` gotcha

`api.createInstrument(IF.Vaporisateur)` does NOT return the created AudioUnitBox. To get the new AU:

```javascript
p.editing.modify(() => { api.createInstrument(IF.Vaporisateur); });
const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({box}) => box);
const newAU = units[units.length - 1];
const unitIndex = units.length - 1;
```

## Upstream plans research (July 2026)

### Plans that are PLANNED but NOT implemented
- **copy-and-paste-audiounits.md** — `AudioUnitsClipboardHandler`, `ClipboardUtils`, `ClipboardManager` — none exist in codebase. `BoxGraphCopy` does not exist. `duplicate_audiounit` MCP tool works via Python orchestration instead.
- **freeze-audiounit.md** — `FrozenPlaybackProcessor`, `setFrozenAudio`, `AudioUnitFreeze` — none exist. Would need offline rendering + `setFrozenAudio` engine command.
- **flatten-audio-regions.md** — `flattenAudioRegions`, `useInstrumentOutput` in `ExportStemConfiguration` — not implemented. Would need `OfflineEngineRenderer.setPosition()` + `step()`.
- **match-tempo.md** — `/tap` page, UI-only, no API changes.
- **advanced-monitoring.md** — monitoring routing, UI/audio graph changes, no API.

### What IS available in ProjectApi.ts
All 27 methods covered by 133 MCP tools. `compactTracks` has MCP equivalent (`compact_tracks`). `duplicateNotes` has MCP equivalent (`duplicate_notes`). `TransferRegions` now has MCP equivalent (`transfer_region` — July 2026, tool #133, uses `TransferRegions.transfer()` with `DAW_TransferRegions` global).

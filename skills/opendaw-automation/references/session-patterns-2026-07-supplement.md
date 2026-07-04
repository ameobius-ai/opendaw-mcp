# openDAW Session Patterns — July 2026 (Supplement)

## Tool Count: 125 (updated from 120) — ProjectApi + Scriptable Devices covered

### Scriptable Device Rendering Fixes (July 2026)

Four bugs were fixed in `set_script_device_code` that prevented scriptable devices from rendering audio offline. See `references/scriptable-device-offline-render.md` for full details:

1. **Constructor destructuring crash** — `new ProcessorClass()` is called with ZERO args. Destructured constructors (`constructor({sampleRate})`) crash silently. Fix: `constructor(opts) { this.sr = (opts && opts.sampleRate) ? opts.sampleRate : 48000; }`
2. **Worklet registry update mismatch** — `#tryLoad()` checks `registry.update === expectedUpdate`. Hardcoded `update: 1` in worklet registration didn't match incremented `device.code` header. Fix: use same `newUpdate` variable for both.
3. **newUpdate scope** — declared inside `editing.modify()` callback, inaccessible for worklet registration outside. Fix: compute before `editing.modify()`.
4. **`\n` escape level** — `'\\\\n'` in Python f-string → literal `\n` in JS code field → header pattern didn't match. Fix: use `'\\n'`.

**Result**: Full chain (Apparat darkbass → Spielwerk arp → Werkstatt coldfold) renders offline with max_sample=0.844 ✅. Two additional bugs were found and fixed (see bugs 5 and 6 below).

### Bug 5: Werkstatt Process API Signature (ROOT CAUSE of full-chain silence)

**Symptom**: Apparat solo renders fine. Apparat + Werkstatt (pair) renders fine. But Apparat + Spielwerk + Werkstatt (full chain) = silence.

**Root cause**: Both Werkstatt scripts (`darksat.js`, `coldfold.js`) used `process(inputL, inputR, outputL, outputR, block)` — 5 args. But `WerkstattDeviceProcessor.processAudio()` calls `proc.process(this.#io, block)` — 2 args. `this.#io` = `{src: [Float32Array, Float32Array], out: [Float32Array, Float32Array]}`. The 5-arg signature silently received `inputL=io_object`, `inputR=block`, `outputL=undefined`, `outputR=undefined` → no audio written to output → silence.

**Fix**: Rewrite both scripts to `process(io, block)`:
```javascript
process(io, block) {
    const inputL = io.src[0]
    const inputR = io.src[1]
    const outputL = io.out[0]
    const outputR = io.out[1]
    // ... DSP ...
    outputL[i] = result  // write to io.out
}
```

### Bug 6: Spielwerk Arpeggiator Block Size vs Rate (ROOT CAUSE of Spielwerk silence)

**Symptom**: Apparat + Spielwerk arpeggiator = silence. Arpeggiator generates 0 notes per block.

**Root cause**: Offline renderer processes blocks of ~128 samples. At 48000Hz, 110 BPM, PPQN=960: 128 samples ≈ 5ppqn per block. Arpeggiator rate=240ppqn (1/8 note). Original arpeggiator used `while (pos + dur <= to)` where `pos=from`, `dur=max(30, rate*gate)=168`. `pos + dur = from + 168 >> to` (block range ~5ppqn) → loop never executes → 0 notes.

**Fix**: Track `nextStepPos` across blocks:
```javascript
class Processor {
    nextStepPos = 0
    lastFrom = -1

    process(block, events) {
        // reset on transport jump
        if (this.lastFrom < 0 || block.from < this.lastFrom) {
            this.nextStepPos = block.from
            this.stepCounter = 0
        }
        this.lastFrom = block.from

        // generate notes where nextStepPos falls within [block.from, block.to)
        while (this.nextStepPos < block.to) {
            if (this.nextStepPos >= block.from) {
                out.push({ position: this.nextStepPos, duration: dur, pitch, velocity, cent: 0 })
            }
            this.stepCounter++
            this.nextStepPos += rate
        }
        return out
    }
}
```
### Demo Track Rendered (July 2026)

Full darksynth demo built and rendered offline via MCP tools:

#### v3 — 32 bars, 5 tracks, breakdown, stems (July 2026)

32-bar darksynth with breakdown in bars 5-6. All tracks drop except pad during breakdown. Pad changes from Cm to Ab in bars 9-16. Stems exported as multichannel WAV (5 channels, 65MB).

- **Bass**: Apparat darkbass (saw, 150Hz, subOsc) → Spielwerk arp (1/8 up, 2 oct) → Werkstatt coldfold (wavefold+bitcrush), -3dB center
- **Lead**: Apparat coldlead (triangle, 800Hz, long release) → Werkstatt darksat (tape sat) → Delay (360ms, 35% fb, wet=-9dB), -5dB pan L20
- **Pad**: Vaporisateur Cm→Ab chord → Dattorro reverb (decay=0.7, wet=-6dB), -10dB pan R15
- **Kick**: Vaporisateur sine C1, 4-on-floor, dropped bars 5-6, -4dB center
- **Hat**: Vaporisateur square C6, off-beat 8ths, dropped bars 5-6, -12dB pan R30
- 110 BPM, C minor, 32 beats. max_sample=0.871, 48kHz stereo, offline render.
- Stems: 5-channel WAV, 65MB (too large for Discord — local mixing only)

See `references/mixing-and-rendering.md` for effect parameter names, Vaporisateur drum synth config, and render debugging checklist.

#### v2 — 16 bars, 4 tracks (July 2026)

### New DSP Script: Apparat Cold Lead

`templates/apparat_coldlead.js` — Post-punk clav synth. Triangle wave default, 2 detuned oscillators with random phase start, lowpass filter, ADSR with long release. 9 @param. Constructor accepts optional `opts.sampleRate`.

### New DSP Script: Spielwerk Arpeggiator

`templates/spielwerk_arpeggiator.js` — MIDI arpeggiator with 4 modes (up/down/up-down/random), octave expansion, velocity decay, gate length. 5 @param. Uses array return pattern (NO generator method). Holds note state, generates stepped arpeggio within block ppqn range.

### New tools (sessions 120→125): Scriptable Devices
- `set_script_device_code(device_type, unit_index, device_index, code)` — FULL COMPILER: parses @param/@sample declarations, creates WerkstattParameterBox/WerkstattSampleBox, validates JS via `new Function()`, registers audio worklet via DAW_audioContext. ALL box creation in ONE editing.modify() block. `device_index` selects Nth device of same type on one AU.
- `get_script_device_code(device_type, unit_index, device_index)` — read current JS code, returns header + length
- `list_script_params(device_type, unit_index, device_index)` — list WerkstattParameterBox entries (label/index/value/defaultValue)
- `set_script_param(device_type, unit_index, device_index, param_label, value)` — set param by label via editing.modify(). Uses json.dumps() for label escaping (NO _escape_js function exists).
- `list_script_samples(device_type, unit_index, device_index)` — list WerkstattSampleBox entries (label/index/hasFile)

device_type: "apparat" (instrument, au.input), "werkstatt" (audio effect, au.audioEffects), "spielwerk" (MIDI effect, au.midiEffects)

### Scriptable Device Architecture (verified July 2026)

Three device types let users write custom JS DSP code:

| Device | Layer | Box Class | Code Field | Params Field | Samples Field |
|--------|-------|------------|------------|--------------|---------------|
| Apparat | Instrument (au.input) | ApparatDeviceBox | 10 | 11 | 12 |
| Werkstatt | Audio effect (au.audioEffects) | WerkstattDeviceBox | 10 | 11 | 12 |
| Spielwerk | MIDI effect (au.midiEffects) | SpielwerkDeviceBox | 10 | 11 | — |

**WerkstattParameterBox**: label(2 StringField), index(3 Int32Field), value(4 Float32Field), defaultValue(5 Float32Field)
**WerkstattSampleBox**: label(2 StringField), index(3 Int32Field), file(4 PointerField→AudioFileBox)

**Code format**: header `// @apparat <name> <version> <update>`, then `Processor` class.
`// @param <name> <default> <min> <max> [type] [unit]` → auto-creates WerkstattParameterBox
`// @sample <name>` → auto-creates WerkstattSampleBox

**@param token order** (from ScriptDeclaration.ts, verified July 2026):
```
// @param <name> <default> <min> <max> [type] [unit]
```
- name: string label
- default: float (or `true`/`false` for bool type)
- min: float (only if 4+ tokens)
- max: float (only if 4+ tokens)
- type: `linear` | `exp` | `int` | `bool` (only if 5+ tokens; if omitted with 4 tokens → `linear`)
- unit: string (only if 6+ tokens)

**Special @param forms**:
- `// @param name` → unipolar 0..1, default 0
- `// @param name 0.5` → unipolar 0..1, default 0.5
- `// @param name true` or `// @param name false` → bool, default 1/0
- `// @param name 0.5 bool` → bool with default
- `// @param name 0.5 0 1` → linear 0..1, default 0.5
- `// @param name 0.5 0 1 linear Hz` → linear with unit

**ScriptCompiler.compile() pipeline** (from ScriptCompiler.ts):
1. Parse header → extract userCode + update number
2. `ScriptDeclaration.parseParams(userCode)` → ParamDeclaration[]
3. `ScriptDeclaration.parseSamples(userCode)` → SampleDeclaration[]
4. `ScriptDeclaration.parseDeclarationOrder(userCode)` → Map<label, index>
5. `reconcileParameters()`: delete removed params, update index of existing, create new WerkstattParameterBox
6. `reconcileSamples()`: same for samples
7. `deviceBox.code.setValue(header + userCode)` with incremented update
8. `validateCode(wrappedCode)` via `new Function()`
9. `registerWorklet(audioContext, wrappedCode)` via Blob URL → `audioWorklet.addModule()`

**MCP set_script_device_code replicates this pipeline** in JS within a single `editing.modify()` block. Worklet registration is optional (non-fatal if it fails).

**Device discovery**:
```javascript
// Apparat = instrument → au.input
const apparat = [...au.input.pointerHub.incoming()].map(({box}) => box)
  .find(b => b.constructor.name === "ApparatDeviceBox");
// Werkstatt = audio effect → au.audioEffects
const werk = [...au.audioEffects.pointerHub.incoming()].map(({box}) => box)
  .find(b => b.constructor.name === "WerkstattDeviceBox");
// Spielwerk = MIDI effect → au.midiEffects
```

**PITFALL: api.insertEffect argument** — takes the field (`au.audioEffects`), NOT the box (`au`):
```javascript
// CORRECT
p.api.insertEffect(au.audioEffects, ef.AudioNamed.Werkstatt);
// WRONG — throws "AudioBusBox has no index field"
p.api.insertEffect(au, ef.AudioNamed.Werkstatt);
```

**PITFALL: Backtick escaping in bridge** — when setting code containing backticks via bridge.evaluate, use `json.dumps()` in Python to escape the code string, then embed as a JS literal. Do NOT use f-string backtick interpolation — bash will mangle `chr()` calls and JS template literals will break.

**PITFALL: Box creation must be inside editing.modify()** — `WerkstattParameterBox.create()` and `WerkstattSampleBox.create()` call `boxGraph.stageBox()` which modifies the graph. If called outside `editing.modify()`, throws `"Modification only prohibited in transaction mode."`. ALL box creation + field mutations (owner.refer, label.setValue, index.setValue, value.setValue, code.setValue) must be in ONE `editing.modify()` block.

**PITFALL: DAW_WerkstattParameterBox / DAW_WerkstattSampleBox must be exported** — these are NOT in the default headless-daw globals. Must add to `headless-daw/src/main.ts` in the studio-boxes loading section:
```typescript
w.DAW_WerkstattParameterBox = boxes.WerkstattParameterBox;
w.DAW_WerkstattSampleBox = boxes.WerkstattSampleBox;
```
Without these exports, `set_script_device_code` silently skips param/sample creation (the `if (window.DAW_WerkstattParameterBox)` guard fails).

**PITFALL: _escape_js does not exist** — the `set_script_param` tool originally referenced `_escape_js()` which was never defined. Use `json.dumps(param_label)` to produce a JS string literal instead.

**DAW_audioContext** — available as `window.DAW_audioContext` in headless-daw globals. Used for audio worklet registration. `new AudioContext()` also works as fallback.

**Verified test flow** (July 2026, end-to-end via MCP tools):
1. Add Werkstatt via `api.insertEffect(au.audioEffects, ef.AudioNamed.Werkstatt)` → WerkstattDeviceBox ✅
2. `set_script_device_code` with code containing 4 @param + 2 @sample declarations → 4 WerkstattParameterBox created (gain=0.5, drive=0.3, mix=0.8, bypass=bool→0), 2 WerkstattSampleBox (kick, snare), worklet_registered=true ✅
3. `get_script_device_code` → header `// @werkstatt js 1 1`, code_length matches ✅
4. `list_script_params` → 4 params with correct label/index/value/defaultValue ✅
5. `set_script_param("gain", 0.85)` → old 0.5, new 0.85 ✅
6. `list_script_samples` → 2 samples (kick index=4, snare index=5), hasFile=false ✅

### New tools (sessions 118→120): Stretch Clips
- `create_time_stretched_clip` — audio clip with playback rate + transient mode (api.createTimeStretchedClip). Same props as create_time_stretched_region but for session view clip launcher. Takes sample_id, clip_index, playback_rate, transient_mode.
- `create_pitch_stretched_clip` — pitch-aligned audio clip (api.createPitchStretchedClip). Uses AudioPitchStretchBox for play mode. Takes sample_id, clip_index, bpm.

These complete the ProjectApi coverage — all clip creation methods now have MCP equivalents.

### New tools (sessions 105→111): MIDI Effects
- `list_midi_effects` — list available MIDI effect types (Arpeggio/Pitch/Velocity/Zeitgeist/Spielwerk)
- `add_midi_effect` — add MIDI effect to au.midiEffects chain (same API as add_effect)
- `remove_midi_effect` — remove MIDI effect from chain
- `get_midi_effect_chain` — get MIDI effect chain for AU
- `list_midi_effect_params` — list MIDI effect parameters with values
- `set_midi_effect_param` — set MIDI effect parameter by name or field index

### New tools (sessions 111→113): Vaporisateur Synth
- `list_vaporisateur_params` — full synth state: oscillators (waveform/volume/octave/tune), LFO, noise, main params (cutoff/resonance/ADSR/etc)
- `set_vaporisateur_osc_param` — set oscillator parameter (waveform: 0=Sine/1=Triangle/2=Saw/3=Square, volume dB, octave, tune)

See `references/midi-effects-and-synth-controls.md` for full API details.

### New tools (sessions 113→118): Universal Instrument Params + Playfield
- `list_instrument_params` — universal: list all params of ANY instrument (Vaporisateur/Tape/Nano/Soundfont/MIDIOutput/Playfield/Apparat). Auto-detects first non-AudioBusBox instrument on AU input.
- `set_instrument_param` — universal: set any instrument parameter by name or field index. Works on all instrument types.
- `list_playfield_samples` — list drum pads on Playfield (midi_note, enabled, has_file)
- `set_playfield_sample_enabled` — enable/disable a Playfield drum pad
- `create_playfield_sample` — add a drum pad to existing Playfield (AudioFileBox + PlayfieldSampleBox via SampleClass.create() from existing sample constructor)

**Instrument detection pattern**: `au.input.pointerHub.incoming()` returns instrument boxes. Filter out `AudioBusBox` (that's the master bus, not an instrument). First non-AudioBusBox = the instrument.

**Instrument parameter map (verified July 2026)**:
- Vaporisateur: 23 params (fields 10-27, 99). cutoff(14), resonance(15), attack(16), release(17), filterEnvelope(18), decay(19), sustain(20), glideTime(21), voicingMode(22), etc.
- Tape: flutter(10), wow(11), noise(12), saturation(13)
- Nano: volume(10), release(20), file(15)
- Soundfont: presetIndex(11), file(10)
- MIDIOutput: channel(11), deprecatedDelay(12)
- Playfield: samples(10) — Field<Pointers.Sample>, access via `pf.samples.pointerHub.incoming()`
- Apparat: no params (scriptable)

**Playfield sample creation (verified July 2026)**:
1. Playfield must be created with `api.createInstrument(IF.Playfield, {attachment: [...]})` — NOT `api.createInstrument(IF.Playfield, [...])`. The second arg is `InstrumentOptions`, not the attachment directly.
2. To add pads to an existing Playfield, get the `SampleClass` from an existing sample's constructor: `existingSamples[0].constructor` — then call `SampleClass.create(boxGraph, UUID.generate(), box => {...})`.
3. `AudioFileBox` must be created in the SAME `editing.modify()` block as the `PlayfieldSampleBox` — the `box.file.refer(fileBox)` call creates the edge that prevents the "requires an edge" validation error.
4. `boxGraph.createBox("PlayfieldSampleBox")` does NOT work — UUID comparator crash. Must use the class `.create()` method.
5. Empty Playfield (no samples) → `create_playfield_sample` returns error. Must have at least one sample for the constructor reference.

## ArrayField Access Pattern (CRITICAL)

`VaporisateurDeviceBox.oscillators` is an `ArrayField` (from `@opendaw/lib-box`), NOT a regular array.

**WRONG:**
- `vap.oscillators.get(0)` → `TypeError: get is not a function`
- `vap.oscillators[0]` → undefined
- `vap.oscillators.length` → undefined

**CORRECT:**
```javascript
const oscFields = vap.oscillators.fields();  // ReadonlyArray<VaporisateurOsc>
const oscCount = vap.oscillators.size();     // number (NOT .length)
const osc0 = oscFields[0];                   // access by index
```

`ArrayField` API:
- `.fields()` → ReadonlyArray of sub-fields
- `.size()` → count (NOT `.length`)
- `.getField(key)` → get sub-field by key
- `.record()` → Record<string, Field>

This pattern applies to ALL ArrayField instances in openDAW (oscillators, LFO arrays, etc).

## MIDI Effects = Same API as Audio Effects

`au.midiEffects` (AudioUnitBox field 21) uses the **same `api.insertEffect()` API** as `au.audioEffects` (field 23). The only difference is which field you pass:

```javascript
// Audio effect
p.api.insertEffect(au.audioEffects, ef.AudioNamed.Delay);
// MIDI effect
p.api.insertEffect(au.midiEffects, ef.MidiNamed.Pitch);
```

Both chains support: list, add, remove, get params, set param, connect sidechain (audio only).

## ProjectApi Coverage — COMPLETE

All high-level ProjectApi methods now have MCP equivalents. All instrument types (Vaporisateur/Tape/Nano/Soundfont/MIDIOutput/Playfield/Apparat) have universal param read/write via `list_instrument_params` + `set_instrument_param`. All clip creation methods covered including stretch clips. Remaining uncovered items are UI-only or require complex staging:
- `PresetStorage` — binary `.odp` files, needs FileAPI
- `RecordAutomation` — live recording during transport
- `YService`/`YMapper` — Yjs collaborative editing

## Upstream Contribution Status (July 2026 — POST-SYNC)

- **Fork synced**: `AMEOBIUS/openDAW` main fast-forwarded to `andremichelle/openDAW` on 2026-07-02 (162 commits, zero conflicts). PR branch rebased + force-pushed.
- **PR #280**: Delay DSP lazy init fix — pinged 2026-07-02 with short human comment. Still awaiting review post-sync.
- **Stale branch cleaned**: `fix/offline-render-tidal-silence` was a stale pointer to upstream commit `9e006511` (no our commits). Deleted 2026-07-02.
- **Issues #278/#281/#282**: CLOSED by andremichelle with "Please do not submit AI generated issues." — he rejects AI-generated issue reports. Do NOT open new issues. Only submit real code fixes as small focused PRs.
- **Issue #125**: Offline renderer in worker — CLOSED.
- **Maximizer is now default on Output unit** (upstream change) — fresh projects start with MaximizerDeviceBox.
- **Scriptable devices available**: Apparat/Spielwerk/Werkstatt — `DAW_ApparatDeviceBox` window global now present.
- Rule from README: "Keep pull requests small and focused. Large PRs will not be reviewed"
- **MAINTAINER INTERACTION RULE**: Keep all GitHub communication short, human, and code-focused. No long AI-style writeups. No issue reports that read as AI-generated. A simple "gentle ping, is there anything to change?" is the right tone.
- See `references/offline-engine-architecture.md` → "Upstream Sync — VERIFIED PROCEDURE" for the full sync + regression test procedure.

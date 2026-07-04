# Werkstatt DSP Script API — Quick Reference (verified July 2026)

## Processor Class Contract (Werkstatt — audio effect)

```javascript
// @werkstatt <name> <version> <update>
// @param <name> <default> <min> <max> [type] [unit]
// @sample <name>

class Processor {
    // Constructor receives destructured context (NOT a block — this is the worklet instance)
    // Fields initialized as class properties. sampleRate is a global.
    
    paramChanged?(name, value)  // called when user changes a @param knob
    
    process(inputL, inputR, outputL, outputR, block)  // audio callback
}
```

### process() signature (Werkstatt — audio effect)
```
process(io: {src: [Float32Array, Float32Array], out: [Float32Array, Float32Array]},
        block: {s0, s1, index, bpm, p0, p1, flags})
```
- `io.src[0]` = left input channel, `io.src[1]` = right input channel
- `io.out[0]` = left output channel, `io.out[1]` = right output channel
- `s0` = first sample index (inclusive)
- `s1` = last sample index (exclusive)
- Iterate `for (let i = block.s0; i < block.s1; i++)`
- Read from `io.src[0][i]`/`io.src[1][i]`, write to `io.out[0][i]`/`io.out[1][i]`

**PITFALL: Werkstatt process() receives a single `io` object, NOT four separate arrays.** `WerkstattDeviceProcessor.processAudio()` calls `proc.process(this.#io, block)` where `this.#io = {src: [ch0, ch1], out: [ch0, ch1]}`. Writing `process(inputL, inputR, outputL, outputR, block)` silently fails — `inputL` receives the `io` object, `inputR` receives `block`, and the rest are `undefined`. No error is thrown, but output is zero → silence. Always destructure at the top of process():
```javascript
process(io, block) {
    const inputL = io.src[0], inputR = io.src[1]
    const outputL = io.out[0], outputR = io.out[1]
    for (let i = block.s0; i < block.s1; i++) { ... }
}
```

### process() signature (Apparat — instrument)
```
process(output: [Float32Array, Float32Array], block: {s0, s1, ...})
```
- No input — Apparat generates audio from note events
- `noteOn(pitch, velocity, cent, id)` / `noteOff(id)` / `reset()` methods
- Host clears output buffer before calling

### Block flags bitmask
- 1 = transporting
- 2 = discontinuous
- 4 = playing
- 8 = bpmChanged

### @param parsing (ScriptDeclaration.ts)
| Token count | Result |
|---|---|
| `// @param name` | unipolar 0..1, default 0 |
| `// @param name 0.5` | unipolar 0..1, default 0.5 |
| `// @param name true` | bool, default 1 |
| `// @param name false` | bool, default 0 |
| `// @param name 0.5 bool` | bool with default |
| `// @param name 0.5 0 1` | linear 0..1, default 0.5 |
| `// @param name 0.5 0 1 linear` | explicit linear |
| `// @param name 0.5 0 1 exp Hz` | exponential with unit |

Valid types: `linear`, `exp`, `int`, `bool`. Default (≤3 tokens): `unipolar`.

**PITFALL: @param token order — NO extra numbers between max and type.** The format is strictly `name default min max [type] [unit]`. Writing `// @param cutoff 200 50 8000 200 exp Hz` (extra `200` before `exp`) produces: `Malformed @param: unknown mapping '200' (expected: linear, exp, int, bool)`. Similarly `// @param resonance 0.7 0.1 8 0.7 linear` fails — the `0.7` after `8` is parsed as the mapping type slot. After `max`, the NEXT token must be a type keyword (`linear`/`exp`/`int`/`bool`) or a unit string — never a number.

**PITFALL: Apparat constructor must accept zero arguments.** `ApparatDeviceProcessor.#swapProcessor()` calls `new ProcessorClass()` with NO arguments. If your constructor destructures (`constructor({audioContext, sampleRate, parameters, samples})`), instantiation throws a silent TypeError and the processor is silenced. Always write:
```javascript
// WRONG — crashes on new ProcessorClass()
constructor({audioContext, sampleRate, parameters, samples}) { ... }

// CORRECT — accepts optional opts, falls back to sensible defaults
constructor(opts) {
    this.sr = (opts && opts.sampleRate) ? opts.sampleRate : 48000;
}
```
This applies to ALL three device types (Apparat, Werkstatt, Spielwerk). The host always instantiates with zero args.

**PITFALL: Worklet registry update number MUST match device.code header update number.** `ApparatDeviceProcessor.#tryLoad()` checks `registry.update === expectedUpdate` where `expectedUpdate = parseUpdate(code)` (the 4th field in the header). If the `globalThis.openDAW.apparatProcessors[uuid].update` doesn't match the header's update field, the processor is never loaded → silence. In `set_script_device_code`, compute `newUpdate` BEFORE `editing.modify()` (not inside the callback) so it's accessible for both `device.code.setValue(header + userCode)` AND worklet registration:
```javascript
// Compute OUTSIDE editing.modify()
const newUpdate = currentUpdate + 1;
p.editing.modify(() => {
    device.code.setValue('// @apparat js 1 ' + newUpdate + '\n' + userCode);
});
// Use same newUpdate for worklet registration
const wrappedCode = '...globalThis.openDAW.apparatProcessors[uuid] = { update: ' + newUpdate + ', ... }';
```

**PITFALL: `\n` in Python f-string JS code.** When building JS header strings inside Python f-strings, `'\\n'` in the f-string becomes `'\n'` in Python → newline character in JS → correct. `'\\\\n'` becomes `'\\n'` in Python → literal backslash-n in JS → WRONG (header pattern `/^\/\/ @apparat \w+ \d+ \d+\n/` expects a real newline). Use `'\\n'` (two chars in f-string source) for a JS newline.

### Spielwerk MIDI Processor API

```javascript
// @spielwerk <name> <version> <update>
// @param <name> <default> <min> <max> [type] [unit]

class Processor {
    paramChanged?(label, value)   // @param changes — NOTE: label, NOT name
    reset?()                       // called on transport stop / discontinuity

    // MUST be a regular method returning an iterable. Do NOT use generator syntax.
    process(block, events) { ... }
}
```

**process(block, events)** — receives MIDI events, yields output notes.

- `block`: `{from: ppqn, to: ppqn, bpm: number, s0: int, s1: int, flags: int}`
- `events`: iterable of `{gate: bool, id, position, duration, pitch, velocity, cent}` (gate=true=note-on, gate=false=note-off)
- **Returns**: iterable of `{position, duration, pitch (0-127), velocity (0-1), cent}`

**PITFALL: NO generator methods (`* process()`) in Spielwerk/Apparat/Werkstatt scripts.** The ScriptCompiler wraps user code in `new Function()` for validation. While `new Function()` in modern V8 supports generator methods, the worklet registration via `audioWorklet.addModule(Blob)` and the Spielwerk's `#tryLoad()` → `new ProcessorClass()` path can fail with `"Unexpected token '{'"` when the class body contains `* process()`. **Use a regular method that returns an array or a hand-written iterator object instead:**

```javascript
// WRONG — may fail to compile/register
* process(block, events) {
    for (const ev of events) { yield {...}; }
}

// CORRECT — return an array (works for small note counts)
process(block, events) {
    const out = [];
    for (const ev of events) { out.push({...}); }
    return out;
}

// CORRECT — hand-written iterator (for lazy/large sequences)
process(block, events) {
    return {
        [Symbol.iterator]() {
            let idx = 0;
            const results = [...]; // compute
            return { next() { return idx < results.length ? {value: results[idx++]} : {done: true}; } }
        }
    };
}
```

**Spielwerk limits**: MAX_NOTES_PER_BLOCK=128, MAX_SCHEDULED_NOTES=128. Exceeding → processor silenced with error message. Notes with `position >= block.to` are auto-scheduled for future blocks.

**PITFALL: Spielwerk block size is tiny (~5ppqn) — arpeggiators MUST track step position across blocks.** At 48000Hz with 128-sample blocks and 110 BPM, one block spans only ~4.7 ppqn (960 ppqn/beat ÷ 0.545s/beat × 0.00267s/block). A typical arp rate of 240 ppqn (1/4 note) spans ~51 blocks. If your `process()` tries to generate notes within a single block using `while (pos + dur <= block.to)`, it will produce ZERO notes because `dur` (168 ppqn) >> block span (5 ppqn). You MUST persist `nextStepPos` as a class field and advance it across block calls:
```javascript
class Processor {
    nextStepPos = 0
    lastFrom = -1

    process(block, events) {
        // Reset on transport jump
        if (this.lastFrom < 0 || block.from < this.lastFrom) {
            this.nextStepPos = block.from
        }
        this.lastFrom = block.from

        // Generate notes whose step position falls within this block
        while (this.nextStepPos < block.to) {
            if (this.nextStepPos >= block.from) {
                out.push({position: this.nextStepPos, duration: dur, ...})
            }
            this.nextStepPos += rate
        }
        return out
    }
}
```

**paramChanged receives `(label, value)` not `(name, value)`** — the first argument is the WerkstattParameterBox.label string, which matches your `@param <name>` declaration.

### @sample slots
- `// @sample <name>` creates a file picker slot
- Accessed as `this.samples.name` in Processor
- Returns `null` until audio file is loaded
- When loaded: `{sampleRate, numberOfFrames, numberOfChannels, frames: [Float32Array, Float32Array]}`

## Performance Rules (CRITICAL for audio processors — Werkstatt/Apparat)

1. **NEVER allocate in process()** — no `new`, no array literals, no closures, no `[]` or `{}` (Werkstatt/Apparat only — these run per-sample at 48kHz)
2. All buffers/state as class field initializers (allocated once at construction)
3. `sampleRate` is a global available at construction time
4. Guard against NaN — host silences processors producing NaN output
5. Hard-clip output to [-1, 1] as safety net

**Spielwerk exception**: MIDI processors run per-block (not per-sample), so allocating a small `const out = []` in `process()` is acceptable — note counts are low (MAX_NOTES_PER_BLOCK=128) and blocks fire infrequently compared to audio blocks.

## Loading via MCP

```python
# Add Werkstatt effect to unit
await bridge.evaluate("""() => {
    const p = window.DAW;
    const factory = window.DAW_EffectFactories.AudioNamed["Werkstatt"];
    const au = [...p.rootBox.audioUnits.pointerHub.incoming()][0]?.box;
    p.editing.modify(() => { p.api.insertEffect(au.audioEffects, factory); });
}""")

# Compile code (parses @param/@sample, creates boxes, registers worklet)
await mcp_opendaw_set_script_device_code(
    device_type="werkstatt", unit_index=0, device_index=0, code=code_string
)

# Tune parameters
await mcp_opendaw_set_script_param(
    device_type="werkstatt", unit_index=0, device_index=0, param_label="drive", value=0.7
)
```

**PITFALL: Apparat device access in JS — use `pointerHub.incoming()`, NOT `targetVertex.unwrapOrNull()`.**
The `set_script_device_code` tool (and all 5 scriptable device tools) find the Apparat box via:
```javascript
const incoming = au.input ? [...au.input.pointerHub.incoming()].map(({box}) => box) : [];
device = incoming.find(b => b.constructor.name === "ApparatDeviceBox") || incoming[0] || null;
```
The old code used `au.input.targetVertex.unwrapOrNull()` which crashes — `targetVertex` is undefined on AudioUnitBox. The `pointerHub.incoming()` pattern is the same one used by `list_instrument_params`, `set_vaporisateur_osc_param`, and other instrument-access tools.

**PITFALL: `device_type` is case-insensitive in all 5 scriptable tools.** `.toLowerCase()` is applied to both the device selection switch (`dt`) and the header tag regex (`headerTag`). Passing "Apparat", "APPARAT", or "apparat" all work. This was fixed after discovering that examples passed capitalized "Apparat" but JS comparisons were lowercase.

**`device_index` parameter** (added July 2026): All 5 scriptable device tools accept `device_index` (default 0) to select which device of a given type on a unit. E.g. two Werkstatt effects on one AU → `device_index=0` and `device_index=1`. The `_find_script_device_js` helper filters by type and picks the Nth match.

## Templates

- `templates/werkstatt_darksat.js` — tape saturation / drive (drive, bias, tone, mix, output dB)
- `templates/werkstatt_coldfold.js` — wavefolding + bitcrush + slew (drive, fold, crush, slew, mix)
- `templates/apparat_darkbass.js` — subtractive bass synth for darksynth (waveform, cutoff, resonance, ADSR, subOsc, detune, volume). 10 @param, multi-voice with lazy allocation. Note: uses regular `process()` method (no generators).
- `templates/apparat_coldlead.js` — Cold lead synth (post-punk clav). Triangle wave default, 2 detuned oscillators with random phase start, lowpass filter, ADSR with long release. 8 @param. Constructor accepts optional `opts.sampleRate`.
- `templates/spielwerk_powerchord.js` — MIDI chord expander (root + fifth + octave). 4 @param (interval, interval2, velScale, detune). Uses array return pattern (NO generator method — see Spielwerk pitfall above).
- `templates/spielwerk_arpeggiator.js` — MIDI arpeggiator with 4 modes (up/down/up-down/random), octave expansion, velocity decay, gate length. 5 @param (rate ppqn, mode int, octaves int, gate linear, velDecay linear). Uses array return pattern. Tracks `nextStepPos` across blocks (critical — see block size pitfall above).

### Additional scripts (not templates — session-specific)

- `scripts/apparat_subcrusher.js` — mono subtractive bass synth (saw↔square, sub-osc, resonant LPF, ADSR, glide, drive). 10 @param. E2E tested, offline render silence (see `references/apparat-spielwerk-scripts-2026-07-03.md`).
- `scripts/spielwerk_arpeggiator.js` — MIDI arpeggiator with rate (beat units), direction (up/down/updown), swing, hold, velocity. 6 @param. Uses `* process()` generator syntax (compiled fine in E2E, but array-return pattern is safer for offline render).

## Mixing Reference

See `references/mixing-and-rendering.md` for:
- Built-in effect parameter names (Delay, DattorroReverb)
- Vaporisateur as drum synth (kick/hat via param_index)
- `set_effect_parameter` uses `parameter_name` (NOT `param_name`)
- `export_stems` creates multichannel WAV (not separate files)
- Render silence debugging checklist
- Demo track patterns (v2: 16 bars, v3: 32 bars with breakdown)

## External SDK Documentation

See `references/naomiaro-opendaw-test-sdk-docs.md` for the authoritative independent SDK reference (naomiaro/opendaw-test, 543 commits):
- 17 chapters: timing, box system, effects, export, MIDI, warp, modular devices
- Verified patterns for `OfflineEngineRenderer`, `ScriptCompiler`, `insertEffect`, project setup
- `useInstrumentOutput` semantics (False = channel strip routing with effects, True = dry instrument)
- `AudioOfflineRenderer` is DEPRECATED (since studio-core@0.0.93) — use `OfflineEngineRenderer`
- audio-verify skill pattern (numerical beat alignment testing)
- SDK upgrade audit procedure

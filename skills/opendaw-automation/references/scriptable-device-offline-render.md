# Scriptable Device Offline Rendering — Debugging & Fixes (July 2026)

Three critical bugs were found and fixed in `set_script_device_code` that prevented Apparat/Werkstatt/Spielwerk processors from producing audio in offline renders. Read this before debugging scriptable device silence.

## Bug 1: Constructor Destructuring Crash (ROOT CAUSE of Apparat silence)

**Symptom**: Apparat darkbass compiled successfully (worklet_registered=true, no error), but offline render produced silence (max_sample=0). Vaporisateur (built-in synth) rendered fine (max_sample=0.41).

**Root cause**: `ApparatDeviceProcessor.#swapProcessor()` calls `new ProcessorClass()` with **zero arguments**. Our `apparat_darkbass.js` had:
```javascript
constructor({audioContext, sampleRate, parameters, samples}) {
    this.sr = sampleRate  // crashes: cannot destructure undefined
}
```
Destructuring `undefined` throws TypeError. The processor catches this in a try/catch and calls `#silence("Failed to instantiate Processor: ...")` — silenced forever, no audio output.

**Fix**: Use optional argument with fallback:
```javascript
constructor(opts) {
    this.sr = (opts && opts.sampleRate) ? opts.sampleRate : 48000;
}
```

**After fix**: Apparat darkbass solo rendered with max_sample=1.085 ✅

**Applies to**: ALL three device types (Apparat, Werkstatt, Spielwerk). The host always calls `new ProcessorClass()` with no args.

## Bug 2: Worklet Registry Update Number Mismatch

**Symptom**: Even with correct constructor, if `update` number in the worklet registry doesn't match the `device.code` header's update field, `#tryLoad()` silently fails.

**Root cause**: `ApparatDeviceProcessor.#tryLoad()`:
```typescript
const registry = (globalThis as any).openDAW?.apparatProcessors?.[this.#uuid]
if (isDefined(registry) && registry.update === expectedUpdate) {
    this.#swapProcessor(registry.create, expectedUpdate)
}
// if registry.update !== expectedUpdate → processor never loads → silence
```

`expectedUpdate` comes from `parseUpdate(code)` which parses the 4th field of `// @apparat js 1 <update>`. Our MCP tool was setting `update: 1` (hardcoded) in the worklet registration while `device.code` got an incremented `newUpdate`. Mismatch → processor never loaded.

**Fix**: Use the same `newUpdate` variable for both the code header and the worklet registry:
```javascript
const wrappedCode = '...globalThis.openDAW.apparatProcessors[uuid] = { update: ' + newUpdate + ', create: ... }';
```

## Bug 3: newUpdate Variable Scope

**Symptom**: `worklet_error: "newUpdate is not defined"`

**Root cause**: `newUpdate` was declared as `const` inside the `editing.modify(() => { ... })` callback. The worklet registration code runs OUTSIDE that callback (after `editing.modify()` completes). `const` is block-scoped → not accessible outside.

**Fix**: Compute `newUpdate` BEFORE `editing.modify()`:
```javascript
const currentCode0 = device.code.getValue();
const currentUpdate0 = currentCode0.match(headerPattern);
const newUpdate = (currentUpdate0 ? parseInt(currentUpdate0[3]) : 0) + 1;

p.editing.modify(() => {
    // uses newUpdate from outer scope
    device.code.setValue('// @apparat js 1 ' + newUpdate + '\n' + userCode);
});

// worklet registration also uses newUpdate from outer scope
const wrappedCode = '...{ update: ' + newUpdate + ', ... }';
```

## Bug 4: `\n` Escape Level in Python f-string

**Symptom**: Stored code header contained literal `\\n` (backslash + n) instead of newline character. `OfflineEngineRenderer` header pattern `/^\/\/ @apparat \w+ \d+ \d+\n/` expects real newline → didn't match → script device not loaded in Worker.

**Root cause**: Python f-string `'\\\\n'` → Python string `'\\n'` → JS string literal `'\n'` → BUT if the string is used in a context where JS doesn't interpret escape sequences (e.g., `StringField.setValue()` stores raw bytes), the literal `\n` stays as two characters.

**Fix**: Use `'\\n'` in the Python f-string (not `'\\\\n'`). This becomes `'\n'` in the JS string → JS interprets as newline character → `StringField` stores the actual newline byte.

**Verification**: Check stored code bytes:
```javascript
const code = apparatBox.code.getValue();
code.indexOf(String.fromCharCode(10));  // should be ~18 (position of first newline)
code.indexOf('\\n');                     // should be -1 (no literal backslash-n)
```

## Offline Renderer Script Device Loading

`OfflineEngineRenderer` (lines 150-188) automatically loads script device code into the Worker:
```typescript
const loadScriptDevice = async (code, headerPattern, registryName, functionName, uuid) => {
    const match = code.match(headerPattern)
    if (match === null) return  // no match → device not loaded
    const userCode = code.slice(match[0].length)
    const update = parseInt(match[3])
    await protocol.addModule(`...globalThis.openDAW.${registryName}[uuid] = { update, create: ... }`)
}
```

It scans `boxGraph.boxes()` for `ApparatDeviceBox`, `WerkstattDeviceBox`, `SpielwerkDeviceBox` instances and loads each one. **This means the MCP tool's worklet registration (via `audioContext.audioWorklet.addModule`) is for real-time playback only.** Offline render uses its own loading path. Both paths must have the correct `update` number.

## RESOLVED: Full Chain Silence (fixed July 2026)

**Apparat darkbass SOLO**: max_sample=1.085 ✅
**Apparat + Spielwerk arp + Werkstatt coldfold (full chain)**: max_sample=0.844 ✅
**4-track demo (bass+lead+pad+kick)**: max_sample=0.964 ✅

Two additional bugs were found via isolation testing (solo, pair, triple):

### Bug 5: Werkstatt Process API Signature

`WerkstattDeviceProcessor.processAudio()` calls `proc.process(this.#io, block)` where `io = {src: [ch0, ch1], out: [ch0, ch1]}`. Scripts using `process(inputL, inputR, outputL, outputR, block)` (5 args) silently received wrong values — `inputL=io_object`, output arrays=undefined → no audio written → silence. Fix: `process(io, block)` with `io.src[0/1]` = input, `io.out[0/1]` = output.

### Bug 6: Spielwerk Arpeggiator Block Size vs Rate

Offline renderer blocks are ~128 samples ≈ 5ppqn at 110BPM/48000Hz. Arp rate=240ppqn. Original arp used `while (pos + dur <= to)` — `pos+dur=from+168 >> to` (5ppqn block) → 0 notes generated. Fix: track `nextStepPos` across blocks, generate notes where `nextStepPos` falls within `[block.from, block.to)`.

### Isolation Testing Approach (proven effective)

When scriptable device chains produce silence, test each combination:
1. Instrument solo (no effects)
2. Instrument + one MIDI effect (no audio effects)
3. Instrument + one audio effect (no MIDI effects)
4. Full chain

The combination that goes silent reveals which device type has the bug. Pair tests that pass but triple tests that fail indicate an API mismatch in one device that only manifests when the other device is also present (because the working device provides the signal the broken one needs).

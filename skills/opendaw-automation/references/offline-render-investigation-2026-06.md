# openDAW Render Investigation — June 2026

## Session 5 (June 30) — SOLVED: TapeDeviceBox

### Root Cause
All silence across sessions 2-4 had ONE root cause: **no TapeDeviceBox connected to AU.input**.

- `CaptureAudioBox` (created by `AudioUnitFactory.create`) is a microphone capture device. It has fields: `accept`, `tags`, `deviceId`, `recordMode`, `requestChannels`, `gainDb`. **NO output field.** Does NOT route audio to AU.input.
- `TapeDeviceBox` is the "Audio Player" instrument (description: "Plays audio regions & clips"). Its `host` field connects to `audioUnitBox.input` (the `host` parameter passed to `factory.create()`).

### Discovery Path
1. Session 2-4: tried `createAudioTrack(outputAu)` → silence (no track.target)
2. Session 3: tried manual AudioUnitBox + TrackBox + CaptureAudioBox → silence (AU.input incoming=[])
3. Session 4: verified default routing IS intact (bus→outputAU→outputDevice). Tried `auBox.output.refer(primaryBus)` → Vite pointer type mismatch crash.
4. Session 5: found `InstrumentFactories.Tape` in `studio-adapters/dist/factories/InstrumentFactories.js` — the OFFICIAL audio track factory. It creates `TapeDeviceBox` with `box.host.refer(host)` where `host = audioUnitBox.input`.
5. Used `p.api.createInstrument(TapeFactory)` → AU.input incoming = `['TapeDeviceBox']` ✅ → render produced maxS=1.2, 11.88M non-zero samples 🎉

### Verified Working Pipeline
```
createInstrument(TapeFactory)
  → AudioUnitFactory.create (studio-adapters, handles routing internally)
    → AudioUnitBox: output.refer(primaryBus.input), capture.refer(CaptureAudioBox)
    → track.target.refer(auBox)
  → factory.create(boxGraph, auBox.input, name, icon)
    → TapeDeviceBox: host.refer(auBox.input)  ← THE MISSING LINK
  → AudioFileBox + createNotStretchedRegion on track
  → sampleManager.getOrCreate + subscribe (wait loaded)
  → p.copy() (mandatory)
  → OER.start(copy, Option.None, progress, signal)
  → WavFile.encodeFloats → Blob → download (accept_downloads=True)
```

### Key Source Files
- `studio-adapters/dist/factories/InstrumentFactories.js` — all instrument factories (Tape, Nano, Playfield, Vaporisateur, etc.)
- `studio-adapters/dist/factories/AudioUnitFactory.js` — AudioUnitFactory.create (sets output.refer(primaryBusBox.input))
- `studio-core/dist/project/ProjectApi.js` — createInstrument (calls AudioUnitFactory + factory.create + TrackBox)
- `studio-core/dist/project/audio/AudioContentFactory.js` — createNotStretchedRegion (sets box.file.refer(audioFileBox))

### Output Specs
- Format: 32-bit float WAV, 48kHz, stereo
- Duration: 248.7s (4:08)
- File size: ~95MB
- Render time: ~90s (headless Chromium, OfflineEngineRenderer)
- Transfer: Blob + `<a download>` + Playwright `accept_downloads=True` (NOT base64 through page.evaluate)

### Mixing Notes (session 5 iterations)
- F38 (3 stems, all 0dB, output 0dB): maxS=1.2 — clipping from maximizer
- F39 (4 stems, anchor -1, minus -3, vocal -2, vocal_2 -5, output -3): maxS=0.84, sub=61% (too much bass)
- F40 (anchor -4, rest same): maxS=0.74, sub=58.4% (user: only -2.6pp drop, need more)
- F41 (F40 + Revamp EQ highShelf@12k+4, highBell@16k+2 on master): maxS=0.74 — air boost, pending user spectral analysis

### User Mixing Workflow
- User runs spectral analysis externally (band %, crest factor, RMS, peak)
- Compares versions side-by-side in a table
- Gives ONE change per iteration (single-variable convergence)
- Target reference: v4 (sub 43.2%, hats 4.3%, air 2.2%, crest 17.6)
- Key lesson: -3dB on anchor only moved sub 2.6pp (61→58.4%) — openDAW volume scaling is non-linear vs perceived band energy. Need larger level changes than expected.

## Session 5b (June 30) — Master EQ & Effect Insertion

### Revamp EQ (Graphical EQ)
`EffectFactories.AudioNamed.Revamp` — insert on any AU's audioEffects field.

```javascript
const ef = window.DAW_EffectFactories;
p.editing.modify(() => {
    const revampBox = p.api.insertEffect(outputAu.audioEffects, ef.AudioNamed.Revamp);
    // highShelf: boost air above 12k
    revampBox.highShelf.enabled.setValue(true);
    revampBox.highShelf.frequency.setValue(12000);
    revampBox.highShelf.gain.setValue(4.0);
    // highBell: presence at 16k
    revampBox.highBell.enabled.setValue(true);
    revampBox.highBell.frequency.setValue(16000);
    revampBox.highBell.gain.setValue(2.0);
});
```

### RevampDeviceBox Field Map
From `studio-boxes/dist/RevampDeviceBox.js`:
- `highPass` (field 10) — RevampShelf: enabled, frequency (20-20000Hz exp), gain
- `lowShelf` (field 11) — RevampShelf: enabled, frequency, gain
- `highBell` (field 13) — RevampShelf: enabled, frequency, gain
- `highShelf` (field 15) — RevampShelf: enabled, frequency, gain
- `gain` — overall output gain

### RevampShelf Parameters (each band)
From `studio-boxes/dist/RevampShelf.js`:
- `enabled` (field 1) — BooleanField
- `frequency` (field 10) — Float32Field, 20-20000Hz, exponential scaling
- `gain` (field 11) — Float32Field, dB

### insertEffect API
```javascript
p.api.insertEffect(auBox.audioEffects, factory, insertIndex?)
// insertIndex defaults to MAX_SAFE_INTEGER (append)
// Available: Compressor, Crusher, DattorroReverb, Delay, Fold, Gate,
//   Maximizer, NeuralAmp, Reverb, Revamp, StereoTool, Tidal, Vocoder, Waveshaper, Werkstatt
```

### Download Transfer Method (Large WAV files)
Do NOT base64-encode WAV through `page.evaluate()` — causes `ERR_STRING_TOO_LONG` / `EPIPE` for files >~95MB.

```python
# Python side — Playwright with download support
context = await browser.new_context(accept_downloads=True)
page = await context.new_page()

async def handle_download(download):
    await download.save_as(outpath)
page.on('download', handle_download)
```

```javascript
// JS side — trigger download from page.evaluate
const blob = new Blob([wavArrayBuffer], { type: 'audio/wav' });
const url = URL.createObjectURL(blob);
const a = document.createElement('a');
a.href = url;
a.download = 'output.wav';
document.body.appendChild(a);
a.click();
document.body.removeChild(a);
URL.revokeObjectURL(url);
```

### Available Effect Factories (EffectFactories.AudioNamed)
From `studio-core/dist/EffectFactories.js`:
- `Revamp` — Graphical EQ (highPass, lowShelf, highBell, highShelf)
- `Compressor` — Dynamic compression
- `Maximizer` — Loudness maximizer (on output AU by default)
- `NeuralAmp` — Neural amp simulation
- `Reverb` / `DattorroReverb` — Reverb
- `Delay` — Delay
- `Gate` — Noise gate
- `Crusher` — Bit crusher
- `Fold` — Wavefolder
- `Waveshaper` — Waveshaping distortion
- `StereoTool` — Stereo width/pan
- `Tidal` — Tidal effects
- `Vocoder` — Vocoder
- `Werkstatt` — Werkstatt

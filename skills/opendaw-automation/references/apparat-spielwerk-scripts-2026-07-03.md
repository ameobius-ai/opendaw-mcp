# Apparat SubCrusher Bass Synth (July 2026)

Mono subtractive bass synth for Apparat (scriptable instrument). E2E tested.

## Script: `scripts/apparat_subcrusher.js`

Also available as template: `templates/apparat_subcrusher.js` (if copied).

### Parameters (10)
| Param | Default | Range | Type | Unit |
|-------|---------|-------|------|------|
| wave | 0.3 | 0-1 | linear | saw↔square mix |
| cutoff | 800 | 50-8000 | exp | Hz |
| resonance | 0.7 | 0.1-8 | linear | |
| attack | 0.005 | 0.001-0.2 | exp | s |
| decay | 0.15 | 0.01-1.0 | exp | s |
| sustain | 0.6 | 0-1 | linear | |
| release | 0.2 | 0.01-2.0 | exp | s |
| drive | 0.4 | 0-1 | linear | |
| sub | 0.5 | 0-1 | linear | sub-osc level |
| glide | 0.04 | 0-0.3 | linear | s |

### Architecture
- **Oscillator**: saw→square mix via `wave` param. `2*phase-1` for saw, step function for square.
- **Sub-osc**: sine one octave below main oscillator, mixed via `sub` param.
- **Envelope**: ADSR state machine ("attack"→"decay"→"sustain"→"release"→"off"). Linear ramp.
- **Filter**: one-pole lowpass with resonance feedback. `lpCoeff = exp(-2π*cutoff/sr)` for stable response. Clamp to ±8 to prevent blowup.
- **Drive**: polynomial tanh approximation `x*d*1.5/(1+0.8*x²*d²)` where `d = 1+drive*4`.
- **DC blocker**: one-pole highpass at ~20Hz (`coeff = 0.999`).
- **Glide**: exponential frequency interpolation. `freq = targetFreq * exp(logRatio - glideRate)` per sample.

### E2E Test Results (2026-07-03)
- `create_synth_track('SubCrusher Bass', 'apparat')` → ApparatDeviceBox created ✅
- `set_script_device_code('apparat', 1, 0, code)` → 10 params created, worklet registered, 0 errors ✅
- `set_script_param('apparat', 1, 0, 'cutoff', 1200)` → 800→1200 ✅
- Note track + region + 4 bass notes (A1, A1, C2, A1) ✅
- `render_full('bass_test', 48000)` → `has_audio: false, max_sample: 0` — **offline renderer does not load scriptable device processors** (architectural limitation, see `references/scriptable-device-offline-render.md`)

### Known Limitation: Offline Render Silence
Apparat/Werkstatt/Spielwerk scripts register their processor via `audioContext.audioWorklet.addModule()` on the **main thread AudioContext**. The `OfflineEngineRenderer` creates a separate Worker with its own `AudioContext` and loads script device code independently via its own `addModule()` call. However, if the update number or header format doesn't match between the two paths, the offline renderer's copy of the processor never loads → silence.

This was fixed for earlier scripts (darkbass, coldlead) by aligning update numbers (see `references/scriptable-device-offline-render.md` Bugs 2-4). The SubCrusher script was not tested with the full offline render chain — it may need the same update-number alignment fix applied to `set_script_device_code` for the offline renderer path.

## Spielwerk Arpeggiator (July 2026)

Also added: `scripts/spielwerk_arpeggiator.js` — MIDI arpeggiator with rate, octaves, direction (up/down/updown), swing, hold, velocity.

### E2E Test
- `add_midi_effect(1, 'Spielwerk')` → SpielwerkDeviceBox added as MIDI effect on unit 1 ✅
- `set_script_device_code('spielwerk', 1, 0, code)` → 6 params created, worklet registered, 0 errors ✅
- `set_script_param('spielwerk', 1, 0, 'rate', 0.125)` → 0.25→0.125 ✅

Note: This script uses `* process(block, events)` generator syntax in the source file. The existing template `templates/spielwerk_arpeggiator.js` uses array return pattern instead (per the generator-syntax pitfall in `references/werkstatt-dsp-api.md`). The generator version compiled and registered fine in E2E, but for offline rendering the array-return pattern is safer.

## DSP Script Trio — Complete

| Device Type | Script | Purpose | E2E | Offline Render |
|-------------|--------|---------|-----|----------------|
| Werkstatt (audio effect) | `werkstatt_darksat.js` | Tape saturation/drive | ✅ | ✅ |
| Werkstatt (audio effect) | `werkstatt_coldfold.js` | Wavefolding+bitcrush | ✅ | ✅ |
| Apparat (instrument) | `apparat_subcrusher.js` | Mono subtractive bass | ✅ | ❌ silence |
| Spielwerk (MIDI effect) | `spielwerk_arpeggiator.js` | Arpeggiator | ✅ | untested |

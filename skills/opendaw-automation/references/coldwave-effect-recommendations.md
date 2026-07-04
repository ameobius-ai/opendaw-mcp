# Coldwave/Darksynth/Post-Punk Effect Recommendations for openDAW

## Context

User asked about SOTA effects for coldwave/darksynth/post-punk genre mixing in openDAW (July 1, 2026, session 8). These recommendations map genre conventions to openDAW's available effect inventory.

## openDAW Available Effects (EffectFactories.AudioNamed)

```
Compressor, Crusher, DattorroReverb, Delay, Fold, Gate,
Maximizer, NeuralAmp, Reverb, Revamp, StereoTool, Tidal, Vocoder, Waveshaper, Werkstatt
```

## Genre Effect Map

### Vocals (most critical)

| Goal | openDAW Effect | Settings | Reference |
|------|---------------|----------|-----------|
| Tape saturation (warm analog grit) | Waveshaper or NeuralAmp | gentle drive, low mix | Хаски, Shortparis — cold vocal + warm tape = genre signature |
| Plate reverb (short, dense) | DattorroReverb or Reverb | 0.8-1.2s decay, tight, no diffuse | Spring reverb also works for post-punk |
| Chorus (cold 80s vocal) | Tidal | dry/wet 15-20%, slow rate | More = muddy, less = dead |
| De-esser | Revamp highBell @4k -2dB | narrow Q, gentle gain | ⚠️ SKIP for coldwave unless explicitly requested — sibilants on edge = genre character (user confirmed F42 > F43 with de-esser) |

### Bass

| Goal | openDAW Effect | Settings | Notes |
|------|---------------|----------|-------|
| Saturation (growl over clean sub) | Waveshaper or Fold | moderate drive | Tube/transformer character |
| Low-pass body | Revamp lowShelf or highPass | cut above 200-250Hz | Remove click, keep body |

### Drums

| Goal | openDAW Effect | Settings | Notes |
|------|---------------|----------|-------|
| Parallel compression | Compressor on aux send | -10dB threshold, 4:1 ratio, fast attack | Returns density without squashing transients |
| Gated room reverb | Reverb + Gate | 0.3-0.5s decay, gate cuts tail | Classic post-punk drum sound |

### Synths

| Goal | openDAW Effect | Settings | Notes |
|------|---------------|----------|-------|
| Chorus (essential) | Tidal | moderate depth | Cold synth without chorus = dead |
| Analog delay | Delay | 1/8 or 1/16, feedback 20-30%, lo-fi | Adds movement and texture |

## Important Caveats

1. **De-esser is COUNTERPRODUCTIVE in coldwave.** User confirmed: "F42 — финал. сибилянты на грани — но это лучше чем мёртвый вокал. в coldwave грань — это характер, не проблема." Do NOT add de-esser unless user explicitly requests it.

2. **All effects must be applied INSIDE openDAW.** User explicitly rejected ffmpeg pre-processing: "какой нахуй ffmpeg блять - всё делается в opendaw". No external audio processing for levels, pan, EQ, or effects.

3. ~~**Effect inventory was listed but NOT YET TESTED at runtime.**~~ **DattorroReverb VERIFIED at runtime (July 1, session 8h).** The following parameters work via `.setValue()` on the reverb box returned by `insertEffect`:

| Parameter | Field | Unit | Default | Verified Value (F08h) |
|-----------|-------|------|---------|----------------------|
| `preDelay` | field 10 | ms (0-1000) | 0 | 15 |
| `bandwidth` | field 11 | % (unipolar) | 0.9999 | 0.7 |
| `decay` | field 14 | % (unipolar) | 0.75 | 0.5 |
| `damping` | field 17 | % (unipolar) | 0.005 | 0.3 |
| `wet` | field 20 | dB | -6 | -12 |
| `dry` | field 21 | dB | 0 | 0 |

Also available but not used: `inputDiffusion1` (field 12, default 0.75), `inputDiffusion2` (field 13, default 0.625), `decayDiffusion1` (field 15, default 0.7), `decayDiffusion2` (field 16, default 0.5), `excursionRate` (field 18, default 0.5), `excursionDepth` (field 19, default 0.7).

**Per-stem effect insertion pattern (VERIFIED, F08h):**
```javascript
// After sampleManager loading completes for a stem:
if (s.effects && s.effects.length > 0) {
    p.editing.modify(() => {
        for (const fx of s.effects) {
            if (fx.type === 'DattorroReverb') {
                const rev = p.api.insertEffect(auBox.audioEffects, ef.AudioNamed.DattorroReverb);
                const pr = fx.params;
                if (pr.preDelay !== undefined) rev.preDelay.setValue(pr.preDelay);
                if (pr.bandwidth !== undefined) rev.bandwidth.setValue(pr.bandwidth);
                if (pr.decay !== undefined) rev.decay.setValue(pr.decay);
                if (pr.damping !== undefined) rev.damping.setValue(pr.damping);
                if (pr.wet !== undefined) rev.wet.setValue(pr.wet);
                if (pr.dry !== undefined) rev.dry.setValue(pr.dry);
            }
        }
    });
}
```
Effects are applied AFTER the stem's sampleManager loading completes (outside the createInstrument modify block). maxS was unaffected by reverb on vocals (0.64 → 0.64) — reverb adds spatial energy but doesn't raise peak.

**Waveshaper VERIFIED at runtime (July 1, session 9).** Parameters: equation(string, default "hardclip"), inputGain(dB 0-40), outputGain(dB -24..24), mix(0..1). Tested on bass: hardclip, +3dB in, -3dB out, mix 15% AND 35%. **⚠️ Waveshaper is NOT processed by OfflineEngineRenderer — BOTH mix values produce output identical to no-effect render.** All spectral metrics (sub 48.4%, air 0.54%, hats 1.32%, LUFS -20.7, H/P 2.31, centroid 3620) are identical to 4 decimal places. The effect node creates successfully, all `.setValue()` calls work, render produces valid audio — but the waveshaper AudioWorklet processor is silently bypassed in the offline render path. **Do NOT use Waveshaper in offline render scripts.** For bass saturation/harmonics, pre-process stems with pedalboard (Python) before importing to openDAW.

**Root cause analysis (July 2):** DSP code in `waveshaper.ts` is correct (hardclip, tanh, sigmoid, arctan, cubicSoft, asymmetric). The processor logic also looks sound. The breakage is upstream — likely parameter catchup or source connection in the offline graph. See `references/offline-effect-rootcauses-2026-07.md` for full source-level analysis and contribution plan.

4. **HighShelf on master Revamp is the proven air fix.** highShelf @12k +4dB + highBell @16k +2dB on output AU. Verified. **Session 9: +4→+8 doubles air (0.29→0.54%) with zero side effects** — sub/LUFS/peak/maxS unchanged. Simulation predicted 0.56%, actual 0.54%. Further +12 risks harshness. Genre-specific effects on individual stems are the next frontier.

5. **No pitch shift / detune available for audio stems (July 1, session 8).** User asked to detune vocal and synth doubles 5 cents relative to anchor for stereo widening. openDAW has `AudioPitchStretchBox` but it only contains `warpMarkers` (a tempo/pitch map for time-warping), NOT a direct cents/semitone parameter. `PitchDeviceBox` exists but is MIDI-only (`type: "midi"`) — it shifts incoming MIDI notes, not audio. `NoteEventBox.cent` exists but only for MIDI note events. **There is no simple audio detune/pitch shift in openDAW.** Workarounds: (a) Python resampling before import (not ffmpeg), (b) skip — panning ±0.7/±0.85 already provides stereo separation, (c) use Tidal (tremolo/autopan) as pseudo-chorus for movement.

6. **Tidal CAUSES SILENCE in offline render (July 1, session 9).** Tidal (tremolo/autopan) on synth stems produced silence in `OER.start()`. Tidal uses LFO-based modulation which the offline engine cannot process — it silently outputs zeros. **Do NOT use Tidal in headless render scripts.** This likely applies to other LFO/modulation-dependent effects. If an effect produces silence, check whether it relies on real-time modulation.

**Root cause found (July 2):** `TidalDeviceProcessor.processAudio()` only advances its LFO phase when `BlockFlag.transporting | BlockFlag.playing` are set on the block. If the offline renderer doesn't set these flags, the phase resets to 0 each block → `TidalComputer.compute(0)` returns zero gain → silence. See `references/offline-effect-rootcauses-2026-07.md` for full source analysis.

7. **Multiple new effects simultaneously cause graph errors (July 1, session 9).** Adding Waveshaper + Compressor + Delay + Revamp across multiple stems in one render caused `Error: [remove] Edge has unannounced vertex` during `OER.start()`. The offline engine's graph terminator fails when too many effect nodes are inserted in a single session. **Add effects ONE AT A TIME** — render with one new effect, verify it works, then add the next. This is the same single-variable approach as mixing levels.

8. **Compressor and Delay cause graph errors in offline render (July 1, session 9-10).** Compressor fields (from source): threshold(-60..0 dB), ratio(1..24 exp), attack(0..100ms), release(5..1500ms), makeup(-40..40 dB), automakeup(bool), mix(0..1). Delay fields: delayMillis(0..1000ms), feedback(0..1), wet/dry(dB), cross(0..1), filter(-1..1). Adding multiple effects across multiple stems caused `Error: [remove] Edge has unannounced vertex`. One-FX-per-render is stable. Multi-FX-multi-stem = graph error. Do NOT use Compressor or Delay in headless render scripts. Pre-process stems with pedalboard (Python) instead.

**Root cause analysis (July 2):** `CompressorDeviceProcessor` resolves sidechain connections via `ProcessPhase.Before` events. If the offline renderer doesn't fire `ProcessPhase` events, sidechain never connects, and edge registration may also fail — explaining the "Edge has unannounced vertex" graph error. See `references/offline-effect-rootcauses-2026-07.md` for full source analysis.

9. **Storage quota fix — launch_persistent_context with fresh temp profile (July 1, session 10).** `--unlimited-storage` flag alone does NOT fix IndexedDB quota buildup. openDAW stores decoded audio in IndexedDB, which accumulates across renders. Solution: `launch_persistent_context(tempfile.mkdtemp(prefix='opendaw_profile_'), args=[..., '--disk-cache-size=1', '--media-cache-size=1', '--disable-application-cache'])`. Cleanup: `shutil.rmtree(tmp_profile)` after context close. Verified across 5+ consecutive renders.

10. **Renders MUST be saved to persistent location, not /tmp (July 1, session 10).** User: "тебе тогда надо финальные версии куда то в другое место сохранять раз storage quota — потому что счас мне даже не с чем сравнить". /tmp gets cleaned between renders. Save to: `~/projects/creative-studio/renders/<project>/`. Versioned filenames (F09_HS8.wav, F10_pedalboard.wav, F11_SOTA.wav, F12_master.wav).

11. **Pedalboard as alternative for openDAW offline effects (July 1, session 10).** Since Waveshaper/Tidal/Compressor/Delay don't work in offline render, pre-process stems with pedalboard (Python) before importing to openDAW. API: `Distortion(drive_db=)`, `PeakFilter(cutoff_frequency_hz=, gain_db=, q=)` (NOT PeakingFilter), `Compressor(threshold_db=, ratio=, attack_ms=, release_ms=)`, `Chorus(rate_hz=, depth=, centre_delay_ms=, feedback=, mix=)`, `Delay(delay_seconds=, feedback=, mix=)`. Distortion has NO built-in oversampling — manual 4x upsample via `Resample(target_sample_rate=SR*4, quality=Resample.Quality.WindowedSinc128)` → distort → `LowpassFilter(cutoff=SR/2*0.9)` → downsample. RMS-matching for saturation kills the effect — saturation should make bass louder in harmonics, not compensate back.

6. **Full effect inventory with descriptions (July 1, session 8, verified from EffectFactories.js source).** All 15 audio effects with factory-verified descriptions:

| Effect | Factory Name | Type | Description |
|--------|-------------|------|-------------|
| Compressor | `Compressor` | audio | Reduces dynamic range by attenuating signals above threshold |
| Gate | `Gate` | audio | Attenuates signals below threshold to reduce noise |
| Maximizer | `Maximizer` | audio | Brickwall limiter with automatic makeup gain |
| Dattorro Reverb | `DattorroReverb` | audio | Dense algorithmic reverb (Dattorro design), infinite decay possible |
| Free Reverb | `Reverb` | audio | Simulates space and depth with reflections |
| Delay | `Delay` | audio | Echo with time-based repeats |
| Revamp (EQ) | `Revamp` | audio | 4-band graphical EQ (highPass, lowShelf, highBell, highShelf) |
| Stereo Tool | `StereoTool` | audio | Stereo matrix: volume, panning, phase inversion, stereo width |
| Tidal | `Tidal` | audio | Tremolo & autopan — shape rhythm and space |
| Waveshaper | `Waveshaper` | audio | Nonlinear waveshaping distortion |
| Fold | `Fold` | audio | Wavefolder — folds signal back into audio range |
| Crusher | `Crusher` | audio | Bit crusher — degrades audio signal |
| NeuralAmp (Tone3000) | `NeuralAmp` | audio (external) | Amp/cab/pedal modeler (NAM) — thousands of models |
| Vocoder | `Vocoder` | audio | Classic analysis/synthesis vocoder |
| Werkstatt | `Werkstatt` | audio | User-scriptable DSP processor |

MIDI-only effects (NOT for audio stems): Arpeggio, Pitch (MIDI note shift), Velocity, Zeitgeist (shuffle), Spielwerk (scriptable MIDI).

**Missing from openDAW:** chorus (use Tidal as workaround), saturation (use Waveshaper/Fold), de-esser (use Revamp narrow cut), pitch shift for audio (not available).

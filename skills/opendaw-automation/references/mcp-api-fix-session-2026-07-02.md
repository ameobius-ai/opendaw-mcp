# openDAW MCP API Fix Session — July 2, 2026

## Context
After the deep code audit (see `references/offline-effect-rootcauses-2026-07.md`) proved that Waveshaper/Tidal/Delay/Compressor are NOT broken in offline render, the real problem was identified: the MCP server (`opendaw-mcp/server.py`) had no effect parameter control API. Effects were added with default parameters and couldn't be changed.

## MCP Server Patches Applied

### 5 New Tools Added to server.py

| Tool | Purpose | Verified |
|------|---------|----------|
| `mcp_opendaw_list_effect_parameters(unit_idx, effect_idx)` | Discover all params via `box.record()` | ✅ Returns name, value, type, min/max |
| `mcp_opendaw_set_effect_parameter(unit_idx, effect_idx, name, value)` | Set numeric param | ✅ inputGain 0→12 confirmed |
| `mcp_opendaw_set_effect_parameter_string(unit_idx, effect_idx, name, str)` | Set string param (equation) | ✅ hardclip→tanh confirmed |
| `mcp_opendaw_remove_effect(unit_idx, effect_idx)` | Remove via `box.delete()` | ✅ Chain updated after removal |
| `mcp_opendaw_get_effect_chain(unit_idx)` | List full chain with types | ✅ Shows Maximizer + Waveshaper |

### Existing Tools Fixed

| Tool | Bug | Fix |
|------|-----|-----|
| `add_effect` | No effect_index returned | Now returns `effect_index` in response |
| `load_audio` | `AudioData.fromAudioBuffer()` doesn't exist | Use `DAW_audioBufferToAudioData()` or skip (just store in maps) |
| `load_audio` | Base64 for 50MB+ files → EPIPE kills Vite | URL fetch for files in `headless-daw/public/` |
| `load_audio` | UUID returned as Bytes object, not string | `DAW_UUID.toString(id)` for all map keys and return values |
| `place_audio_region` | `TrackType.Audio = 0` (actually Undefined) | Changed to `=== 2` |
| `place_audio_region` | Manual `AudioRegionBox.create()` → "requires an edge" on events field | Rewrote to use `api.createNotStretchedRegion()` which handles all wiring |
| `place_audio_region` | `box.audioFile.refer(audioFileBox.file)` — wrong field names | `box.file.refer(audioFileBox)` — field is `file`, refer takes Box |
| `remove_effect` | `p.boxGraph.deleteBox()` — no such method | `effectBox.delete()` — instance method |

### main.ts Patches

| Change | Purpose |
|--------|---------|
| `w.DAW_OfflineEngineRenderer = OfflineEngineRenderer` | Expose on window for page.evaluate access |
| sampleProvider fallback scan | When UUID doesn't match any box, scan ALL AudioFileBox fileNames in boxGraph. Needed because `project.copy()` regenerates UUIDs. |

## All 15 Audio Effects — Parameter Discovery Results

All 15 effects tested with `list_effect_parameters`. All return correct parameters:

| Effect | Key Parameters |
|--------|---------------|
| Compressor | threshold(-10), ratio(2), knee(0), attack(0), release(25), makeup(0), mix(1), inputgain(0), lookahead(F), automakeup(T), autoattack(F), autorelease(F) |
| Crusher | crush(0), bits(16), boost(0), mix(1) |
| DattorroReverb | preDelay(0), bandwidth(0.9999), inputDiffusion1(0.75), decay(0.75), damping(0.005), wet(-6), dry(0) |
| Delay | delayMusical(13), feedback(0.5), cross(1), wet(-6), dry(0), lfoSpeed(0.1) |
| Fold | drive(0), overSampling(0), volume(0) |
| Gate | threshold(-6), attack(1), hold(50), release(100), floor(-72) |
| Maximizer | lookahead(T), threshold(0) |
| NeuralAmp | (model-based) |
| Reverb | decay(0.5), preDelay(0.001), damp(0.5), wet(-3), dry(0) |
| Revamp | gain(0) — 7-band EQ, each band has enabled/frequency/gain/q sub-fields |
| StereoTool | volume(0), panning(0), stereo(0), swap(F), panningMixing(1) |
| Tidal | slope(-0.25), symmetry(0.5), rate(3), depth(0.75), offset(0), channelOffset(0) |
| Vocoder | (carrier/modulator config) |
| Waveshaper | equation(hardclip), inputGain(0), outputGain(0), mix(1) |
| Werkstatt | (scripting-based) |

## Render Silence Blocker (UNRESOLVED)

Full render test: load sine 440Hz → create track → place region → force sample load → render via AudioOfflineRenderer → **256 seconds of silence (peak=0)**.

### Root Cause
Two issues identified:
1. **Missing TapeDeviceBox** — `createAudioTrack` creates a TrackBox but the AudioUnit needs a TapeDeviceBox instrument to play audio regions. Without `p.api.createInstrument(InstrumentFactories.Tape)`, regions exist but produce zero output. (Documented in `references/offline-render-investigation-2026-06.md` Session 5, but not applied in this session's test.)
2. **`--disable-web-security` in browser launch args** — server.py still uses this flag. It breaks COOP/COEP headers, causing AudioWorklet processors to fail silently. The skill SKILL.md already documents this, but server.py wasn't updated.

### Fix Applied (not yet tested)
- `place_audio_region` rewritten to use `api.createNotStretchedRegion()` ✅
- main.ts `OfflineEngineRenderer` exposed on window ✅
- main.ts sampleProvider fallback scan ✅

### Fix Still Needed
- ~~Remove `--disable-web-security` from server.py browser launch args~~ ✅ Fixed July 2
- ~~Add `--unlimited-storage` to browser launch args~~ ✅ Fixed July 2
- ~~Add `p.api.createInstrument(InstrumentFactories.Tape)` before `createAudioTrack` in the test flow~~ ✅ Fixed July 2 — but via manual box creation (CaptureAudioBox + AudioUnitBox + TapeDeviceBox), NOT `p.api.createInstrument()` which is unavailable in headless mode. See `references/headless-instrument-au-2026-07-02.md`.
- ~~Set `outputAu.volume.setValue(1.0)` before render~~ ✅ Fixed July 2 — raw 0.734 for 0 dB (NOT 1.0)
- ~~Test full render pipeline end-to-end~~ ✅ Real-time playback verified (maxAmplitude=0.592). Offline export still blocked — see `references/oer-troubleshooting.md` "Export blockers" section.

## Fork

- `AMEOBIUS/openDAW` forked from `andremichelle/openDAW`
- Branch: `fix/offline-render-tidal-silence` (will repurpose)
- Remotes: origin=AMEOBIUS/openDAW, upstream=andremichelle/openDAW
- Contribution plan: headless SDK gaps (parameter control, sampleProvider UUID mismatch), not DSP bug fixes

## bd Tracking

- `ameobius-gic` — parent: openDAW render pipeline refactor
- `ameobius-ide` — Waveshaper (not a bug, needs inputGain>0dB)
- `ameobius-bin` — Tidal (not a bug, audio loop unconditional)
- `ameobius-kk3` — Compressor (not a bug, ProcessPhase timing correct)
- `ameobius-s85` — Delay (not a bug, unconditional processing)

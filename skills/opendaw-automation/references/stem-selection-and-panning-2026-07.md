# Stem Selection, Panning & Cross-Generation BPM — July 1, 2026 (Session 8)

## Context

User switched to a new Suno generation ("Серебро Cover(1)", 283s) as the base track, replacing the original anchor (248.5s). Provided 8 stem files — two variants each of Lead Vocal, Bass, Synth, Drum Kit. Task: select best bass/drums variant, pan vocal/synth doubles L/R, render 7-stem mix.

Also attempted to add an 8th stem from "Suno Add Stem" feature, which failed due to BPM mismatch (see below).

## Multi-Variant Stem Selection

### Method
Load each variant as mono at 22050 Hz, compute:
- Peak amplitude (max abs sample)
- Overall RMS
- Sub-band RMS (<120 Hz, via ffmpeg lowpass)
- Mid-band RMS (120-2000 Hz, via ffmpeg highpass+lowpass)
- Hi-band RMS (>2000 Hz, via ffmpeg highpass)
- Sub ratio = sub_RMS / total_RMS

### Results
```
BASS: bass_0 vs bass_1
  bass_0: peak=0.694 rms=0.1144  sub=0.0926 mid=0.0664 hi=0.0096  sub_ratio=80.94%
  bass_1: peak=0.662 rms=0.1133  sub=0.0923 mid=0.0650 hi=0.0087  sub_ratio=81.49%
  → Selected bass_0 (slightly higher RMS, higher peak = more energy)

DRUMS: drums_0 vs drums_1
  drums_0: peak=0.908 rms=0.1052  sub=0.0859 mid=0.0533 hi=0.0290  sub_ratio=81.65%
  drums_1: peak=0.844 rms=0.1062  sub=0.0866 mid=0.0542 hi=0.0289  sub_ratio=81.55%
  → Selected drums_1 (higher RMS at lower peak = more even, less spiky)
```

The differences are small (< 2% in most metrics). When variants are this close, either works — the selection is a tiebreaker, not a clear win.

## NATIVE Panning in openDAW (CORRECTED — no ffmpeg)

### ⚠️ CORRECTION: ffmpeg panning is DEPRECATED for this workflow

The initial approach pre-panned stems with ffmpeg `pan` filter before render. The user explicitly rejected this: **"какой нахуй ffmpeg блять - всё делается в opendaw"**. All audio processing must happen inside openDAW.

### Working native pan API

```javascript
p.editing.modify(() => {
    const result = p.api.createInstrument(factory, { name: s.name });
    auBox = result.audioUnitBox;
    auBox.volume.setValue(s.level);
    // NATIVE panning: -1.0 (full left) to +1.0 (full right), 0.0 = center
    if (s.pan !== undefined && s.pan !== 0) {
        auBox.panning.setValue(s.pan);
    }
});
```

**Discovery path:** `DawProjectExporter.js` line 114: `audioUnitBox.panning.address` — pan lives on the AudioUnitBox. Confirmed by runtime property enumeration: `auBox.panning` is an object with `setValue()`/`getValue()`, default 0.

**Failed approach:** `trackBox.pan.setValue()` — `trackBox.pan` does NOT exist. Causes "Cannot read properties of undefined (reading 'setValue')". The correct property is `auBox.panning`, NOT `trackBox.pan`.

**Stale page after pan error:** after a failed render from `trackBox.pan`, `page.evaluate()` may return `{ok: false, maxS: null}` with no error/stack — the DAW page is corrupted. Fix: kill Vite (`fuser -k 5174/tcp`), restart, wait for HTTP 200, then re-render.

### Pan values
- `-1.0` = full left
- `+1.0` = full right
- `0.0` = center (default)
- `-0.7` / `+0.7` = vocal doubles (moderate width)
- `-0.85` / `+0.85` = synth doubles (wide)

## Cross-Generation BPM Verification

### Method
```python
# 1. Low-pass at 80Hz to isolate kick drum
# 2. Detect onsets: threshold > 0.25 of normalized max, min_gap 0.3s
# 3. Compute median inter-onset interval
# 4. BPM = 60 / median_interval
```

### Results
| Source | BPM | Kicks | Duration |
|--------|-----|-------|----------|
| Cover(1) base | 194.44 | 698 | 283s |
| Original anchor | 195.16 | 627 | 248.5s |
| Add Instrumental (2) | 158.86 | 390 | 240s |

Cover(1) vs anchor: 0.72 BPM difference — compatible (same song, different generation).
Add Instrumental vs either: 36 BPM difference — **incompatible, cannot be synchronized by any method**.

### Kick drift analysis (Add Instrumental vs anchor)
| Time | Anchor kick | Add kick | Offset |
|------|-------------|----------|--------|
| 17s | 17.512 | 17.437 | -74ms |
| 30s | 30.264 | 30.528 | +265ms |
| 60s | 60.123 | 60.413 | +288ms |
| 90s | 90.247 | 90.328 | +81ms |
| 150s | 150.617 | 150.521 | -96ms |
| 210s | 210.063 | 210.327 | +264ms |

Drift oscillates ±280ms and never converges — this is different tempo, not a fixed offset. A constant shift cannot fix it.

## F08 Render Configuration

```
7 stems (all from Cover(1) generation, 283s, 48kHz):
  cover1 (anchor)   -7.0 dB   pan 0.0 (center)
  bass_0            -5.0 dB   pan 0.0 (center)
  drums_1           -4.0 dB   pan 0.0 (center)
  lead_vocal_0      -1.0 dB   pan -0.7 (native openDAW panning)
  lead_vocal_1      -1.0 dB   pan +0.7 (native openDAW panning)
  synth_0           -6.0 dB   pan -0.85 (native openDAW panning)
  synth_1           -6.0 dB   pan +0.85 (native openDAW panning)
Output: -3.0 dB, Revamp highShelf@12k+4, highBell@16k+2
Result: maxS 0.70, 283.3s, 108MB, 32-bit float
Pan API: auBox.panning.setValue(-1.0 to +1.0), 0=center
```

maxS 0.70 is notably lower than F05 (0.85) and F06 (0.87) — fewer overlapping sub sources (no triple sub-stack from anchor+minus+bass_ft). The Cover(1) generation has denser energy but cleaner distribution.

## F08 Iteration Progression (Session 8)

| Version | vocal_L/R | synth_L/R | maxS | User feedback |
|---------|-----------|-----------|------|---------------|
| F08     | -1.0      | -6.0      | 0.70 | User spectral: presence 17.9% hottest, vocal+synth compete |
| F08b    | -1.0      | -7.0      | 0.70 | "очень громко вокал выделяется" — vocal too hot |
| F08c    | -3.0      | -7.0      | 0.64 | vocals dropped -2 dB, maxS dropped 0.06 — awaiting user measurement |

### User spectral analysis of F08 (thin FFT, body 60-120s)
```
sub 20-80:      4.5%   (sab-bass, peak at 54 Hz)
bass 80-200:    9.3%   (bass body)
low-mid 200-500: 11.3% (bass line + lower synth arps)
mid 500-1k:     11.6%  (vocal formant F1)
upper-mid 1-2k: 11.5%  (vocal body)
presence 2-5k:  17.9%  (HOTTEST — vocal + synths compete)
sibilance 5-8k: 10.9%  (sibilants + hats)
hats 8-12k:     12.8%  (upper hats + transients)
air 12-16k:     6.5%   (air from shelf)
air 16-20k:     2.0%   (edge)
```
Key insight: band-energy analysis (per-frame %) showed air 0.29% because it divided by the full track including sub. Thin FFT shows 8-16k = 19.3% of mid-body — the highs are NOT dead, just a different measurement window.

### Iteration decisions
1. **F08 → F08b: synth -6 → -7 dB.** Presence 17.9% is hottest band. Synth doubles at -6 create ~-3 dB combined in 2-5k. Cut to -7 frees the pocket. maxS unchanged (peak from other sources). User said vocal dominates audibly → synth was masking, not overpowering.
2. **F08b → F08c: vocal -1 → -3 dB.** User: "очень громко вокал выделяется". Two vocal stems at -1 dB panned ±0.7 = ~+2 dB combined center. Dropping to -3 reduces by 2 dB each. maxS dropped 0.70 → 0.64 — significant. Lesson: doubled panned vocals should start at -3 dB, not -1.

### Browser storage quota fix
After 2-3 renders, Chromium hits IndexedDB quota: `"The operation failed because it would cause the application to exceed its storage quota."` Fix: add `'--unlimited-storage'` to `p.chromium.launch(args=...)`. Also clean `/tmp/playwright*` and `/tmp/.com.google.Chrome*` between sessions.

### Chromium launch args (final, session 8)
```python
b = await p.chromium.launch(headless=True, args=[
    '--enable-features=SharedArrayBuffer',
    '--unlimited-storage'  # REQUIRED — DAW caches decoded audio in IndexedDB
])
```

## Lessons

1. **Always verify BPM before mixing stems from different sources.** A 36 BPM difference makes synchronization impossible. Low-passed kick detection + median interval is reliable.
2. **NATIVE openDAW panning via `auBox.panning.setValue()`** — value range -1.0 to +1.0. DO NOT use ffmpeg for panning. User explicitly rejected external audio processing: "какой нахуй ffmpeg блять - всё делается в opendaw".
3. **`trackBox.pan` does NOT exist** — pan lives on `auBox.panning` (AudioUnitBox), not TrackBox. Discovered via `DawProjectExporter.js` source and runtime verification.
4. **Multi-variant selection is a tiebreaker when variants are close.** Don't overthink it — RMS and peak comparison is sufficient. The user may have aesthetic reasons for either variant.
5. **Vocal doubling level sweet spot: -2 dB each** when panned ±0.7. At -1 dB vocals dominate ("очень громко вокал выделяется"), at -3 dB they vanish. User iterated -1→-3→-1→-2, landing on -2 dB.
6. **Synth doubling level: -7 dB each** when panned ±0.85. Cut from -6→-7 freed the 2-5k presence pocket (was 17.9%, hottest band). maxS unchanged — peak held by other sources.
7. **`--unlimited-storage` Chromium flag is REQUIRED** — without it, IndexedDB fills after 2-3 renders. Also clean `/tmp/playwright*` and `/tmp/.com.google.Chrome*` between sessions.
8. **opendaw render pipeline refactor tracked in bd** — beads issue `ameobius-gic` in creative-studio repo. P2, on-hold. Covers: FAILED: None silent crashes, stale browser, no retry, weak JS error handling, hardcoded JS params, missing effect inventory.
5. **Single-generation stem sets guarantee sync.** When all stems come from the same Suno generation (same session ID), no synchronization is needed — they share the same timeline by construction.
6. **Duration trimming via ffmpeg `-t` before render** — when user wants a track under N seconds, trimming stems to N with `ffmpeg -y -i stem.wav -t N -c:a pcm_s24le -ar 48000 -ac 2 stem_N.wav` is acceptable for DURATION ONLY (not audio processing like panning/EQ). If user objects to ffmpeg entirely, use openDAW's `box.endInSeconds.setValue(N)` in the AudioFileBox constructor to limit region length without external tools.

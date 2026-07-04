# Stem Synchronization Investigation — July 1, 2026 (Session 7)

## Context

User provided an 8th stem ("Add Instrumental" WAV, 240s, 48kHz/16-bit) — a **Suno Add Stem** (new Suno feature that generates additional instrumental layers on top of an existing track). The stem needed synchronization with the existing 7-stem Серебро mix (all 248.5s, from the same song session).

## Key Finding (REVISED)

**The add_instr stem was ALREADY synchronized with the original master in the body of the track.** When comparing the 15-22s region at 100ms resolution:
- Both have a break/dropout at 16.4-17.3s
- Both have a strong hit at exactly 17.4s
- Peaks at 18.5, 19.6, 20.7, 21.8 all match without any shift

The 230ms of silence at the start of add_instr is **encoder latency**, not a sync offset. **Do NOT trim it — trimming shifts the body earlier and breaks the alignment.**

The first F06 render (no shift, original add_instr) was correct. The +93ms padding (from bad cross-correlation) was what caused the audible desync the user reported.

## Methods Tried (in order)

### 1. First-peak comparison
- anchor first peak: 0.048s
- add_instr first peak: 0.230s
- Difference: 182ms — this is encoder delay, NOT a tempo offset

### 2. RMS energy onset detection (10ms hops)
- anchor onsets: 18.070, 18.610, 19.160, 19.690, 20.790...
- add_instr onsets: 17.960, 18.530, 19.060, 19.620, 20.710...
- Average offset: -80ms (add_instr earlier)
- add_instr has MORE onsets (268 vs 243) — denser pattern, not 1:1 matchable by onset counting

### 3. Cross-correlation of RMS energy envelopes (full track) — MISLEADING
- Best shift: +0.093s, correlation: **0.057**
- Low-pass filtered (<100Hz) correlation: **0.028**
- **VERDICT:** Correlation values near zero = noise. The "best shift" of +93ms was meaningless and led to the wrong correction (padding +93ms) which caused the audible desync. **Never trust cross-correlation "best shift" when correlation < 0.1 — the value is noise.**

### 4. Kick transient analysis (low-passed at 100Hz)
- anchor kicks (first 4): 17.508, 17.820, 18.125, 18.429
- add_instr kicks (first 4): 17.430, 17.737, 18.040, 18.444
- First 3 kicks: offset consistent at ~-78ms
- Kick 4+: inter-kick intervals diverge (anchor 0.304s, add_instr 0.404s)
- **VERDICT:** Different drum patterns within the same song structure. This is expected for Add Stem — it generates a NEW arrangement that shares the song's structural boundaries (break, build, drop) but has different percussion patterns.

### 5. Fine-grained envelope comparison (100ms steps, 15-22s region) — THE ANSWER
- Both original_master and add_instr have identical structural events:
  - Break/dropout at 16.4-17.3s (both go to ~0 energy)
  - Strong hit at 17.4s (both spike)
  - Peak at 18.5s, 19.6s, 20.7s, 21.8s — all match
- **This proves the stems share the same song structure and are already aligned.** The different onset counts and inter-kick intervals are because Add Stem generates a denser/different percussion arrangement, not because of a time offset.

## ffmpeg adelay Bug

Applied `adelay=4464|4464` intending to shift by 4464 samples (=93ms at 48kHz).
**adelay takes MILLISECONDS, not samples.** 4464ms = 4.5 seconds of delay.

Result: add_instr_synced started at 4.69s instead of 0.32s. Catastrophic.

Fix: `adelay=93|93` for 93ms delay. Always verify with first-peak scan after applying.

## Lessons

1. **Suno Add Stem = same song structure, different arrangement.** The stem shares break/build/drop boundaries with the original but has different percussion and energy density. It is already synchronized to the original — do not attempt to shift it.
2. **Encoder silence at start ≠ sync offset.** 230ms of silence before the first sample is codec latency. Trimming it shifts the body and breaks alignment.
3. **Cross-correlation on RMS envelopes gives noise (corr < 0.1) for stems with different arrangements.** The "best shift" is meaningless — do not act on it. Use structural event matching (break/hit alignment) instead.
4. **Structural event matching is the reliable sync method.** Compare energy envelopes at 100ms resolution in a region with clear structural events (breaks, drops, builds). If the events align, the stems are in sync regardless of onset count differences.
5. **ffmpeg `adelay` takes MILLISECONDS, not samples.** Always convert: `ms = samples / sampleRate * 1000`. Verify with first-peak scan after any time-shift operation.
6. **When user says "она гораздо позже начинается" — verify which version they heard.** The user heard the +93ms padded version, not the original. The "fix" (padding) caused the problem, not the original alignment.

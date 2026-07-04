# openDAW 7-Stem & Add Stem Render — Session 7 (July 1, 2026)

## F01-F07 Mix Progression — Серебро (dark post-punk, 110 BPM)

### 4-stem → 7-stem transition (F42 → F01)

F42 was the 4-stem final (anchor -7, minus -3, vocal -2, vocal_2 -5, out -3, HS@12k+4, HB@16k+2).

Moving to 7 stems added: drums_ft -4, bass_ft -5, other_bs6 -6, vocals_pf -5 (replaced vocal_2).

| Ver | anchor | minus | vocal | vocal_pf | drums_ft | bass_ft | other_bs6 | out | sub% | low-mid% | 2-5k% | air% | crest | RMS | peak | maxS |
|-----|--------|-------|-------|----------|----------|---------|-----------|-----|------|----------|-------|------|-------|-----|------|------|
| F01 | -7 | -3 | -2 | -5 | -4 | -5 | -6 | -3 | 59.0 | 35.5 | 3.1 | 0.31 | 17.2 | -18.4 | -1.2 | 0.86 |
| F02 | -7 | -3 | -2 | -5 | -4 | -8 | -6 | -3 | 57.1 | 37.0 | 3.3 | 0.34 | 17.5 | -18.7 | -1.2 | 0.89 |
| F03 | -7 | -5 | -2 | -5 | -4 | -8 | -6 | -3 | 55.0 | 38.7 | 3.53 | 1.05 | 0.36 | 17.6 | -19.3 | -1.74 | 0.83 |
| F04 | -7 | -5 | -1 | -5 | -4 | -8 | -6 | -3 | 53.7 | 39.8 | 3.66 | 1.09 | 0.37 | 17.6 | -19.2 | -1.55 | 0.84 |
| F05 | -7 | -5 | -1 | -4 | -4 | -8 | -6 | -3 | — | — | — | — | — | — | — | 0.85 |
| F06 | -7 | -5 | -1 | -4 | -4 | -8 | -6 | -3 + add_instr | — | — | — | — | — | — | — | 0.85 |
| F07 | -7 | — | -1 | -4 | — | — | — | -3 | — | — | — | — | — | — | — | 0.70 |

### Key observations

- **7-stem sub overload**: three sub sources (anchor + minus + bass_ft) push sub to 59% vs F42's 49%. The 2.6pp/dB rule from 4-stem DOES NOT HOLD — bass_ft -3dB only moved sub 1.9pp (59→57.1). Expect ~0.6pp/dB for individual stem cuts in 7-stem.
- **Single-variable iteration converges**: F02 (bass_ft -3) → F03 (minus -2) → F04 (vocal +1) → F05 (vocal_pf +1). Each change ~1.5-2pp shift. User measures externally, identifies next move.
- **Vocal boost splits between bands**: vocal +1dB raised both low-mid AND 2-5k (0.13pp only on 2-5k). Vocal energy lives in 200-800Hz formants, not just presence band. To lift 2-5k specifically, boost the PARALLEL vocal stem (vocals_pf) which sits denser in that range.
- **Peak stays hot at 7 stems**: -1.2 dB at F01, barely moves with cuts. 7 stems = more energy. Output -3dB too hot for 7 stems. After minus cut (F03), peak dropped to -1.74 — safer.
- **F07 restructure**: replaced minus + drums_ft + bass_ft + other_bs6 with a single Suno Add Stem (add_instr_2). 4 stems total, maxS 0.70 — much cleaner. Add Stem carries the full instrumental arrangement.

## Suno Add Stem Synchronization

### Method: structural marker comparison (NOT cross-correlation)

RMS energy cross-correlation between Add Stem and original master returns ~0.05 (near zero) even when properly synced. Add Stems have different texture/density — energy envelopes don't match.

**Working method**: compare energy envelopes at 100ms resolution in the 15-23s region. Look for:
- Break sections (both drop to near-silence at the same timestamp)
- Kick hits (both have energy spike at the same timestamp)
- Dynamic shifts (build-ups, drops)

Example: anchor and add_instr_2 both had break at 16.3-17.3s and hit at 17.4s → confirmed sync with zero shift.

### Encoder delay silence

Add Stems may have 200-300ms silence at start. This is normal encoder delay. The body is already aligned. **Do NOT trim** — trimming shifts body earlier, breaks sync.

### Not all Add Stems sync

"Серебро (Add Instrumental)" — kick onsets diverged after 3-4 hits (different generation, different kick pattern).
"Серебро (Add Instrumental)(2)" — properly aligned, all structural markers matched.

If kick onsets diverge after 3-4 hits → stem is from a different generation, cannot be synchronized. Try another Add Stem variant.

## Stem trimming for duration control

To trim stems to a target duration (e.g., 240s for under 4 minutes):
```bash
for stem in anchor vocal vocals_pf; do
  ffmpeg -y -i "stems/${stem}.wav" -t 240 -c:a pcm_s24le -ar 48000 -ac 2 "stems/${stem}_240.wav"
done
```
All stems must be the same duration for clean rendering. Add Stems that are already shorter (240s vs 248.5s) don't need trimming — the render engine handles the length difference (shorter stem just ends earlier, leaving silence).

## ffmpeg adelay pitfall

`adelay` filter takes MILLISECONDS, not samples:
- `adelay=4464|4464` = 4464ms = 4.5 seconds (WRONG if you meant 93ms)
- `adelay=93|93` = 93ms (CORRECT)

This caused a 4.5s shift that completely broke stem sync. Always specify in ms.

# LUFS Measurement + Auto-Gain Implementation (2026-07-03)

## Refactoring (v1.9.6 session)

`measure_lufs` was a 223-line monolith. Refactored to ~20 lines delegating to two testable helpers:

- **`_parse_wav(raw: bytes) -> dict`** — RIFF parser, returns `{audio_format, n_channels, sample_rate, bits_per_sample, n_frames, channels}`. Supports float32, PCM16/24/32. Raises `ValueError` on invalid input.
- **`_compute_lufs(channels: list, sample_rate: int) -> dict`** — ITU-R BS.1770-4 K-weighting + gated mean squares. Returns `{lufs_integrated, true_peak_db, max_sample, blocks_measured, gated_blocks}`.

Both helpers are unit-tested in `tests/test_utils.py` (9 tests covering WAV parsing and LUFS computation). The K-weighting filter coefficients were also deduplicated — the old code had identical if/else branches for 48kHz vs other rates.

### Test WAV generator struct field order pitfall

`struct.pack("<HHIIHH", ...)` field order is: format, channels, sample_rate, byte_rate, block_align, bits_per_sample. **block_align comes before bits_per_sample** — swapping them produces bits_per_sample=0 in the parsed WAV → ZeroDivisionError when computing n_frames. The 5th positional arg is block_align (n_channels × bytes_per_sample), the 6th is bits_per_sample (bytes_per_sample × 8).

## measure_lufs — ITU-R BS.1770-4 simplified

Was a stub (`return _err("Not yet reconstructed")`). Now fully implemented in pure Python (no numpy).

### WAV parsing — 32-bit float limitation

Python's `wave` module does NOT support IEEE float WAVs (format code 3). openDAW's `WavFile.encodeFloats()` produces 32-bit float WAVs. Must parse RIFF/WAVE header manually:

```
RIFF header (12 bytes): "RIFF" + size + "WAVE"
Loop chunks:
  "fmt " chunk: audio_format (H), n_channels (H), sample_rate (I), bits_per_sample (H)
  "data" chunk: audio_data = raw[pos+8:pos+8+chunk_size]
  pos += 8 + chunk_size + (chunk_size % 2)  # pad to even
```

Format codes: 1=PCM (16/24/32-bit), 3=IEEE float (32-bit). For float32: `struct.unpack(f"<{count}f", audio_data)`.

### K-weighting biquad coefficients

Computed from BS.1770-4 Annex formulas (NOT hardcoded — hardcoded values had transposed numerator/denominator causing signal attenuation to -70 LUFS):

**Stage 1 — high-shelf (+4dB @ 1.68kHz):**
```
f0 = 1681.974450955533
G  = 3.9998432737  (≈4dB)
Q  = 0.7081754356
K  = tan(π * f0 / sample_rate)
Vh = 10^(G/20)
Vb = 10^(G/40)
a0 = 1 + K/Q + K²
b0 = (Vh + Vb*K/Q + K²) / a0
b1 = 2*(K² - Vh) / a0
b2 = (Vh - Vb*K/Q + K²) / a0
a1 = 2*(K² - 1) / a0
a2 = (1 - K/Q + K²) / a0
```

**Stage 2 — RLB highpass (~38Hz):**
```
f0 = 38.1354708761
Q  = 0.5003270373
K  = tan(π * f0 / sample_rate)
a0 = 1 + K/Q + K²
b0 = 1/a0, b1 = -2/a0, b2 = 1/a0
a1 = 2*(K² - 1) / a0
a2 = (1 - K/Q + K²) / a0
```

**Biquad application (Direct Form I):**
```python
def apply_biquad(data, b0, b1, b2, a0, a1, a2):
    b0n, b1n, b2n = b0/a0, b1/a0, b2/a0  # normalize
    a1n, a2n = a1/a0, a2/a0
    # y[n] = b0*x[n] + b1*x[n-1] + b2*x[n-2] - a1*y[n-1] - a2*y[n-2]
```

**Critical**: coefficient order in function call is `(data, b0, b1, b2, a0, a1, a2)` — numerator (b) first, denominator (a) second. The old code had `(data, a0, a1, a2, b0, b1, b2)` which transposed the filter.

### Gated mean squares

1. 400ms blocks, 75% overlap (hop = 100ms)
2. Per block: `ms = Σ(ch_weight × sample²) / block_size` across all channels
3. Channel weights: L/R/C = 1.0, surround = 1.41
4. Absolute gate: -70 LUFS → `ms > 10^((-70 + 0.691) / 10)`
5. Relative gate: -10 LU below mean of absolutely-gated blocks
6. `LUFS = -0.691 + 10 × log10(gated_mean_square)`

### E2E result

`lufs_test.wav` (3-note Vaporisateur chord, 2.25s, 48kHz stereo float32):
- LUFS integrated: **-16.2**
- True peak: **-5.49 dBTP**
- Max sample: 0.531377
- 19 blocks measured, 19 gated

## auto_gain — iterative render-measure-adjust loop

Was a single Maximizer threshold set (no iteration). Now a real loop:

1. Ensure Maximizer on output AU (insert if missing)
2. For each iteration (max 3):
   a. Set Maximizer threshold (dB) via `editing.modify()`
   b. Render full mix: `OfflineEngineRenderer.start(p.copy(), Option.None, ...)`
   c. Save WAV via base64 round-trip
   d. Call `measure_lufs()` on the rendered file
   e. Check convergence (±1 LUFS of target)
   f. Adjust threshold: `adjustment = -diff × 0.8` (too loud → increase threshold, too quiet → decrease)
3. Return iterations array with threshold/lufs/diff per step

### Output AU volume field — dB DIRECTLY (critical discovery)

`au.volume` on the OUTPUT AU stores dB directly (unit="dB", min -96, max +6, raw value 0 = 0dB). NOT normalized 0..1 like the instrument AU volume (which uses 0.767835 for 0dB via powerByCenter mapping). This is a critical difference:

- **Instrument AU volume**: normalized 0..1, `0.767835 ≈ 0dB`, needs `powerByCenter` conversion
- **Output AU volume**: dB directly, `0 = 0dB`, `-6 = -6dB`, just pass the dB value

The initial auto_gain code converted dB → linear → × 0.768 multiplier → `au.volume.setValue(rawVol)`, treating output AU volume as normalized. This gave near-zero effect: -7dB volume → only -0.5 LUFS change. After fix (`au.volume.setValue(volume_db)` directly): -7.68dB → -13.7 LUFS (converged).

### Convergence achieved (2026-07-03 session 2)

**Bidirectional adjustment logic:**
- Too quiet (diff < 0): decrease Maximizer threshold → more makeup gain
- Too loud (diff > 0): decrease output AU volume (negative dB) → attenuation

E2E result: target -14 LUFS
- iter 1: -6.0 LUFS, vol=0dB, thr=-20dB (too loud by +8.0)
- iter 2: -12.4 LUFS, vol=-6.4dB, thr=-20dB (closing in, diff=+1.6)
- iter 3: **-13.7 LUFS**, vol=-7.68dB, thr=-20dB → **converged** (diff=+0.3, ±1.0 threshold)

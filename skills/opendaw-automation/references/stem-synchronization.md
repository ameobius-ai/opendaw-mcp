# Stem Synchronization — Cross-Correlation Technique

## Problem

When adding an external stem (different Suno generation, different source) to an existing stem mix, the new stem may be time-shifted relative to the reference stems. Simple "first peak" alignment fails because:
- Different stems have different attack characteristics
- Silent intros mean the first energy peak may be seconds into the track
- The new stem may have a denser onset grid (more percussion hits) making 1:1 onset matching diverge

## Solution: RMS Energy Cross-Correlation

### Step 1: Load both stems as mono float32

```python
import subprocess, struct, math

def load_mono(path, sr=22050, dur=60):
    r = subprocess.run(['ffmpeg','-i',path,'-ac','1','-ar',str(sr),'-f','f32le','-t',str(dur),'-'], capture_output=True)
    return list(struct.unpack(f'{len(r.stdout)//4}f', r.stdout)), sr
```

### Step 2: Compute RMS energy envelope (10ms hops)

```python
def rms_env(samples, sr, hop=512):
    env, n = [], len(samples)//hop
    for i in range(n):
        chunk = samples[i*hop:(i+1)*hop]
        env.append(sum(x*x for x in chunk)/len(chunk))
    mx = max(env) if env else 1
    return [e/mx for e in env], hop  # normalized
```

### Step 3: Cross-correlate in body region

Skip the intro (first 15s) — it's silence/ambient and adds noise to correlation.

```python
def cross_corr(a, b, max_shift_samples):
    best_shift, best_corr = 0, -1
    for shift in range(-max_shift_samples, max_shift_samples):
        corr = 0
        for i in range(max(0, shift), min(len(a), len(b)+shift)):
            j = i - shift
            if 0 <= j < len(b):
                corr += a[i] * b[j]
        if corr > best_corr:
            best_corr = corr
            best_shift = shift
    return best_shift, best_corr
```

Search range: ±500ms is sufficient for Suno-to-Suno offsets.

### Step 4: Apply offset with ffmpeg

If new stem is N ms **earlier** than reference (negative shift), pad silence at start:

```bash
# 93ms at 48000Hz = 4464 samples
ffmpeg -y -i add_instr.wav -af "adelay=4464|4464" -c:a pcm_s24le -ar 48000 -ac 2 add_instr_synced.wav
```

If new stem is N ms **later** (positive shift), trim from start:

```bash
ffmpeg -y -i add_instr.wav -ss 0.093 -c:a pcm_s24le -ar 48000 -ac 2 add_instr_synced.wav
```

### Step 5: Verify

Re-run cross-correlation on synced file. Residual offset should be ≤25ms (one hop resolution at 22050Hz/512 = 23ms). That's effectively zero.

## Key Lessons

- **Don't compare first peaks.** Different stems have different amplitude profiles. A vocal stem's first peak is at 8.7s; the anchor's is at 0.048s. This tells you nothing about sync.
- **Don't compare onset grids 1:1.** A denser stem (more percussion) will have more onsets than a sparser one. Matching onset #5 to onset #5 diverges as the grids have different densities.
- **Do use cross-correlation of normalized RMS envelopes in the body region.** This is robust to onset density differences and amplitude differences.
- **Same BPM ≠ same alignment.** Two stems at 110 BPM can still be 93ms offset. Tempo matching is necessary but not sufficient.
- **Duration difference is OK.** A 240s stem added to 248s stems just means the new stem ends earlier. As long as the start is aligned, the tail silence is harmless.
- **adelay filter format.** Use `adelay=4464|4464` (pipe-separated for stereo), NOT `adelay=4464:4464` (colon syntax doesn't work in all ffmpeg versions for channel-specific delay).

## Verified Session (July 2026, Серебро F06)

- add_instr.wav: 240s, 48kHz, 16-bit stereo
- anchor.wav: 248.5s, 48kHz, 16-bit stereo
- First-peak method: suggested 182ms offset (WRONG — misleading)
- Onset grid comparison: suggested 80ms offset (partially right but diverged due to density mismatch)
- Cross-correlation: 93ms offset, corr=118.7 (CORRECT)
- After adelay=4464|4464: residual 23ms (one hop, effectively zero)
- Both stems at ~110 BPM, same onset interval (0.54-0.55s), just time-shifted

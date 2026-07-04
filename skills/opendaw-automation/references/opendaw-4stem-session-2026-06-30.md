# openDAW 4-Stem Render — Session 5 (June 30, 2026)

## Breakthrough: TapeDeviceBox

The root cause of all silence across sessions 1-4: `createInstrument` factory's `create()` must return a **TapeDeviceBox**, not `null` or a CaptureAudioBox.

- `CaptureAudioBox` — microphone capture device, has NO output field, does NOT route audio to AU.input
- `TapeDeviceBox` — "Audio Player" instrument, `box.host.refer(host)` connects it to `audioUnitBox.input`
- `InstrumentFactories.Tape` in studio-adapters is the official factory for audio tracks

Source: `node_modules/@opendaw/studio-adapters/dist/factories/InstrumentFactories.js`

## Revamp EQ — Band Map

```
RevampDeviceBox
├── highPass   (HPF)     — enabled, frequency, gain
├── lowShelf   (low)     — enabled, frequency, gain
├── highBell   (peak)    — enabled, frequency, gain
└── highShelf  (high)    — enabled, frequency, gain
```

Each band: `enabled` (BooleanField), `frequency` (Float32Field 20-20000Hz exponential), `gain` (Float32Field dB).

Add to AU: `p.api.insertEffect(au.audioEffects, ef.AudioNamed.Revamp)`

## Iterative Mix Results — Серебро (dark post-punk, 110 BPM)

| Ver | anchor | minus | vocal | v_2  | out  | Master EQ | De-ess | sub%  | air%  | crest | maxS  |
|-----|--------|-------|-------|------|------|-----------|--------|-------|-------|-------|-------|
| F39 | -1     | -3    | -2    | -5   | -3   | —         | —      | 61.0  | 0.12  | 17.0  | 1.20  |
| F40 | -4     | -3    | -2    | -5   | -3   | —         | —      | 58.4  | 0.12  | 17.5  | 0.74  |
| F41 | -4     | -3    | -2    | -5   | -3   | +12k+16k  | —      | 52.1  | 0.39  | 18.0  | 0.74  |
| F42 | -7     | -3    | -2    | -5   | -3   | +12k+16k  | —      | 49.4  | 0.40  | 18.3  | 0.69  |
| F43 | -7     | -3    | -2    | -5   | -3   | +12k+16k  | 4k-2   | 50.4  | 0.40  | 18.1  | 0.66  |
| F44 | -7     | -3    | -2    | -5   | -3   | +12k+16k  | 4.5k-3 | 50.7  | 0.40  | 18.0  | 0.65  |

### Observations
- **dB cuts don't translate linearly to spectral %.** -3 dB on anchor → only ~2.6% sub drop. Each ~1dB ≈ 2.6pp sub shift. Rule: target_pp ÷ 2.6 × 1.5 = dB to apply.
- **Air is structural.** If stems have no high-end, shelf boost amplifies silence. 0.12% → 0.39% is the ceiling. Below 0.5% after +4dB shelf = stems are the bottleneck.
- **Crest factor improved** with each iteration: 17.0 → 18.3. openDAW's clean render preserves dynamics better than lossy pipelines.
- **De-esser KILLED vocal presence.** F43 (4k -2dB): 2-5k dropped 4.8→3.9%. F44 (4.5k -3dB): 2-5k 3.7%. Vocal went muffled, lost authority. User: "F43 and F44 — two steps back."
- **BEST VERSION: F42** — sub 49.4%, crest 18.3, 2-5k 4.8%, vocal alive. No de-esser. Sibialants on the edge are CHARACTER in coldwave, not a problem. F42 is the final. Do NOT de-ess unless user explicitly asks for it again.
- **User explicitly rejected de-esser approach:** "вернись к F42. это лучший микс из всех 11 версий. сибилянты на грани — но это лучше чем мёртвый вокал. в coldwave грань — это характер, не проблема"

## Download Transfer Method

```python
# Playwright context MUST accept downloads
context = await b.new_context(accept_downloads=True)
page = await context.new_page()

# In JS: create Blob + <a download> trigger
# In Python: page.on('download', handler) saves to disk
async def handle_download(download):
    await download.save_as(output_path)
page.on('download', handle_download)
```

Base64 transfer fails for files >~95MB (ERR_STRING_TOO_LONG in Node.js transport). WAV at 248s/48kHz/32-bit/stereo = ~95MB — right at the limit. Download method is reliable.

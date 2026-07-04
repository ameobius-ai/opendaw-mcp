# Render Pipeline Fixes — July 2, 2026

Session findings from fixing the offline render silence bug.

## Finding 1: --disable-web-security breaks lazy module loading

**Symptom:** `DAW_AudioOfflineRenderer` and `DAW_OfflineEngineRenderer` are `undefined` on window despite lazy import running.

**Root cause:** `--disable-web-security` flag sets `crossOriginIsolated: false`. COOP/COEP headers from Vite are ignored. Lazy-loaded ES modules from `@opendaw/studio-core` fail to initialize in non-isolated context.

**Fix:** Remove `--disable-web-security`, use only:
```python
args=["--enable-features=SharedArrayBuffer", "--unlimited-storage"]
```

**Verified result:**
- `crossOriginIsolated: true` ✅
- `SharedArrayBuffer: true` ✅
- `DAW_AudioOfflineRenderer: true` ✅ (was false)
- `DAW_OfflineEngineRenderer: true` ✅ (was false)

## Finding 2: OfflineEngineRenderer "Already connected" — main engine conflict

**Symptom:** `OfflineEngineRenderer.start()` throws `Error: Already connected` at `LiveStreamReceiver.connect()`.

**Root cause:** `EngineWorklet` (main engine) connects to `project.liveStreamReceiver` at startup (EngineWorklet.ts:234). `OfflineEngineRenderer.create()` tries to connect again (OfflineEngineRenderer.ts:145) → panic.

**Fix (VERIFIED July 2):** Call `p.engine.releaseWorklet()` before render, `p.startAudioWorklet()` after:
```javascript
p.engine.releaseWorklet();  // EngineFacade.ts:67-72 — worklet.terminate() + disconnect + Option.None
const progress = {setValue: (v) => console.log("Render: " + Math.round(v*100) + "%")};
const audioData = await OfflineEngineRenderer.start(p, Option.None, progress, undefined, 48000);
try { p.startAudioWorklet(); } catch(_) {}  // restore
```

**Alternative tested:** `AudioOfflineRenderer` (deprecated, uses `OfflineAudioContext`) does NOT need `releaseWorklet()` — it calls `source.copy()` internally which creates a fresh `liveStreamReceiver`. No conflict. BUT still produces silence if TapeDeviceBox is missing (see oer-troubleshooting.md).

## Finding 3: createAudioTrack must be inside editing.modify()

**Symptom:** `Error: Modification only prohibited in transaction mode` at `BoxGraph.stageBox()`.

**Root cause:** `p.api.createAudioTrack(au)` → `TrackBox.create()` → `boxGraph.stageBox()` requires active transaction.

**Fix:** Wrap ALL box creation in `p.editing.modify()`:
```javascript
p.editing.modify(() => {
    const track = p.api.createAudioTrack(au);
    const fileBox = AudioFileBox.create(p.boxGraph, UUID.generate(), (box) => {
        box.fileName.setValue(sampleId);
        box.startInSeconds.setValue(0.0);
        box.endInSeconds.setValue(audioBuffer.duration);
    });
    const region = p.api.createNotStretchedRegion({
        boxGraph: p.boxGraph,
        targetTrack: track,
        position: 0,
        audioFileBox: fileBox,
        sample: { name: sampleId, duration: audioBuffer.duration, bpm: 120, sample_rate: audioBuffer.sampleRate }
    });
});
```

## Finding 4: TrackType.Audio = 2, not 0

Filter for audio tracks: `box.type?.getValue?.() === 2` (TrackType.Audio). Using `=== 0` (Undefined) finds nothing.

## Finding 5: sampleProvider fallback works

When `project.copy()` generates new UUIDs for AudioFileBoxes, the sampleProvider fallback in main.ts successfully resolves by scanning all AudioFileBox fileNames. Console shows:
```
[sampleProvider] fetch UUID: <new-uuid>
[sampleProvider] resolved by fileName (exact UUID): <original-uuid>
```

## Finding 6: Volume field stores dB, not linear

`au.volume.setValue(0.0)` = 0 dB = linear gain 1.0 = normal volume. This is NOT the cause of silence. The silence comes from the "Already connected" error preventing render from completing.

## Render API comparison

| Renderer | Returns | Needs SAB | Needs releaseWorklet | Needs TapeDeviceBox | Status |
|----------|---------|-----------|----------------------|---------------------|--------|
| OfflineEngineRenderer | AudioData (`.frames: Float32Array[]`) | Yes | Yes | Yes | Works with releaseWorklet + Tape |
| AudioOfflineRenderer | AudioBuffer (`.getChannelData()`) | No (OfflineAudioContext) | No (copy internally) | Yes | Works with Tape |

## Resolution (July 2, end of session)

All 4 next steps completed:
1. ✅ Read `EngineFacade.ts` — found `releaseWorklet()` method (line 67-72)
2. ✅ Tested `AudioOfflineRenderer` with correct browser args — works (no releaseWorklet needed), but still silent without TapeDeviceBox
3. ✅ Implemented `releaseWorklet → OfflineEngineRenderer → startAudioWorklet` in MCP server.py render tool
4. ✅ Tested full pipeline — render completes, sampleProvider resolves, but **STILL SILENT** because test script did NOT create TapeDeviceBox (`p.api.createInstrument(InstrumentFactories.Tape)`). This was already documented in oer-troubleshooting.md as the root cause of all silence in June sessions. The July 2 test script created track+region but skipped the instrument step — repeating the same mistake.

**THE FIX for silence:** Add `p.api.createInstrument(InstrumentFactories.Tape)` before `createAudioTrack`. See `references/offline-render-investigation-2026-06.md` Session 5 for the full verified pipeline. The MCP `place_audio_region` tool in server.py needs this step added.

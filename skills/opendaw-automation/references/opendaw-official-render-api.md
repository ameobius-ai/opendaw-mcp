# openDAW Official Render API — Source Analysis (June 30, 2026)

Analyzed from GitHub: `andremichelle/opendaw` main branch.

## Mixdowns.ts (packages/app/studio/src/service/Mixdowns.ts)

The official UI export code. Two entry points:

### exportMixdown (full mixdown → WAV/MP3/FLAC)
```typescript
export const exportMixdown = async ({project: source, meta}: ProjectProfile): Promise<void> => {
    const project = source.copy()                           // 1. copy project
    const abortController = new AbortController()
    const progress = new DefaultObservableValue(0.0)
    // 2. OER.start with 4 args (NOT 5 — no sampleRate)
    const result = await Promises.tryCatch(OfflineEngineRenderer
        .start(project, Option.None, progress, abortController.signal))
    // 3. result is AudioData → WavFile.encodeFloats(audioData) → download
}
```

### exportStems (per-track stems → ZIP)
```typescript
export const exportStems = async ({project: source, meta}, config: ExportConfiguration) => {
    const project = source.copy()
    const result = await Promises.tryCatch(OfflineEngineRenderer
        .start(project, Option.wrap(config), progress, abortController.signal))
    // result.numberOfChannels = numStems * 2 (stereo per stem)
    // Each stem = frames[stemIndex*2] + frames[stemIndex*2+1]
}
```

**KEY:** No manual sampleManager registration before copy. No `handler.setLoaded()`. Just copy → start. This means `GlobalSampleLoaderManager` must share loaded state across copies, OR the original project's sampleProvider handles fetchAudio for the copy too.

## OfflineEngineRenderer.ts (packages/studio/core/src/OfflineEngineRenderer.ts)

### start() signature — 5 params but sampleRate is optional with default
```typescript
static async start(
    source: Project,                    // project copy
    optExportConfiguration: Option<ExportConfiguration>,
    progress: DefaultObservableValue<number>,
    abortSignal?: AbortSignal,          // 4th arg, optional
    sampleRate: int = 48_000            // 5th arg, defaults to 48000
): Promise<AudioData>
```

### start() internal flow
1. Disables loop area on the copy
2. Determines render range: `0 → source.lastRegionAction()` (or from exportConfiguration.range)
3. Calculates `maxDurationSeconds` from tempoMap
4. Calls `this.create(source, optExportConfiguration, sampleRate)` → creates Worker, Messenger, Protocol
5. Calls `renderer.render({maxDurationSeconds}, startPosition, endPosition, progress, abortSignal)`

### create() — THE CRITICAL PART

The offline engine sets up its OWN `fetchAudio` handler, SEPARATE from main.ts's sampleProvider:

```typescript
fetchAudio: (uuid: UUID.Bytes): Promise<AudioData> => new Promise((resolve, reject) => {
    const handler = source.sampleManager.getOrCreate(uuid)
    const subscription = handler.subscribe(state => {
        if (state.type === "error") { reject(...); subscription.terminate() }
        else if (state.type === "loaded") {
            resolve(handler.data.unwrap("handler.data"))
            subscription.terminate()
        }
    })
}),
```

**THIS IS WHY WE GET SILENCE.** `source` = project copy. `source.sampleManager` = copy's sampleManager. If the handler for the copy's UUID has state "pending" (never loaded), `subscribe` hangs forever. The engine waits for audio, gets nothing, outputs silence.

### How the official code avoids this

In Mixdowns.ts, audio is already loaded in the ORIGINAL project (user dragged files into the UI). The `GlobalSampleLoaderManager` (from main.ts) wraps a `sampleProvider`. When `source.copy()` is called, if `GlobalSampleLoaderManager` uses a **global/static** registry, the loaded state persists. The copy's `getOrCreate(uuid)` returns the SAME handler with state "loaded".

**In our headless case:** we put audio in `window.DAW_localAudioBuffers` (a Map). The sampleProvider.fetch() reads from this Map. But we never triggered the sampleManager's `setLoaded()` flow — we bypassed it. So handler.state = "pending" → subscribe hangs → silence.

### Fix (untried)

Before `p.copy()`, force the sampleManager to load each audio file:

```javascript
// For each stem:
const fileUuid = UUID.generate();
const idStr = fileUuid.toString();
window.DAW_localAudioBuffers.set(idStr, ab);
window.DAW_fileNameToAudioBuffer.set(idStr, ab);

// Force sampleManager to load via sampleProvider (which reads localAudioBuffers)
const handler = window.DAW_sampleManager.getOrCreate(fileUuid);
// Option A: manually setLoaded
const audioData = window.DAW_audioBufferToAudioData(ab);
handler.setLoaded(audioData, { name: idStr, bpm: 120, duration: ab.duration, sample_rate: ab.sampleRate, origin: 'import' });

// THEN copy — if GlobalSampleLoaderManager is global, loaded state persists
const projectCopy = p.copy();
```

**If `GlobalSampleLoaderManager` is NOT global (per-project instance):** need to register in copy too:
```javascript
// After copy, find AudioFileBox UUIDs and register
for (const box of projectCopy.boxGraph.boxes()) {
    if (box.constructor?.name !== 'AudioFileBox') continue;
    const addr = String(box.address); // copy's UUID
    const fn = box.fileName?.getValue?.();
    const ab = window.DAW_fileNameToAudioBuffer.get(fn);
    if (ab) {
        const ad = window.DAW_audioBufferToAudioData(ab);
        const h = projectCopy.sampleManager.getOrCreate(UUID.parse(addr));
        h.setLoaded(ad, { name: addr, bpm: 120, duration: ab.duration, sample_rate: ab.sampleRate, origin: 'import' });
    }
}
```

## offline-renderer.ts (packages/studio/adapters/src/offline-renderer.ts)

Protocol interface for the worker side:

```typescript
interface OfflineEngineInitializeConfig {
    sampleRate: number
    numberOfChannels: number
    processorsUrl: string
    syncStreamBuffer: SharedArrayBuffer
    controlFlagsBuffer: SharedArrayBuffer
    project: ArrayBufferLike              // serialized project via toArrayBuffer()
    exportConfiguration?: ExportConfiguration
}
```

The project is serialized via `source.toArrayBuffer()` and sent to the worker. The worker deserializes it and runs the engine-processor.

## Render flow summary

```
Mixdowns.exportMixdown()
  → source.copy()
  → OfflineEngineRenderer.start(copy, Option.None, progress, signal)
    → .create(copy, ...) → new Worker, Communicator, fetchAudio handler on copy.sampleManager
    → .render({maxDurationSeconds}, start, end, progress, signal)
      → engineCommands.play() + queryLoadingComplete()
      → protocol.render(config) → worker processes audio → returns Float32Array[]
      → AudioData.create(sampleRate, frames, channels)
```

## What to check next session

1. Is `GlobalSampleLoaderManager` a global singleton or per-project? Check constructor in studio-core.
2. Does `handler.setLoaded()` before `p.copy()` make the copy's handler return "loaded" state?
3. If not, register in copy's sampleManager AFTER copy using `box.address` UUIDs (already works in our code).
4. The `subscribe` approach means even if we setLoaded in copy, the worker's fetchAudio must see state "loaded" — verify the timing (setLoaded must happen before engine.play()).

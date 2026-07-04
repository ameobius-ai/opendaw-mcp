# openDAW Verified API Map (May 2026)

Tested via Playwright page.evaluate() against @opendaw/studio-core running in headless Chromium.

## Project Object (`window.DAW`)

### Own Properties
`boxGraph`, `rootBox`, `userInterfaceBoxes`, `primaryAudioBusBox`, `primaryAudioUnitBox`, `timelineBox`, `api`, `captureDevices`, `editing`, `selection`, `deviceSelection`, `regionSelection`, `boxAdapters`, `userEditingManager`, `parameterFieldAdapters`, `liveStreamReceiver`, `midiLearning`, `mixer`, `tempoMap`, `overlapResolver`, `timelineFocus`, `engine`, `audioUnitFreeze`

### Prototype Methods
`loadScriptDevices`, `startAudioWorklet`, `handleCpuOverload`, `startRecording`, `stopRecording`, `isRecording`, `commitMidiCapture`, `subscribeMidiCaptureAvailable`, `follow`, `own`, `ownAll`, `spawn`, `env`, `rootBoxAdapter`, `timelineBoxAdapter`, `sampleManager`, `soundfontManager`, `clipSequencing`, `isAudioContext`, `isMainThread`, `primaryAudioUnitBoxAdapter`, `liveStreamBroadcaster`, `skeleton`, `receivedMIDIFromEngine`, `collectSampleUUIDs`, `restartRecording`, `toArrayBuffer`, `copy`, `invalid`, `lastRegionAction`, `trackUserCreatedSample`, `terminate`

## Engine (`window.DAW.engine`)

### Methods (callable)
`play`, `stop`, `setPosition`, `prepareRecordingState`, `stopRecording`, `isReady`, `queryLoadingComplete`, `panic`, `sleep`, `wake`, `loadClickSound`, `setFrozenAudio`, `subscribeClipNotification`, `subscribeNotes`, `ignoreNoteRegion`, `noteSignal`, `scheduleClipPlay`, `scheduleClipStop`, `subscribeDeviceMessage`, `registerMonitoringSource`, `unregisterMonitoringSource`, `terminate`

### Getters (access as properties, NOT function calls)
`position`, `bpm`, `isPlaying`, `isRecording`, `isCountingIn`, `playbackTimestamp`, `countInBeatsRemaining`, `markerState`, `cpuLoad`, `project`, `sampleRate` (44100), `preferences`, `perfBuffer`, `perfIndex`

⚠️ `eng.isPlaying` NOT `eng.isPlaying()` — calling as function throws "is not a function".

## ProjectApi (`window.DAW.api`)

### All Methods
`setBpm`, `catchupAndSubscribeBpm`, `catchupAndSubscribeAudioUnits`, `createInstrument(1 param)`, `createAnyInstrument(1 param)`, `replaceMIDIInstrument`, `insertEffect(field, factory, insertIndex?)`, `createNoteTrack(audioUnitBox, insertIndex?)`, `createAudioTrack(audioUnitBox, insertIndex?)`, `createAutomationTrack(audioUnitBox, target, insertIndex?)`, `compactTracks(audioUnitBox)`, `createTimeStretchedClip(props)`, `createTimeStretchedRegion`, `createPitchStretchedClip`, `createPitchStretchedRegion`, `createNotStretchedClip`, `createNotStretchedRegion`, `createNoteClip`, `duplicateRegion`, `exportMIDI`, `exportAudio(owner, suggestedName="audio.wav")`, `quantiseNotes`, `createValueClip`, `createNoteRegion`, `createTrackRegion(trackBox, position, duration, {name?, hue?})`, `createNoteEvent`, `deleteAudioUnit`, `duplicateNotes`

### Critical Signatures
```
createAudioTrack(audioUnitBox, insertIndex?)
  → audioUnitBox = p.primaryAudioUnitBox (REQUIRED, not optional)
  → insertIndex defaults to MAX_SAFE_INTEGER

insertEffect(field, factory, insertIndex?)
  → field = audioUnitBox.audioEffects (NOT the audioUnitBox itself!)
  → factory = EffectFactories.AudioNamed["Compressor"] etc.

createTrackRegion(trackBox, position, duration, {name?, hue?})
  → position/duration in beats or seconds (TBD — check units)
  → returns Option (may be None if duration <= 0)
```

## AudioUnitBox Properties (`primaryAudioUnitBox`)
All are reactive fields with `getValue()` / `setValue()`:
`accept`, `tags`, `type`, `collection`, `editing`, `index`, `volume`, `panning`, `mute`, `solo`, `tracks`, `midiEffects`, `input`, `audioEffects`, `auxSends`, `output`, `capture`

Volume field methods: `serialization`, `equals`, `clamp`, `read`, `write`, `unit`, `constraints`, `fromJSON`

## EffectFactories (`window.DAW_EffectFactories`)

### AudioNamed (15 effects)
Compressor, Crusher, DattorroReverb, Delay, Fold, Gate, Maximizer, NeuralAmp, Reverb, Revamp, StereoTool, Tidal, Vocoder, Waveshaper, Werkstatt

### MidiNamed (5 effects)
Arpeggio, Pitch, Spielwerk, Velocity, Zeitgeist

### Other Keys
`Modular`, `AudioList`, `MidiList`, `MergedNamed`

## BoxGraph (`window.DAW.boxGraph`)
Methods: `beginTransaction`, `abortTransaction`, `endTransaction`, `inTransaction`, `createBox`, `stageBox`, `findBox`, `findVertex`, `boxes()` (iterator), `edges()`, `toArrayBuffer`, `fromArrayBuffer`, `toJSON`, `fromJSON`, `debugBoxes`, `debugDependencies`

### Box Types Found in Empty Project
`TimelineBox`, `TrackBox`, `AudioBusBox`, `GrooveShuffleBox`, `AudioUnitBox`, `RootBox`, `MaximizerDeviceBox`, `ValueEventCollectionBox`, `UserInterfaceBox`

After creating 1 audio track + Compressor + Reverb: adds `CompressorDeviceBox`, `ReverbDeviceBox` (11 total)

## Editing (`window.DAW.editing`)
Methods: `modify(fn)` (wraps mutations for undo), `undo`, `redo`, `canUndo`, `canRedo`, `clear`, `hasUnsavedChanges`, `markSaved`

All mutations MUST be wrapped in `editing.modify(() => { ... })` for undo support.

## SampleManager (`window.DAW.sampleManager`)
Methods: `fetch`, `remove`, `invalidate`, `register`, `record`, `getOrCreate`, `getAudioData`

## Mixer (`window.DAW.mixer`)
Methods: `registerChannelStrip`, `terminate`

## Export
`api.exportAudio(owner, "audio.wav")` → delegates to `AudioWavExport.toFile()`
`api.exportMIDI` — available, signature TBD

## Common Pitfalls
1. `createAudioTrack()` without audioUnitBox → "Cannot read properties of undefined (reading 'tracks')"
2. `insertEffect(audioUnitBox, factory)` → "AudioBusBox has no index field" — must pass `.audioEffects` field
3. `engine.isPlaying()` as function call → "is not a function" — it's a getter
4. `engine.transport.play()` → transport is not a sub-object — use `engine.play()` directly
5. Multiple zombie Vite processes can accumulate — kill stale ones before testing

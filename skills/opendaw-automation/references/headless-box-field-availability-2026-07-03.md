# Headless Box Field Availability (2026-07-03)

## ProjectMetaBox — NOT accessible in headless

### What happened

Tried to add `get_project_info` / `set_project_info` MCP tools for project metadata (name, artist, description, tags, notepad). Discovered `RootBox` in `studio-boxes` does NOT have a `projectMeta` field.

### Root cause

openDAW has two box definition systems:

1. **studio-boxes** (`packages/studio/boxes/src/`) — runtime boxes with TypeScript classes. This is what loads in headless Chromium. `RootBox` here has fields: timeline(1), users(2), created(3), groove(4), baseFrequency(5), modularSetups(10), audioUnits(20), audioBusses(21), outputDevice(30), outputMidiDevices(35), pianoMode(40), shadertoy(100), editingChannel(111). **No field 101 (projectMeta).**

2. **forge-boxes** (`packages/studio/forge-boxes/src/schema/std/`) — code generation schemas. `RootBox.ts` here defines field 101: `{type: "pointer", name: "project-meta", pointerType: Pointers.ProjectMeta, mandatory: false}`. But forge-boxes are build-time codegen, not runtime imports.

`ProjectProfile.ts` creates `ProjectMetaBox` dynamically via `#createMetaBox()` and attaches it through `rootBox.projectMeta.refer(box)`. But since `rootBox.projectMeta` doesn't exist as a getter in studio-boxes `RootBox`, this only works in the full app context where forge-boxes are compiled in.

### Verification

```javascript
// In headless bridge:
const root = h.rootBox;
root.projectMeta           // → undefined
root.getField(101)         // → Error: "Field 101 not found in RootBox"
Object.keys(root)          // → no "projectMeta" key
```

### Lesson

Before adding MCP tools that access box fields, verify the field exists in **studio-boxes** (runtime), not just forge-boxes (codegen). The two systems can diverge.

**Audit command**: Check if a field getter exists:
```javascript
typeof h.rootBox.fieldName  // "function" = exists, "undefined" = not in runtime
```

### What's NOT available in headless

- `get_project_info` (name, artist, description, tags, notepad)
- `set_project_info`
- `updateCover` / cover image
- `saveAs` with metadata

### What IS available (project-level)

- `get_project_metadata` — created date, time signature, AU count, track count, groove_enabled
- `set_tuning` — A4 base frequency (rootBox.baseFrequency, field 5)
- `set_bpm` — tempo
- All box-level operations (tracks, effects, regions, notes, etc.)

## RootBox Fields (studio-boxes, verified Jul 3)

```
1:  timeline          (PointerField<Timeline>)
2:  users             (Field<User>)
3:  created           (StringField) — ISO date string
4:  groove            (PointerField<Groove>)
5:  baseFrequency     (Float32Field, 400-480 Hz, default 440)
10: modularSetups     (Field<ModularSetup>)
20: audioUnits        (Field<AudioUnits>)
21: audioBusses       (Field<AudioBusses>)
30: outputDevice      (Field<AudioOutput>)
35: outputMidiDevices (Field<MIDIDevice>)
40: pianoMode         (PianoMode)
100: shadertoy        (PointerField<Shadertoy>)
111: editingChannel   (PointerField<Editing>)
```

No field 101 (projectMeta). No field for project name/artist/description.

## TrackBox Fields (verified Jul 3)

TrackBox has NO name field. Track display names come from AudioUnitBox, not TrackBox.

```
1:  tracks            (PointerField<TrackCollection>)
2:  target            (PointerField<Automation>)
3:  regions           (Field<RegionCollection>)
4:  clips             (Field<ClipCollection>)
10: index             (Int32Field)
11: type              (Int32Field) — 0=Undefined, 1=Notes, 2=Audio, 3=Value
20: enabled           (BooleanField, default true)
30: excludePianoMode  (BooleanField, default false)
```

Upstream issue #212 (automation track naming) — TrackBox has no name to set. `add_automation` passes `{name: paramName}` to `createValueClip`, which sets the clip label, not the track name.

## Vite Startup Patterns (recurring)

Vite dev server on headless-daw has consistent quirks:

1. **IPv6 only**: listens on `[::1]:5174`, not `127.0.0.1`. `ss -tlnp` shows it. `curl http://localhost:5174` may fail; use `curl http://[::1]:5174`.
2. **~20s warmup**: Vite needs 15-20s for dep optimization before serving. Don't test immediately.
3. **`--strictPort`**: crashes if port occupied. Without it, falls back to 5175/5176.
4. **Zombie processes**: stale Vite processes accumulate. Kill before starting: `ps aux | grep "[v]ite" | awk '{print $2}' | xargs kill`
5. **Background terminal**: `terminal(background=true)` for Vite. Output may be empty (stderr not captured). Verify via `ss -tlnp | grep 5174` instead of checking output.
6. **Command**: `cd headless-daw && node node_modules/vite/bin/vite.js --port 5174 --strictPort` (no `&`, no `nohup`)

## Engine ObservableValues (verified Jul 3)

All accessible as getters (NOT function calls):

```
eng.isPlaying              → ObservableValue<boolean>
eng.position               → ObservableValue<ppqn>
eng.bpm                    → ObservableValue<bpm>
eng.cpuLoad                → ObservableValue<number> (0-1)
eng.isRecording            → ObservableValue<boolean>
eng.isCountingIn           → ObservableValue<boolean>
eng.countInBeatsRemaining  → ObservableValue<number>
eng.playbackTimestamp      → ObservableValue<ppqn>
eng.markerState            → ObservableValue<[uuid, index] | null>
```

All covered by `get_engine_status` MCP tool. Access pattern: `eng.isPlaying?.getValue?.() ?? false`.

## upstream/wasm branch

Separate experimental branch (not merged to main). Contains WASM audio engine, PerformancePage, soundfont loading, scriptable devices. NOT relevant to our headless MCP work — we track `upstream/main` only.

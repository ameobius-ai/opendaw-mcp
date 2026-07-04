# Upstream Transfer & Preset Pitfalls (July 2026 session)

## AudioUnitType is a STRING enum (not number)
`type.getValue()` returns `"instrument"`, `"bus"`, `"aux"`, `"output"` — NOT numbers.
Compare with `=== "output"`, not `=== 2`.
```typescript
enum AudioUnitType {
    Instrument = "instrument",
    Bus = "bus",
    Aux = "aux",
    Output = "output"
}
```
TransferAudioUnits filters Output units: `box.type.getValue() !== AudioUnitType.Output` → `"output" !== "output"`.

## pointerHub loses regions after new AU creation
**Create ALL audio units and tracks BEFORE adding regions/notes.**
After creating a region on AU1, creating AU2 causes AU1's regions to disappear from `pointerHub.incoming()`.
The pointerHub stabilizes once after structural changes; adding new top-level boxes (AU) invalidates existing connections.

```js
// ✅ CORRECT ORDER:
p.editing.modify(() => { api.createInstrument(IF.Vaporisateur); });  // AU1
p.editing.modify(() => { api.createInstrument(IF.Vaporisateur); });  // AU2
p.editing.modify(() => { t1 = api.createNoteTrack(au1); });
p.editing.modify(() => { t2 = api.createNoteTrack(au2); });
// NOW add regions/notes — pointerHub stays stable
p.editing.modify(() => { /* create region on t1 */ });
```

```js
// ❌ WRONG: AU2 creation kills AU1's pointerHub
p.editing.modify(() => { api.createInstrument(IF.Vaporisateur); });  // AU1
p.editing.modify(() => { t1 = api.createNoteTrack(au1); });
p.editing.modify(() => { /* create region on t1 */ });  // visible ✅
p.editing.modify(() => { api.createInstrument(IF.Vaporisateur); });  // AU2
// → t1.regions.pointerHub.incoming() now returns [] ❌
```

## Finding primaryAudioBusBox for ProjectSkeleton
TransferAudioUnits and PresetDecoder need `ProjectSkeleton` with `primaryAudioBusBox`.
Find it via the Output unit's input pointerHub:
```js
const outputAU = units.find(u => u.type.getValue() === "output");
const primaryBus = [...outputAU.input.pointerHub.incoming()].map(({box}) => box)[0];
```

## Preset base64 roundtrip
ArrayBuffer ↔ base64 for JSON transport over MCP:
```js
// Encode: Uint8Array → charCodes → btoa
const bytes = new Uint8Array(buffer);
let binary = '';
for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
const base64 = btoa(binary);

// Decode: atob → Uint8Array → .buffer
const binary = atob(b64);
const bytes = new Uint8Array(binary.length);
for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
PresetDecoder.decode(bytes.buffer, skeleton);
```

## .gitignore for opendaw-mcp
Glob `*.backup` does NOT match `server.py.backup.20260703_022625` — use `server.py.backup*`.
Same for final backups: `server.py.final*` not `*.final`.
Full .gitignore:
```
__pycache__/
*.pyc
server.py.backup*
server.py.final*
server_recovered.py
venv/
.env
```

## Kanban --goal for autonomous development
User requested goal-based autonomous development. Workflow:
```bash
# 1. Create project (binds folders + board)
hermes project create openDAW --board producers
hermes project add-folder openDAW /path/to/opendaw-mcp
hermes project add-folder openDAW /path/to/openDAW
hermes project add-folder openDAW /path/to/headless-daw
hermes project set-primary openDAW /path/to/opendaw-mcp

# 2. Create goal task with detailed body (algorithm, constraints, candidates)
hermes kanban --board producers create "title" --body "..." --goal --goal-max-turns 30 --priority 1 --project openDAW

# 3. Assign to profile
hermes kanban --board producers assign <task_id> producers

# 4. Dispatch (spawns worker in worktree)
hermes kanban --board producers dispatch

# Monitor:
hermes kanban --board producers tail <task_id>   # event stream
hermes kanban --board producers show <task_id>    # status + comments
hermes kanban --board producers runs <task_id>    # attempt history
```

## Upstream namespaces covered vs uncovered (July 2026)

### Covered by MCP tools (updated to 154)
- ProjectApi.ts (27 methods: createInstrument, insertEffect, createNoteTrack, createAudioTrack, createAutomationTrack, compactTracks, createTimeStretchedClip/Region, createPitchStretchedClip/Region, createNotStretchedClip/Region, createNoteClip, createValueClip, createNoteRegion, createTrackRegion, createNoteEvent, deleteAudioUnit, duplicateNotes, quantiseNotes, setBpm)
- TransferRegions (transfer_region tool)
- TransferAudioUnits (transfer_audiounit tool)
- PresetEncoder (export_preset, export_effect_chain tools)
- PresetDecoder (import_preset, replace_from_preset tools)
- PresetHeader (ChainKind enum for encodeEffects)
- ScriptCompiler (set_script_device_code tool)
- EffectFactories (15 audio + 5 MIDI effects)
- InstrumentFactories (Vaporisateur, Nano, Soundfont, Tape, Playfield, Apparat)
- **VaryingTempoMap** (ppqn_to_seconds, seconds_to_beats, get_tempo_at tools) — tempo automation aware conversion
- **AudioUnitFreeze** (get_unit_freeze_status tool) — isFrozenUuid + hasSidechainDependents
- **Project** (get_project_duration, validate_project, list_samples tools) — lastRegionAction, invalid, collectSampleUUIDs
- **Mixer** (get_mixer_state tool) — all AU volume/pan/mute/solo via namedParameter
- **NoteRegionBoxAdapter.flatten** (flatten_note_regions tool) — merge overlapping note regions
- **Region.consolidate** (consolidate_region tool) — unique event collection
- **AudioPlayMode** (list_warp_markers, get_region_play_mode, set_time_stretch_cents tools) — warp markers, playback rate, cents
- **TrackBoxAdapter.valueAt** (get_automation_value tool) — automation curve resolution
- **AudioFileBoxAdapter** (get_audio_file_info tool) — fileName, start/end seconds, sample rate
- **Region.moveContentStart** (move_region_content tool) — shift content without moving region

### Uncovered candidates (future MCP tools)
- TransferUtils.extractRegions — copy regions + their AU between projects (cross-project)
- PresetDecoder.peekHasTimeline — check if preset contains timeline data
- PresetEncoder.encode with excludeEffect callback — selective effect exclusion during AU export
- ClipSequencing — session view sequencing interface
- packages/studio/adapters/src/engine/ — engine control
- packages/studio/adapters/src/sample/ — sample management
- packages/studio/adapters/src/soundfont/ — soundfont management
- packages/studio/adapters/src/modular/ — modular system
- packages/studio/adapters/src/nam/ — NeuralAmp model loading

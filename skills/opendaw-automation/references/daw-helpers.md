# DAW_HELPERS — JS Helper Injection for Shorter MCP Tools

## Problem

Every MCP tool that accesses AU/track/region adapters repeated 10-15 lines of boilerplate:
```javascript
const p = window.DAW;
const auAdapters = p.rootBoxAdapter.audioUnits.adapters();
if (i >= auAdapters.length) return {error: "No AU at " + i};
const auAdapter = auAdapters[i];
const trackAdapters = auAdapter.tracks.collection.adapters();
if (j >= trackAdapters.length) return {error: "No track " + j};
const trackAdapter = trackAdapters[j];
const regions = trackAdapter.regions.collection.asArray();
if (k >= regions.length) return {error: "No region " + k};
```

## Solution: DAW_HELPERS injected in bridge.start()

After DAW globals are loaded, inject helper functions into `window.DAW_HELPERS`:

```javascript
// In HeadlessDawBridge.start(), after wait_for_function checks:
await self.page.evaluate("""() => {
    if (window.DAW_HELPERS) return;  // idempotent
    const p = window.DAW;
    window.DAW_HELPERS = {
        au: (i) => {
            const aus = p.rootBoxAdapter.audioUnits.adapters();
            if (i >= aus.length) throw new Error('No AU at ' + i);
            return aus[i];
        },
        track: (auIdx, trackIdx) => {
            const au = window.DAW_HELPERS.au(auIdx);
            const tracks = au.tracks.collection.adapters();
            if (trackIdx >= tracks.length) throw new Error('No track ' + trackIdx);
            return tracks[trackIdx];
        },
        region: (auIdx, trackIdx, regIdx) => {
            const track = window.DAW_HELPERS.track(auIdx, trackIdx);
            const regions = track.regions.collection.asArray();
            if (regIdx >= regions.length) throw new Error('No region ' + regIdx);
            return regions[regIdx];
        },
        allAUs: () => p.rootBoxAdapter.audioUnits.adapters(),
        instrumentAU: () => {
            const aus = p.rootBoxAdapter.audioUnits.adapters();
            const inst = aus.find(a => a.isInstrument);
            if (!inst) throw new Error('No instrument AU found');
            return inst;
        },
        modify: (fn) => p.editing.modify(fn),
        project: p, api: p.api, boxGraph: p.boxGraph,
        editing: p.editing, tempoMap: p.tempoMap,
        audioUnitFreeze: p.audioUnitFreeze,
        rootBoxAdapter: p.rootBoxAdapter,
    };
}""")
```

## Usage in MCP tools — 3x shorter

```javascript
// BEFORE (15 lines):
const p = window.DAW;
const auAdapters = p.rootBoxAdapter.audioUnits.adapters();
if (idx >= auAdapters.length) return {error: "No AU"};
const auAdapter = auAdapters[idx];
// ...

// AFTER (3 lines):
const h = window.DAW_HELPERS;
const region = h.region(unit_index, track_index, region_index);
// h throws Error with descriptive message if index out of range
```

## Helper reference

| Helper | Returns | Throws on error |
|--------|---------|-----------------|
| `h.au(i)` | AudioUnitBoxAdapter | "No AU at i" |
| `h.auBox(i)` | AudioUnitBox (raw box, not adapter) | "No AU at i" |
| `h.track(auIdx, trackIdx)` | TrackBoxAdapter | "No track j on AU i" |
| `h.region(auIdx, trackIdx, regIdx)` | RegionBoxAdapter | "No region k" |
| `h.allAUs()` | AudioUnitBoxAdapter[] | — |
| `h.allAUBoxes()` | AudioUnitBox[] (raw boxes, sorted by index) | — |
| `h.instrumentAU()` | AudioUnitBoxAdapter (first instrument) | "No instrument AU found" |
| `h.modify(fn)` | void (wraps editing.modify) | — |
| `h.project` | Project | — |
| `h.api` | ProjectApi | — |
| `h.tempoMap` | VaryingTempoMap | — |
| `h.audioUnitFreeze` | AudioUnitFreeze | — |

### Box-level vs adapter-level

`h.au(i)` returns an **adapter** (AudioUnitBoxAdapter) — has `.tracks`, `.audioEffects`, `.input` as adapter collections.
`h.auBox(i)` returns a **raw box** (AudioUnitBox) — has `.tracks`, `.audioEffects`, `.input` as pointerHub collections.

Use `h.auBox(i)` / `h.allAUBoxes()` when you need raw box access (pointerHub.incoming(), field.getValue(), box creation inside editing.modify). Use `h.au(i)` / `h.allAUs()` when you need adapter convenience methods (`.isInstrument`, `.collection.adapters()`).

**DRY migration COMPLETE (2026-07-03):** ~295 raw enumeration occurrences replaced across 17 helper types (v1.9.3):
- 133 AU enumeration → `h.allAUBoxes()` / `h.auBox()` (113+ tools)
- 25+13 effect enumeration → `h.effectBoxes(au)` (38 tools)
- 5+6 MIDI effect enumeration → `h.midiEffectBoxes(au)` (11 tools)
- 28+12+4 track enumeration → `h.trackBoxes(au)` (44 tools)
- 29+5+3 region enumeration → `h.regionBoxes(track)` (37 tools)
- 15+5+4 event enumeration → `h.eventBoxes(coll)` (24 tools)
- 18+6+6 input enumeration → `h.inputBoxes(au)` (30 tools)
- 6 marker enumeration → `h.markerBoxes(mt)` (6 tools)
- 7 send enumeration → `h.sendBoxes(au)` (7 tools)
- 4 bus enumeration → `h.busBoxes()` (4 tools)
- 3+4 sample enumeration → `h.sampleBoxes(pf)` (7 tools)
- 10+2 note track enumeration → `h.noteTrackBoxes(au)` (12 tools)
- 3+2 clip enumeration → `h.clipBoxes(track)` (5 tools)
- 1 root clip enumeration → `h.rootClipBoxes()` (1 tool)
- 2 script param enumeration → `h.scriptParams(device)` (2 tools)
- 1 script sample enumeration → `h.scriptSamples(device)` (1 tool)
- 3 chain field enumeration → `h.chainBoxes(field)` (3 tools)

**0 raw enumeration patterns remain.** 20 total `pointerHub.incoming()` in server.py: 18 helper definitions + 1 comment + 1 field check + 0 working patterns.

See `references/dry-box-level-au-enumeration-2026-07-03.md` for the original AU migration details.
See `references/dry-migration-technique.md` for the full technique + all 3 rounds.

### Box-level enumeration helpers (v1.9.2–v1.9.3)

| Helper | Returns | Sorted? | Notes |
|--------|---------|---------|-------|
| `h.effectBoxes(au)` | EffectDeviceBox[] | Yes, by index | Replaces `[...au.audioEffects.pointerHub.incoming()].map(({box})=>box).sort(...)` |
| `h.midiEffectBoxes(au)` | MidiEffectDeviceBox[] | Yes, by index | Replaces `[...au.midiEffects.pointerHub.incoming()].map(({box})=>box).sort(...)` |
| `h.trackBoxes(au)` | TrackBox[] | Yes, by index | Replaces `[...au.tracks.pointerHub.incoming()].map(({box})=>box).sort(...)` |
| `h.regionBoxes(track)` | RegionBox[] | **No** (insertion order) | Replaces `[...track.regions.pointerHub.incoming()].map(({box})=>box)`. Intentionally unsorted — original code didn't sort, sorting by position would change region indices. |
| `h.eventBoxes(coll)` | EventBox[] | **No** (insertion order) | Replaces `[...coll.events.pointerHub.incoming()].map(({box})=>box)`. Works for note events (NoteEventCollectionBox) and signature events (SignatureTrack). Unsorted. |
| `h.inputBoxes(au)` | DeviceBox[] | **No** (insertion order) | Replaces `[...au.input.pointerHub.incoming()].map(({box})=>box)`. Returns instrument/effect boxes connected to AU input. Unsorted. |
| `h.markerBoxes(mt)` | MarkerBox[] | **No** (insertion order) | Replaces `[...mt.markers.pointerHub.incoming()].map(({box})=>box)`. Marker track enumeration. |
| `h.sendBoxes(au)` | AuxSendBox[] | Yes, by index | Replaces `[...au.auxSends.pointerHub.incoming()].map(({box})=>box).sort(index)`. Send routing. |
| `h.busBoxes()` | AudioBusBox[] | **No** (insertion order) | Replaces `[...p.rootBox.audioBusses.pointerHub.incoming()].map(({box})=>box)`. Root-level bus enumeration. |
| `h.sampleBoxes(pf)` | SampleBox[] | **No** (insertion order) | Replaces `[...pf.samples.pointerHub.incoming()].map(({box})=>box)`. Playfield sample enumeration. |
| `h.noteTrackBoxes(au)` | TrackBox[] | Yes, by index + filter | Replaces `[...au.tracks...].map().sort(index).filter(type===1)`. Note tracks only. |
| `h.clipBoxes(track)` | ClipBox[] | **No** (insertion order) | Replaces `[...track.clips.pointerHub.incoming()].map(({box})=>box)`. **NOT** `regionBoxes` — clips and regions are different collections. |
| `h.rootClipBoxes()` | ClipBox[] | **No** (insertion order) | Replaces `[...p.rootBox.clips.pointerHub.incoming()].map(({box})=>box)`. Root-level clips, NOT track clips. |
| `h.scriptParams(device)` | WerkstattParameterBox[] | **No** (insertion order) | Replaces `[...device.parameters.pointerHub.incoming()].map(({box})=>box)`. Scriptable device internal params. NOT the same as Playfield samples. |
| `h.scriptSamples(device)` | WerkstattSampleBox[] | **No** (insertion order) | Replaces `[...device.samples.pointerHub.incoming()].map(({box})=>box)`. Scriptable device internal samples. NOT the same as Playfield `h.sampleBoxes(pf)`. |
| `h.chainBoxes(field)` | DeviceBox[] | **No** (insertion order) | Replaces `[...field.pointerHub.incoming()].map(({box})=>box)`. Generic — accepts any field with pointerHub. Used for dynamic `const field = kind === 0 ? au.midiEffects : au.audioEffects`. |

**Pitfall: regionBoxes is unsorted by design.** If you need sorted-by-position regions, call `h.regionBoxes(track).sort((a,b) => a.position.getValue() - b.position.getValue())` explicitly. Do NOT add sort to the helper — it would silently change region index semantics for 29+ tools.

**Pitfall: eventBoxes and inputBoxes are also unsorted.** Same principle — original code didn't sort these, so the helpers don't either. If sorted access is needed, chain `.sort()` explicitly after the helper call.

**Pitfall: clipBoxes is NOT regionBoxes.** `h.regionBoxes(track)` accesses `track.regions`, `h.clipBoxes(track)` accesses `track.clips`. These are different collections on the same track box. Using `regionBoxes` to replace a clips enumeration silently corrupts every clips call — the data comes from the wrong field. Always verify the field name in the helper matches the field name in the original code before `replace_all`.

**Pitfall: ternary guard patterns migrate cleanly.** Many tools use `au.midiEffects ? [...au.midiEffects.pointerHub.incoming()].map(({box})=>box) : []` to guard against missing fields. These migrate to `au.midiEffects ? h.midiEffectBoxes(au) : []` — the ternary stays, only the enumeration is replaced. Same for `au.input ? h.inputBoxes(au) : []`. Use `replace_all=true` for these — they're identical across 5+ scriptable device tools.

**Pitfall: scriptSamples is NOT sampleBoxes.** `h.sampleBoxes(pf)` accesses `pf.samples` on a Playfield instrument box. `h.scriptSamples(device)` accesses `device.samples` on a Werkstatt scriptable device. These are different box types with different sample fields. Using the wrong helper returns wrong data or throws.

**Pitfall: rootClipBoxes is NOT clipBoxes.** `h.clipBoxes(track)` accesses `track.clips` on a TrackBox. `h.rootClipBoxes()` accesses `p.rootBox.clips` on the RootBox. Different objects, different collections.

**Pitfall: chainBoxes is a generic fallback.** When the field is determined dynamically (`const field = isMidi ? au.midiEffects : au.audioEffects`), you can't use `h.effectBoxes()` or `h.midiEffectBoxes()` because the helper hardcodes the field name. `h.chainBoxes(field)` accepts any field with `pointerHub.incoming()`. It's unsorted — chain `.sort()` explicitly if needed.

**Technique: edge case migration patterns.** Multi-line patterns with `.filter()` after `.map().sort()` migrate by chaining the filter after the helper call: `h.trackBoxes(au).filter(t => t.type === 3)`. forEach loops swap the enumeration source: `h.effectBoxes(au).forEach((box) => {...})`. Object literal maps change `({{box}})` to `(box)` since the helper returns boxes directly: `h.trackBoxes(au).map((box) => ({{name: ...}}))`. See `references/dry-migration-technique.md` round 3 for all 8 edge case techniques.

## Tools using DAW_HELPERS (post-refactor)

- `get_mixer_state` — uses `h.allAUs()`
- `flatten_note_regions` — uses `h.track()` + `h.modify()`
- `consolidate_region` — uses `h.region()`
- `list_warp_markers` — uses `h.region()`
- `get_region_play_mode` — uses `h.region()`
- `set_time_stretch_cents` — uses `h.region()` + `h.modify()`
- `get_unit_freeze_status` — uses `h.au()` + `h.audioUnitFreeze`
- `get_automation_value` — uses `h.track()`
- `get_audio_file_info` — uses `h.region()`
- `move_region_content` — uses `h.region()` + `h.modify()`
- `get_track_info` — uses `h.track()`
- `get_full_project_state` — uses `h.allAUs()` + `h.project`
- `get_region_info` — uses `h.region()`
- `clone_clip` — uses `h.track()` + `h.modify()`
- `consolidate_clip` — uses `h.track()` + `h.modify()`
- `create_automation_event` — uses `h.track()` + `h.modify()`
- `list_automation_events_detail` — uses `h.track()`
- `set_automation_interpolation` — uses `h.region()` + `h.modify()`
- `get_note_range` — uses `h.region()`
- `find_overlapping_notes` — uses `h.region()`
- `set_note_advanced` — uses `h.region()` + `h.modify()` (conditional JS build)
- `consolidate_note` — uses `h.region()` + `h.modify()` (outer let for result)
- `set_device_label` — uses `h.au()` + `h.modify()`
- `get_device_chain_detail` — uses `h.au()` + `au.input.adapter()` + `au.audioEffects.adapters()`

Older tools (1-138) still use `const p = window.DAW` pattern — they work fine, refactoring is optional.

## Pitfall: clips.collection.adapters() NOT asArray()

Track clips use `IndexedBoxAdapterCollection` which has `.adapters()`, NOT `.asArray()`:
```javascript
// ❌ BREAKS:
const clips = track.clips.collection.asArray();  // TypeError: not a function

// ✅ WORKS:
const clips = track.clips.collection.adapters();
```

Regions use `.asArray()` (different collection type). This inconsistency is upstream.

## Pitfall: clip.consolidate() needs editing.modify()

Unlike `region.consolidate()` (which works without a transaction), `clip.consolidate()` MUST be wrapped:
```javascript
// ❌ May silently fail:
clip.consolidate();

// ✅ Works:
h.modify(() => { clip.consolidate(); });
```

## Pitfall: clip.clone() needs editing.modify()

Same as consolidate — `clip.clone(consolidate)` must be inside `editing.modify()`:
```javascript
h.modify(() => { clip.clone(false); });
```

## Pitfall: type.getValue() returns STRING not number

`AudioUnitBox.type.getValue()` returns `"instrument"` or `"output"` (string enum), NOT 0/1.
```javascript
// ❌ NEVER WORKS:
const synth = units.find(u => u.type.getValue() === 0);

// ✅ WORKS:
const synth = aus.find(a => a.isInstrument);  // via adapter
// or:
const synth = units.find(u => u.type.getValue() === 'instrument');
```

## Pattern: conditional JS field setting (set_note_advanced)

When a tool accepts optional fields with sentinel values, build JS conditionally in Python:
```python
js_lines = []
if chance >= 0: js_lines.append(f"noteBox.chance.setValue({chance});")
if cent > -999: js_lines.append(f"noteBox.cent.setValue({cent});")
js_body = " ".join(js_lines)
# inject: h.modify(() => { {js_body} });
```
This avoids setting fields the caller didn't specify.

## Pattern: outer let for editing.modify() results

`editing.modify()` callback return values are lost. Capture via outer variable:
```javascript
let result;
h.modify(() => { result = first.flatten(toFlatten); });
// result is now accessible outside
```

## Pattern: device chain access

```javascript
const au = h.au(idx);
const input = au.input.adapter();  // Option<InstrumentAdapter>
const instrument = input.isEmpty() ? null : {
    label: input.unwrap().labelField.getValue(),
    type: input.unwrap().box.constructor.name,
};
const audioFx = au.audioEffects.adapters();  // EffectDeviceBoxAdapter[]
const midiFx = au.midiEffects.adapters();
```

## E2E verification (July 2026)

- `get_mixer_state`: 2 AUs (Vaporisateur + Output), correct volume/mute/solo ✅
- `flatten_note_regions`: 2 overlapping regions → 1 merged (6 beats, 2 notes) ✅
- `consolidate_region`: mirrored → unique ✅
- `clone_clip`: 1 clip → 2 clips, same label ✅
- `consolidate_clip`: was_mirrored=true → is_mirrored=false ✅
- `get_full_project_state`: BPM, 2 AUs, tracks with type/regions/clips ✅
- `get_track_info`: type, enabled, region/clip counts ✅
- `get_automation_value`: edge case (no tracks) handled ✅
- `get_note_range`: C4(60)→C5(72), 4 notes, max duration 1 beat ✅
- `find_overlapping_notes`: pitch 60, beats 0-2 → 1 note found ✅
- `create_automation_event`: collection.createEvent with interpolation ✅ (tested via box-level access)
- `set_automation_interpolation`: event.interpolation setter works ✅
- `ppqn_to_seconds`: 4 beats @120bpm = 2.0s, @140bpm = 1.714s ✅
- `seconds_to_beats`: roundtrip accurate ✅
- `get_tempo_at`: correct BPM at position ✅
- `get_project_duration`: 0 beats for empty project ✅
- `validate_project`: valid=true for clean project ✅
- `list_samples`: 0 for empty project ✅
- `get_unit_freeze_status`: frozen=false, no sidechain ✅
- `set_note_advanced`: chance=50, cent=10, playCount=4, playCurve=0.5 ✅
- `consolidate_note`: 1 note (playCount=4) → 4 individual notes ✅
- `get_device_chain_detail`: Vaporisateur + Delay, type/enabled ✅
- `set_device_label`: Delay → Echo ✅

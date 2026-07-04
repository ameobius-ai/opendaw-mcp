# Box-Level Patterns — ValueEventBox, AudioRegionBox, Duplicate Notes (July 2026 session 8)

## ValueEventBox — Automation Events

ValueEventBox stores automation points on Value-type (type 3) tracks.

### Fields
| Key | Name | Type | Notes |
|-----|------|------|-------|
| 1 | events | PointerField<Pointers.ValueEvents> | Points to ValueEventCollectionBox.events |
| 10 | position | Int32Field | Position in PPQN ticks (960 = 1 beat) |
| 11 | index | Int32Field | Sort index within collection |
| 12 | interpolation | Int32Field<Pointers.ValueInterpolation> | 0=hold, 1=linear; curve via attached ValueEventCurveBox |
| 13 | value | Float32Field | Automation value (0-1 normalized for most params) |
| 14 | slope | Float32Field | DEPRECATED — use ValueEventCurveBox instead |

### Interpolation values
- `0` = **hold** (step value, no interpolation) — unless a ValueEventCurveBox is attached via pointerHub, then it's **curve**
- `1` = **linear** (smooth ramp between points)

Detection pattern for reading interpolation:
```javascript
const interpVal = evt.interpolation?.getValue?.() ?? 0;
let interp = "none";
if (interpVal === 1) interp = "linear";
else if (interpVal === 0) {
    const curveBox = evt.interpolation?.pointerHub?.incoming?.()?.at?.(0)?.box;
    interp = curveBox ? "curve" : "hold";
}
```

### Creating automation events
```javascript
p.editing.modify(() => {
    const autoTrack = p.api.createAutomationTrack(au, field);
    const valueClip = p.api.createValueClip(autoTrack, 0, {name: paramName});
    const collection = valueClip.events?.targetVertex?.unwrap?.()?.box;
    
    points.forEach(([beatPos, value], i) => {
        ValueEventBox.create(p.boxGraph, UUID.generate(), (box) => {
            box.events.refer(collection.events);
            box.position.setValue(Math.round(beatPos * 960));
            box.index.setValue(i);
            box.value.setValue(value);
            box.interpolation.setValue(1); // linear
        });
    });
});
```

### Listing automation events
Walk Value-type tracks → clips → collection → ValueEventBox array:
```javascript
let valueTracks = [...au.tracks.pointerHub.incoming()]
    .map(({box}) => box)
    .filter(b => b.type?.getValue?.() === 3);  // type 3 = Value/automation

for (const track of valueTracks) {
    const clips = [...track.clips?.pointerHub?.incoming?.() ?? []].map(({box}) => box);
    for (const clip of clips) {
        const collection = clip.events?.targetVertex?.unwrap?.()?.box;
        if (collection?.events) {
            const evtBoxes = [...collection.events.pointerHub.incoming()].map(({box}) => box);
            // each evtBox has: position, value, index, interpolation
        }
    }
}
```

## AudioRegionBox — Fading and Gain (uncovered fields)

### AudioRegionBox full field map
| Key | Name | Type | Notes |
|-----|------|------|-------|
| 1 | regions | PointerField | Track regions collection |
| 2 | file | PointerField | AudioFileBox reference |
| 3 | playback | StringField | DEPRECATED |
| 4 | timeBase | StringField | "musical" or "seconds" |
| 5 | events | PointerField | ValueEventCollection (for gain automation?) |
| 6 | warping | PointerField | DEPRECATED |
| 7 | waveformOffset | Float32Field | Sample offset into audio file |
| 8 | playMode | PointerField | AudioTimeStretchBox / AudioPitchStretchBox |
| 10 | position | Int32Field | Timeline position in PPQN |
| 11 | duration | Float32Field | Duration in PPQN (Float, not Int!) |
| 12 | loopOffset | Float32Field | Loop start offset |
| 13 | loopDuration | Float32Field | Loop length |
| 14 | mute | BooleanField | Region mute |
| 15 | label | StringField | Display label |
| 16 | hue | Int32Field | Color |
| 17 | gain | Float32Field | **Per-region gain** (linear, NOT dB) |
| 18 | fading | Fading (ObjectField) | **Fade in/out curves** |

### Fading ObjectField
Fading is an ObjectField (not a Box — no UUID, no create). Fields:
| Key | Name | Type | Default | Notes |
|-----|------|------|---------|-------|
| 1 | in | Float32Field | 0 | Fade-in duration (positive, in beats or seconds depending on timeBase) |
| 2 | out | Float32Field | 0 | Fade-out duration |
| 3 | inSlope | Float32Field | 0.75 | Fade-in curve shape (0.5 = linear, >0.5 = fast start, <0.5 = slow start) |
| 4 | outSlope | Float32Field | 0.25 | Fade-out curve shape |

Access: `audioRegionBox.fading.in.setValue(0.5)` — directly on the ObjectField, no unwrap needed.

### Planned MCP tools (kanban tasks)
- `set_audio_region_fade` (t_39d3a5bd) — set fade in/out + slopes
- `set_audio_region_gain` (t_59a656f2) — set per-region gain (field 17)

## duplicate_notes — Box-Level Note Duplication

`api.duplicateNotes(notes: NoteEventBoxAdapter[])` requires adapters (unavailable in headless). Box-level implementation:

### Algorithm
1. Find all NoteEventBox in the region's collection
2. Compute block span: `blockEnd - blockStart` where `blockStart = min(position)`, `blockEnd = max(position + duration)`
3. Create new NoteEventBox copies shifted by `span`
4. All copies reference the same collection's events pointer

```javascript
const notes = [...collection.events.pointerHub.incoming()].map(({box}) => box);
let blockStart = Infinity, blockEnd = -Infinity;
for (const n of notes) {
    const pos = n.position.getValue();
    const dur = n.duration.getValue();
    if (pos < blockStart) blockStart = pos;
    if (pos + dur > blockEnd) blockEnd = pos + dur;
}
const shift = blockEnd - blockStart;

p.editing.modify(() => {
    for (const n of notes) {
        NoteEventBox.create(p.boxGraph, UUID.generate(), box => {
            box.events.refer(collection.events);
            box.position.setValue(n.position.getValue() + shift);
            box.duration.setValue(n.duration.getValue());
            box.pitch.setValue(n.pitch.getValue());
            box.velocity.setValue(n.velocity.getValue());
            box.chance.setValue(n.chance?.getValue?.() ?? 100);
            box.cent.setValue(n.cent?.getValue?.() ?? 0);
        });
    }
});
```

### Test result
3 notes C4(0-2), E4(1-2), G4(2-2) → shift=4 beats → copies at C4(4-6), E4(5-7), G4(6-8) → 6 total ✅

### NoteEventBox fields
| Key | Name | Type | Default | Notes |
|-----|------|------|---------|-------|
| 1 | events | PointerField | — | → NoteEventCollectionBox.events |
| 10 | position | Int32Field | — | Position within region (PPQN ticks) |
| 11 | duration | Int32Field | 240 | Length in PPQN ticks |
| 20 | pitch | Int32Field | 60 | MIDI pitch (0-127) |
| 21 | velocity | Float32Field | 0.787 | Velocity (0-1 normalized, NOT 0-127) |
| 22 | playCount | Int32Field | 1 | |
| 23 | playCurve | Float32Field | 0 | |
| 24 | cent | Float32Field | 0 | Detune in cents |
| 25 | chance | Int32Field | 100 | Probability (0-100, not 0-1!) |

## ProjectApi — Complete Method Inventory (verified July 2026)

All methods on `p.api` (ProjectApi class, `packages/studio/core/src/project/ProjectApi.ts`):

### Covered by MCP tools ✅
| Method | MCP Tool | Notes |
|--------|----------|-------|
| `setBpm(value)` | set_bpm | clamps 30-1000 |
| `createInstrument(factory, opts)` | create_instrument_track / create_synth_track | |
| `createAnyInstrument(factory)` | create_synth_track | simplified |
| `insertEffect(field, factory, idx)` | add_effect | |
| `createNoteTrack(au, idx?)` | create_note_track | |
| `createAudioTrack(au, idx?)` | create_audio_track | |
| `createAutomationTrack(au, target, idx?)` | add_automation | |
| `compactTracks(au)` | compact_tracks | MUST wrap in editing.modify() |
| `createNoteRegion(props)` | create_note / import_midi | |
| `createNoteEvent(props)` | create_note | |
| `deleteAudioUnit(au)` | delete_audio_unit | |
| `createValueClip(track, idx, opts)` | add_automation | internal |
| `quantiseNotes(notes, opts)` | quantize_notes | |
| `duplicateNotes(notes)` | duplicate_notes | box-level impl (adapter version unavailable) |

### NOT covered (require adapter or browser) ❌
| Method | Blocker | Notes |
|--------|---------|-------|
| `replaceMIDIInstrument(target, factory, attachment)` | adapter | Needs boxAdapters context |
| `duplicateRegion(region, opts)` | adapter | Takes AnyRegionBoxAdapter, not box. Manual box copy used instead |
| `exportMIDI(collection, name)` | browser dialog | Uses Files.save. Use MidiFileEncoder directly instead |
| `exportAudio(owner, name)` | browser dialog | Uses Files.save. Use OfflineEngineRenderer instead |
| `createTimeStretchedRegion(props)` | complex props | AudioContentFactory.TimeStretchedProps — needs research |
| `createPitchStretchedRegion(props)` | complex props | AudioContentFactory.PitchStretchedProps |
| `createNotStretchedRegion(props)` | used internally | Via load_audio + place_audio_region |
| `createNoteClip(track, idx, opts)` | clip vs region | Clip view (piano roll), not arrangement. Different from region |
| `createTrackRegion(track, pos, dur, opts)` | returns Option | Creates Note or Value region depending on track type |
| `catchupAndSubscribeBpm(observer)` | reactive sub | Not applicable to headless |
| `catchupAndSubscribeAudioUnits(listener)` | reactive sub | Not applicable to headless |

## InstrumentFactories — Available in headless

`window.DAW_InstrumentFactories` keys: `Tape`, `Nano`, `Playfield`, `Vaporisateur`, `MIDIOutput`, `Soundfont`, `Apparat`, `Named`

**Pitfall**: `Vaporisateur` is an object but may not work with `createAnyInstrument` in some bridge states. `Tape` is the most reliable for testing. Always check `typeof window.DAW_InstrumentFactories` before use — lazy-load may not be ready in fresh bridge sessions.

## Testing with heredoc syntax (avoids f-string `}}` escaping)

When running complex bridge tests from Python, use heredoc (`<< 'PYEOF'`) instead of `-c` with f-strings. This avoids the `{{`/`}}` escaping nightmare:

```python
# BAD: f-string with embedded JS requires doubling all { and }
python3 -c "
result = await bridge.evaluate(f'''() => {{
    return {{success: true}};
}}''')
"

# GOOD: heredoc, no f-string escaping needed
python3 << 'PYEOF'
import asyncio, sys
sys.path.insert(0, '.')
from server import bridge

async def test():
    r = await bridge.evaluate("""() => {
        return {success: true};
    }""", timeout=15000)
    print(r)

asyncio.run(test())
PYEOF
```

**Key**: Use `"""..."""` (triple-quoted regular string) for JS code. Only use f-strings when you need Python variable interpolation, and then use `str(auIdx)` concatenation instead of `{auIdx}` inside the JS block.

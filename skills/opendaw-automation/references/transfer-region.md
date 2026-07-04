# transfer_region — TransferRegions.transfer + pointerHub Pitfall

## Tool: `transfer_region` (MCP tool #133)

Copies/moves a region between tracks using `TransferRegions.transfer()` from `@opendaw/studio-adapters`.

### Signature
```python
async def mcp_opendaw_transfer_region(
    src_unit_index: int, src_track_index: int, region_index: int,
    dst_unit_index: int, dst_track_index: int,
    insert_position: float, delete_source: bool = False
) -> str
```

- `insert_position` — position in **beats** (converted to ppqn internally: `Math.round(beats * 960)`)
- `delete_source=False` → copy (source preserved), `delete_source=True` → move (source deleted)
- Works across different audio units and different tracks
- Preserved resources (AudioFileBox) are shared, not duplicated

### How TransferRegions.transfer works

```javascript
TransferRegions.transfer(region, targetTrack, insertPosition, deleteSource)
```

1. Collects region + all dependencies via `region.graph.dependenciesOf(region, {alwaysFollowMandatory: true, stopAtResources: true, excludeBox: dep.ephemeral})`
2. Remaps UUIDs (preserved resources keep UUID, others get new UUID)
3. Serializes via `box.toArrayBuffer()` → deserializes into target graph
4. Sets new region position to `insertPosition`
5. If `deleteSource`, deletes original region

### DAW_TransferRegions global

Added to `headless-daw/src/main.ts` in the lazy-load adapters block:
```typescript
w.DAW_TransferRegions = adapters.TransferRegions;
```

### E2E test result (July 2026)
- Source AU1: NoteRegionBox at position 0, duration 2 beats, 1 note (pitch 60)
- Transfer to AU2 at position 4 beats, `delete_source=false`
- Result: ✅ destination has NoteRegionBox at position 4, duration 2. Source preserved.

## CRITICAL PITFALL: pointerHub loses regions after new AU creation

### Symptom
After creating a note region on AU1 (visible via `trackBox.regions.pointerHub.incoming()`), creating a new AU2 causes AU1's regions to **disappear** from `pointerHub.incoming()`. The regions still exist in the BoxGraph but pointerHub returns empty.

### Reproduction
```javascript
// Step 1: Create AU1 + note track + region → regions visible
p.editing.modify(() => { api.createInstrument(IF.Vaporisateur); });  // AU1
p.editing.modify(() => { track = api.createNoteTrack(au1); });
p.editing.modify(() => { /* create NoteRegionBox, regions.refer(trackBox.regions) */ });
// → trackBox.regions.pointerHub.incoming() returns [region] ✅

// Step 2: Create AU2
p.editing.modify(() => { api.createInstrument(IF.Vaporisateur); });  // AU2
// → trackBox.regions.pointerHub.incoming() returns [] ❌ (was [region] before!)
```

### Workaround
**Create ALL audio units and tracks BEFORE adding any regions/notes.** The pointerHub stabilization appears to happen once after all structural changes, and adding new top-level boxes (AU) invalidates existing pointerHub connections.

```javascript
// ✅ CORRECT ORDER:
p.editing.modify(() => { api.createInstrument(IF.Vaporisateur); });  // AU1
p.editing.modify(() => { api.createInstrument(IF.Vaporisateur); });  // AU2
p.editing.modify(() => { t1 = api.createNoteTrack(au1); });
p.editing.modify(() => { t2 = api.createNoteTrack(au2); });
// NOW add regions/notes to AU1 — pointerHub stays stable
p.editing.modify(() => { /* create region on t1 */ });
```

### Why this matters for transfer_region
The transfer test failed initially because notes were added to AU1, then AU2 was created, then transfer was attempted — but AU1's regions were gone from pointerHub. Once both AUs were created first, transfer worked perfectly.

### Alternative: use createNote's pattern instead of api.createNoteRegion
`api.createNoteRegion()` creates a region but it may not be immediately visible via pointerHub. The `create_note` MCP tool uses a different pattern that creates `NoteEventCollectionBox` + `NoteRegionBox` directly with `box.regions.refer(trackBox.regions)` — this is more reliable in headless mode.

## TransferRegions vs move_region_to_track

| Feature | `transfer_region` | `move_region_to_track` |
|---------|-------------------|------------------------|
| Implementation | `TransferRegions.transfer()` (upstream) | Inline JS `region.regions.refer(dstTrack.regions)` |
| Cross-AU | ✅ Yes (different BoxGraphs) | ✅ Yes (same BoxGraph) |
| Position control | ✅ Explicit `insert_position` | ❌ Keeps original position |
| Dependency copy | ✅ Full dependency tree (notes, events, audio) | ⚠️ Region box only (pointer-based move) |
| Copy mode | ✅ `delete_source=false` | ❌ Move only |
| Preserved resources | ✅ Shared (no duplicate AudioFileBox) | N/A |

Use `transfer_region` when you need to copy a region (not move), control the destination position, or ensure all dependencies are copied. Use `move_region_to_track` for simple re-referencing within the same graph.

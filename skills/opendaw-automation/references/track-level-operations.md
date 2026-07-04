# Track-Level Operations — delete_track, move_region_to_track, compact_tracks (tools #127-128, #131, verified July 2026)

## AudioUnitBoxAdapter — new global

Added to `headless-daw/src/main.ts`:
```typescript
w.DAW_AudioUnitBoxAdapter = adapters.AudioUnitBoxAdapter;
```

This enables `auAdapter.deleteTrack(trackAdapter)` from bridge.evaluate.

## delete_track(unit_index, track_index)

Deletes a track from an AU. Uses `AudioUnitBoxAdapter.deleteTrack()`.

```javascript
const AudioUnitBoxAdapter = window.DAW_AudioUnitBoxAdapter;
const au = units[unit_index];
const tracks = [...au.tracks.pointerHub.incoming()].map(({box}) => box).sort((a,b) => a.index.getValue() - b.index.getValue());
const trackBox = tracks[track_index];
const auAdapter = p.boxAdapters.adapterFor(au, AudioUnitBoxAdapter);
const trackAdapter = p.boxAdapters.adapterFor(trackBox, window.DAW_TrackBoxAdapter);
p.editing.modify(() => {
    auAdapter.deleteTrack(trackAdapter);
});
```

**PITFALL**: `AudioUnitBoxAdapter` must be in globals (`DAW_AudioUnitBoxAdapter`). Without it, `p.boxAdapters.adapterFor(au, AudioUnitBoxAdapter)` fails — the class reference is undefined.

**PITFALL**: Both `auAdapter` and `trackAdapter` must be created via `p.boxAdapters.adapterFor(box, AdapterClass)`. You cannot call `auAdapter.deleteTrack(trackBox)` directly — it expects a `TrackBoxAdapter`, not a raw `TrackBox`.

## move_region_to_track(src_unit, src_track, region_idx, dst_unit, dst_track)

Moves a region between tracks (same or different AU). Uses `region.regions.refer(dstTrack.regions)`.

```javascript
const srcTrack = srcTracks[src_track_index];
const dstTrack = dstTracks[dst_track_index];
const regions = [...srcTrack.regions.pointerHub.incoming()].map(({box}) => box);
const region = regions[region_index];

// Check type compatibility
const srcType = srcTrack.type?.getValue();
const dstType = dstTrack.type?.getValue();
if (srcType !== dstType) return {error: `Track type mismatch`};

p.editing.modify(() => {
    region.regions.refer(dstTrack.regions);
});
```

**How it works**: `region.regions` is a PointerField pointing to `TrackBox.regions`. Calling `.refer(dstTrack.regions)` re-points the region to the destination track. The source track automatically loses the region (pointer graph update).

**Type compatibility**: Note tracks (type=1) accept NoteRegionBox, audio tracks (type=2) accept AudioRegionBox. Mixing types throws at render time, not at refer time — so we check upfront.

**Cross-AU works**: src_unit and dst_unit can be different AUs. The region keeps its position, duration, and content. Only the track association changes.

## compact_tracks(unit_index) — tool #131

Compacts tracks on an AU: removes empty main tracks, packs regions top-down to minimize lane count. Uses `p.api.compactTracks(audioUnitBox)`.

```javascript
p.editing.modify(() => {
    p.api.compactTracks(au);
});
```

Automation tracks and clips are never moved or deleted — only note/audio tracks with regions get compacted.

## move_audio_unit(unit_index, delta) — tool #132

Moves an AU up/down in the mixer order by directly swapping `index` fields with neighbors. Delta: -1 = up, +1 = down. Only swaps within same `AudioUnitType` group.

### PITFALL: AudioUnitBoxAdapter.move(delta) does NOT work in headless mode

`p.boxAdapters.adapterFor(auBox, AudioUnitBoxAdapter).move(1)` executes without error but does NOT change the AU's index. The `IndexedBoxAdapterCollection.move()` calls `this.adapters()` which returns an empty or stale list in headless mode — the adapter collection isn't properly initialized without the full UI/adapter context. The `moveIndex()` function silently no-ops because `newIndex === startIndex` when `adapters.length` is 0 or 1.

### SOLUTION: Direct index field swap

```javascript
const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({box}) => box)
    .sort((a, b) => a.index.getValue() - b.index.getValue());
const auBox = units[unit_index];
const oldIdx = auBox.index.getValue();
const newIdx = oldIdx + delta;
if (newIdx < 0 || newIdx >= units.length) return {error: "Cannot move beyond bounds"};
const swapWith = units[newIdx];
if (swapWith.type.getValue() !== auBox.type.getValue()) return {error: "Cannot move across type groups"};
p.editing.modify(() => {
    auBox.index.setValue(newIdx);
    swapWith.index.setValue(oldIdx);
});
```

**Confirmed**: `Int32Field.setValue(n)` works and persists inside `editing.modify()`. Direct index manipulation is the reliable approach in headless mode.

## move_track(unit_index, track_index, delta) — tool #133

Same pattern as move_audio_unit but for tracks within an AU. Direct index swap, not `auAdapter.moveTrack()`.

```javascript
const tracks = [...auBox.tracks.pointerHub.incoming()].map(({box}) => box)
    .sort((a, b) => a.index.getValue() - b.index.getValue());
const trackBox = tracks[track_index];
const newIdx = trackBox.index.getValue() + delta;
p.editing.modify(() => {
    trackBox.index.setValue(newIdx);
    tracks[newIdx].index.setValue(oldIdx);
});
```

Same pitfall as move_audio_unit: `AudioUnitBoxAdapter.moveTrack(trackAdapter, delta)` calls `IndexedBoxAdapterCollection.move()` which silently no-ops in headless mode.

## CRITICAL PITFALL: Never use write_file on server.py

`server.py` is 8500+ lines with all MCP tools. `write_file` overwrites the ENTIRE file — a July 2026 session accidentally replaced it with "PLACEHOLDER", destroying all 133 tools. **ALWAYS use `patch` (mode='replace') for server.py.** If patch fails with escape-drift, re-read exact content with `read_file` and retry without backslash-escaping quotes.

### Recovery options (in priority order)

1. **`.pyc` string extraction** — `__pycache__/server.cpython-313.pyc` contains the last compiled bytecode (373KB, source size 345668 bytes). Extract all string constants (JS f-strings, docstrings, paths) via `marshal.load()`. The .pyc does NOT contain full source — only bytecode + constants — but 495 string constants >50 chars cover most JS f-string payloads. See `references/disaster-recovery.md` for the extraction script.
2. **TOOL_CATALOG.md + compaction summaries** — reconstruct tool signatures and JS patterns from the catalog (210 lines, survives) + session compaction summaries (full tool map with parameters and technical details).
3. **`git checkout -- server.py`** — ONLY works if the file is tracked. **As of July 2026, `opendaw-mcp/` has NO git repo** — this command fails with exit 128. Do not rely on this unless a repo is initialized.
4. **`debugfs` undelete** — requires sudo (not available on this system). Only viable with root access to the block device.

### Prevention

- **NEVER** use `write_file` on `server.py` — always `patch` with `mode='replace'`
- **Initialize a git repo** in `opendaw-mcp/` and commit after each session — this is the only reliable safety net
- The `.pyc` cache in `__pycache__/` is an accidental backup — do not clean it manually

## PITFALL: Vite node_modules/.bin symlinks vanish after rebases

After upstream syncs, `headless-daw/node_modules/.bin/vite` symlink may disappear while `node_modules/vite/bin/vite.js` still exists. Launch with `node node_modules/vite/bin/vite.js --port 5174`, NOT `node node_modules/.bin/vite`. Startup takes ~30s (pre-bundling). Vite may bind to IPv6 `[::1]:5174` — test with `curl -s http://[::1]:5174/`. Playwright bridge resolves `localhost` → `::1` correctly.

## PITFALL: Playwright Python page.evaluate() does NOT accept timeout kwarg

`page.evaluate(expression, timeout=30000)` raises `TypeError: Page.evaluate() got an unexpected keyword argument 'timeout'`. The correct approach is to call `page.set_default_timeout(timeout)` BEFORE `page.evaluate()`:

```python
# WRONG
result = await self.page.evaluate(wrapped, timeout=timeout)

# RIGHT
self.page.set_default_timeout(timeout)
result = await self.page.evaluate(wrapped)
```

## PITFALL: bridge.start() may hang when called via asyncio.run() from server.py

When `from server import bridge` is used and then `asyncio.run(bridge.start())` is called, the start method logs "DAW engine ready!" but never returns control. The same code in a standalone script (without importing server.py) works fine. Likely cause: `atexit.register(cleanup)` which calls `asyncio.run(bridge.stop())` interferes with the event loop, or FastMCP initialization does something that blocks.

**Workaround**: For testing, create a `SimpleBridge` class with the same `start()`/`evaluate()` methods but without the `atexit` registration or FastMCP dependency. Or run the MCP server directly (`python3 server.py`) instead of importing bridge in a test script.

## PITFALL: Empty catch(e) {} blocks missing in .pyc reconstruction

When reconstructing JS f-strings from .pyc bytecode, empty `catch(e) {}` blocks lose their inner braces. Fix with regex: `re.sub(r'catch\((e)\)\s*$', r'catch(\1) {{}}', text, flags=re.MULTILINE)`.

## Verified test (July 2026)

- Source: unit 1, track 0 with 2 NoteRegionBoxes (2 notes each)
- Move region 0 → unit 2, track 0: ✅ source has 1 region, dest has 1 region
- Delete track 0 from unit 1: ✅ remaining_tracks: 0
- Type mismatch check: note→audio track returns error ✅
- Direct index swap `t0.index.setValue(99)` → persists ✅, confirmed via sorted list re-read

# AudioUnit Freeze/Unfreeze — Session Notes (2026-07-03)

## Context

Found `AudioUnitFreeze` class in upstream `packages/studio/core/src/AudioUnitFreeze.ts` while auditing for uncovered API surfaces. `get_unit_freeze_status` tool already existed (read-only), but no action tools for freeze/unfreeze.

## Upstream API (`AudioUnitFreeze.ts`)

```typescript
class AudioUnitFreeze implements Terminable {
    isFrozen(auAdapter: AudioUnitBoxAdapter): boolean
    isFrozenUuid(uuid: UUID.Bytes): boolean
    hasSidechainDependents(auAdapter: AudioUnitBoxAdapter): boolean
    async freeze(auAdapter: AudioUnitBoxAdapter): Promise<void>
    unfreeze(auAdapter: AudioUnitBoxAdapter): void
    subscribe(observer: Observer<UUID.Bytes>): Subscription
    terminate(): void
}
```

### Key behaviors:
- `freeze()` is **async** — renders AU output via `OfflineEngineRenderer.start(copiedProject, Option.wrap(exportConfig), ...)` with `skipChannelStrip: true`. Caches as `AudioData` via `engine.setFrozenAudio(uuid, audioData)`.
- `unfreeze()` is **sync** — calls `engine.setFrozenAudio(uuid, null)` and removes from map.
- `hasSidechainDependents()` checks if any other AU's effects have outgoing edges to this AU's labeled audio outputs. If true → freeze blocks with "Cannot Freeze" message.
- **BPM/tempo automation changes unfreeze ALL** — constructor subscribes to `timelineBoxAdapter.box.bpm` and `catchupAndSubscribeTempoAutomation`, both call `#unfreezeAll()`.
- `freeze()` uses `RuntimeNotifier.progress()` for UI dialog — in headless mode this is a no-op (doesn't block, doesn't crash).

## MCP Tools Added

### `freeze_audiounit(unit_index: int)` (#210)
- Uses `async () => { await freeze.freeze(auAdapter); }` in bridge.evaluate
- Checks `hasSidechainDependents` before attempting freeze
- Returns `{success, frozen, unit_index}`

### `unfreeze_audiounit(unit_index: int)` (#211)
- Sync call: `freeze.unfreeze(auAdapter)`
- Checks `isFrozen` first — returns error if not frozen
- Returns `{success, was_frozen, frozen, unit_index}`

## E2E Test (2026-07-03)

```
setup: {unit_index: 0, type: 'instrument'}  # Vaporisateur
freeze_status: {frozen: False, can_freeze: True, label: 'Vaporisateur', is_instrument: True}
freeze_result: {success: True, frozen: True}
after_freeze: {frozen: True}
unfreeze_result: {success: True, was_frozen: True, frozen: False}
```

## Adapter Access Pattern

```javascript
const auAdapters = p.rootBoxAdapter.audioUnits.adapters();
const au = auAdapters[unit_index];  // AudioUnitBoxAdapter
freeze.isFrozen(au)      // → bool
freeze.freeze(au)        // → Promise<void> (async!)
freeze.unfreeze(au)      // → void (sync)
```

**Important**: freeze/unfreeze expect `AudioUnitBoxAdapter` (from `.adapters()`), NOT raw boxes from `pointerHub.incoming()`. The existing `get_unit_freeze_status` tool already used adapters correctly.

## CI Threshold Bump

`ci.yml`: `assert count >= 210` (was 208). 211 tools total.

## Files Modified

- `server.py`: +2 tools (freeze_audiounit, unfreeze_audiounit)
- `TOOL_CATALOG.md`: count 209→211, added freeze/unfreeze entries
- `README.md`: badge 209→211, body text, catalog ref
- `server.json`: description 209→211
- `.github/workflows/ci.yml`: threshold 208→210

## Commit

`a86dc4a` — feat: freeze/unfreeze audiounit tools (#210, #211) + docs update. CI ✅.

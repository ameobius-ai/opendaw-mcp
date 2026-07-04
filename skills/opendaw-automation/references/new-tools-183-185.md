# New Tools 183-185 — Metadata, Bus Control, CI Infrastructure

## Tools added

### get_project_metadata (183)
One-call project overview: creation date, time signature, AU count, track count, groove state.

**API path:** `RootBoxAdapter.created` (Date), `RootBoxAdapter.audioUnits.adapters()`, `RootBoxAdapter.timeline.signatureTrack.storageSignature`, `RootBoxAdapter.groove.enabled`.

**Access pattern:**
```js
const root = p.rootBoxAdapter;
const aus = root.audioUnits.adapters();
let trackCount = 0;
aus.forEach(au => { trackCount += au.tracks.collection.adapters().length; });
const sig = root.timeline.signatureTrack.storageSignature;
return {
    created: root.created.toISOString(),
    time_signature: [sig[0], sig[1]],
    audio_unit_count: aus.length,
    total_track_count: trackCount,
    groove_enabled: root.groove.enabled,
};
```

**Pitfall:** `p.rootBox.tempo` does NOT exist. BPM is accessed via the `get_tempo_at(0)` tool (VaryingTempoMap). Do NOT try `p.rootBox.tempo.getValue()` — it crashes with "Cannot read properties of undefined (reading 'getValue')".

**Pitfall:** `root.groove.enabled` may return `null` in some project states. The GrooveShuffleBoxAdapter has an `enabled` getter but it may not always resolve. Not critical — groove state is minor metadata.

### set_bus_label (184)
Renames an audio bus. Works on Output bus (index 0, always present) and custom buses.

**API path:** `AudioBusBoxAdapter.labelField` (StringField) — `bus.labelField.setValue(label)`.

**Access pattern:**
```js
const buses = p.rootBoxAdapter.audioBusses.adapters();
const bus = buses[busIndex];
p.editing.modify(() => { bus.labelField.setValue(label); });
```

**Note:** `p.rootBoxAdapter.audioBusses` is a `BoxAdapterCollection<AudioBusBoxAdapter>`, NOT `IndexedBoxAdapterCollection`. Use `.adapters()` for iteration.

**String escaping:** Use `json.dumps(label)` in Python to safely escape the label string for JS injection. Do NOT use raw f-string interpolation with user strings.

### set_bus_color (185)
Sets the color hue (0-360 HSL) of an audio bus.

**API path:** `AudioBusBoxAdapter.colorField` (StringField, but stores int hue 0-360).

**Access pattern:** Same as set_bus_label but with `bus.colorField.setValue(hue)`.

**Note:** The Output bus (index 0) is always present in a fresh project. Custom buses are created via `create_audio_bus`. Both support label and color.

## CI Infrastructure (GitHub Actions)

### Workflow file: `.github/workflows/ci.yml`

Runs on push/PR to main. Steps:
1. **Python syntax check** — `python -m py_compile server.py`
2. **AST tool count verification** — parses server.py, counts `mcp_opendaw_*` async functions, asserts ≥150
3. **DSP script validation** — checks all 6 scripts exist in `scripts/`
4. **Hardcoded path check** — greps for `/home/` in server.py, fails if found

**Key insight:** The AST tool count check is a regression guard — if tools are accidentally removed, CI catches it. The threshold (150) should be updated as the tool count grows.

### Additional files
- **CONTRIBUTING.md** — tool template, DAW_HELPERS reference, guidelines for contributors
- **examples/** — 5 example scripts showing typical usage patterns
- **GitHub topics** — mcp, ai-music, daw, opendaw, audio-production, model-context-protocol, playwright, music-production, agent-native, typescript

## Orchestration pattern

When user says "следуй" (follow), they mean: be fully autonomous. Self-resolve blockers, track in kanban, research proactively, create tasks, plan/implement/optimize. Do NOT wait for micro-approvals.

**Workflow:**
1. Check git status + AST tool count
2. Research uncovered upstream adapters (`packages/studio/adapters/src/`)
3. Write tools using DAW_HELPERS pattern
4. E2E test (start Vite → bridge → test → kill Vite)
5. Commit + push to GitHub
6. Update TOOL_CATALOG.md + README badge count
7. Verify CI passes
8. Update kanban tasks
9. Repeat — find next uncovered API or infrastructure gap

**Pitfall:** `hermes goal` command does NOT exist in current Hermes version. Cannot dispatch background workers via goal. Orchestrate from main session instead.

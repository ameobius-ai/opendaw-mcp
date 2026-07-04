# Adapter Coverage Audit — 2026-07-03

## Methodology

1. List all adapter classes: `grep -rn 'class.*Adapter.*{' packages/studio/adapters/src/ --include='*.ts' | grep -v '.test.' | grep -v 'dist/'`
2. Read each adapter's public getters and FieldAdapter properties
3. Cross-reference with `grep -n '<field_name>\|<getter_name>' server.py` to check MCP coverage
4. Focus on FieldAdapter getters — each is a potential setter tool (read via `.getValue()`, write via `.field.setValue()` inside `editing.modify()`)
5. Check RootBoxAdapter for root-level collections (e.g. `midiOutputDevices` was missed)
6. When upstream is static (no new commits), this is the primary way to find new tool opportunities

## Results

### Fully covered (no action needed)

| Adapter | Tools | Notes |
|---------|-------|-------|
| PianoModeAdapter | 6 | `set_transpose`, `get_piano_mode`, `set_piano_keyboard`, `set_piano_note_scale`, `set_piano_note_labels`, `set_piano_time_range`. All 5 FieldAdapter setters covered. |
| RootBoxAdapter | via multiple tools | `audioUnits`, `audioBusses`, `clips`, `groove`, `timeline`, `pianoMode`, `created` (in get_project_metadata), `midiOutputDevices` (list_midi_output_devices). |
| AudioBusBoxAdapter | 5+ | `enabled`, `color`, `label` covered. `icon` is cosmetic — skipped. `minimized` not covered (low priority). |
| SignatureTrackAdapter | 7+ | `toParts`, `getBarInterval`, `barLengthAt`, `signatureAt`, `changeSignature`, `createEvent`, `moveEvent`, `deleteAdapter` — all covered. |
| TimelineBoxAdapter | via multiple tools | `markerTrack`, `signatureTrack`, `tempoTrackEvents`, `signature`, `signatureDuration` — covered through tempo/signature/marker tools. |

### Remaining to audit (interrupted)

| Adapter | Status | Potential tools |
|---------|--------|----------------|
| FadingAdapter | Not yet read | `FadingEnvelope.Config` — fade curve parameters |
| TransientMarkerBoxAdapter | `list_transient_markers` exists (read-only) | No setters — transient markers are derived from audio analysis, not user-set |
| ValueEventCollectionBoxAdapter | Partially covered via automation tools | May have collection-level operations |
| GrooveShuffleBoxAdapter | 2 tools (amount, duration) | Check for additional fields |
| ParameterAdapterSet | Internal | Not a user-facing adapter |

## New tools added this audit (197 → 202)

1. `set_piano_keyboard(keyboard_type: int)` — 88/76/61/49, validated
2. `set_piano_note_scale(scale: float)` — 0.5–2.0 exponential
3. `set_piano_note_labels(show: bool)` — toggle
4. `set_piano_time_range(quarters: float)` — 1.0–64.0 exponential
5. `list_midi_output_devices()` — root-level MIDIOutputBox[] reader

## Upstream diff analysis (2026-07-03)

`git diff 39456de8..upstream/main -- packages/studio/` shows only:
- `DeviceBox.ts`: +2 lines (isChainEffectOf helper — internal)
- `ScriptDeclaration.test.ts`: +8 lines (test only)
- `PresetEncoder.playfield.test.ts`: +53 lines (test only)
- `DuplicateUnitGraftsRoot.test.ts`: +17 lines (test only)
- `riffle.ts`: +9 lines (UI renderer — waveform display, not API)
- `value.ts`: +14 lines (UI renderer — value display, not API)

**No new API surfaces.** Upstream changes are bugfixes, test additions, and UI rendering tweaks. ProjectApi.ts unchanged. No new adapter classes. No new public methods on existing adapters.

## Next audit priorities

1. FadingAdapter — read source, check if fade curve params are settable
2. ValueEventCollectionBoxAdapter — check for collection-level operations beyond individual event CRUD
3. GrooveShuffleBoxAdapter — verify all fields covered
4. AudioClipBoxAdapter — check for clip-level operations not yet covered
5. NoteEventCollectionBoxAdapter — check for collection-level operations

# DAW_HELPERS Refactoring Session E — 2026-07-03

## Scope
Continued DAW_HELPERS refactoring from 79/180 to 89/180 (49%). 4 new pre-existing bugs found and fixed. 3 new packages converted.

## Packages converted this session

### Package 16: Notes CRUD (4 tools)
- `duplicate_notes` — Quarter=960 hardcode fixed → h.ppqn.Quarter
- `list_notes` — Quarter=960 hardcode fixed → h.ppqn.Quarter
- `set_note_properties` — Quarter=960 hardcode fixed → h.ppqn.Quarter
- `delete_note` — no bugs, clean conversion
- Commit: `7de5fec`

### Package 17: Project info + compact + loop + export/render (8 tools)
- `get_project_info` — /960 hardcode × 2 fixed → h.ppqn.Quarter
- `compact_tracks` — clean conversion
- `set_region_loop` — PPQN=window.DAW_PPQN fixed → h.ppqn
- `export_midi` — PPQN hardcode fixed → h.ppqn
- `render_range` — PPQN hardcode fixed → h.ppqn, p.copy() → h.project.copy()
- `render_full` — p.copy() → h.project.copy()
- `export_stems` — p.copy() → h.project.copy(), UUID → h.uuid
- `export_single_stem` — p.copy() → h.project.copy(), UUID → h.uuid
- Commit: `3ac3105`

## New pre-existing bugs found (4)
20. `get_project_info` — hardcoded `/ 960` × 2 → `h.ppqn.Quarter`
21. `export_midi` — used `window.DAW_PPQN` → `h.ppqn`
22. `render_range` — used `window.DAW_PPQN` → `h.ppqn`
23. `set_region_loop` — used `window.DAW_PPQN` → `h.ppqn`

## E2E verification
- project_state ✅ (bpm=120, totalBoxes=8)
- create_synth ✅ (unit_index=1)
- add_effect ✅ (effect_index=0)
- create_note ✅
- list_note_regions ✅ (region_count=1, pos=0)
- set_effect_param with wrong field name → expected error (not a regression)

## Pattern: h.project.copy() for OfflineEngineRenderer
All render/export tools now use `h.project.copy()` instead of `p.copy()`. The `h.project` property in DAW_HELPERS is `p` (the DAW project object), so `h.project.copy()` is equivalent to `p.copy()`. This is critical because OfflineEngineRenderer requires a COPIED project, not the live one.

## Progress
- 180 → 91 tools with `const p = window.DAW;` (89 converted, 49%)
- 211 tools total, AST confirmed
- 17 packages completed across sessions C/D/E
- 23 pre-existing bugs found and fixed total

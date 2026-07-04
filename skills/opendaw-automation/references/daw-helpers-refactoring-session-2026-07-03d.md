# DAW_HELPERS Refactoring Session D (2026-07-03)

## Progress: 69 → 79 tools converted (111 → 101 remaining)

### Packages converted this session

**Package 11: Duplicate notes + list notes + set note props + delete note (4 tools)**
- `duplicate_notes` — `Quarter = 960` hardcode → `h.ppqn.Quarter`. `p.boxGraph` → `h.boxGraph`. `UUID.generate()` → `h.uuid.generate()`. `p.editing.modify` → `h.modify`.
- `list_notes` — `Quarter = 960` hardcode → `h.ppqn.Quarter`. `p.rootBox` → `h.rootBox`.
- `set_note_properties` — `Quarter = 960` hardcode → `h.ppqn.Quarter`. `p.editing.modify` → `h.modify`.
- `delete_note` — `p.rootBox` → `h.rootBox`. `p.editing.modify` → `h.modify`.
- Commit: `7de5fec`

**Package 12: Region CRUD (6 tools)**
- `delete_region` — `p.rootBox` → `h.rootBox`. `p.editing.modify` → `h.modify`.
- `set_region_position` — `window.DAW_PPQN` → `h.ppqn`. `p.editing.modify` → `h.modify`.
- `set_region_duration` — `window.DAW_PPQN` → `h.ppqn`. `p.editing.modify` → `h.modify`.
- `set_region_mute` — `p.rootBox` → `h.rootBox`. `p.editing.modify` → `h.modify`.
- `set_region_label` — `p.rootBox` → `h.rootBox`. `p.editing.modify` → `h.modify`.
- `set_region_color` — `p.rootBox` → `h.rootBox`. `p.editing.modify` → `h.modify`.
- Commit: `1e05e5f`

### New pre-existing bugs found (5 new, 19 total)

14. `duplicate_notes` — `Quarter = 960` hardcode
15. `list_notes` — `Quarter = 960` hardcode
16. `set_note_properties` — `Quarter = 960` hardcode
17. `set_region_position` — `window.DAW_PPQN` should be `h.ppqn`
18. `set_region_duration` — `window.DAW_PPQN` should be `h.ppqn`

### Pattern observed

The `Quarter = 960` hardcode is the most common pre-existing bug found during refactoring. It appears in tools that were written early (before DAW_HELPERS existed) and hardcoded the PPQN value. Every conversion should check for `960` and replace with `h.ppqn.Quarter`.

Similarly, `window.DAW_PPQN` / `window.DAW_UUID` are direct window globals that should be replaced with `h.ppqn` / `h.uuid` during conversion — they're already available through DAW_HELPERS.

### E2E verification

Tested via bridge with Vite on 5174:
- `get_project_state` ✅ (DAW_HELPERS, bpm=120, totalBoxes=8)
- `create_synth` ✅ (unit_index=1)
- `add_effect` ✅ (Delay, effect_index=0)
- `create_note` ✅ (C4, velocity=0.8)
- `list_note_regions` ✅ (region_count=1, pos=0)

### Remaining packages (101 tools)

Next targets:
- Clips, automation, export, render (~40 tools)
- Modular, scriptable, inspection helpers (~30 tools — inspection helpers already use DAW_HELPERS)
- Misc tools (~30 tools)

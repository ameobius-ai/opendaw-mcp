# DAW_HELPERS Mass Conversion — 2026-07-03 (final session)

## Summary

Converted remaining 91 tools from `const p = window.DAW;` to `const h = window.DAW_HELPERS;` in a single automated pass. Total: 83 full conversions + 5 partial (hybrid tools that already had `h` but still used `p`/`window.DAW.editing`). Commit: `0e280b0`.

## Auto-conversion script design

```python
# Key structure:
# 1. Split by @mcp.tool() decorator → per-tool chunks
# 2. For each chunk with 'const p = window.DAW;':
#    a. If chunk already has 'const h = window.DAW_HELPERS;' → partial: remove p line, redirect window.DAW.editing → h.editing, apply p.→h. replacements
#    b. If not → full: replace 'const p = window.DAW;' with 'const h = window.DAW_HELPERS;'
# 3. Replace window.DAW_UUID → h.uuid, window.DAW_PPQN → h.ppqn
# 4. Replace 'const Quarter = 960;' → 'const Quarter = h.ppqn.Quarter;'
# 5. Replace AU list boilerplate with h.allAUs() (SEE PITFALL #2)
# 6. Apply P_TO_H_REPLACEMENTS (longest first to avoid prefix conflicts)
# 7. Replace /960 and *960 hardcodes (SEE PITFALL #1)
```

## P_TO_H replacement order (critical — longest first)

```python
P_TO_H_REPLACEMENTS = [
    ('p.rootBoxAdapter', 'h.rootBoxAdapter'),      # before p.rootBox
    ('p.rootBox', 'h.rootBox'),
    ('p.editing', 'h.editing'),
    ('p.boxGraph', 'h.boxGraph'),
    ('p.audioUnitFreeze', 'h.audioUnitFreeze'),
    ('p.tempoMap', 'h.tempoMap'),
    ('p.primaryAudioUnitBox', 'h.primaryAudioUnitBox'),
    ('p.primaryAudioBusBox', 'h.primaryAudioBusBox'),
    ('p.timelineBox', 'h.timelineBox'),
    ('p.engine', 'h.engine'),
    ('p.api', 'h.api'),
    ('p.boxAdapters', 'h.project.boxAdapters'),    # boxAdapters is on project, not rootBoxAdapter
    ('p.copy()', 'h.project.copy()'),
    ('p.toArrayBuffer()', 'h.project.toArrayBuffer()'),
    ('p.invalid()', 'h.project.invalid()'),
    ('p.collectSampleUUIDs', 'h.project.collectSampleUUIDs'),
    ('p.lastRegionAction', 'h.project.lastRegionAction'),
    ('p.project.boxGraph', 'h.boxGraph'),          # already covered by p.boxGraph above
    ('p.NoteEventBoxAdapter', 'h.project.NoteEventBoxAdapter'),
    ('p.ValueEventBoxAdapter', 'h.project.ValueEventBoxAdapter'),
    ('p.project', 'h.project'),                    # catch-all last
]
```

## Verification commands after conversion

```bash
# 1. Syntax check
python3 -c "import py_compile; py_compile.compile('server.py', doraise=True)"

# 2. Tool count (must stay 211)
python3 -c "import ast; tree=ast.parse(open('server.py').read()); tools=[n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name.startswith('mcp_opendaw_')]; print(f'OK: {len(tools)} tools')"

# 3. Remaining p references (must be 1 — DAW_HELPERS definition only)
grep -c 'const p = window.DAW;' server.py   # → 1

# 4. No .Quarter.0 artifacts
grep -n 'Quarter\.0' server.py              # → 0 results

# 5. No window.DAW.editing outside DAW_HELPERS
grep -n 'window\.DAW\.editing' server.py    # → 0 results
```

## E2E test (post-conversion)

Run 20 representative tools across all categories:
```python
tests = [
    ('project_state', get_project_state),
    ('create_synth', create_synth_track("Test","vaporisateur")),
    ('add_effect', add_effect(0,"Delay")),
    ('list_effect_params', list_effect_parameters(0,0)),
    ('create_note', create_note(0,60,0,4,0.8,1)),  # track_index FIRST, unit_index LAST
    ('list_notes', list_notes(1,0,0)),
    ('list_note_regions', list_note_regions(1,0)),
    ('set_bpm', set_bpm(140.0)),
    ('set_track_volume', set_track_volume(1,-3.0)),
    ('get_mixer_state', get_mixer_state()),
    ('undo', undo()),
    ('add_marker', add_marker(4,"Verse")),
    ('list_markers', list_markers()),
    ('get_full_project_state', get_full_project_state()),
    ('get_track_info', get_track_info(1,0)),       # NOTE: fails if undo ran before
    ('get_region_info', get_region_info(1,0,0)),   # NOTE: fails if undo ran before
    ('set_position', set_position(0)),
    ('set_time_signature', set_time_signature(4,4)),
    ('get_project_duration', get_project_duration()),
    ('serialize', serialize()),
]
```

Expected: 17+ pass. `get_track_info`/`get_region_info` fail if `undo` deleted tracks. `get_project_duration` fails if `.Quarter.0` bug present.

## Commit message

```
refactor: complete DAW_HELPERS conversion — 91 tools migrated to h.* pattern

Full conversion: 83 tools (const p = window.DAW → const h = window.DAW_HELPERS)
Partial conversion: 5 tools (window.DAW.editing → h.modify)
Fixed: 5 /960.0 hardcoded → h.ppqn.Quarter in JS code
Fixed: window.DAW.editing.modify → h.modify in hybrid tools
Removed: all p.rootBox, p.api, p.editing, p.boxGraph boilerplate
Pattern: h.allAUs(), h.track(), h.region(), h.modify(), h.ppqn, h.uuid
Result: 0 remaining 'const p = window.DAW;' outside DAW_HELPERS definition
```

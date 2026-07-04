# MIDI Velocity + Parameter Type Audit (2026-07-03)

## MIDI Export Velocity Bug

**Symptom**: All MIDI-exported notes had near-zero velocity (MIDI vel 1 instead of 127).

**Root cause**: `export_midi` used:
```js
const vel = Math.round(note.velocity.getValue() * 127 / 100);
```
openDAW velocity is **0..1 float** (default 0.7874015748031497), not 0..100.
The `/ 100` divisor made all velocities ~1.

**Fix**:
```js
const vel = Math.round(note.velocity.getValue() * 127);
```

**E2E verification** — 3 notes with different velocities:
| openDAW velocity | MIDI velocity (before fix) | MIDI velocity (after fix) |
|-----------------|---------------------------|--------------------------|
| 1.0             | 1                         | 127                      |
| 0.5             | 0                         | 64                       |
| 0.787           | 1                         | 100                      |

## Import MIDI offset_beats String Bug

**Symptom**: `import_midi` with non-integer `offset_beats` (e.g. "4.5") produced garbage.

**Root cause**:
```python
offset_ticks = int(offset_beats * 960)  # "4.5" * 960 = "4.54.54.5..." (string repetition)
```

**Fix**:
```python
offset_ticks = int(float(offset_beats) * 960)
```

## Parameter Type Audit

Systematic audit of all `def mcp_opendaw_*` signatures. FastMCP auto-converts based on
declared types — wrong types cause SILENT truncation.

### Audit method
1. `grep -n "def mcp_opendaw_" server.py` — list all tool signatures
2. For each parameter, cross-reference with openDAW adapter source:
   - `grep -n "field.*Float32Field\|field.*Int32Field\|field.*BooleanField" packages/studio/boxes/src/*.ts`
3. Float fields (velocity, pan, mix, gain, fade, slope, curve) → `float`
4. Index/count fields → `int`
5. Label/name/equation fields → `str`
6. `str` params used in f-string arithmetic → MUST wrap with `float()` or change type

### Fixes applied

| Tool | Parameter | Before | After | Reason |
|------|-----------|--------|-------|--------|
| `create_note` | `start_beat` | `int` | `float` | Beats can be fractional (e.g. 0.5) |
| `create_note` | `duration_beats` | `int` | `float` | Same |
| `create_note` | `velocity` | `int` | `float` | openDAW velocity is 0..1 float |
| `set_note_properties` | `position_beats` | `int` | `float` | Fractional beats |
| `set_note_properties` | `duration_beats` | `int` | `float` | Same |
| `set_note_properties` | `velocity` | `int` | `float` | 0..1 float |
| `set_note_advanced` | `play_curve` | `int` | `float` | -1..+1 float range |
| `set_send_level` | `src_unit` | `str` | `int` | Index |
| `set_send_level` | `send_index` | `str` | `int` | Index |
| `set_send_level` | `level_db` | `str` | `float` | dB value |
| `set_send_routing` | `send_index` | `str` | `int` | Index |
| `set_send_pan` | `send_index` | `str` | `int` | Index |
| `set_bus_enabled` | `bus_index` | `str` | `int` | Index |
| `set_track_volume` | `volume_db` | `str` | `float` | dB value, removed redundant `float()` wrapper |

### Mass type fix batch (37 params, 25+ functions, 2026-07-03)

Systematic grep of ALL `str`-typed params with numeric-suggesting names:
```python
import ast
for node in ast.walk(tree):
    if isinstance(node, ast.AsyncFunctionDef) and node.name.startswith('mcp_opendaw_'):
        for arg in node.args.args:
            if arg.annotation and isinstance(arg.annotation, ast.Name) and arg.annotation.id == 'str':
                name = arg.arg
                numeric_hints = ['index','level','volume','pan','gain','db','bpm','beat','position',
                                 'duration','pitch','velocity','threshold','rate','speed','offset',
                                 'size','count','hue','color','freq','oct','tune','slope','cents',
                                 'loop','from','to','source','target','fx','send','osc','param','event']
                if any(h in name.lower() for h in numeric_hints):
                    print(f'  {node.name}:{name}')
```

Additional fixes beyond the first table:

| Tool | Parameter | Before | After |
|------|-----------|--------|-------|
| `set_track_panning` | `panning` | `str` | `float` |
| `move_effect` | `from_index`, `to_index` | `str` | `int` |
| `create_send` | `send_level_db` | `str` | `float` |
| `remove_send` | `send_index` | `str` | `int` |
| `remove_audio_bus` | `bus_index`, `fx_unit_index` | `str` | `int` |
| `set_vaporisateur_osc_param` | `osc_index` | `str` | `int` |
| `set_midi_effect_param` | `param_index` | `str` | `int` |
| `create_playfield_sample` | `duration_seconds` | `str` | `float` |
| `import_midi` | `offset_beats` | `str` | `float` |
| `duplicate_note_region` | `offset_beats` | `str` | `float` |
| `transpose_notes` | `semitones` | `str` | `int` |
| `set_region_color` | `hue` | `str` | `int` |
| `set_clip_playback` | `speed` | `str` | `float` |
| `set_clip_properties` | `hue` | `str` | `int` |
| `connect_sidechain` | `source_unit_index`, `target_unit_index` | `str` | `int` |
| `auto_gain` | `target_lufs` | `str` | `float` |
| `create_time_stretched_region` | `playback_rate` | `str` | `float` |
| `create_time_stretched_clip` | `playback_rate` | `str` | `float` |
| `create_note_clip` | `hue` | `str` | `int` |
| `create_track_region` | `hue` | `str` | `int` |
| `set_region_loop` | `loop_beats`, `loop_offset_beats`, `event_offset_beats` | `str` | `float` |

**Total: 37 parameters across 25+ tool functions.**

**E2E verified**: `set_track_volume(-6.0)`→-6 ✅, `set_track_panning(0.5)`→0.5 ✅,
`transpose_notes(semitones=5)`→pitches 60→65, 64→69 ✅, velocities preserved (0.8, 0.6) ✅

### Remaining `str` params that are CORRECT
- `set_effect_parameter_string` — `value: str` (equation names like "tanh")
- `set_send_routing` — `routing: str` ("pre"/"post")
- `cent: str` / `chance: str` in `set_note_properties` — sentinel "-1" check works with str
- `synth_type: str` / `name: str` / `label: str` / `filename: str` — genuine strings

### Pitfall: str params in f-string arithmetic
```python
# WRONG — string multiplication if offset_beats is str
offset_ticks = int(offset_beats * 960)

# ALSO WRONG — works for integers but breaks for decimals
offset_ticks = int(float(offset_beats) * 960)  # This is correct

# BEST — declare as float in signature
async def mcp_opendaw_import_midi(..., offset_beats: float, ...):
```

### Rule
If a parameter is used in ANY arithmetic operation (`*`, `/`, `+`, `-`),
it MUST be `int` or `float` in the Python signature, never `str`.
If backward compat requires `str`, ALWAYS wrap with `float()` before arithmetic.

## openDAW field value ranges (reference)

| Field | Type | Range | Default |
|-------|------|-------|---------|
| velocity | Float32Field | 0..1 | 0.787 |
| chance | Int32Field | 0..100 | 100 |
| cent | Float32Field | -50..+50 | 0 |
| playCount | Int32Field | 1..16 | 1 |
| playCurve | Float32Field | -1..+1 | 0 |
| pitch | Int32Field | 0..127 | 60 (C4) |
| pan | Float32Field | -1..+1 | 0 |
| mix | Float32Field | 0..1 | varies |
| hue | Int32Field | 0..360 or -1 | -1 |

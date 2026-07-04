# .pyc→source Reconstruction Artifacts — Catalog & Fixes

When server.py was reconstructed from `server.cpython-313.pyc` (bytecode disassembly), several classes of bugs emerged. This file catalogs each artifact type, how to detect it, and the fix pattern.

**Status (July 2026): ALL 11 artifact classes FIXED.** 130/132 JS f-strings pass `node --check` (2 remaining are runtime-evaluated false positives). E2E workflow 25/25 PASS: synth creation, 3 notes, transpose, quantize, effect chain (add/list/set/move/disable), transport, volume/pan/rename, markers, groove, undo/redo, save, project_info.

## Artifact 1: `const X = ;` — Missing boolean/string interpolation

### Cause
`.pyc` bytecode stores string constants and `FORMAT_SIMPLE` opcodes. When a boolean argument (`enabled`, `mute`, `find_free_space`) was interpolated via `{enabled}`, the reconstruction script sometimes failed to emit the `FORMAT_SIMPLE` segment, producing `const enableVal = ;` (empty RHS).

### Detection
```bash
grep -n '= ;' server.py
```

### Fix pattern
Replace `= ;` with `= {json.dumps(varname)};` where `varname` is the Python parameter. Use `json.dumps()` not raw f-string interpolation — handles booleans (`true`/`false` → JS), strings (quotes), and escaping.

### Sites fixed (6 total)
- `set_bus_enabled` → `enableVal = {json.dumps(enabled)}`
- `set_playfield_sample_enabled` → `enabledVal = {json.dumps(enabled)}`
- `set_region_mute` → `muteVal = {json.dumps(mute)}`
- `set_effect_enabled` → `enabled = {json.dumps(enabled)}`
- `duplicate_region` → `findFree = {json.dumps(find_free_space)}`
- `set_script_param` → `targetLabel = {json.dumps(param_label)}`

## Artifact 2: `const device = ;` — Missing entire JS block

### Cause
Scriptable device tools all had `const device = ;` — the entire device-finding JS was lost. The `_find_script_device_js` helper was `pass` (TODO) in the .pyc.

### Fix pattern
Replace `const device = ;` with inline JS that finds the device by type:

```javascript
const allAU = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({box}) => box);
const au = allAU[{unit_index}];
if (!au) return {error: "Unit {unit_index} not found"};
let device = null;
const dt = "{device_type}";
if (dt === "werkstatt") {
    const fx = [...au.audioEffects.pointerHub.incoming()].map(({box}) => box);
    device = fx[{device_index}] || null;
} else if (dt === "spielwerk") {
    const me = au.midiEffects ? [...au.midiEffects.pointerHub.incoming()].map(({box}) => box) : [];
    device = me[{device_index}] || null;
} else if (dt === "apparat") {
    const inp = au.input ? au.input.targetVertex.unwrapOrNull() : null;
    device = inp;
}
```

### Device type mapping
- **werkstatt** → audio effect (in `au.audioEffects`)
- **spielwerk** → MIDI effect (in `au.midiEffects`, field 21)
- **apparat** → instrument (in `au.input.targetVertex`)

### Sites fixed (5 total)
`set_script_device_code`, `get_script_device_code`, `list_script_params`, `set_script_param`, `list_script_samples`

## Artifact 3: `{{var}}` — Double-braced Python interpolation (MAJOR — 36 sites)

### Cause
The reconstruction script doubled ALL braces `{`→`{{` and `}`→`}}` for JS safety, but failed to un-double Python interpolations that should be single-braced `{var}`. This affected **36 sites** across ~25 functions.

### Detection (systematic scan)
```python
import re, ast

with open('server.py') as f:
    lines = f.readlines()
for i, line in enumerate(lines, 1):
    matches = re.findall(r'\{\{([a-z_][a-z0-9_]*)\}\}', line)
    for m in matches:
        if m != 'box':
            print(f'L{i}: {{{{{m}}}}} | {line.strip()[:80]}')
```

### Fix approach (automated batch)
1. Replace ALL `{{varname}}` → `{varname}` in the file (simple string replace)
2. For each affected function, add `varname = <expression>` before the f-string

### Variable mapping (which Python expression each var needs)
| Pattern | Expression | Example |
|---------|-----------|---------|
| `safe_label` | `label.replace('"', '').replace("'", '').replace('\\', '')` | add_marker, set_marker_label, set_region_label |
| `safe_param` | `param_name.replace('"', '').replace("'", '').replace('\\', '')` | set_midi_effect_param, set_vaporisateur_osc_param, set_instrument_param |
| `safe_value` | `string_value.replace(...)` | set_effect_parameter_string |
| `safe_mode` | `transient_mode.replace(...)` | create_time_stretched_clip |
| `mute_val` | `json.dumps(mute)` | set_track_mute, set_clip_properties |
| `solo_val` | `json.dumps(solo)` | set_track_solo |
| `loop_val` / `reverse_val` / `speed_val` | `json.dumps(loop/reverse/speed)` | set_clip_playback |
| `interp_val` | `json.dumps(interpolation)` | add_tempo_change |
| `routing_val` | `json.dumps(routing)` | create_send, set_send_routing |
| `pan_val` | `json.dumps(pan)` | set_send_pan |
| `name_val` / `icon_val` | `json.dumps(name/icon)` | rename_unit |
| `type_val` | `json.dumps(region_type)` | delete_region |
| `clip_idx` | `clip_index` | create_value_clip |
| `grid_ticks` | `int(division * 960 / 4)` | quantize_notes (PPQN.Quarter=960) |
| `ppqn` | `960` | import_midi |
| `offset_ticks` | `int(offset_beats * 960)` | import_midi |
| `notes_json` | `json.dumps(notes_data)` (needs MIDI parser) | import_midi |
| `points_js` | `json.dumps(points)` | add_automation |
| `stems_js` | `json.dumps(stems_list)` (needs AU query) | export_stems |
| `stems_config` | `json.dumps([unit_index])` | export_single_stem |
| `b64_data` | `base64.b64encode(open(filepath,'rb').read()).decode()` | load_project |
| `fname` | `name.replace(...)` | load_audio |
| `factory_key` | `synth_type.capitalize()` | create_synth_track |
| `code_json` | `json.dumps(code)` | set_script_device_code |

## Artifact 4: `\n` in f-strings → real newline (CRITICAL — breaks JS)

### Cause
Python f-strings interpret `\n` as a real newline character. When JS string literals or regex patterns contain `\n` (e.g., `code.split('\n')` or `RegExp('...\\n')`), the f-string emits an actual newline into the JS source, causing `SyntaxError: Invalid or unexpected token`.

### Detection
```python
# Check generated JS with node --check
result = eval(f'f"""{fstring_content}"""')
with open('/tmp/test.js', 'w') as f: f.write(result)
subprocess.run(['node', '--check', '/tmp/test.js'])
```

### Fix pattern
In f-strings, `\n` that should be a JS escape must be `\\n` in Python source (→ `\n` in JS):
```python
# BROKEN (f-string turns \n into real newline):
const header = '// @' + headerTag + ' js 1 ' + newUpdate + '\n';
const headerPattern = new RegExp('^// @' + headerTag + ' \w+ \d+ \d+\n');
const header = code.split('\n')[0];

# FIXED (double backslash → JS sees \n escape):
const header = '// @' + headerTag + ' js 1 ' + newUpdate + '\\n';
const headerPattern = new RegExp('^// @' + headerTag + ' \w+ \d+ \d+\\n');
const header = code.split('\\n')[0];
```

### Sites fixed
- `set_script_device_code`: header string `\n` → `\\n` in JS string literal
- `set_script_device_code`: headerPattern regex `\n` → `\\n`
- `get_script_device_code`: `code.split('\n')` → `code.split('\\n')`

### Key insight
`\w`, `\d`, `\/` in f-strings generate SyntaxWarnings but work correctly (Python passes them through as literal `\w` etc). Only `\n` is dangerous because Python interprets it as a real newline.

## Artifact 5: Missing `success: true` in return statements

### Cause
Reconstruction sometimes dropped `success: true` from JS return objects, causing MCP consumers that check `r.get('success')` to fail.

### Fix
Add `success: true,` to return objects in mutating tools (set/mute/solo/panning etc).

### Sites fixed
- `set_track_mute`, `set_track_solo`, `set_track_panning`

## Artifact 6: Missing Python computations before f-strings

### Cause
Some functions had Python-side computations (MIDI parsing, file reading, base64 encoding, AU queries) that were entirely lost during reconstruction. The f-strings referenced variables that didn't exist.

### Sites fixed
- **import_midi**: Added `mido.MidiFile()` parser → `notes_data` list of `{pitch, velocity, start_tick}`
- **export_stems**: Added `bridge.evaluate()` query for instrument AUs → `stems_list` of unit indices
- **load_project**: Added `base64.b64encode(open(filepath,'rb').read())` → `b64_data`

## Artifact 7: `set_track_volume` — `{{raw}}` and `.6f` fragments

### Cause
Reconstruction produced `au.volume.setValue({{raw}});` (double-braced) and `raw_value: .6f` (truncated format spec).

### Fix
Replaced with JS-side volume mapping using `valueMapper.mapToNormalized(volDb)`:
```javascript
const volDb = {vol_db};
let raw = volDb;
try {
    const c = au.volume.constraints;
    if (c?.valueMapper) raw = c.valueMapper.mapToNormalized(volDb);
    else if (c?.mapper) raw = c.mapper.mapToNormalized(volDb);
} catch(e) {}
```
Added `vol_db = float(volume_db)` in Python before the f-string.

## Testing recovered tools

### Smoke test pattern
```python
import asyncio, json, logging
logging.basicConfig(level=logging.INFO)
import server

async def smoke():
    await server.bridge.start()
    results = []
    tests = [
        ('get_project_state', lambda: server.mcp_opendaw_get_project_state()),
        ('set_bpm', lambda: server.mcp_opendaw_set_bpm(bpm=110)),
        ('create_synth_track', lambda: server.mcp_opendaw_create_synth_track(name='T', synth_type='vaporisateur')),
        # ... more ...
    ]
    for name, fn in tests:
        try:
            r = json.loads(await fn())
            ok = r.get('success') or any(k in r for k in ['bpm','units','audio','parameters'])
            results.append((name, ok and not r.get('error'), str(r)[:90]))
        except Exception as e:
            results.append((name, False, str(e)[:80]))
    await server.bridge.stop()
    passed = sum(1 for _,ok,*_ in results if ok)
    print(f'{passed}/{len(results)} passed')

asyncio.run(smoke())
```

### Results progression
- After initial recovery: 5/12 passed
- After Artifact 1-3 fixes: 10/14 passed
- After all fixes: 25/31 passed, scriptable devices 7/7 ✅
- After Artifact 8-9 fixes: 129/131 JS syntax OK, E2E core workflow passing
- After Artifact 10-11 fixes + TODO removal: **130/132 JS OK (0 FAIL), E2E 25/25 PASS**

### Clean E2E workflow test (reproducible)
```python
# Order matters — create resources before testing operations on them:
# 1. get_project_state (fresh)
# 2. create_synth_track(name='Lead', synth_type='vaporisateur') → unit_index=1
# 3. add_effect(unit_index=1, effect_type='Delay') → effect_index=0
# 4. list_effect_parameters → discover param names (delayMusical, feedback, cross, filter, wet)
# 5. set_effect_parameter(unit_index=1, effect_index=0, parameter_name='feedback', value=0.4)
# 6. set_track_volume(unit_index=1, volume_db='-3.0')
# 7. rename_unit(unit_index=1, name='MyLead', icon='Piano')
# 8. list_vaporisateur_params(unit_index=1) → oscillators, LFO, noise, main_params
# 9. transport(action='play') then transport(action='stop')
# 10. save_project(filename='test_project')
```

### Key finding: bridge.start() works via import
```python
import server  # imports fine, atexit registered
asyncio.run(server.bridge.start())  # works, returns normally
result = await server.bridge.evaluate('() => 42')  # returns 42
await server.bridge.stop()
```
Previous sessions thought `bridge.start()` hangs — FALSE. Hangs were in broken test scripts with `atexit` conflicts.

### Vite launch (headless-daw)
```bash
# .bin/vite symlink may be missing — use direct path:
cd headless-daw && node node_modules/vite/bin/vite.js --port 5174
# Vite listens on [::1]:5174 (IPv6), not 127.0.0.1
# Chromium resolves localhost → ::1, so DAW_URL="http://localhost:5174" works
```

## Artifact 8: Truncated/mixed f-string bodies (2 functions rewritten from scratch)

### Cause
`load_audio` and `move_region_to_track` had their f-string bodies severely mangled during reconstruction — chunks of two different code paths were interleaved, beginnings and ends were cut off, producing JS that started with `",` or `];` (SyntaxError on line 1).

### Detection
```bash
# All f-strings validated with node --check:
# 129/131 OK, 0 FAIL after fixes
```

### Fix: full rewrite
Both functions were rewritten from scratch using known openDAW APIs:

**load_audio** — reads file in Python, base64-encodes, sends to JS for `decodeAudioData`:
```python
import base64 as b64mod
with open(file_path, 'rb') as f:
    audio_b64 = b64mod.b64encode(f.read()).decode('ascii')
# JS: atob → Uint8Array → audioCtx.decodeAudioData → store in DAW_localAudioBuffers
```

**move_region_to_track** — finds source/dest tracks, checks type compatibility, re-references region:
```javascript
region.regions.refer(dstTrack.regions);  // inside editing.modify()
```

## Artifact 9: Missing interpolations in return statements (3 sites)

### Cause
Reconstruction dropped interpolation values from JS return objects, producing `enabled: ,` or `label: ,` (empty RHS in object literal).

### Sites fixed
- `set_loop_region`: `enabled: ,` → `enabled: {json.dumps(enabled)}` AND `loop.enabled.setValue()` → `loop.enabled.setValue({json.dumps(enabled)})`
- `auto_gain`: `Math.abs(.2f)` → `Math.abs({target_lufs})` (truncated format spec)
- `create_audio_bus`: `label: ,` → `label: "{name}"`

## Artifact 10: `uuid() =>` — Wrong function wrapper in f-string

### Cause
`export_stems` had its second `bridge.evaluate(f"""uuid() => {{...}}""")` — the `uuid()` prefix is invalid JS (not a valid arrow function parameter pattern). Reconstruction garbled the opening of the f-string.

### Fix
Replace `uuid() =>` with `async () =>` (standard async arrow function wrapper).

### Site fixed (1)
- `export_stems` second evaluate call

## Artifact 11: `num_stems: ,` and `quantize_notes` str/int type mismatch

### Cause
Two distinct issues:
1. `export_stems` return object had `num_stems: ,` (empty RHS — same pattern as Artifact 9)
2. `quantize_notes` had `grid_ticks = int(division * 960 / 4)` but `division` is typed `str` — `str * int` raises `TypeError`

### Fix
1. `num_stems: ,` → `num_stems: stemsConfig.length` (JS-side count)
2. `int(division * 960 / 4)` → `int(float(division) * 960 / 4)` (parse str to float first)

### Sites fixed (2)
- `export_stems`: `num_stems: stemsConfig.length`
- `quantize_notes`: `int(float(division) * 960 / 4)`

## What was NOT a reconstruction artifact (test errors)

These were initially flagged as bugs but were actually test script errors:
- **`add_effect('delay')`** — factory key is `Delay` (PascalCase), not `delay`. The tool docstring already lists correct names.
- **`list_effects(unit_index=1)`** — function takes NO arguments. Test passed wrong args.
- **`set_effect_parameter('time', ...)`** — Delay parameters are `delayMusical`, `feedback`, etc. Use `list_effect_parameters` to discover names first.

## JS syntax validation pattern (systematic)

To validate ALL 131 f-strings at once:
```python
import ast, subprocess, tempfile, os, json

with open('server.py') as f:
    src = f.read()
tree = ast.parse(src)
lines = src.split('\n')

for node in ast.walk(tree):
    if not isinstance(node, ast.AsyncFunctionDef): continue
    if not node.name.startswith('mcp_opendaw_'): continue
    # Extract f-string content, eval with test locals, node --check
    # See references/reconstruction-artifacts.md for full script
```
Result: 129 OK, 0 FAIL, 2 EVAL_ERR (false positives — variables computed at runtime).

## Remaining work

1. **TODO helpers REMOVED**: `_export_offline`, `_export_realtime` were `pass` stubs in original .pyc — never implemented, never called. Removed as dead code. Export functions (`export_mix`, `export_stems`, `render_range`, `export_single_stem`) have inline JS and work independently.
2. **SyntaxWarnings FIXED (July 2026)**: `\w`, `\/` in regex strings inside Python f-strings triggered SyntaxWarnings. Fixed by converting `f"""` → `rf"""` (raw f-string) on `set_script_device_code` and `get_script_device_code`. Raw f-strings preserve `\\w` as literal `\\w` (2 chars) — same JS output, no Python warning. `py_compile` now reports 0 SyntaxWarnings.
3. **Git initialized (July 2026)**: `git init` in opendaw-mcp/, 3 commits. `.gitignore` excludes `__pycache__/`, `*.pyc`, `server.py.backup*`, `server.py.final*`, `server_recovered.py`, `venv/`, `.env`. Backups no longer needed — version controlled.
4. **PR #280**: approved by andremichelle, awaiting merge.

## Artifact 12: `rf"""` for SyntaxWarnings (Python 3.12+)

### Cause
Python 3.12+ emits `SyntaxWarning: invalid escape sequence '\w'` for `\w`, `\/`, `\d` in non-raw strings. These appear in JS regex patterns inside f-strings (e.g., `new RegExp('^// @' + headerTag + ' \\w+ \\d+ \\d+\\\\n')`).

### Detection
```bash
python3 -W all -c "import py_compile; py_compile.compile('server.py', doraise=True)"
```

### Fix
Convert `f"""` → `rf"""` (raw f-string) on affected functions. Raw f-strings preserve backslash sequences literally — `\\w` stays `\\w` (2 chars) instead of being interpreted. JS output is identical; only the Python warning disappears.

### Key insight
`\\w` in a normal f-string and `\\w` in a raw f-string produce the SAME string (`\\w`, 2 chars). The difference is purely cosmetic — Python stops warning. Functionally identical.

### Sites fixed (2)
- `set_script_device_code`: `f"""` → `rf"""`
- `get_script_device_code`: `f"""` → `rf"""`

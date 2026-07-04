# Testing Procedures — openDAW MCP Server

## 1. JS Syntax Validation (ALL f-strings)

Validates every `bridge.evaluate(f"""...""")`  f-string in server.py by extracting it, interpolating test locals, and running `node --check`.

```python
import ast, subprocess, tempfile, os, json, re

with open('server.py') as f:
    src = f.read()
tree = ast.parse(src)
lines = src.split('\n')

ok = fail = err = 0
fails = []
for node in ast.walk(tree):
    if not isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)): continue
    if not node.name.startswith('mcp_opendaw_'): continue
    func_lines = lines[node.lineno-1:node.end_lineno]
    func_src = '\n'.join(func_lines)
    
    search_from = 0
    start_marker = 'bridge.evaluate(f"""'
    while True:
        start_idx = func_src.find(start_marker, search_from)
        if start_idx < 0: break
        start_idx += len(start_marker)
        end_idx = func_src.find('""")', start_idx)
        if end_idx < 0: break
        fstring_content = func_src[start_idx:end_idx]
        search_from = end_idx + 4
        
        args = [a.arg for a in node.args.args]
        local_ctx = {a: 1 for a in args}
        for child in ast.walk(node):
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Name) and target.id not in local_ctx:
                        try:
                            val = eval(compile(ast.Expression(child.value), '<s>', 'eval'),
                                      {'json': json}, local_ctx)
                            local_ctx[target.id] = val
                        except: local_ctx[target.id] = "test"
        try:
            js_code = eval(f'f"""{fstring_content}"""', {'json': json}, local_ctx)
            with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as tmp:
                tmp.write(js_code); tmp_path = tmp.name
            r = subprocess.run(['node', '--check', tmp_path], capture_output=True, text=True, timeout=5)
            os.unlink(tmp_path)
            if r.returncode == 0: ok += 1
            else:
                fail += 1
                fails.append(f"{node.name}: {r.stderr.strip().split(chr(10))[0][:80]}")
        except Exception as e:
            err += 1  # false positives — runtime-computed vars

print(f"JS: {ok} OK, {fail} FAIL, {err} EVAL_ERR")
```

**Expected result**: ~170 OK, 0 FAIL, 2 EVAL_ERR (false positives: `add_automation`/`points_js`, `create_value_clip`/`safe_name` — computed at runtime). Count grows as tools are added.

## 2. E2E Workflow Test (25 steps, full pipeline)

Creates a project from scratch: synth → effects → notes → transpose → quantize → params → transport → mix → markers → undo/redo → save.

**Prerequisites**: Vite running on 5174, venv activated, `PYTHONPATH=.`

```bash
cd /home/ameobius/projects/creative-studio/agent-daw/opendaw-mcp
source venv/bin/activate
# Start Vite if not running:
# cd headless-daw && node node_modules/vite/bin/vite.js --port 5174 &
```

Template at `templates/e2e_test.py`. Copy and run:
```bash
PYTHONPATH=. python3 /tmp/e2e_test.py
```

**Expected**: 25/25 PASS

### Key parameter gotchas (NOT bugs — correct API signatures)
- `create_note(track_index=, pitch=, start_beat=, duration_beats=, velocity=, unit_index=)` — NOT `region_index`
- `transpose_notes(semitones="12", unit_index=, track_index=)` — `str` type, NO `region_index`
- `quantize_notes(division="0.25", unit_index=, track_index=, strength="1.0")` — `str` types
- `add_effect(effect_type="Delay")` — PascalCase factory keys (Delay, Reverb, Compressor, etc.)
- `list_effects()` — NO arguments
- `set_effect_parameter(parameter_name="feedback")` — discover names via `list_effect_parameters` first

## 3. Scriptable Device Test (7 steps)

Tests Apparat/Werkstatt/Spielwerk code compilation, parameter management, and worklet registration.

```python
DSP_SCRIPT = '''// @werkstatt testscript 1 1
// @param drive 0.5 0 1 linear
// @param mix 0.8 0 1 linear

class Processor {
  constructor() {}
  paramChanged(name, value) {}
  processAudio(inputs, outputs, parameters) {}
}
'''
# 1. create_synth_track(synth_type="vaporisateur") → unit_index=1
# 2. add_effect(effect_type="Werkstatt") → effect_index=0
# 3. set_script_device_code(device_type="werkstatt", unit_index=1, device_index=0, code=DSP_SCRIPT)
#    → success=True, params_created=2, worklet_registered=True
# 4. get_script_device_code(device_type="werkstatt", unit_index=1, device_index=0)
#    → success=True, code_length>0, header="// @werkstatt js 1 N"
# 5. list_script_params(device_type="werkstatt", unit_index=1, device_index=0)
#    → param_count=2, params=[{label:"drive",...}, {label:"mix",...}]
# 6. set_script_param(device_type="werkstatt", unit_index=1, device_index=0, param_label="drive", value=0.85)
#    → success=True, old_value=0.5, new_value=0.85
# 7. list_script_samples(device_type="werkstatt", unit_index=1, device_index=0)
#    → success=True, sample_count=0
```

**Expected**: 7/7 PASS, worklet_registered=True

## 4. Quick Smoke Test (10 core tools)

Fast check when making changes. Tests the most commonly used tools.

```python
# 1. get_project_state → bpm=120 (fresh)
# 2. list_tracks → total_units=1 (output only)
# 3. set_bpm(110) → success
# 4. create_audio_track() → success
# 5. create_synth_track(name="Test", synth_type="vaporisateur") → success
# 6. add_effect(unit_index=1, effect_type="Delay") → success
# 7. list_effect_parameters(unit_index=1, effect_index=0) → 14 params
# 8. set_track_volume(unit_index=1, volume_db="-3.0") → success
# 9. transport(action="play") → status="playing"
# 10. undo() → success
```

## 5. Note Advanced + Device Management Test (6 steps)

Tests NoteEventBox advanced properties and device chain inspection.

```python
# Setup: synth + note track + region + 1 note (C4)
# 1. set_note_advanced(chance=50, cent=10, play_count=4, play_curve=0.5)
#    → chance=50, cent=10, play_count=4, play_curve=0.5
# 2. consolidate_note(note_index=0)
#    → notes_created=4, total_events=4 (original deleted, 4 new)
# 3. get_note_range(region_index=0)
#    → min_pitch=60, max_pitch=72, note_count=4
# 4. find_overlapping_notes(pitch=60, from_beat=0, to_beat=2)
#    → count=1 (C4 at beat 0)
# 5. get_device_chain_detail(unit_index=synth)
#    → instrument.label, audio_effects[{index, label, type, enabled}]
# 6. set_device_label(effect_index=0, label="Echo")
#    → new_label="Echo"
```

**Expected**: 6/6 PASS

## Vite startup notes

- `.bin/vite` symlink may be missing — use `node node_modules/vite/bin/vite.js --port 5174`
- Vite listens on `[::1]:5174` (IPv6), NOT `127.0.0.1`
- `DAW_URL="http://localhost:5174"` works because Chromium resolves `localhost` → `::1`
- Kill stale Vite before testing: `lsof -i :5174` + `kill <pid>`
- Startup takes ~30s, no immediate log output

## Critical: pointerHub region visibility

**Create ALL audio units and tracks BEFORE adding regions/notes.** Creating a new AU (via `api.createInstrument`) invalidates existing `pointerHub.incoming()` connections on previously-created tracks — regions appear to vanish. See `references/transfer-region.md` for full details and reproduction.

## Module-level bridge for MCP tool testing

MCP tool functions (`mcp_opendaw_*`) reference the module-level `bridge` object in `server.py`. To test them directly:

```python
import server
server.bridge = HeadlessDawBridge()
await server.bridge.start()
# Now mcp_opendaw_* functions work — they use server.bridge
result = json.loads(await server.mcp_opendaw_create_synth_track(name="Test", synth_type="Vaporisateur"))
await server.bridge.stop()
```

## 6. Unit Tests (pytest, no bridge required)

Pure Python helper functions (`_ok`, `_err`, `_wrap_eval`, `_unwrap_eval`, `_safe_filename`, `_safe_path`, `_parse_wav`, `_compute_lufs`) and module-level lookup tables (`TIDAL_RATE_MAP`, `DELAY_SYNC_MAP`, `WAVESHAPER_FUNCS`, `REVAMP_SECTIONS`) can be tested without a running DAW. Tests live in `tests/test_utils.py` and run in CI.

```bash
python -m pytest tests/ -v
# Expected: 54 passed
```

### Module-level constants pattern (v1.9.7+)

Lookup tables that were previously inline function locals (e.g. `rate_map = {"1/1": 0, ...}` inside `set_tidal_rate`) are now extracted to module-level typed constants (`TIDAL_RATE_MAP: dict[str, int] = {...}`). This makes them importable by tests and eliminates duplication. When adding a new tool with a lookup table, define the constant at module level (near the top of server.py after the env vars) and reference it from the tool function. CI AST check counts tools; pytest covers the constants.

### Test classes (54 total)

| Class | Tests | What |
|-------|-------|------|
| TestOk | 3 | `_ok()` success flag handling |
| TestErr | 1 | `_err()` error JSON |
| TestWrapEval | 5 | `_wrap_eval()` dict/list/string/none |
| TestUnwrapEval | 3 | `_unwrap_eval()` JSON parse round-trip |
| TestSafeFilename | 6 | sanitization, quotes, backslash, extensions, traversal, empty |
| TestSafePath | 4 | normal, traversal blocked, extension, empty filename |
| TestParseWav | 5 | float32 mono/stereo, pcm16, invalid header, no data chunk |
| TestComputeLufs | 4 | silence raises, full-scale tone, low level, stereo |
| TestTidalRateMap | 4 | basic fractions, count=17, contiguous indices, triplets |
| TestDelaySyncMap | 5 | off=0, basic fractions, count=21, contiguous, ordering |
| TestWaveshaperFuncs | 4 | known funcs, count=6, expressions nonempty, hardclip |
| TestRevampSections | 3 | known sections, count=7, camelCase |
| TestSafeFilenameEdgeCases | 5 | .dawproject, multiple dots, unicode, only extension, double extension |
| TestOkErrCombo | 2 | ok has success key, err has error key |

### Test WAV generator helpers (in test_utils.py)

`_make_wav_float32(samples, n_channels, sample_rate)` and `_make_wav_pcm16(...)` create minimal RIFF/WAVE bytes in-memory for testing `_parse_wav` and `_compute_lufs` without disk I/O.

**Critical struct field order**: `struct.pack("<HHIIHH", format, channels, sample_rate, byte_rate, block_align, bits_per_sample)`. The 5th field is `block_align` (n_channels × bytes_per_sample), NOT bits_per_sample. Swapping them produces bits_per_sample=0 in the parser → ZeroDivisionError. This mirrors the RIFF fmt chunk layout exactly.

### _parse_wav tests (5 tests)
- `test_float32_mono` — 5 samples, exact float round-trip
- `test_float32_stereo` — interleaved L/R de-interleave correctness
- `test_pcm16` — 16-bit PCM with int→float normalization
- `test_invalid_header` — non-RIFF data raises ValueError
- `test_no_data_chunk` — fmt-only WAV raises ValueError

### _compute_lufs tests (4 tests)
- `test_silence_raises` — all-zero samples → ValueError (below -70 LUFS gate)
- `test_full_scale_tone` — 1kHz sine at amplitude 1.0 → LUFS > -5, true_peak ≥ 0
- `test_low_level` — -30dB sine → LUFS between -40 and -20
- `test_stereo` — stereo LUFS > mono LUFS (double power → ~+3 LU)

### Lookup table tests (23 tests, added v1.9.7)
- `TestTidalRateMap` — 17 entries, contiguous indices 0-16, triplets at expected positions
- `TestDelaySyncMap` — 21 entries, "off"=0, contiguous indices 0-20, smallest-to-largest ordering
- `TestWaveshaperFuncs` — 6 funcs, all reference x, hardclip has min/max
- `TestRevampSections` — 7 sections, all camelCase
- `TestSafeFilenameEdgeCases` — .dawproject extension, multiple dots, unicode, double extension
- `TestOkErrCombo` — success/error key presence

### Bugs found by unit tests (v1.9.4)

1. **`_ok()` success override** — `{"success": True, **data}` allowed `data={"success": False}` to overwrite the True flag. Fix: force `d["success"] = True` after merge.
2. **`_safe_filename()` case-sensitive extensions** — `.MP3` / `.FLAC` not stripped because the check was `.replace('.mp3', '')` (lowercase only). Fix: loop with `safe.lower().endswith(ext)`.
3. **`_safe_filename()` Windows backslash traversal** — `..\\..\\secret` not split by `os.path.basename()` on Linux. Fix: replace `\\` with `/` before basename.

### Lesson: unit tests catch what manual testing misses

The `_ok()` bug existed for months — every tool that passed `{"success": False, ...}` as data would return a failure response even on success. Manual testing never caught it because the happy path never passes `success: False` in data. Unit tests with adversarial inputs found it immediately.

### CI integration

`ci.yml` runs pytest after the smoke test step:
```yaml
- name: Run unit tests
  run: |
    python -m pytest tests/ -v
```

### .gitignore pattern

Use `/test_*.py` (root-anchored) to exclude local test scripts while allowing `tests/test_*.py`:
```gitignore
# Local test scripts (not unit tests in tests/)
/test_*.py
```

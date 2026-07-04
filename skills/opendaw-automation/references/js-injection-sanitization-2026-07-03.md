# JS Injection Sanitization — COMPLETE (2026-07-03)

## Problem

String parameters in MCP tools are interpolated into `bridge.evaluate(f"""...JS...""")` template literals. If a str param is placed inside a JS string literal (e.g. `const x = "{param}";`), a malicious user can inject arbitrary JS by including `"` or `\` in the param value.

## Scope — COMPLETE (19+ functions, 28+ params)

### Phase 1 (9 functions)

| Function | Param | Sanitized var |
|----------|-------|---------------|
| `add_effect` | `effect_type` | `safe_effect` |
| `add_midi_effect` | `effect_type` | `safe_effect` |
| `set_effect_parameter` | `parameter_name` | `safe_param` |
| `set_effect_parameter_string` | `parameter_name` | `safe_param` |
| `add_automation` | `parameter_name` | `safe_param` |
| `replace_instrument` | `new_instrument` | `safe_instrument` |
| `place_audio_region` | `sample_id` | `safe_sample_id` |
| `flatten_note_regions` | `region_indices` | `safe_indices` |
| `create_synth_track` | `name` | `safe_name` |

### Phase 2 (10+ functions)

| Function | Param | Sanitized var |
|----------|-------|---------------|
| `create_instrument_track` | `name` | `safe_name` |
| `create_send` | `name` | `safe_name` |
| `create_note_clip` | `name` | `safe_name` |
| `create_track_region` | `name` | `safe_name` |
| `create_audio_bus` | `name` | `safe_name` |
| `create_audio_clip` | `sample_id` | `safe_sample_id` |
| `create_time_stretched_region` | `sample_id` | `safe_sample_id` |
| `create_time_stretched_clip` | `sample_id` | `safe_sample_id` |
| `create_pitch_stretched_region` | `sample_id` | `safe_sample_id` |
| `create_pitch_stretched_clip` | `sample_id` | `safe_sample_id` |
| `quantize_notes` | `division` | `safe_division` |
| `export_effect_chain` | `effect_type` | `safe_effect_type` |
| `set_device_label` | `label` | `safe_label` |
| `set_script_device_code` | `device_type` | `safe_device_type` |
| `get_script_device_code` | `device_type` | `safe_device_type` |
| `list_script_params` | `device_type` | `safe_device_type` |
| `list_script_samples` | `device_type` | `safe_device_type` |
| `set_script_param` | `device_type` | `safe_device_type` |
| `add_modular_module` | `module_type` | `safe_module_type` |

## Pattern

```python
# BEFORE (vulnerable):
result = await bridge.evaluate(f"""() => {{
    const effectType = "{effect_type}";
    ...
}}""")

# AFTER (sanitized):
safe_effect = effect_type.replace('"', '').replace('\\', '').replace("'", "")
result = await bridge.evaluate(f"""() => {{
    const effectType = "{safe_effect}";
    ...
}}""")
```

For `region_indices` (comma-separated numbers), also strip `;{}`:
```python
safe_indices = region_indices.replace('"', '').replace('\\', '').replace("'", "").replace(';', '').replace('{', '').replace('}', '')
```

## What does NOT need sanitization

- Str params interpolated as raw JS expressions (`{points}` → `[[0, 0.5], ...]`) — already valid JS syntax
- Str params that go through `json.dumps()` — json escaping handles quotes
- Str params only used in Python-side string operations (not interpolated into JS)
- Params with `safe_` prefix already applied
- Whitelisted params: `module_type` in `add_modular_module` is validated against `type_map` dict before interpolation

## Audit method

### Manual grep
Search for `"{` in f-string evaluate blocks:
```bash
grep -n '"{' server.py | grep -v safe_
```
Each `"{param}"` pattern where `param` is `str`-typed and NOT `safe_`-prefixed is a potential injection point.

### Automated audit
`scripts/audit_unsanitized_js.py` — scans for `"{param}"` patterns in f-string evaluate blocks, cross-references with str-typed function params, reports unsanitized injection points.

## Mass sanitization script approach

When sanitizing many functions at once, a Python script can batch-insert `safe_` definitions and replace `"{param}"` → `"{safe_var}"`:

```python
# For each (func_name, param, safe_var):
# 1. Find function body
# 2. Insert safe_var definition before first bridge.evaluate call
# 3. Replace "{param}" with "{safe_var}" in body
```

**CRITICAL PITFALL**: The script must preserve indentation. Inserting `safe_x = ...` before `result = await bridge.evaluate(...)` can break the 4-space Python indent if the script doesn't account for the existing indentation level. After running, check with `python3 -c "import ast; ast.parse(open('server.py').read())"` and fix any `IndentationError` by re-indenting lines that start with `result = await` at column 0 (should be column 4).

## quantize_notes division parser bug (fixed same session)

`quantize_notes` accepted `division` as `"1/4"`, `"1/8"`, etc. but the code did `float(division)` which crashes on `"1/4"` (ValueError: could not convert string to float: '1/4').

**Fix**: parse fraction notation explicitly:
```python
if '/' in division:
    num, den = division.split('/')
    grid_ticks = int(float(num.strip()) / float(den.strip()) * 960)
else:
    grid_ticks = int(float(division) * 960)
```

`"1/4"` → 240 ticks, `"1/8"` → 120, `"1/16"` → 60, `"1/32"` → 30.

## E2E verification

Injection attempts tested:
- `create_synth_track(name='test"; return {hacked: true}; //')` → created successfully, quotes stripped ✅
- `add_effect(effect_type='Delay"; return {hacked: true}; //')` → "factory not found: Delay" (quotes stripped, no injection) ✅
- `set_effect_parameter(parameter_name='feedback"; return {hacked: true}; //')` → sanitized, no crash ✅
- `replace_instrument(new_instrument='Nano"; return {hacked: true}; //')` → sanitized ✅

Normal functionality intact: create_synth_track, add_effect, set_effect_parameter, create_note, clone_effect_chain, replace_instrument all pass.

## Patch tool indentation pitfall

When using `patch` to insert a `safe_x = ...` line before `result = await bridge.evaluate(...)`, the tool frequently strips indentation from the f-string body. **4+ times in one session**.

**Symptom**: `IndentationError: unexpected indent` on the line after the inserted code.

**Fix**: include the full opening block in `new_string` with correct indentation:
```python
    """
    safe_x = x.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const p = window.DAW;
        ...
```
The `safe_x` and `result =` are at 4-space indent (function body). JS content stays at 8-space indent.

**Alternative**: use a Python script to batch-apply, then fix indentation with:
```python
# Fix lines starting with "result = await" at indent 0 that should be indent 4
for i, line in enumerate(lines):
    if line.startswith('result = await bridge.evaluate'):
        if i > 0 and lines[i-1].strip().startswith('safe_') and lines[i-1].startswith('    '):
            lines[i] = '    ' + line
```

## awesome-mcp PR #9133 update

Bot requires Glama.ai registration (SPA, manual). Asked if MCP Registry + Docker is sufficient. PR still open, awaiting response. Tool count updated from 194 → 211 in PR README.

## v1.5.2 final state

- 25+ functions sanitized (all str params in JS template literals)
- 3 intentional raw interpolations by design (evaluate_raw.script, wait_for_condition.condition_js, add_automation.points)
- CONTRIBUTING.md step 6 documents the `safe_` pattern as official policy
- CI threshold set to >=211 (exact tool count, regression guard)
- `audit_unsanitized_js.py` and `audit_str_params.py` scripts available for automated checks
- E2E verified: injection attempts blocked, normal functionality intact

## Batch script indentation breakage — detailed log

When a Python script batch-inserted `safe_` definitions before `result = await bridge.evaluate(...)` across 19 functions:
- **First pass**: 19 `result =` lines lost 4-space indent (dropped to column 0)
- **Fix pass 1**: `if line.startswith('result = await bridge.evaluate') and lines[i-1].strip().startswith('safe_'): lines[i] = '    ' + line` — fixed 19 lines
- **Second breakage**: 3 `safe_` lines that were inserted after `"""` docstring close also lost indent
- **Fix pass 2**: `if line.startswith('safe_') and not line.startswith('    '): if lines[i-1].strip().endswith('"""'): lines[i] = '    ' + line`
- **Lesson**: batch-insert scripts MUST run `ast.parse()` after BOTH insertion AND each fix pass. Line number shifts between passes can introduce new issues.

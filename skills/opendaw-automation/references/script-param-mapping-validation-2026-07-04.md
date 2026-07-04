# Script Param Mapping Info + Range Validation (2026-07-04, v1.11.1)

## What changed

`list_script_params` and `set_script_param` now use `ScriptDeclaration.parseParams()` to read mapping metadata from `@param` declarations. Added `DAW_ScriptDeclaration` global to headless-daw/main.ts.

### list_script_params — new fields

Previously returned: label, index, value, defaultValue.
Now also returns: **min, max, mapping, unit** — parsed from the code string (the code is the single source of truth for mapping info, per upstream plan `custom-mapping.md`).

```python
# Response per param:
{
    "label": "cutoff",
    "index": 0,
    "value": 1000,
    "defaultValue": 1000,
    "min": 20,
    "max": 20000,
    "mapping": "exp",     # unipolar|linear|exp|int|bool
    "unit": "Hz"
}
```

### set_script_param — range validation

Now validates value against the `@param` declaration before setting:

| mapping | behavior |
|---------|----------|
| `bool`  | snaps to 0 or 1 (≥0.5 → 1) |
| `int`   | rounds to nearest integer, clamps to [min, max] |
| `linear`/`exp`/`unipolar` | clamps to [min, max] |

Response includes `clamped: bool`, `requested_value: float`, and `range: {min, max, mapping, unit}` when declaration is found. If no declaration matches, value is set raw (backward compatible).

### E2E verified

- `cutoff=99999` → clamped to 20000 (exp, 20–20000 Hz) ✅
- `mode=2.7` → rounded to 3 (int, 0–4) ✅
- `bypass=0.8` → snapped to 1 (bool) ✅

---

## PITFALL: Maximizer at effect index 0

Upstream (since ~e17f7789) adds a **MaximizerDeviceBox** to the Output unit's audio effects chain by default. When you `add_effect(unit_index, 'Werkstatt')`, the Werkstatt lands at **index 1**, not 0.

### Symptoms

```
compile error: "Cannot read properties of undefined (reading 'getValue')"
list_script_params error: "Device has no parameters field"
```

This happens because MaximizerDeviceBox has no `.code`, `.parameters`, or `.samples` fields — it's not a scriptable device.

### Fix

Always enumerate effects first to find the correct index:

```python
# Check what's on the unit
r = await bridge.evaluate('''() => {
    const h = window.DAW_HELPERS;
    const au = h.allAUBoxes()[unit_idx];
    return JSON.stringify(h.effectBoxes(au).map((b,i) => ({index: i, class: b.constructor.name})));
}''')
# Find Werkstatt/Apparat/Spielwerk by class name, not by fixed index
```

Or document to users that `device_index` must point to the scriptable device's actual position in the effect chain, which may not be 0 if Maximizer is present.

### Affected tools

All scriptable device tools: `set_script_device_code`, `get_script_device_code`, `list_script_params`, `set_script_param`, `list_script_samples`.

---

## DAW_ScriptDeclaration global

Added to `headless-daw/src/main.ts` alongside `DAW_ScriptCompiler`:

```typescript
w.DAW_ScriptDeclaration = adapters.ScriptDeclaration;
```

`ScriptDeclaration.parseParams(code)` returns `ParamDeclaration[]` with fields: `label`, `defaultValue`, `min`, `max`, `mapping`, `unit`. Safe to call — wrapped in try/catch in the evaluate block. Returns empty array if code has no `@param` lines.

### Mapping types (from ScriptDeclaration.ts)

- `unipolar` (default, no explicit token needed) — 0–1
- `linear` — min to max, linear
- `exp` — min to max, exponential
- `int` — integer min to max
- `bool` — 0 or 1, displayed as Off/On

**`unipolar` CANNOT be passed as explicit 5th token** — throws "unknown mapping 'unipolar'". Use `linear` for explicit 0–1 ranges, or omit bounds for implicit unipolar.

# Maximizer at Effect Index 0 (upstream ~e17f7789)

## Problem

Upstream adds a **MaximizerDeviceBox** to the Output unit's audio effects chain by default. When you `add_effect(unit_index, 'Werkstatt')`, the Werkstatt lands at **index 1**, not 0.

### Symptoms

```
compile error: "Cannot read properties of undefined (reading 'getValue')"
list_script_params error: "Device has no parameters field"
```

MaximizerDeviceBox has no `.code`, `.parameters`, or `.samples` fields — it's not a scriptable device.

## Fix

Always enumerate effects first to find the correct index:

```python
r = await bridge.evaluate('''() => {
    const h = window.DAW_HELPERS;
    const au = h.allAUBoxes()[unit_idx];
    return JSON.stringify(h.effectBoxes(au).map((b,i) => ({index: i, class: b.constructor.name})));
}''')
# Find Werkstatt/Apparat/Spielwerk by class name, not by fixed index
```

Or document to users that `device_index` must point to the scriptable device's actual position in the effect chain, which may not be 0 if Maximizer is present.

## Affected tools

All scriptable device tools: `set_script_device_code`, `get_script_device_code`, `list_script_params`, `set_script_param`, `list_script_samples`.

## Note

This is NOT a bug — Maximizer is an intentional upstream default on the Output unit. The fix is awareness, not removal.

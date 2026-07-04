# Inline-to-Module-Level Constant Extraction (v1.9.7)

## Problem

Effect-specific MCP tools (`set_tidal_rate`, `set_delay_sync`, `set_waveshaper_equation`, `set_revamp_filter`) contained lookup tables as inline function locals:

```python
async def mcp_opendaw_set_tidal_rate(..., rate: str) -> str:
    rate_map = {"1/1": 0, "1/2": 1, ...}  # inline
    if rate not in rate_map:
        return _err(...)
    idx = rate_map[rate]
```

These maps are pure data with no bridge dependency, but they were untestable — trapped inside async tool functions that require a running DAW.

## Fix

Extract to typed module-level constants at the top of `server.py` (after env vars, before class definitions):

```python
TIDAL_RATE_MAP: dict[str, int] = {
    "1/1": 0, "1/2": 1, "1/3": 2, "1/4": 3, "3/16": 4, ...
}
DELAY_SYNC_MAP: dict[str, int] = {
    "off": 0, "1/128": 1, "1/96": 2, ...
}
WAVESHAPER_FUNCS: dict[str, str] = {
    "hardclip": "min(1, max(-1, x))", ...
}
REVAMP_SECTIONS: tuple[str, ...] = (
    "highPass", "lowShelf", "lowBell", "midBell",
    "highBell", "highShelf", "lowPass",
)
```

Then reference from tool functions:

```python
if rate not in TIDAL_RATE_MAP:
    return _err(f"Invalid rate '{rate}'. Valid: {', '.join(sorted(TIDAL_RATE_MAP.keys()))}")
idx = TIDAL_RATE_MAP[rate]
```

## Revamp sections: derived map

The Revamp tool accepts lowercase user input (`"highpass"`) but box fields are camelCase (`"highPass"`). Instead of a hardcoded section_map dict, derive it from the constant:

```python
section_map = {k.lower(): k for k in REVAMP_SECTIONS}
```

This eliminates the maintenance burden of keeping two lists in sync.

## Testing

Import constants directly in tests:

```python
from server import TIDAL_RATE_MAP, DELAY_SYNC_MAP, WAVESHAPER_FUNCS, REVAMP_SECTIONS
```

Test classes verify: entry count, index contiguity, ordering direction, known key→value mappings, and structural properties (e.g. all waveshaper expressions contain "x", all revamp sections are camelCase).

## When to apply

Apply this pattern to ANY tool that has a validation lookup table (enum mapping, fraction→index, name→field). If the table is pure data with no runtime dependencies, it belongs at module level. The CI AST check verifies tool count; pytest covers the data correctness.

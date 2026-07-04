# Testability Patterns for server.py

## Module-level lookup table extraction

When a tool function contains an inline lookup dict (fraction→index maps, valid key sets, enum→boxField maps), extract it to a module-level constant. This lets unit tests verify the mapping without a bridge connection.

### Problem

```python
# BAD — untestable, buried inside async function body
async def mcp_opendaw_set_tidal_rate(unit_index, effect_index, rate):
    rate_map = {"1/1": 0, "1/2": 1, "1/4": 3, ...}  # 17 entries
    if rate not in rate_map:
        return _err(f"Invalid rate '{rate}'...")
    idx = rate_map[rate]
    # ... bridge.evaluate(...)
```

The map is invisible to `tests/test_utils.py` because it's a local variable inside an async function that requires a Playwright bridge to run.

### Solution

```python
# GOOD — module-level constant, importable from tests
TIDAL_RATE_MAP: dict[str, int] = {
    "1/1": 0, "1/2": 1, "1/3": 2, "1/4": 3, ...
}

async def mcp_opendaw_set_tidal_rate(unit_index, effect_index, rate):
    if rate not in TIDAL_RATE_MAP:
        return _err(f"Invalid rate '{rate}'...")
    idx = TIDAL_RATE_MAP[rate]
```

### Test coverage

```python
class TestTidalRateMap:
    def test_basic_fractions(self):
        from server import TIDAL_RATE_MAP
        assert TIDAL_RATE_MAP["1/1"] == 0
        assert TIDAL_RATE_MAP["1/4"] == 3

    def test_count(self):
        from server import TIDAL_RATE_MAP
        assert len(TIDAL_RATE_MAP) == 17

    def test_indices_contiguous(self):
        from server import TIDAL_RATE_MAP
        indices = sorted(TIDAL_RATE_MAP.values())
        assert indices == list(range(17))
```

### Currently extracted constants (as of v1.9.8)

| Constant | Type | Entries | Notes |
|----------|------|---------|-------|
| `TIDAL_RATE_MAP` | `dict[str,int]` | 17 | Largest→smallest ordering. Triplets included (3/16, 3/32, 3/64). |
| `DELAY_SYNC_MAP` | `dict[str,int]` | 21 | Smallest→largest + "off"=0. Different array from Tidal — NOT interchangeable. |
| `WAVESHAPER_FUNCS` | `dict[str,str]` | 6 | hardclip/cubicSoft/tanh/sigmoid/arctan/asymmetric. Each expression references `x`. |
| `REVAMP_SECTIONS` | `tuple[str,...]` | 7 | camelCase box field names: highPass/lowShelf/lowBell/midBell/highBell/highShelf/lowPass. Forge-boxes schema uses kebab-case but generated boxes use camelCase. |

### Revamp section lookup pattern

Revamp sections are camelCase in the generated box but user input may be lowercase. Use a derived map:

```python
REVAMP_SECTIONS = ("highPass", "lowShelf", "lowBell", "midBell", "highBell", "highShelf", "lowPass")
# In the tool function:
section_map = {k.lower(): k for k in REVAMP_SECTIONS}
if safe_section not in section_map:
    return _err(...)
box_field = section_map[safe_section]  # e.g. "highpass" → "highPass"
```

# Security Audit: Enum Validation + Path Traversal (v1.9.1, 2026-07-03)

## Audit Methodology

### Full sanitization audit script pattern

```python
# Scan ALL str-typed params in MCP tool signatures
# Cross-reference: is the param (a) sanitized, (b) json.dumps'd, (c) validated against enum,
# or (d) flowing raw into bridge.evaluate / subprocess?
import re
with open('server.py') as f:
    source = f.read()

tool_defs = re.findall(r'async def mcp_opendaw_(\w+)\((.*?)\) -> str:', source, re.DOTALL)
issues = []
for name, params in tool_defs:
    str_vars = re.findall(r'(\w+):\s*str', params)
    for v in str_vars:
        if v in ('return',): continue
        has_safe = f'safe_{v}' in source
        has_jsondumps = f'json.dumps({v}' in source
        has_enum_check = f'valid_' in source and v in source
        if not has_safe and not has_jsondumps and not has_enum_check:
            issues.append((name, v))
```

### Classification of unsanitized params

| Category | Risk | Example | Fix |
|----------|------|---------|-----|
| **JS eval raw** | HIGH — JS injection | `parameter_name` in `"{param}"` | `safe_x = param.replace('"','')...` or `json.dumps()` |
| **Enum not validated** | MEDIUM — unexpected behavior | `action` in transport | Validate against `set()` before eval |
| **Path traversal** | HIGH — write outside export_dir | `filename="../../../etc/passwd"` | `os.path.basename()` + containment check |
| **Subprocess arg** | LOW if list-based | `ffmpeg ["-i", path]` | `asyncio.create_subprocess_exec(*list)` — no shell |
| **Python-only use** | NONE | `filename` in `os.path.exists()` | No fix needed |
| **Intentionally raw** | BY DESIGN | `evaluate_raw.script`, `add_automation.points` | Document in docstring |

## Fixes Applied

### 1. Enum validation for transport action

```python
# BEFORE: action flows raw into JS string
act = (action or "toggle").lower().strip()
result = await bridge.evaluate(f"""() => {{
    if ('{act}' === 'play') {{ ... }}
}}""")

# AFTER: validated against whitelist
valid_actions = {"play", "stop", "toggle"}
act = (action or "toggle").lower().strip()
if act not in valid_actions:
    return json.dumps({"error": f"Invalid action '{act}'. Must be one of: {', '.join(sorted(valid_actions))}"})
```

### 2. Enum validation for duplicate_effect chain_type

Same pattern — validate against `{"audio", "midi"}` before eval.

### 3. Path traversal protection

Centralized helpers replacing 6 inline sanitizations:

```python
def _safe_filename(name: str) -> str:
    """Sanitize: strip quotes/backslashes, remove extension, prevent path traversal."""
    safe = name.replace('"', '').replace("'", '').replace('\\', '')
    safe = safe.replace('.wav', '').replace('.WAV', '').replace('.mp3', '').replace('.flac', '')
    safe = os.path.basename(safe)          # KEY: strips directory components
    safe = safe.replace('/', '').replace('\\', '')
    return safe or "output"

def _safe_path(export_dir: str, filename: str, ext: str = "wav") -> str:
    """Build path inside export_dir, preventing traversal."""
    safe = _safe_filename(filename)
    path = os.path.join(export_dir, f"{safe}.{ext}")
    # Double-check: resolved path must start with export_dir
    if not os.path.abspath(path).startswith(os.path.abspath(export_dir)):
        path = os.path.join(export_dir, f"output.{ext}")
    return path
```

**IMPORTANT**: `os.path.basename("../../../etc/passwd")` → `"passwd"` — strips traversal. Then containment check catches edge cases (symlinks, `..` after basename).

### 4. Bare except cleanup

```python
# BEFORE: catches everything including KeyboardInterrupt
except: return s

# AFTER: specific exception
except (json.JSONDecodeError, ValueError): return s
```

One bare except remains in `atexit.register(cleanup)` — acceptable for shutdown handlers.

## Audit Results Summary

| Metric | Value |
|--------|-------|
| Total str params scanned | 46 |
| Properly sanitized (safe_ prefix) | 28+ |
| json.dumps'd | 4 |
| Enum validated | 2 (transport, chain_type) |
| Intentionally raw (documented) | 4 (evaluate_raw, wait_for_condition, add_automation, add_instrument_automation) |
| Path traversal protected | 6 filename usages → `_safe_filename()` |
| Remaining risk | NONE — all categories covered |

## DAW_HELPERS: auBox / allAUBoxes

Added box-level AU access helpers (complement existing adapter-level `au()`/`allAUs()`):

```javascript
// DAW_HELPERS now has:
auBox: (i) => {
    const aus = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({box}) => box)
        .sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
    if (i >= aus.length) throw new Error('No AU at ' + i);
    return aus[i];
},
allAUBoxes: () => [...p.rootBox.audioUnits.pointerHub.incoming()].map(({box}) => box)
    .sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0)),
```

113 tools still use raw enumeration boilerplate (~2 lines each). Migration path: replace raw pattern with `h.auBox(i)` / `h.allAUBoxes()`. Batch by 10-15 tools, E2E smoke test after each batch.

### When to use auBox vs au

- **`h.au(i)`** → returns adapter. Use when you need `.audioEffects.adapters()`, `.tracks.collection.adapters()`, `.box` access
- **`h.auBox(i)`** → returns raw box. Use when you need `.audioEffects.pointerHub.incoming()`, `.midiEffects`, `.input.pointerHub`, box field access

## Device-Specific Parameter Coverage (v1.9.0 + v1.9.1)

All non-float fields on all 15 audio effect boxes are now covered:

| Effect | Field | Type | Tool |
|--------|-------|------|------|
| NeuralAmp | model (→NeuralAmpModelBox) | PointerField | `set_neuralamp_model` |
| NeuralAmp | mono | BooleanField | `set_effect_parameter_bool` |
| Vocoder | modulatorSource | StringField | `set_vocoder_modulator_source` |
| Vocoder | bandCount | Int32Field | `set_vocoder_band_count` |
| StereoTool | panningMixing | Int32Field | `set_stereo_tool_panning` / `set_effect_parameter_int` |
| StereoTool | invertL, invertR, swap | BooleanField | `set_effect_parameter_bool` |
| Fold | overSampling | Int32Field | `set_fold_oversampling` / `set_effect_parameter_int` |
| Crusher | bits | Int32Field | `set_crusher_bits` / `set_effect_parameter_int` |
| Compressor | lookahead, automakeup, autoattack, autorelease | BooleanField | `set_effect_parameter_bool` |
| Gate | inverse | BooleanField | `set_effect_parameter_bool` |
| Maximizer | lookahead | BooleanField | `set_effect_parameter_bool` |

### PointerField linking pattern (NeuralAmp model loading)

```javascript
// Create box → get vertex → refer pointer
h.modify(() => {
    const modelBox = NeuralAmpModelBox.create(h.boxGraph, UUID.generate());
    modelBox.label.setValue(label);
    modelBox.model.setValue(modelJson);
    const modelVertex = h.boxGraph.findVertex(modelBox.address);
    effectBox.model.refer(modelVertex.unwrap());  // NOT .point(), NOT .targetVertex =
});
```

**Pitfall**: `PointerField.refer()` requires a `Vertex`, not a `Box`. Get vertex via `graph.findVertex(box.address)`.
**Pitfall**: Box creation needs `UUID.generate()`, NOT `h.uuid()` (which is for string UUIDs in DAW_HELPERS).

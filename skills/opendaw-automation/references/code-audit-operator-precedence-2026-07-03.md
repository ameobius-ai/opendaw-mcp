# Code Audit: Operator Precedence + AST Scanning (2026-07-03)

## The bug: `X / Quarter ?? 0` is NOT a safe default

### Root cause
JS nullish coalescing (`??`) has **lower precedence** than division (`/`). So:
```js
n.position?.getValue?.() / Quarter ?? 0
```
parses as:
```js
(n.position?.getValue?.() / Quarter) ?? 0
```

When `getValue()` returns `undefined`:
1. `undefined / 960` = `NaN`
2. `NaN ?? 0` = `NaN` (NOT 0! — `??` only catches `null` and `undefined`, not `NaN`)
3. `JSON.stringify(NaN)` = `"null"` → agents see `null` instead of `0`

### Correct pattern
```js
(n.position?.getValue?.() ?? 0) / Quarter
```
Coalesce FIRST, then divide. If `getValue()` is undefined, `(undefined ?? 0) / Quarter` = `0 / 960` = `0`.

### Fix method
Python regex on server.py source:
```python
import re
pattern = r'(\w+(?:\?\.\w+)*)\?\.\(\) / (\w+(?:\.\w+)*) \?\? 0'
# Replace: ({chain}?.getValue?.() ?? 0) / {quarter_expr}
```

**CRITICAL REGEX PITFALL**: A naive regex that captures only `object.field` (not the full `object.field?.getValue?.()` chain) will produce doubled `.getValue`:
```
# BAD: e.(relativePosition?.getValue?.getValue?.() ?? 0) / Quarter
# GOOD: (e.relativePosition?.getValue?.() ?? 0) / Quarter
```
Always verify after applying: `grep -n "?? 0) / " server.py` — check no `.getValue?.getValue` artifacts.

### Detection (ongoing regression check)
```bash
grep -n "/ Quarter ?? \|/ h.ppqn.Quarter ?? " server.py
# Should return 0 results if all fixed
```

### Affected tools (14 occurrences)
- `list_notes` — position_beats, duration_beats
- `list_automation_events` — position_beats (2x: e.position, e.relativePosition)
- `list_automation_events_detail` — position_beats (2x)
- `list_value_regions` — position, duration, loopOffset, loopDuration (4x)
- `list_clips` — duration_beats (2x: clip.duration)
- `get_engine_status` — position_beats
- Various region listing tools

## AST-based code audit techniques

### 1. Find unused function parameters
```python
import ast
tree = ast.parse(open('server.py').read())
for node in ast.walk(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        for d in node.decorator_list:
            if isinstance(d, ast.Call) and hasattr(d.func, 'attr') and d.func.attr == 'tool':
                params = [a.arg for a in node.args.args if a.arg != 'self']
                body_lines = lines[node.lineno:node.end_lineno]
                body_text = '\n'.join(body_lines)
                for p in params:
                    if p not in body_text:
                        print(f'L{node.lineno}: {node.name}() — param "{p}" unused')
```
Found 2 unused params: `region_type` in `set_region_duration` and `set_region_mute`.

### 2. Find raw string interpolation (injection risk)
```python
import re
for tool in tools:
    str_params = [a.arg for a in tool.args.args 
                  if a.annotation and isinstance(a.annotation, ast.Name) and a.annotation.id == 'str']
    body = '\n'.join(lines[tool.lineno-1:tool.end_lineno])
    for p in str_params:
        raw = re.findall(r'\{' + re.escape(p) + r'\}', body)
        safe = re.findall(r'json\.dumps\(' + re.escape(p) + r'\)|_sanitize\(' + re.escape(p) + r'\)', body)
        if raw and not safe:
            print(f'L{tool.lineno}: {tool.name}() — "{p}" interpolated raw ({len(raw)}x)')
```
Found 6 — all either sanitized via `.replace()` or intentionally raw (points, condition_js, script).

### 3. Find missing .sort() on audioUnits
```python
import re
matches = list(re.finditer(r'audioUnits\.pointerHub\.incoming\(\)', src))
for m in matches:
    next_chunk = src[m.end():m.end()+200]
    if '.sort(' not in next_chunk:
        line_num = src[:m.start()].count('\n') + 1
        # Check if it's safe (length, findIndex, find — don't need sort)
        line = src[src.rfind('\n', 0, m.start())+1:src.find('\n', m.end())]
        print(f'L{line_num}: {line.strip()[:80]}')
```
Found 8 — all safe (use `.length`, `.findIndex()`, `.find()` — not index access).

### 4. Verify type annotations complete
```python
from collections import Counter
types = Counter()
no_type = []
for tool in tools:
    for arg in tool.args.args:
        if arg.arg == 'self': continue
        ann = arg.annotation
        if isinstance(ann, ast.Name): types[ann.id] += 1
        elif ann is None: no_type.append(f'{tool.name}.{arg.arg}')
print(f'Types: {dict(types)}')
print(f'Untyped: {len(no_type)}')
```
Result: 404 int, 91 str, 66 float, 23 bool, 0 untyped.

### 5. Tool count verification (CI check)
```python
import ast
tree = ast.parse(open('server.py').read())
tools = [n for n in ast.walk(tree) 
         if isinstance(n, ast.AsyncFunctionDef) and n.name.startswith('mcp_opendaw_')]
count = len(tools)
assert count >= THRESHOLD, f'Expected at least {THRESHOLD} tools, got {count}'
```

## Key lesson
When writing JS inside Python f-strings, **always test the JS operator precedence**. Python's `??` doesn't exist, so there's no intuition transfer. The safe pattern for any `getValue() / divider` with a fallback is ALWAYS:
```js
(x?.getValue?.() ?? 0) / divider
```
Never `x?.getValue?.() / divider ?? 0`.

## Related bug class: TypeScript type property mismatches

Same session found another instance of "wrong property name on a TS type":

**Bug**: `capture_realtime` used `audioData.channels` — but `AudioData` has `numberOfChannels`, not `channels`.

```typescript
// packages/lib/dsp/src/audio-data.ts
export type AudioData = {
    sampleRate: number
    numberOfFrames: number    // NOT "frames.length" for the field name
    numberOfChannels: number  // NOT "channels"
    frames: ReadonlyArray<Float32Array>
}
```

`audioData.channels` → `undefined` → key omitted from JSON output entirely.

**Detection**: Cross-reference TypeScript type definitions when accessing properties returned from `page.evaluate()`. Always grep the upstream type:
```bash
grep -rn "type AudioData\|interface AudioData" packages/
```

**Fix**: `audioData.channels` → `audioData.numberOfChannels`

**Audit command** for all audioData property accesses:
```bash
grep -n "audioData\." server.py | grep -v "frames\|sampleRate\|numberOfChannels\|numberOfFrames"
# Should return 0 results — any other property is likely wrong
```

### 6. Find unused imports (2026-07-03)
```python
import ast
tree = ast.parse(open('server.py').read())
imports = set()
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        for alias in node.names:
            imports.add(alias.asname or alias.name)
    elif isinstance(node, ast.ImportFrom):
        for alias in node.names:
            imports.add(alias.asname or alias.name)
used = set()
for node in ast.walk(tree):
    if isinstance(node, ast.Name):
        used.add(node.id)
    elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        used.add(node.value.id)
unused = imports - used - {'self', 'cls'}
print(f"Unused imports: {unused}")
```
Found `Path` from pathlib — imported but never used in code (only appeared in docstring text). Note: `subprocess` appeared unused but was actually used via `asyncio.subprocess` — AST tracks the `asyncio` name, not `subprocess` directly. Check `grep -n "subprocess" server.py` before removing.

**Bare except clause detection**:
```python
for node in ast.walk(tree):
    if isinstance(node, ast.ExceptHandler) and node.type is None:
        print(f"L{node.lineno}: bare except")
```
Found 1 bare except in `atexit` cleanup handler — acceptable (must not crash during shutdown).

## Related bug class: Undefined safe_ variables (2026-07-03, separate session)

Same audit pass found two tools that referenced `safe_<param>` variables in f-string JS but never assigned them — `create_value_clip` (safe_name) and `set_region_position` (safe_region_type). Both would crash with NameError at runtime.

**Detection**: AST scan for `safe_` variables used but never assigned. See `references/undefined-variable-audit-2026-07-03.md` and `scripts/audit_undefined_safe_vars.py`.

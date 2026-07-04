# Ruff Lint + Catalog Sync + Docker Tag Fix (2026-07-03, post-v1.9.5)

## Ruff Lint Audit

### What ruff found (59 → 0 errors)

| Code | Count | Type | Fix |
|------|-------|------|-----|
| F541 | 25 | f-string-missing-placeholders | `--fix` auto |
| W293 | 11 | blank-line-with-whitespace | `--fix` auto |
| E701 | 7 | multiple-statements-on-one-line-colon | ignored (compact style) |
| E702 | 6 | multiple-statements-on-one-line-semicolon | ignored (compact style) |
| F841 | 4 | unused-variable | manual removal |
| **F821** | **3** | **undefined-name** | **manual fix — RUNTIME BUGS** |
| E722 | 1 | bare-except | `except` → `except Exception` |
| F401 | 1 | unused-import | manual removal |
| W292 | 1 | missing-newline-at-end-of-file | `--fix` auto |

### The F821 runtime bugs (CRITICAL)

Three tools used `h.ppqn.Quarter` in **Python-side** code, but `h` is a JS-only bridge helper — not a Python variable. This causes `NameError` at runtime.

```python
# WRONG — crashes with NameError:
new_ppqn = int(new_position_beats * h.ppqn.Quarter)

# CORRECT — PPQN.Quarter = 960, hardcoded:
new_ppqn = int(new_position_beats * 960)
```

Affected tools:
- `move_automation_event` (line ~7436)
- `get_automation_value` (line ~8396)
- `move_region_content` (line ~8487)

### Why pytest couldn't catch these

Unit tests only cover pure Python functions (`_ok`, `_safe_filename`, etc.). The 243 MCP tools all call `bridge.evaluate()` which requires a running openDAW instance — can't be tested in CI without Vite + Chromium. ruff's static analysis catches the NameError without execution.

### ruff config in pyproject.toml

```toml
[tool.ruff]
line-length = 120

[tool.ruff.lint]
select = ["F", "E722", "W292"]
ignore = ["E501", "E701", "E702"]
```

### CI step

```yaml
- name: Lint with ruff
  run: |
    ruff check server.py
    echo "Ruff lint passed"
```

### Unused variables removed

- `ppqn_base` in `import_midi` — assigned but never read
- `safe_transient_mode` in `create_time_stretched_region` — assigned but `{transient_mode}` used directly (already sanitized via `json.dumps`)
- `fn_json` × 2 in `export_dawproject` / `import_dawproject` — leftover from refactoring
- `subprocess` import — `asyncio.subprocess` is auto-available, no top-level import needed

## TOOL_CATALOG.md Sync

### Problem

TOOL_CATALOG.md said "237 tools" but server.py had 243. Only 136 of 245 tools were listed. 108 tools missing from catalog.

### Solution: AST-generated catalog

```python
import ast

with open('server.py') as f:
    source = f.read()
tree = ast.parse(source)

tools = []
for node in ast.walk(tree):
    if isinstance(node, ast.AsyncFunctionDef) and node.name.startswith('mcp_opendaw_'):
        name = node.name.replace('mcp_opendaw_', '')
        doc = ast.get_docstring(node) or ''
        first_line = doc.split('\n')[0].strip()
        tools.append((name, first_line))
```

Then categorize into ~32 sections, verify header counts match actual entries, verify total matches AST count.

### Verification

```python
import re
with open('TOOL_CATALOG.md') as f:
    text = f.read()
listed = len(re.findall(r'^- `(?!h\.|werkstatt|apparat|spielwerk)', text, re.MULTILINE))
headers = re.findall(r'^## .*\((\d+)', text, re.MULTILINE)
total = sum(int(h) for h in headers)
assert listed == total == 243  # all three must match
```

## server.json Docker Tag Bug

`server.json` had `"identifier": "ghcr.io/ameobius/opendaw-mcp:1.0.0"` — stale since the very first release. Updated to match current version on every release.

**Lesson**: Always check `server.json` packages[].identifier when releasing. It's not auto-updated by the publish workflow — it's a static file.

## Commits

- `2c25767` — fix: sync TOOL_CATALOG.md (243 tools) + server.json Docker tag
- `52a1db5` — release: v1.9.4 (dedup + catalog sync)
- `6cba13c` — ci: add smoke test
- `884b912` — chore: py.typed marker
- `551f483` — feat: CLI commands
- `a180797` — test: unit tests + 3 bug fixes
- `73f7ed0` — docs: Tests badge, mastering example
- `3a480f7` — release: v1.9.5
- `16151f9` — fix: ruff lint cleanup (3 runtime bugs, 36 code issues)
- `3fbf88b` — chore: ruff config in pyproject.toml
- `faa2f80` — docs: ruff lint badge

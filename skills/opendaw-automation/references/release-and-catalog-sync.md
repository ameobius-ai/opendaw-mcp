# Release & Catalog Sync Procedures

## Full Release Checklist (v1.9.4+)

1. Update version in ALL of these (they drift independently):
   - `pyproject.toml` — `version = "1.9.X"`
   - `server.json` — `version` field **AND** `packages[].identifier` Docker tag (e.g. `ghcr.io/ameobius/opendaw-mcp:1.9.X`)
   - `README.md` — badge counts (MCP Tools + Tests), header line, tool catalog link count, changelog section
   - `.github/workflows/ci.yml` — `assert count >= N` threshold (both AST and smoke test steps)
   - `TOOL_CATALOG.md` — header line + section counts + `**Total: N tools**`
2. If unit test count changed: update README badges (`Tests-N passing`), README changelog, and the `pytest` expected count in `references/testing-procedures.md`
2. `git commit -m "release: v1.9.X — ..."` → `git push`
3. Wait ~20s → `gh run list --limit 3` → confirm CI green
4. `git tag v1.9.X && git push origin v1.9.X`
5. `gh release create v1.9.X --title ... --notes ...`
6. Publish workflow auto-triggers on tag push → Docker build + MCP Registry publish (~4 min)
7. Update memory entry

## server.json Docker tag pitfall

`server.json` `packages[].identifier` contains a Docker tag that must match the release version.
It was stale at `1.0.0` for 23 releases (v1.0.0 through v1.9.3) because nobody updated it during the release procedure.
Always update it — it's what MCP Registry consumers pull.

## Catalog Sync (when tool count changes)

TOOL_CATALOG.md drifts silently when tools are added or removed. At v1.9.3 it said "237 tools" and only had 136 entries while server.py had 245.

### Regeneration procedure

```python
import ast

with open('server.py') as f:
    tree = ast.parse(f.read())

tools = []
for node in ast.walk(tree):
    if isinstance(node, ast.AsyncFunctionDef) and node.name.startswith('mcp_opendaw_'):
        name = node.name.replace('mcp_opendaw_', '')
        doc = ast.get_docstring(node) or ''
        first_line = doc.split('\n')[0].strip() if doc else ''
        tools.append((name, first_line))

# Group by category dict (name → list of tool names)
# Write markdown: ## Category (N) + one `- \`tool_name\` — desc` line per tool
```

### Verification invariant

```
server.py tool count  ==  catalog tool entries  ==  sum of header section counts
```

Check with:
```python
import re
# server count
ast_count = len([n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef) and n.name.startswith('mcp_opendaw_')])
# catalog entries
catalog_count = len(re.findall(r'^- `(?!h\.|werkstatt|apparat|spielwerk)', text, re.MULTILINE))
# header total
header_total = sum(int(h) for h in re.findall(r'^## .*\((\d+)(?:\s+tools?)?\)', text, re.MULTILINE))
assert ast_count == catalog_count == header_total
```

## CI Smoke Test (v1.9.4+)

CI now includes a smoke test that imports server.py and verifies tool registration via FastMCP's `list_tools()`:

```python
import server
mcp = server.mcp
import asyncio
tools = asyncio.run(mcp.list_tools())
assert len(tools) >= 243
tool_names = {t.name for t in tools}
for required in ['mcp_opendaw_get_project_info', 'mcp_opendaw_create_synth_track',
                 'mcp_opendaw_add_effect', 'mcp_opendaw_export_mix', 'mcp_opendaw_transport']:
    assert required in tool_names
```

**Key detail**: FastMCP registers tools with their full function name including `mcp_opendaw_` prefix. Don't check for bare names like `'get_project_info'` — they won't be found.

**What it catches that AST check doesn't**: imports that fail at runtime, FastMCP registration errors, decorator issues. The AST count check only parses syntax — it doesn't verify the `@mcp.tool()` decorator actually registers.

## Duplicate Detection

Run before releases to catch overlapping tools:

```python
from collections import defaultdict
desc_groups = defaultdict(list)
for name, desc in tools.items():
    key = ' '.join(desc.lower().split()[:5])  # first 5 words normalized
    desc_groups[key].append(name)
for key, names in desc_groups.items():
    if len(names) > 1:
        print(f"  '{key}': {names}")
```

### When duplicates found, compare:

1. **Access pattern**: box-level (fields, pointers, `pointerHub.incoming()`) vs adapter-level (`.adapters()`, `.unwrap()`). Box-level is richer — it can access fields the adapter doesn't expose.
2. **Return fields**: one may return more data. Keep the richer one.
3. **Parameter flexibility**: one may accept position OR index while the other only accepts index. Keep the more flexible one.
4. **Document the removal** in the changelog with the reason (e.g. "superseded by X which has richer API").

### Known good pairs that look like duplicates but aren't:

- `create_instrument_track` (Tape device, audio playback) vs `create_synth_track` (MIDI synth, note playback) — different purposes
- `set_region_color` vs `set_clip_hue` — different target objects (regions vs clips)
- `set_clip_label` vs `set_bus_label` — different target objects
- `get_track_info` vs `get_region_info` — different target objects

### Removed duplicates (v1.9.4):

- `delete_signature_event` → removed. `delete_signature_change` is richer (position match + index, returns updated event list).
- `list_aux_sends` → removed. `list_sends` is richer (target_bus_name, send_level_db, routing, send_pan via box-level access).

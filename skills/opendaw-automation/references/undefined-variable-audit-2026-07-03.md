# Undefined Variable Audit: safe_ Pattern (2026-07-03)

## The bugs

Two MCP tools used `safe_<param>` variables in f-string JS interpolation but never assigned them — classic copy-paste error where the sanitization line was forgotten.

### Bug 1: `create_value_clip` — undefined `safe_name`
```python
# BEFORE (broken):
async def mcp_opendaw_create_value_clip(unit_index: int, track_index: int, name: str, clip_index: int) -> str:
    clip_idx = clip_index
    result = await bridge.evaluate(f"""() => {{
        ...
        clip = h.api.createValueClip(targetTrack, clipIdx, {{name: "{safe_name}"}});  # NameError!
    }}""")
```
`safe_name` referenced in f-string but never defined. Calling this tool would crash with `NameError: name 'safe_name' is not defined`.

### Bug 2: `set_region_position` — undefined `safe_region_type`
```python
# BEFORE (broken):
async def mcp_opendaw_set_region_position(..., region_type: str) -> str:
    result = await bridge.evaluate(f"""() => {{
        const rType = "{safe_region_type}";  # NameError!
    }}""")
```
Same pattern — `safe_region_type` used in interpolation, never assigned.

### Fix
Add the sanitization line before the f-string:
```python
safe_name = name.replace('"', '').replace('\\', '').replace("'", "")
safe_region_type = region_type.replace('"', '').replace('\\', '').replace("'", "")
```

## Detection: AST scan for undefined safe_ variables

```python
import ast, re

with open('server.py') as f:
    source = f.read()

tree = ast.parse(source)

issues = []
for node in ast.walk(tree):
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        continue
    func_source = ast.get_source_segment(source, node)
    if not func_source:
        continue
    # Find all safe_ variable names used
    safe_vars = set(re.findall(r'\b(safe_\w+)\b', func_source))
    for var in safe_vars:
        # Check if it's assigned in this function scope
        assigned = False
        for child in ast.walk(node):
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Name) and target.id == var:
                        assigned = True
        if not assigned:
            issues.append(f'{node.name}: uses {var} but never assigns it')

for i in issues:
    print(f'  {i}')
```

This catches the pattern where a `safe_` prefixed variable is referenced (typically in an f-string) but the assignment line was accidentally omitted — usually due to copy-paste from another tool that did have the sanitization.

## Why this happens

The opendaw-mcp codebase has ~232 tools, most following the same pattern:
1. Receive a `str` param
2. Sanitize: `safe_x = x.replace('"', '').replace('\\', '').replace("'", "")`
3. Use `{safe_x}` in the f-string JS template

When adding a new tool by copying an existing one, step 2 can be accidentally skipped if the developer focuses on the JS body (step 3) and forgets the Python sanitization preamble. The f-string will still be valid Python syntax — the NameError only fires at runtime when the tool is called.

## Prevention

- **Always run the AST scan** before committing new tools
- **Add to CI**: the `audit_str_params.py` script in `scripts/` already checks for unsanitized str params — extend it to also check for undefined `safe_` variables
- **E2E test every new tool**: even a basic smoke test would catch NameError immediately

## Related audit scripts

- `scripts/audit_str_params.py` — checks str params for sanitization
- `scripts/audit_unsanitized_js.py` — checks for raw JS injection
- The AST scan above should be added as `scripts/audit_undefined_safe_vars.py`

## Session context

Found during v1.8.0 code quality audit pass. Both bugs were pre-existing (not introduced in v1.8.0). The `create_value_clip` tool was added in an earlier session, `set_region_position` in another. Neither had been E2E tested with their `name`/`region_type` parameters — only the numeric params were tested.

# Release & Publishing Workflow

## Version Bump

Three files must stay in sync:
1. `pyproject.toml` → `version = "X.Y.Z"`
2. `server.json` → `"version": "X.Y.Z"`
3. `server.py` → `print("opendaw-mcp X.Y.Z — NNN MCP tools")` (in `main()` --version)

Tool count references to update: README.md badge + body, TOOL_CATALOG.md header + total, CI threshold in `.github/workflows/ci.yml` (two assertions).

## PyPI Publish

```bash
# Token stored in credman: pypi/__token__
source venv/bin/activate
pip install build twine  # if not yet installed
rm -rf dist build
python3 -m build
TWINE_PASSWORD="<token>" TWINE_USERNAME="__token__" python3 -m twine upload dist/opendaw_mcp-VERSION*
```

Verify: `pip index versions opendaw-mcp`

## GitHub Release

```bash
gh release create vX.Y.Z --title "vX.Y.Z — <short desc>" --notes "<changelog>"
```

## Catalog Updates (after publish)

Three external catalogs need comment updates per release:
- **punkpeye/awesome-mcp-servers PR #9133** — `gh pr comment 9133 --repo punkpeye/awesome-mcp-servers`
- **chatmcp/mcpso issue #3003** — `gh issue comment 3003 --repo chatmcp/mcpso`
- **YuzeHao2023/Awesome-MCP-Servers issue #338** — `gh issue comment 338 --repo YuzeHao2023/Awesome-MCP-Servers`

All wait for maintainer review. Do NOT open new issues — just update existing ones.

## Unit Test Pattern

Tests live in `tests/test_utils.py`. Pure Python, no bridge required.
78 tests covering: JSON helpers, WAV parsing, LUFS computation, orchestration curves (linear/exp/log), chord theory, drum notation, song structure parsing.

When adding orchestration math tests: mirror the JS interpolation formula in Python test methods, test boundary values (t=0, t=1) and curve characteristics (exp accelerates, log decelerates).

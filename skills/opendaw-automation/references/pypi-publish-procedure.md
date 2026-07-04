# PyPI Publish Procedure

## Prerequisites
- PyPI token in credentials.db: `pypi` / `ameobius` (password column = full `pypi-AgE...` token)
- **If the user gives you a token, SAVE IT IMMEDIATELY** — do not just use it inline. Previous sessions failed to persist it 3×, causing user frustration.
- `uv` installed (use `uv build` + `uv publish`, NOT `python3 -m build` + `twine upload`)

## Steps

```bash
cd /home/ameobius/projects/creative-studio/agent-daw/opendaw-mcp
source venv/bin/activate

# 1. Bump version in pyproject.toml, server.json, server.py --version line, README changelog
# 2. Run tests (unit only is fine, E2E auto-skips without Vite)
python3 -m pytest tests/test_utils.py -q

# 3. Ruff check
ruff check . --fix  # auto-fix what it can, then manually fix remaining

# 4. Build (uv, NOT python3 -m build)
uv build  # produces dist/opendaw_mcp-<VERSION>-py3-none-any.whl + .tar.gz

# 5. Publish (uv, NOT twine)
uv publish --token "pypi-AgE..."  # reads all files in dist/

# 6. Verify on PyPI
curl -s https://pypi.org/pypi/opendaw-mcp/json | python3 -c "import sys,json; d=json.load(sys.stdin); print('latest:', d['info']['version'])"

# 7. Git tag (triggers Docker publish + MCP Registry via GitHub Actions)
git tag v<VERSION> && git push origin v<VERSION>

# 8. GitHub Release
gh release create v<VERSION> dist/*.whl dist/*.tar.gz --title "v<VERSION> — ..." --notes "..."
```

## CI Threshold Pitfall (CRITICAL)

CI counts tools with `n.name.startswith('mcp_opendaw_')` prefix.
This EXCLUDES `start`, `stop`, `evaluate` (3 non-tool async defs).
So: 261 total async defs - 3 = **258 mcp_opendaw_* tools**.
CI threshold must be **258**, NOT 261.

Setting it higher causes CI failure: `AssertionError: Expected at least 258 tools, got 257`

Check locally before pushing:
```bash
python3 -c "import ast; tree=ast.parse(open('server.py').read()); tools=[n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef) and n.name.startswith('mcp_opendaw_')]; print(len(tools))"
```

## Docker Auto-Publish

Tag push (`git tag v*`) triggers `.github/workflows/publish-mcp.yml`:
- Builds Docker image
- Pushes to `ghcr.io/ameobius/opendaw-mcp:<VERSION>` and `:latest`
- Publishes to MCP Registry

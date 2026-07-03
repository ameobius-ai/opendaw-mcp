# Contributing to openDAW MCP

Thanks for your interest in contributing! This project wraps [openDAW](https://github.com/andremichelle/openDAW) behind an MCP server, enabling AI agents to control a browser-based DAW programmatically.

## Getting Started

1. Fork the repo and clone your fork
2. Set up the development environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   playwright install chromium
   ```
3. You'll also need a running openDAW instance (see [README](README.md) for setup)

## Adding a New MCP Tool

Each tool is a Python async function decorated with `@mcp.tool()`. Tools communicate with openDAW via `bridge.evaluate()` which runs JavaScript in the headless Chromium context.

### Tool Template

```python
@mcp.tool()
async def mcp_opendaw_my_tool(param: str) -> str:
    """One-line description.

    Detailed description of what the tool does and when to use it.

    param: Parameter description.

    Returns description of the result.
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            // Use DAW_HELPERS for boilerplate-free access
            const au = h.au(0);
            // ... your logic ...
            return {{success: true, data: "result"}};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)
```

### Guidelines

1. **Use DAW_HELPERS** — `h.au(i)`, `h.track(auIdx, trackIdx)`, `h.region(au, track, reg)`, `h.modify(fn)`. This eliminates boilerplate and keeps tools short.

2. **All box mutations inside `editing.modify()`** — openDAW requires a transactional context for any state changes. Use `h.modify(fn)` or `window.DAW.editing.modify(() => { ... })`.

3. **Error handling** — wrap in try/catch and return `{error: e.message}`. Never let exceptions escape to the MCP layer.

4. **Descriptive docstrings** — the docstring is what the AI agent reads to understand the tool. Be specific about parameters, valid ranges, and return values.

5. **Escape curly braces in f-strings** — JavaScript `{` and `}` must be doubled as `{{` and `}}` inside Python f-strings.

6. **Test your tool** — start Vite + bridge and call the tool with edge cases (empty project, invalid indices, missing content).

7. **Update TOOL_CATALOG.md** — add your tool to the appropriate section.

8. **Update the tool count** in README.md if you add multiple tools.

### DAW_HELPERS Reference

| Helper | Description |
|--------|-------------|
| `h.au(i)` | Get audio unit adapter by index |
| `h.track(auIdx, trackIdx)` | Get track adapter |
| `h.region(au, track, reg)` | Get region adapter |
| `h.instrumentAU()` | Get first instrument AU |
| `h.modify(fn)` | Wrapper for `editing.modify()` |
| `h.allAUs()` | List all audio unit adapters |

### Key Patterns

- **Effect parameters**: `fx.namedParameter` gives access to named params, each with `.field`, `.getValue()`, `.setValue()`
- **Note events**: `reg.events.targetVertex.unwrap("events").box` → `.events.pointerHub.incoming()` for note boxes
- **Adapters**: `p.boxAdapters.adapterFor(box, AdapterClass)` to get a typed adapter from a box
- **Signature track**: `p.rootBoxAdapter.timeline.signatureTrack` for time signature operations

## DSP Scripts

Scriptable device scripts (Werkstatt/Apparat/Spielwerk) live in `scripts/`. See existing scripts for the `// @param` and `// @sample` declaration format.

## Pull Requests

1. Create a feature branch: `git checkout -b feat/my-feature`
2. Commit with conventional commits: `feat: ...`, `fix: ...`, `docs: ...`
3. Push and open a PR with a clear description
4. Ensure CI passes (syntax check + tool count verification)

## License

By contributing, you agree your contributions are licensed under Apache-2.0.

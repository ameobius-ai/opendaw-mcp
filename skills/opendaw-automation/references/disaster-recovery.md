# Disaster Recovery — server.py Destruction (July 2026 incident)

## What happened

A `write_file` call with `path=server.py` and `content="PLACEHOLDER"` overwrote the entire 8500-line MCP server (133 tools, 345KB). The file was NOT in any git repo. No manual backups existed. Recovery took hours of `.pyc` bytecode disassembly.

## .pyc extraction — what works (Python 3.13)

`__pycache__/server.cpython-313.pyc` contains the last compiled bytecode. Key extraction technique:

```python
import marshal, struct, types, dis

with open('__pycache__/server.cpython-313.pyc', 'rb') as f:
    f.read(16)  # skip header
    code = marshal.load(f)

# Function names: co_names at module level
func_names = [n for n in code.co_names if n.startswith('mcp_opendaw_')]

# For each function: args via co_varnames[:co_argcount]
# JS f-strings: walk BUILD_STRING(n) backwards collecting LOAD_CONST + FORMAT_SIMPLE
# FORMAT_SIMPLE = Python 3.13 rename of FORMAT_VALUE (f-string interpolation)
```

### What .pyc gives you
- All string constants (JS f-strings, docstrings, paths, error messages)
- Function names + arg names via `co_varnames[:co_argcount]`
- f-string interpolations via `BUILD_STRING` + `FORMAT_SIMPLE` opcodes
- Module-level constants (docstring, paths, URLs)

### What .pyc does NOT give you
- Python control flow (if/else, for loops, try/except)
- Import statements
- Decorator usage

### JS f-string brace escaping
Reconstructed JS has SINGLE braces — both `{arg_name}` and JS `{ key: value }`. To write back as f-string, JS braces must be doubled `{{` `}}` while Python interpolations stay single `{arg}`.

### Reconstruction limitations (caused artifacts — see references/reconstruction-artifacts.md)
- `catch(e) {}` — empty catch bodies dropped (zero-length string constants skipped)
- Boolean/string interpolations lost → `const X = ;`
- Python variable names doubled → `{{var}}` instead of `{var}` (36 sites)
- `\n` in JS strings became real newlines (f-string interprets `\n`)
- Missing Python computations before f-strings (MIDI parsing, file reading, base64)

All artifacts documented and fixed in `references/reconstruction-artifacts.md`.

## bridge.start() works fine via import (CORRECTION)

Previous notes claimed `bridge.start()` hangs when importing `server.py`. **FALSE.** Hangs were in broken test scripts with `atexit`/`asyncio.run` conflicts.

```python
import server  # imports fine, atexit registered, no hang
asyncio.run(server.bridge.start())  # returns normally in ~10s
result = await server.bridge.evaluate('() => 42')  # returns 42
```

Always import `server` and use `server.bridge` — don't instantiate your own. Kill stale Vite before testing: `lsof -i :5174` + `kill <pid>`.

## Prevention checklist
- [ ] Initialize git in `opendaw-mcp/`: `git init && git add -A && git commit -m "initial"`
- [ ] Add `.gitignore` for `venv/`, `__pycache__/`, `exports/`
- [ ] NEVER use `write_file` on server.py — always `patch` (write_file overwrites ENTIRE file)
- [ ] Keep `.pyc` cache as accidental backup
- [ ] Run JS syntax validation (references/testing-procedures.md §1) after ANY server.py change
- [ ] Run E2E test (templates/e2e_test.py) after structural changes

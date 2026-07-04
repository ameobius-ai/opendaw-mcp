# Packaging opendaw-mcp for GitHub Publication

## When to use
When preparing the opendaw-mcp project (or similar agent-built MCP server) for public GitHub release.

## Steps

### 1. Audit for personal data
- `grep -rn "/home/ameobius" .` — hardcoded paths in server.py, test files
- `grep -riE "(token|password|secret|api_key|credential)" .` — exclude JS variable names like `tokens` (false positives from @param parser)
- Check `.env`, backup files (`*.backup.*`, `*.final.*`, `*_recovered.py`)

### 2. Replace hardcoded paths with env vars
```python
# Before:
DAW_HOST_DIR = "/home/ameobius/projects/creative-studio/agent-daw/headless-daw"
DAW_URL = "http://localhost:5174"
EXPORT_DIR = "/home/ameobius/projects/creative-studio/agent-daw/exports"

# After:
DAW_HOST_DIR = os.environ.get("OPENDAW_HOST_DIR", os.path.join(os.path.dirname(__file__), "..", "headless-daw"))
DAW_URL = os.environ.get("OPENDAW_URL", "http://localhost:5174")
EXPORT_DIR = os.environ.get("OPENDAW_EXPORT_DIR", os.path.join(os.path.dirname(__file__), "..", "exports"))
```

Also replace Node.js hardcoded path:
```python
# Before:
env["PATH"] = env.get("HOME","") + "/.nvm/versions/node/v23.11.1/bin:" + env.get("PATH","")
# After:
node_dir = os.environ.get("NODE_BIN_DIR", "")
if node_dir:
    env["PATH"] = node_dir + ":" + env.get("PATH", "")
```

### 3. Clean git history (critical)
Orphan branch approach — creates a single clean commit with no history of personal paths:
```bash
git checkout --orphan clean-main
git add -A
git commit -m "openDAW MCP — N MCP tools for agent-native DAW control ..."
git branch -D main
git branch -m clean-main main
# Remove any worktrees and old branches that still reference old history
git worktree remove .worktrees/<name> --force
git branch -D <old-branch>
```

Verify:
```bash
git log --all -p | grep -iE "/home/ameobius" | wc -l   # must be 0
git log --all -p | grep -iE "(token|password|secret)" | grep -v "tokens\b" | wc -l  # must be 0
```

### 4. Remove test files from tracking
Test files (`test_*.py`) contain hardcoded local paths. Untrack them:
```bash
git rm --cached test_*.py
```
Add to `.gitignore`:
```
test_*.py
*.backup
*.final
*_recovered.py
exports/
*.wav
*.ogg
```

### 5. Delete backup files from disk
```bash
rm -f server.py.backup.* server.py.final.* server_recovered.py
```

### 6. Create required files
- **LICENSE** — Apache-2.0 (matches openDAW upstream)
- **README.md** — architecture diagram, features list, quick start, env vars table, DSP scripts table, limitations
- **requirements.txt** — `playwright>=1.40`, `mcp>=0.3`

### 7. Create GitHub repo and push
```bash
gh repo create opendaw-mcp --public --description "..."
git remote add origin https://github.com/AMEOBIUS/opendaw-mcp.git
git push -u origin main
```

## Pitfalls
- **Worktree branches retain old history** — `git log --all -p` will still show personal paths from worktree branches. Must remove worktrees and delete those branches before verifying clean history.
- **`tokens` in JS @param parser is NOT a secret** — false positive when grepping for "token". Filter with `grep -v "tokens\b"`.
- **Test files with local paths** — don't just .gitignore them; `git rm --cached` to untrack if already committed.
- **Orphan branch is the cleanest approach** — squashing keeps intermediate commits with old paths. Orphan = single fresh commit.

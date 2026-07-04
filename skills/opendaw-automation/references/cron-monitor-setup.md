# Cron Monitor Setup (2026-07-03)

## Pattern

Create a shell script that checks upstream/PR status and delivers to Telegram.
Use `hermes cron create` with `--no-agent` mode (script stdout delivered directly,
no LLM call needed — classic watchdog pattern).

## hermes cron create syntax

```bash
# 1. Copy script to ~/.hermes/scripts/ (REQUIRED — must be relative path)
cp /path/to/script.sh ~/.hermes/scripts/script.sh

# 2. Create cron job — reference by FILENAME only, not absolute path
hermes cron create "0 9 * * *" "job name" \
  --name "human-name" \
  --deliver telegram \
  --script "script.sh" \
  --no-agent
```

## Key gotchas

- **Script path must be relative to `~/.hermes/scripts/`** — passing `/home/user/.hermes/scripts/script.sh` fails with "Script path must be relative". Use just `"script.sh"`.
- **`--no-agent` mode** — script IS the job, stdout delivered verbatim. Empty stdout = silent (no message sent). This is correct for watchdog/monitor scripts.
- **`--deliver telegram`** — delivers to the user's Telegram. Also available: `origin`, `local`, `discord`, `signal`, `platform:chat_id`.
- **Schedule format** — cron syntax `"0 9 * * *"` (daily 9am) or shorthand `"30m"` (every 30 min), `"every 2h"`.

## opendaw_upstream_monitor.sh (working example)

Checks upstream openDAW for new commits, PR #280 status, and MCP tool count.
Delivers daily at 9am to Telegram.

```bash
#!/bin/bash
cd /home/ameobius/projects/creative-studio/agent-daw/openDAW 2>/dev/null || exit 0
git fetch upstream 2>/dev/null

NEW_COMMITS=$(git log --oneline main..upstream/main 2>/dev/null | head -5)
PR_STATUS=$(gh pr view 280 --repo andremichelle/openDAW --json state --jq '.state' 2>/dev/null)

MSG="🦀 openDAW daily monitor\n\n"
if [ -n "$NEW_COMMITS" ]; then
    MSG+="⚠️ Upstream has new commits:\n$NEW_COMMITS\n\n"
else
    MSG+="✅ Upstream: no new commits\n\n"
fi
MSG+="PR #280: $PR_STATUS\n\n"

TOOL_COUNT=$(python3 -c "
import ast
with open('/home/ameobius/projects/creative-studio/agent-daw/opendaw-mcp/server.py') as f:
    tree = ast.parse(f.read())
tools = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith('mcp_opendaw_')]
print(len(tools))
" 2>/dev/null)
MSG+="MCP tools: $TOOL_COUNT\ngithub.com/AMEOBIUS/opendaw-mcp"

echo "$MSG"
```

## Created job

- Job ID: `96df0f4d2ded`
- Name: `opendaw-monitor`
- Schedule: `0 9 * * *` (daily 9am MSK)
- Deliver: telegram
- Mode: no-agent (script stdout → Telegram directly)
- Next run: 2026-07-04T09:00:00+03:00

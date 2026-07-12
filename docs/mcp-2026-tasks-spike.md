# MCP 2025-07-28 Tasks Spike — Design

## Problem

Render and stem separation take 5-30 seconds. Current MCP tools block
the client for the full duration. Clients can't show progress, can't
cancel, can't run concurrent renders.

## MCP Tasks extension (2025-06-18 → 2026-07-28)

The Tasks extension introduces a handle-based pattern:

```
client → server: create_task(tool="render_full", args={...})
server → client: { task_id: "uuid", status: "pending" }

client → server: get_task(task_id)
server → client: { status: "running", progress: 0.45 }

client → server: get_task(task_id)
server → client: { status: "completed", result: {...} }
```

## Implementation

`opendaw_mcp/tasks.py` — in-process task registry:

| Function | Purpose |
|---|---|
| `create_task(tool, args)` | Returns task_id immediately |
| `run_task(task_id, coro_factory)` | Executes async, updates status |
| `get_task(task_id)` | Poll: status, progress, result |
| `cancel_task(task_id)` | Request cancellation |
| `list_tasks()` | List all tasks |

Task states: `pending → running → completed | failed | cancelled`

## Feature flag

```
OPENDAW_MCP_TASKS=1 python -m opendaw_mcp
```

Default: off. Existing synchronous tool calls unchanged.

## Host implications (2026-07-28)

- MCP spec moves from `initialize` to `server/discover` — tasks
  capability advertised there
- `_meta` field on requests carries task IDs
- Tasks may become a required capability for MCP Apps (sandboxed HTML UI)

## What's stub vs real

- **Stub**: MCP protocol integration (discover, _meta) — needs SDK v2
- **Real**: Task registry, async execution, cancellation, status polling
- **Real**: Unit tested with mock coroutines

## Compatibility

Tasks are an extension. Clients that don't support Tasks use the
existing synchronous tool calls. No breaking change.

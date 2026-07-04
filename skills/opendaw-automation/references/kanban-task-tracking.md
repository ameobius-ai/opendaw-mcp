# Hermes Kanban Task Tracking for openDAW

Track openDAW blockers and feature tasks on the `producers` kanban board via `hermes kanban` CLI.

**User directive**: "kanban_show/kanban_create/kanban_complete tools - чекни - туда будешь блокеры вписывать" — use kanban, not bd, for openDAW task tracking.

## Why kanban not bd

bd is the security-workstation issue tracker (beads DB, Dolt sync). Kanban is Hermes-native:
- Shared across profiles (producers, redops, default boards)
- Supports blocking with typed kinds (needs_input, dependency, capability, transient)
- Workers spawned by dispatcher get kanban tools automatically
- `hermes kanban` CLI works from any terminal

## Board

The `producers` board is already active:
```
hermes kanban boards list
# ●   producers    Producers    ready=2
```

## Key commands

```bash
# List tasks
hermes kanban list

# Create a task
hermes kanban create "title" --body "description" --priority 3 --json

# Show task details + events + comments
hermes kanban show <task_id>

# Block a task (waiting on external input)
hermes kanban block <task_id> "reason text" --kind needs_input

# Complete a task
hermes kanban complete <task_id>

# Add a progress comment
hermes kanban comment <task_id> "update text"

# Unblock a previously blocked task
hermes kanban unblock <task_id>
```

## Block kinds

| Kind | When to use | Behavior |
|------|-------------|----------|
| `needs_input` | Waiting on human/external (PR review, user decision) | Goes to blocked, needs human unblock |
| `dependency` | Waiting on parent task completion | Stays in todo, auto-promotes when parents finish |
| `capability` | Missing tool/feature capability | Goes to blocked |
| `transient` | Maybe-flaky failure, retry might work | Goes to blocked, repeated re-blocks → triage |

## Current openDAW tasks on producers board (July 2026)

| Task ID | Title | Status |
|---------|-------|--------|
| t_39d3a5bd | set_audio_region_fade — Fading ObjectField | done |
| t_59a656f2 | set_audio_region_gain — AudioRegionBox.gain | done |
| t_63c7e3cb | list_value_regions — ValueRegionBox | done |
| t_56314df3 | PR #280 monitor — await review | blocked (needs_input) |

## Enabling kanban toolset in agent sessions

The `kanban` toolset is now **ENABLED** (session 9, July 2026). Removed from `agent.disabled_toolsets` and added to `discord` platform toolsets in `~/.hermes/config.yaml`.

Gating logic (`tools/kanban_tools.py`):
- `_check_kanban_mode()` → True if `HERMES_KANBAN_TASK` env set OR `kanban` in toolsets config
- `_check_kanban_orchestrator_mode()` → True if NOT a worker task AND `kanban` in toolsets
- Workers get lifecycle tools (show/complete/block/heartbeat/comment/create/link)
- Orchestrators additionally get board tools (list/unblock)

Kanban tools available in Discord sessions after restart: `kanban_show`, `kanban_create`, `kanban_complete`, `kanban_block`, `kanban_comment`, `kanban_link`, `kanban_heartbeat`, `kanban_list`, `kanban_unblock`.

"""
MCP Tasks — production long-ops API for opendaw-mcp.

Wraps slow operations (render, stems) as async tasks with:
1. create_task — returns a task handle immediately
2. get_task — poll status (pending → running → completed/failed/cancelled)
3. cancel_task — request cancellation

Design: in-process task registry with progress callbacks.
Default stdio path unchanged. Enable with OPENDAW_MCP_TASKS=1.

Compatible with current MCP clients — tasks are an extension, not a
replacement for synchronous tool calls.
"""
import asyncio
import os
import time
import uuid
from enum import Enum

# Max tasks to keep in memory (older pruned)
_MAX_TASKS = int(os.environ.get("OPENDAW_MCP_TASKS_MAX", "100"))
# Task TTL in seconds (completed tasks pruned after this)
_TASK_TTL = float(os.environ.get("OPENDAW_MCP_TASKS_TTL", "3600"))

_tasks: dict[str, dict] = {}


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


def _prune_old() -> None:
    """Remove completed/failed tasks older than TTL."""
    now = time.time()
    to_remove = [
        tid for tid, t in _tasks.items()
        if t["status"] in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
        and t["completed_at"] is not None
        and (now - t["completed_at"]) > _TASK_TTL
    ]
    for tid in to_remove:
        del _tasks[tid]
    # Hard cap on total tasks
    if len(_tasks) > _MAX_TASKS:
        oldest = sorted(_tasks.values(), key=lambda x: x["created_at"])[:len(_tasks) - _MAX_TASKS]
        for t in oldest:
            _tasks.pop(t["id"], None)


def create_task(tool_name: str, args: dict) -> str:
    """Create a task handle for a long-running operation."""
    _prune_old()
    task_id = str(uuid.uuid4())
    _tasks[task_id] = {
        "id": task_id,
        "tool": tool_name,
        "args": args,
        "status": TaskStatus.PENDING,
        "created_at": time.time(),
        "started_at": None,
        "completed_at": None,
        "result": None,
        "error": None,
        "progress": 0.0,
    }
    return task_id


async def run_task(task_id: str, coro_factory, progress_callback=None):
    """Execute a task asynchronously, updating status.

    progress_callback: optional callable(float) accepting 0.0–1.0 progress.
    """
    if task_id not in _tasks:
        raise KeyError(f"Unknown task: {task_id}")
    task = _tasks[task_id]
    if task["status"] == TaskStatus.CANCELLED:
        return
    task["status"] = TaskStatus.RUNNING
    task["started_at"] = time.time()

    def _update_progress(p: float):
        if task_id in _tasks and _tasks[task_id]["status"] == TaskStatus.RUNNING:
            _tasks[task_id]["progress"] = max(0.0, min(1.0, p))

    cb = progress_callback or _update_progress
    try:
        result = await coro_factory(cb)
        if _tasks[task_id]["status"] == TaskStatus.CANCELLED:
            return
        task["result"] = result
        task["status"] = TaskStatus.COMPLETED
        task["progress"] = 1.0
    except asyncio.CancelledError:
        task["status"] = TaskStatus.CANCELLED
    except Exception as e:
        task["status"] = TaskStatus.FAILED
        task["error"] = str(e)
    finally:
        task["completed_at"] = time.time()


def get_task(task_id: str) -> dict:
    """Get task status and result."""
    if task_id not in _tasks:
        raise KeyError(f"Unknown task: {task_id}")
    task = _tasks[task_id]
    return {
        "id": task["id"],
        "tool": task["tool"],
        "status": task["status"].value,
        "progress": task["progress"],
        "result": task["result"],
        "error": task["error"],
        "elapsed_s": round(
            (task["completed_at"] or time.time()) - task["started_at"], 1
        ) if task["started_at"] else None,
    }


def cancel_task(task_id: str) -> bool:
    """Request task cancellation."""
    if task_id not in _tasks:
        return False
    task = _tasks[task_id]
    if task["status"] in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
        return False
    task["status"] = TaskStatus.CANCELLED
    return True


def list_tasks() -> list[dict]:
    """List all tasks (most recent first)."""
    _prune_old()
    return [
        {
            "id": t["id"],
            "tool": t["tool"],
            "status": t["status"].value,
            "progress": t["progress"],
        }
        for t in sorted(_tasks.values(), key=lambda x: x["created_at"], reverse=True)
    ]

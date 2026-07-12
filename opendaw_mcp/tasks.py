"""
MCP Tasks spike — experimental long-ops API for opendaw-mcp.

MCP 2025-06-18 introduces Tasks extension for long-running operations.
This module provides a Tasks-shaped API for render/stem operations:

1. create_task — returns a task handle immediately
2. get_task — poll status (pending → running → completed/failed/cancelled)
3. cancel_task — request cancellation

Design: wraps existing async tools with a task registry. Default stdio
path unchanged. Enable with OPENDAW_MCP_TASKS=1.

Compatible with current MCP clients — tasks are an extension, not a
replacement for synchronous tool calls.
"""
import asyncio
import time
import uuid
from enum import Enum

# Task registry (in-process; for multi-process use Redis/db)
_tasks: dict[str, dict] = {}


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


def create_task(tool_name: str, args: dict) -> str:
    """Create a task handle for a long-running operation."""
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


async def run_task(task_id: str, coro_factory):
    """Execute a task asynchronously, updating status."""
    if task_id not in _tasks:
        raise KeyError(f"Unknown task: {task_id}")
    task = _tasks[task_id]
    if task["status"] == TaskStatus.CANCELLED:
        return
    task["status"] = TaskStatus.RUNNING
    task["started_at"] = time.time()
    try:
        result = await coro_factory()
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
    return [
        {
            "id": t["id"],
            "tool": t["tool"],
            "status": t["status"].value,
            "progress": t["progress"],
        }
        for t in sorted(_tasks.values(), key=lambda x: x["created_at"], reverse=True)
    ]

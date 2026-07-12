"""Unit tests for opendaw_mcp.tasks — MCP Tasks production."""
import asyncio
import pytest
from opendaw_mcp.tasks import (
    create_task,
    run_task,
    get_task,
    cancel_task,
    list_tasks,
    _tasks,
    _prune_old,
    _MAX_TASKS,
    _TASK_TTL,
)


@pytest.fixture(autouse=True)
def clear_tasks():
    _tasks.clear()
    yield
    _tasks.clear()


def _run(coro):
    """Run async test synchronously."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestCreateTask:
    def test_returns_uuid(self):
        tid = create_task("render_full", {"bpm": 120})
        assert len(tid) == 36

    def test_initial_status_pending(self):
        tid = create_task("render_full", {})
        task = get_task(tid)
        assert task["status"] == "pending"
        assert task["progress"] == 0.0

    def test_stores_tool_and_args(self):
        tid = create_task("render_stems", {"model": "demucs"})
        task = get_task(tid)
        assert task["tool"] == "render_stems"


class TestRunTask:
    def test_completes_successfully(self):
        tid = create_task("render", {})

        async def coro(cb):
            cb(0.5)
            await asyncio.sleep(0.01)
            return {"samples": 44100}

        _run(run_task(tid, coro))
        task = get_task(tid)
        assert task["status"] == "completed"
        assert task["result"]["samples"] == 44100
        assert task["progress"] == 1.0

    def test_progress_callback_updates(self):
        tid = create_task("render", {})
        progress_values = []

        async def coro(cb):
            for p in [0.1, 0.3, 0.7, 0.9]:
                cb(p)
                progress_values.append(get_task(tid)["progress"])
                await asyncio.sleep(0.01)
            return {"ok": True}

        _run(run_task(tid, coro))
        assert progress_values == [0.1, 0.3, 0.7, 0.9]

    def test_records_elapsed(self):
        tid = create_task("render", {})

        async def coro(cb):
            await asyncio.sleep(0.05)
            return {"ok": True}

        _run(run_task(tid, coro))
        task = get_task(tid)
        assert task["elapsed_s"] is not None
        assert task["elapsed_s"] >= 0.0

    def test_failed_task(self):
        tid = create_task("render", {})

        async def coro(cb):
            raise RuntimeError("bridge offline")

        _run(run_task(tid, coro))
        task = get_task(tid)
        assert task["status"] == "failed"
        assert "bridge offline" in task["error"]


class TestCancelTask:
    def test_cancel_before_start(self):
        tid = create_task("render", {})
        assert cancel_task(tid) is True
        task = get_task(tid)
        assert task["status"] == "cancelled"

    def test_cancel_unknown(self):
        assert cancel_task("nonexistent") is False

    def test_cancel_after_complete(self):
        tid = create_task("render", {})

        async def coro(cb):
            return {"ok": True}

        _run(run_task(tid, coro))
        assert cancel_task(tid) is False


class TestListTasks:
    def test_lists_all(self):
        create_task("render", {})
        create_task("stems", {})
        tasks = list_tasks()
        assert len(tasks) == 2

    def test_empty(self):
        assert list_tasks() == []


class TestPruning:
    def test_prune_old_removes_completed(self):
        tid = create_task("render", {})

        async def coro(cb):
            return {"ok": True}

        _run(run_task(tid, coro))
        assert len(_tasks) == 1
        # Simulate old completion time
        _tasks[tid]["completed_at"] = 0.0  # epoch
        _prune_old()
        assert len(_tasks) == 0

    def test_hard_cap(self):
        for i in range(_MAX_TASKS + 5):
            create_task("render", {"i": i})
        _prune_old()
        assert len(_tasks) <= _MAX_TASKS

"""The async subprocess helper (ch. 8.8, 8.10; Q17, Q19)."""

import asyncio
import logging
import os
import shutil
import sys
import tempfile
import textwrap
import time
from asyncio import unix_events
from pathlib import Path

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.solvers.process import run_process

pytestmark = pytest.mark.asyncio

# A fake external command: echoes stdin, writes an output file, exits with the code in argv[1].
ECHO_SCRIPT = textwrap.dedent(
    """
    import os, sys
    data = sys.stdin.read()
    sys.stdout.write("cwd-files=" + ",".join(sorted(os.listdir("."))) + "\\n")
    sys.stdout.write("stdin=" + data)
    sys.stderr.write("warn\\n")
    open("out.txt", "w").write(open("in.txt").read().upper())
    sys.exit(int(sys.argv[1]))
    """
)

# Writes "<pid> <grandchild pid> <cwd>" to the marker file given in argv[1], then sleeps.
SLEEP_SCRIPT = textwrap.dedent(
    """
    import os, subprocess, sys, time
    grandchild = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    with open(sys.argv[1], "w") as marker:
        marker.write(f"{os.getpid()} {grandchild.pid} {os.getcwd()}")
    time.sleep(60)
    """
)


@pytest.fixture
def script(tmp_path: Path) -> Path:
    path = tmp_path / "fake_tool.py"
    path.write_text(ECHO_SCRIPT)
    return path


async def test_runs_the_command_and_returns_its_output(script: Path) -> None:
    run = await run_process(
        {"in.txt": "abc"},
        "go\n",
        executable=sys.executable,
        args=[str(script), "0"],
        collect=["out.txt", "missing.txt"],
    )
    assert run.returncode == 0
    assert run.stdout == "cwd-files=in.txt\nstdin=go\n"
    assert run.stderr == "warn\n"
    assert run.files == {"out.txt": b"ABC"}


async def test_nonzero_exit_is_returned_not_raised(script: Path) -> None:
    run = await run_process(
        {"in.txt": b"x"}, "", executable=sys.executable, args=[str(script), "3"]
    )
    assert run.returncode == 3


BAD_NAMES = ["../escape.txt", "/abs.txt", "sub/file.txt", "", ".", ".."]


@pytest.mark.parametrize("name", BAD_NAMES)
async def test_rejects_file_names_that_leave_the_directory(name: str, script: Path) -> None:
    with pytest.raises(ValueError, match="plain file name"):
        await run_process({name: "x"}, "", executable=sys.executable, args=[str(script), "0"])


@pytest.mark.parametrize("name", BAD_NAMES)
async def test_rejects_collect_names_that_leave_the_directory(name: str, script: Path) -> None:
    with pytest.raises(ValueError, match="plain file name"):
        await run_process(
            {"in.txt": "x"},
            "",
            executable=sys.executable,
            args=[str(script), "0"],
            collect=[name],
        )


async def test_missing_executable_is_tool_unavailable(tmp_path: Path) -> None:
    with pytest.raises(FormulaError) as caught:
        await run_process({}, "", executable=str(tmp_path / "no_such_tool"))
    assert caught.value.category is ErrorCategory.TOOL_UNAVAILABLE
    assert caught.value.code == "tool_unavailable"
    assert caught.value.detail == {"executable": "no_such_tool"}
    assert str(tmp_path) not in caught.value.message


async def _start_sleeper(
    tmp_path: Path,
) -> tuple[asyncio.Task[object], int, int, Path]:
    """Start the sleeping fake tool and wait until it announced itself."""
    sleeper = tmp_path / "sleeper.py"
    sleeper.write_text(SLEEP_SCRIPT)
    marker = tmp_path / "marker.txt"
    task: asyncio.Task[object] = asyncio.create_task(
        run_process({}, "", executable=sys.executable, args=[str(sleeper), str(marker)])
    )
    pid, grandchild, cwd = await asyncio.to_thread(_read_marker, marker)
    return task, pid, grandchild, cwd


def _read_marker(marker: Path) -> tuple[int, int, Path]:
    """Wait (in a worker thread) until the fake tool wrote "<pid> <grandchild pid> <cwd>"."""
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if marker.exists() and marker.read_text().count(" ") >= 2:
            pid, grandchild, cwd = marker.read_text().split(" ", 2)
            return int(pid), int(grandchild), Path(cwd)
        time.sleep(0.02)
    msg = "the fake tool did not start"
    raise AssertionError(msg)


def _is_dir(path: Path) -> bool:
    return path.is_dir()


def _entries(path: Path) -> list[Path]:
    return list(path.iterdir())


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


async def _wait_dead(pid: int) -> bool:
    for _ in range(100):
        if not _alive(pid):
            return True
        await asyncio.sleep(0.02)
    return False


async def test_cancel_kills_the_process_group_and_removes_the_temp_dir(tmp_path: Path) -> None:
    task, pid, grandchild, cwd = await _start_sleeper(tmp_path)
    assert _is_dir(cwd)
    task.cancel()
    # Bounded: a kill that spares the grandchild leaves the pipes open and asyncio waits ~60 s.
    # Hitting the bound raises TimeoutError, which is not the CancelledError expected here.
    with pytest.raises(asyncio.CancelledError):
        async with asyncio.timeout(5):
            await task
    assert not _is_dir(cwd)
    assert await _wait_dead(pid)
    assert await _wait_dead(grandchild)


@pytest.fixture
def held_start(monkeypatch: pytest.MonkeyPatch) -> asyncio.Event:
    """Hold every subprocess start open after the child exists, until the event is set.

    The child is already running and writing, but ``create_subprocess_exec`` has not returned:
    the window in which a loaded machine lets a cancel arrive (GH #1188). Deterministic, so the
    test does not depend on CPU starvation.
    """
    gate = asyncio.Event()
    original = unix_events._UnixSubprocessTransport._connect_pipes  # type: ignore[attr-defined]  # asyncio internal, patched to hold the start open

    async def held(self: object, waiter: asyncio.Future[None]) -> None:
        await gate.wait()
        await original(self, waiter)  # type: ignore[arg-type]  # same call as asyncio's own

    monkeypatch.setattr(unix_events._UnixSubprocessTransport, "_connect_pipes", held)  # type: ignore[attr-defined]  # as above
    return gate


async def test_cancel_during_the_start_kills_the_group_and_removes_the_temp_dir(
    tmp_path: Path, held_start: asyncio.Event
) -> None:
    """GH #1188: the cancel arrives while ``create_subprocess_exec`` is still waiting.

    ``process`` is not assigned yet then, so the group was neither killed nor the cancel prompt:
    asyncio itself kills only the direct child and waits for the pipes the grandchild holds open.
    """
    task, pid, grandchild, cwd = await _start_sleeper(tmp_path)
    assert _is_dir(cwd)
    task.cancel()
    held_start.set()  # the start may now finish, but the cancel is already on its way
    with pytest.raises(asyncio.CancelledError):
        async with asyncio.timeout(5):
            await task
    assert not _is_dir(cwd)
    assert await _wait_dead(pid)
    assert await _wait_dead(grandchild)


async def test_a_second_cancel_while_the_start_is_settling_changes_nothing(
    tmp_path: Path, held_start: asyncio.Event
) -> None:
    task, pid, grandchild, cwd = await _start_sleeper(tmp_path)
    task.cancel()
    await asyncio.sleep(0.05)  # the task is now waiting for the held start to end
    task.cancel()
    held_start.set()
    with pytest.raises(asyncio.CancelledError):
        async with asyncio.timeout(5):
            await task
    assert not _is_dir(cwd)
    assert await _wait_dead(pid)
    assert await _wait_dead(grandchild)


async def test_a_budget_that_expires_during_the_start_kills_the_group(
    tmp_path: Path, held_start: asyncio.Event
) -> None:
    sleeper = tmp_path / "sleeper.py"
    sleeper.write_text(SLEEP_SCRIPT)
    marker = tmp_path / "marker.txt"
    asyncio.get_running_loop().call_later(0.5, held_start.set)
    budget = asyncio.timeout(0.2)
    with pytest.raises(TimeoutError):
        async with budget:
            await run_process({}, "", executable=sys.executable, args=[str(sleeper), str(marker)])
    assert budget.expired()
    pid, grandchild, cwd = _read_marker(marker)
    assert not _is_dir(cwd)
    assert await _wait_dead(pid)
    assert await _wait_dead(grandchild)


async def test_a_cancel_before_a_failing_start_ends_is_still_a_cancel_and_leaves_no_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))
    task = asyncio.create_task(run_process({}, "", executable=str(tmp_path / "no_such_tool")))
    await asyncio.sleep(0)  # the task waits for the start; the start has not run yet
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert _entries(scratch) == []


async def test_expired_budget_kills_the_process_and_removes_the_temp_dir(tmp_path: Path) -> None:
    sleeper = tmp_path / "sleeper.py"
    sleeper.write_text(SLEEP_SCRIPT)
    marker = tmp_path / "marker.txt"
    # The outer bound only guards against a hang; the budget itself must be what expired.
    guard = asyncio.timeout(6)
    budget = asyncio.timeout(1.0)
    with pytest.raises(TimeoutError):
        async with guard, budget:
            await run_process({}, "", executable=sys.executable, args=[str(sleeper), str(marker)])
    assert budget.expired()
    assert not guard.expired()
    pid, grandchild, cwd = _read_marker(marker)
    assert not _is_dir(cwd)
    assert await _wait_dead(pid)
    assert await _wait_dead(grandchild)


async def test_temp_dir_is_removed_after_a_normal_run(
    script: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))
    run = await run_process({"in.txt": "a"}, "", executable=sys.executable, args=[str(script), "0"])
    assert run.returncode == 0
    assert _is_dir(scratch)
    assert _entries(scratch) == []


async def test_a_failed_cleanup_is_logged_and_does_not_mask_the_result(
    script: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))

    def failing_rmtree(path: Path) -> None:
        msg = "busy"
        raise PermissionError(msg)

    monkeypatch.setattr(shutil, "rmtree", failing_rmtree)
    with caplog.at_level(logging.WARNING, logger="aero_kernel.solvers.process"):
        run = await run_process(
            {"in.txt": "a"}, "", executable=sys.executable, args=[str(script), "0"]
        )
    assert run.returncode == 0
    (record,) = [r for r in caplog.records if r.levelno == logging.WARNING]
    message = record.getMessage()
    assert "temp directory of external process not removed" in message
    assert "aero_kernel_" in message
    assert str(scratch) not in message


@pytest.fixture
def failing_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> pytest.LogCaptureFixture:
    """Make every temp-directory removal fail; temp dirs are created below ``tmp_path``."""
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))

    def failing_rmtree(path: Path) -> None:
        msg = "busy"
        raise PermissionError(msg)

    monkeypatch.setattr(shutil, "rmtree", failing_rmtree)
    caplog.set_level(logging.WARNING, logger="aero_kernel.solvers.process")
    return caplog


def _cleanup_warnings(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [
        r.getMessage()
        for r in caplog.records
        if "temp directory of external process not removed" in r.getMessage()
    ]


async def test_failed_cleanup_during_cancel_is_logged_and_cancelled_error_propagates(
    tmp_path: Path, failing_cleanup: pytest.LogCaptureFixture
) -> None:
    task, pid, _, _ = await _start_sleeper(tmp_path)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert await _wait_dead(pid)
    assert len(_cleanup_warnings(failing_cleanup)) == 1


async def test_failed_cleanup_during_timeout_is_logged_and_timeout_error_propagates(
    tmp_path: Path, failing_cleanup: pytest.LogCaptureFixture
) -> None:
    sleeper = tmp_path / "sleeper.py"
    sleeper.write_text(SLEEP_SCRIPT)
    marker = tmp_path / "marker.txt"
    with pytest.raises(TimeoutError):
        async with asyncio.timeout(1.0):
            await run_process({}, "", executable=sys.executable, args=[str(sleeper), str(marker)])
    pid, _, _ = _read_marker(marker)
    assert await _wait_dead(pid)
    assert len(_cleanup_warnings(failing_cleanup)) == 1

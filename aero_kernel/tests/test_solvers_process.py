"""The async subprocess helper (ch. 8.8, 8.10; Q17, Q19)."""

import asyncio
import concurrent.futures
import errno
import gc
import logging
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import NoReturn

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.runtime import SolverRuntime
from aero_kernel.solvers import process as process_module
from aero_kernel.solvers.process import ProcessRun
from aero_kernel.solvers.process import run_process as _run_process

pytestmark = pytest.mark.asyncio

# The pool that runs ``communicate``: the runtime's own in production, one per test module here.
# Threads start on first use, so creating it at import costs nothing.
POOL = concurrent.futures.ThreadPoolExecutor(max_workers=16, thread_name_prefix="test_process")


async def run_process(
    files: Mapping[str, str | bytes],
    commands: str,
    *,
    executable: str | Path,
    args: Sequence[str] = (),
    collect: Sequence[str] = (),
) -> ProcessRun:
    """``run_process`` on the test pool."""
    return await _run_process(
        files, commands, executable=executable, args=args, collect=collect, executor=POOL
    )


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
    assert isinstance(caught.value.__cause__, FileNotFoundError)


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


async def test_a_binary_that_may_not_run_is_tool_unavailable(tmp_path: Path) -> None:
    plain = tmp_path / "plain.txt"
    plain.write_text("not executable")
    plain.chmod(0o644)
    with pytest.raises(FormulaError) as caught:
        await run_process({}, "", executable=plain)
    assert caught.value.code == "tool_unavailable"
    assert caught.value.detail == {"executable": "plain.txt"}
    assert isinstance(caught.value.__cause__, PermissionError)


async def test_a_binary_in_no_executable_format_is_tool_unavailable(tmp_path: Path) -> None:
    junk = tmp_path / "junk"
    junk.write_bytes(b"\x00\x01 not a program")
    junk.chmod(0o755)
    with pytest.raises(FormulaError) as caught:
        await run_process({}, "", executable=junk)
    assert caught.value.code == "tool_unavailable"
    assert caught.value.detail == {"executable": "junk"}
    cause = caught.value.__cause__
    assert isinstance(cause, OSError)
    assert cause.errno == errno.ENOEXEC


def _open_descriptors() -> int:
    """The number of descriptors this process holds right now (POSIX: macOS and Linux)."""
    return len(os.listdir("/dev/fd"))


async def test_a_normal_run_and_a_cancelled_run_return_every_descriptor(
    script: Path, tmp_path: Path
) -> None:
    gc.disable()
    try:
        before = _open_descriptors()
        await run_process(
            {"in.txt": "abc"}, "go\n", executable=sys.executable, args=[str(script), "0"]
        )
        assert _open_descriptors() == before
        task, pid, grandchild, _ = await _start_sleeper(tmp_path)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            async with asyncio.timeout(5):
                await task
        assert await _wait_dead(pid)
        assert await _wait_dead(grandchild)
        await asyncio.sleep(0.05)
        assert _open_descriptors() == before
    finally:
        gc.enable()


@pytest.fixture
def spawned(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """The pids of every process the run starts, recorded without changing how it starts."""
    pids: list[int] = []
    original = subprocess.Popen

    class Recording(original):  # type: ignore[type-arg,misc]  # a recording Popen
        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args, **kwargs)  # type: ignore[call-overload]  # as Popen's own
            pids.append(self.pid)

    monkeypatch.setattr(subprocess, "Popen", Recording)
    return pids


@pytest.mark.parametrize("steps", [1, 2, 3, 4])
async def test_cancelling_every_task_ends_the_run_and_kills_the_group(
    steps: int, spawned: list[int], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """GH #1188 / CPython gh-103847: an ``asyncio.run`` shutdown cancels every task at once."""
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))
    task = asyncio.create_task(
        run_process({}, "", executable=sys.executable, args=["-c", "import time; time.sleep(30)"])
    )
    for _ in range(steps):
        await asyncio.sleep(0)
    current = asyncio.current_task()
    for other in asyncio.all_tasks():
        if other is not current:
            other.cancel()
    done, _ = await asyncio.wait([task], timeout=5)
    assert done, "run_process is still running 5 s after every task was cancelled"
    assert task.cancelled()
    assert _entries(scratch) == []
    assert len(spawned) == 1
    assert await _wait_dead(spawned[0])


class _Killer:
    """A stand-in for the ``os`` module of ``solvers/process.py`` that controls ``killpg``."""

    def __init__(self, delay: float | None) -> None:
        self.delay = delay
        self.calls: list[int] = []

    def killpg(self, pgid: int, sig: int) -> None:
        self.calls.append(pgid)
        if self.delay is not None:
            threading.Timer(self.delay, os.killpg, args=(pgid, sig)).start()


async def test_a_second_cancel_during_the_reaping_wait_changes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    killer = _Killer(delay=0.3)  # the group dies only after the second cancel has arrived
    monkeypatch.setattr(process_module, "os", killer)
    task, pid, grandchild, cwd = await _start_sleeper(tmp_path)
    task.cancel()
    await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        async with asyncio.timeout(5):
            await task
    assert killer.calls == [pid]
    assert not _is_dir(cwd)
    assert await _wait_dead(pid)
    assert await _wait_dead(grandchild)


async def test_a_process_that_is_not_reaped_in_time_is_reported_once_and_the_cancel_ends(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(process_module, "_REAP_BOUND_S", 0.3)
    killer = _Killer(delay=None)  # the kill never happens: the child survives
    monkeypatch.setattr(process_module, "os", killer)
    task, pid, grandchild, _ = await _start_sleeper(tmp_path)
    began = time.monotonic()
    try:
        with caplog.at_level(logging.DEBUG, logger="aero_kernel"):
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                async with asyncio.timeout(5):
                    await task
        assert time.monotonic() - began < 0.3 + 2
        assert [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING] == [
            f"process not reaped ({Path(sys.executable).name})"
        ]
    finally:
        os.killpg(pid, signal.SIGKILL)  # the test cleans up what the run was told not to kill
    assert await _wait_dead(pid)
    assert await _wait_dead(grandchild)


async def test_a_start_that_fails_for_another_reason_propagates_and_leaks_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))

    def refuse(*args: object, **kwargs: object) -> object:
        raise OSError(errno.EMFILE, "Too many open files")

    monkeypatch.setattr(subprocess, "Popen", refuse)
    gc.disable()
    try:
        before = _open_descriptors()
        for _ in range(5):
            with pytest.raises(OSError, match="Too many open files") as caught:
                await run_process({}, "", executable=sys.executable)
            assert not isinstance(caught.value, FormulaError)
            assert caught.value.errno == errno.EMFILE
        assert _open_descriptors() == before
    finally:
        gc.enable()
    assert _entries(scratch) == []


class _NoDefaultExecutor(concurrent.futures.ThreadPoolExecutor):
    """An executor that fails the test when anything runs on it."""

    def submit(self, fn: object, /, *args: object, **kwargs: object) -> NoReturn:  # type: ignore[override]  # the point is to fail
        msg = "the default executor must not be used"
        raise AssertionError(msg)


async def test_the_runtime_runs_processes_on_its_own_pool_and_closes_it(script: Path) -> None:
    asyncio.get_running_loop().set_default_executor(_NoDefaultExecutor())
    runtime = SolverRuntime(max_concurrency=2)
    async with asyncio.timeout(10):
        run = await runtime.run_process(
            {"in.txt": "abc"}, "go\n", executable=sys.executable, args=[str(script), "0"]
        )
        assert run.stdout == "cwd-files=in.txt\nstdin=go\n"
        await runtime.aclose()
    with pytest.raises(RuntimeError, match="shutdown"):
        runtime._threads.submit(int)  # type: ignore[attr-defined]  # the owner's pool, read by the test


async def test_a_tool_that_stops_reading_its_input_is_not_an_error(tmp_path: Path) -> None:
    quitter = tmp_path / "quitter.py"
    quitter.write_text("import sys\nsys.exit(0)\n")
    run = await run_process({}, "x" * 1_000_000, executable=sys.executable, args=[str(quitter)])
    assert run.returncode == 0


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
        async with asyncio.timeout(5):
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

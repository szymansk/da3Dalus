"""The async subprocess helper (ch. 8.8, 8.10; Q17, Q19)."""

import asyncio
import contextlib
import errno
import gc
import logging
import os
import shutil
import signal
import sys
import tempfile
import textwrap
import time
from asyncio import unix_events
from pathlib import Path

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.solvers import process as process_module
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


async def test_a_start_that_fails_without_a_cancel_is_not_tool_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))

    async def refuse(*args: object, **kwargs: object) -> object:
        raise OSError(errno.EMFILE, "Too many open files")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", refuse)
    gc.disable()  # the count below must hold WITHOUT a collection
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


START_FAILED_WARNING = "process start failed; a child may have been left running (python-tool)"


async def test_a_start_that_raises_something_else_is_internal_and_warns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """E.g. asyncio's child-watcher registration fails after the spawn: no pid, a child may run."""

    async def broken(*args: object, **kwargs: object) -> object:
        msg = "can't start new thread"
        raise RuntimeError(msg)

    tool = tmp_path / "python-tool"
    monkeypatch.setattr(asyncio, "create_subprocess_exec", broken)
    with (
        caplog.at_level(logging.DEBUG, logger="aero_kernel"),
        pytest.raises(RuntimeError, match="can't start new thread"),
    ):
        async with asyncio.timeout(5):
            await run_process({}, "", executable=tool)
    (record,) = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert record.getMessage() == START_FAILED_WARNING
    assert str(tmp_path) not in record.getMessage()


async def test_a_start_error_that_is_not_the_binarys_refusal_warns_too(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    async def refuse(*args: object, **kwargs: object) -> object:
        raise OSError(errno.EMFILE, "Too many open files")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", refuse)
    with (
        caplog.at_level(logging.DEBUG, logger="aero_kernel"),
        pytest.raises(OSError, match="Too many open files"),
    ):
        await run_process({}, "", executable=tmp_path / "python-tool")
    assert [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING] == [
        START_FAILED_WARNING
    ]


async def test_a_cancel_followed_by_a_failing_start_still_warns_and_stays_a_cancel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    release = asyncio.Event()

    async def late_failure(*args: object, **kwargs: object) -> object:
        await release.wait()
        msg = "can't start new thread"
        raise RuntimeError(msg)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", late_failure)
    task = asyncio.create_task(run_process({}, "", executable=tmp_path / "python-tool"))
    await asyncio.sleep(0.05)
    with caplog.at_level(logging.DEBUG, logger="aero_kernel"):
        task.cancel()
        await asyncio.sleep(0.05)
        release.set()
        with pytest.raises(asyncio.CancelledError):
            async with asyncio.timeout(3):
                await task
    # asyncio (3.14) logs the shielded start's exception on its own logger; ours is the one asked
    ours = [r for r in caplog.records if r.name == process_module.logger.name]
    assert [r.getMessage() for r in ours if r.levelno >= logging.WARNING] == [START_FAILED_WARNING]


async def test_the_binarys_own_refusal_logs_no_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.DEBUG, logger="aero_kernel"), pytest.raises(FormulaError):
        await run_process({}, "", executable=tmp_path / "no_such_tool")
    assert [r for r in caplog.records if r.levelno >= logging.WARNING] == []


@pytest.mark.skipif(
    not hasattr(unix_events, "ThreadedChildWatcher") or sys.version_info >= (3, 14),
    reason="the child-watcher registration only exists before Python 3.14",
)
async def test_a_failing_child_watcher_registration_does_not_hang_and_warns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    spawned: list[int] = []

    def failing(self: object, pid: int, callback: object, *args: object) -> None:
        spawned.append(pid)
        msg = "can't start new thread"
        raise RuntimeError(msg)

    monkeypatch.setattr(unix_events.ThreadedChildWatcher, "add_child_handler", failing)
    tool = tmp_path / "python-tool"
    tool.symlink_to(sys.executable)
    try:
        with (
            caplog.at_level(logging.DEBUG, logger="aero_kernel"),
            pytest.raises(RuntimeError, match="can't start new thread"),
        ):
            async with asyncio.timeout(5):
                await run_process(
                    {}, "", executable=tool, args=["-c", "import time; time.sleep(20)"]
                )
        assert [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING] == [
            START_FAILED_WARNING
        ]
        assert len(spawned) == 1  # the child exists and nobody holds its pid: the warning says so
    finally:
        for pid in spawned:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(pid, signal.SIGKILL)
            with contextlib.suppress(ChildProcessError):
                await asyncio.to_thread(
                    os.waitpid, pid, 0
                )  # reaped, so the orphaned Popen object has nothing to warn of


async def test_a_single_failure_of_the_run_keeps_its_chained_cause(
    script: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cause = ValueError("the underlying cause")

    async def broken(self: asyncio.AbstractEventLoop, factory: object, pipe: object) -> object:
        try:
            raise cause
        except ValueError as inner:
            msg = "pipe failed"
            raise OSError(errno.EMFILE, msg) from inner

    loop_type = type(asyncio.get_running_loop())
    original = loop_type.connect_read_pipe
    calls: list[int] = []

    async def first_only(self: asyncio.AbstractEventLoop, factory: object, pipe: object) -> object:
        calls.append(1)
        if len(calls) == 1:
            return await broken(self, factory, pipe)
        return await original(self, factory, pipe)  # type: ignore[arg-type]  # same call as run_process makes

    monkeypatch.setattr(loop_type, "connect_read_pipe", first_only)
    with pytest.raises(OSError, match="pipe failed") as caught:
        await run_process({}, "", executable=sys.executable, args=[str(script), "0"])
    assert caught.value.__cause__ is cause


async def test_a_binary_that_may_not_run_is_tool_unavailable(tmp_path: Path) -> None:
    plain = tmp_path / "plain.txt"
    plain.write_text("not executable")
    plain.chmod(0o644)
    with pytest.raises(FormulaError) as caught:
        await run_process({}, "", executable=plain)
    assert caught.value.code == "tool_unavailable"
    assert caught.value.detail == {"executable": "plain.txt"}


async def test_a_binary_in_no_executable_format_is_tool_unavailable(tmp_path: Path) -> None:
    junk = tmp_path / "junk"
    junk.write_bytes(b"\x00\x01 not a program")
    junk.chmod(0o755)
    with pytest.raises(FormulaError) as caught:
        await run_process({}, "", executable=junk)
    assert caught.value.code == "tool_unavailable"
    assert caught.value.detail == {"executable": "junk"}


async def test_a_start_cancelled_with_its_caller_leaves_a_plain_cancel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Loop shutdown cancels every task, the start included: nothing was started."""
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))
    never = asyncio.Event()

    async def stalled(*args: object, **kwargs: object) -> object:
        await never.wait()
        raise AssertionError

    monkeypatch.setattr(asyncio, "create_subprocess_exec", stalled)
    task = asyncio.create_task(run_process({}, "", executable=sys.executable))
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    others = [t for t in asyncio.all_tasks() if t is not task and t is not asyncio.current_task()]
    assert len(others) >= 1  # the start task
    for other in others:
        other.cancel()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        async with asyncio.timeout(3):
            await task
    assert _entries(scratch) == []


def _open_descriptors() -> int:
    """The number of descriptors this process holds right now (POSIX: macOS and Linux)."""
    return len(os.listdir("/dev/fd"))


async def test_a_cancel_during_the_start_leaves_no_descriptor_and_no_process(
    tmp_path: Path, held_start: asyncio.Event
) -> None:
    gc.disable()
    try:
        before = _open_descriptors()
        task, pid, grandchild, cwd = await _start_sleeper(tmp_path)
        task.cancel()
        held_start.set()
        with pytest.raises(asyncio.CancelledError):
            async with asyncio.timeout(5):
                await task
        assert not _is_dir(cwd)
        assert await _wait_dead(pid)
        assert await _wait_dead(grandchild)
        await asyncio.sleep(0.05)  # the loop closes the pipe transports on its next turns
        assert _open_descriptors() == before
    finally:
        gc.enable()


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


@pytest.mark.parametrize("failing_calls", [1, 2], ids=["one pipe", "two pipes"])
async def test_a_pipe_that_cannot_be_connected_fails_the_run_and_leaks_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failing_calls: int
) -> None:
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))
    loop_type = type(asyncio.get_running_loop())
    original = loop_type.connect_read_pipe
    calls: list[int] = []

    async def flaky(self: asyncio.AbstractEventLoop, factory: object, pipe: object) -> object:
        calls.append(1)
        if len(calls) <= failing_calls:
            raise OSError(errno.EMFILE, "Too many open files")
        return await original(self, factory, pipe)  # type: ignore[arg-type]  # same call as run_process makes

    monkeypatch.setattr(loop_type, "connect_read_pipe", flaky)
    gc.disable()
    try:
        before = _open_descriptors()
        expected = OSError if failing_calls == 1 else ExceptionGroup
        with pytest.raises(expected):
            await run_process({}, "", executable=sys.executable, args=["-c", "pass"])
        await asyncio.sleep(0.05)
        assert _open_descriptors() == before
    finally:
        gc.enable()
    assert _entries(scratch) == []


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

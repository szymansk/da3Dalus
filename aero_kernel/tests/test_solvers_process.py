"""The async subprocess helper (ch. 8.8, 8.10; Q17, Q19)."""

import asyncio
import contextlib
import errno
import gc
import logging
import os
import shutil
import sys
import tempfile
import textwrap
import time
import warnings
from asyncio import unix_events
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.runtime import SolverRuntime
from aero_kernel.solvers import process as process_module
from aero_kernel.solvers.process import ProcessRun, Start
from aero_kernel.solvers.process import run_process as _run_process

pytestmark = pytest.mark.asyncio


async def run_process(
    files: Mapping[str, str | bytes],
    commands: str,
    *,
    executable: str | Path,
    args: Sequence[str] = (),
    collect: Sequence[str] = (),
    call_id: str | None = None,
    keep: set[Start] | None = None,
) -> ProcessRun:
    """``run_process`` with a keeper of the test's own, unless the test brings one."""
    return await _run_process(
        files,
        commands,
        executable=executable,
        args=args,
        collect=collect,
        call_id=call_id,
        keep=set() if keep is None else keep,
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


@pytest.fixture
def start_fails_after_the_spawn(monkeypatch: pytest.MonkeyPatch) -> None:
    """The child exists, then the pipe set-up fails (e.g. no file descriptors left).

    asyncio then waits for pipes that never connect, so the start never ends on its own.
    """

    async def failing(self: object, waiter: asyncio.Future[None]) -> None:
        waiter.set_exception(OSError(errno.EMFILE, "simulated pipe registration failure"))

    monkeypatch.setattr(unix_events._UnixSubprocessTransport, "_connect_pipes", failing)  # type: ignore[attr-defined]  # asyncio internal, patched to fail the start


async def test_a_cancel_during_a_start_that_hangs_is_bounded_and_reported(
    tmp_path: Path,
    start_fails_after_the_spawn: None,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Without the process object the group cannot be killed; the cancel must still end in time."""
    monkeypatch.setattr(process_module, "_START_SETTLE_S", 0.3)
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))
    task: asyncio.Task[object] = asyncio.create_task(
        run_process({}, "", executable=sys.executable, args=["-c", "pass"], call_id="c4ll1d")
    )
    await asyncio.sleep(0.1)  # the child exists and the start is stuck
    with caplog.at_level(logging.DEBUG, logger="aero_kernel"):
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            async with asyncio.timeout(3):
                await task
    assert _entries(scratch) == []
    (record,) = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert record.levelno == logging.WARNING
    assert record.getMessage() == (
        "process start did not settle within 0.3 s; its process group could not be killed"
    )
    assert (record.call_id, record.tool) == ("c4ll1d", Path(sys.executable).name)  # type: ignore[attr-defined]  # logging extra
    assert str(tmp_path) not in record.getMessage()


async def test_a_budget_that_expires_during_a_hung_start_ends_within_the_bound(
    tmp_path: Path, start_fails_after_the_spawn: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(process_module, "_START_SETTLE_S", 0.3)
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))
    guard = asyncio.timeout(4)
    budget = asyncio.timeout(0.2)
    with pytest.raises(TimeoutError):
        async with guard, budget:
            await run_process({}, "", executable=sys.executable, args=["-c", "pass"])
    assert budget.expired()
    assert not guard.expired()
    assert _entries(scratch) == []


async def test_a_start_stuck_in_the_connect_wait_is_cancelled_again_and_ends(
    tmp_path: Path,
    held_start: asyncio.Event,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The first cancel lands in asyncio's wait for pipes that never connect; the second ends it."""
    monkeypatch.setattr(process_module, "_START_SETTLE_S", 0.3)
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))
    task: asyncio.Task[object] = asyncio.create_task(
        run_process(
            {},
            "",
            executable=sys.executable,
            args=["-c", "import time; time.sleep(20)"],
            call_id="slow01",
        )
    )
    await asyncio.sleep(0.1)
    began = time.monotonic()
    with caplog.at_level(logging.DEBUG, logger="aero_kernel"):
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            async with asyncio.timeout(3):
                await task
    assert time.monotonic() - began < 0.3 * 2 + 0.5  # twice the bound, plus scheduling slack
    held_start.set()  # let the held transport task end
    assert _entries(scratch) == []
    (record,) = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert record.getMessage() == (
        "process start did not settle within 0.3 s; its process group could not be killed"
    )
    assert record.call_id == "slow01"  # type: ignore[attr-defined]  # logging extra
    assert not hasattr(process_module, "_GIVEN_UP_STARTS")  # no module-level state (CLAUDE.md)


async def test_a_start_that_ignores_every_cancel_is_given_up_after_twice_the_bound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(process_module, "_START_SETTLE_S", 0.2)
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))
    release = asyncio.Event()
    monkeypatch.setattr(asyncio, "create_subprocess_exec", _stubborn_start(release))
    keep: set[asyncio.Future[asyncio.subprocess.Process]] = set()
    task: asyncio.Task[object] = asyncio.create_task(
        run_process({}, "", executable=sys.executable, call_id="stub01", keep=keep)
    )
    await asyncio.sleep(0.05)
    began = time.monotonic()
    with caplog.at_level(logging.DEBUG, logger="aero_kernel"):
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            async with asyncio.timeout(3):
                await task
    assert 0.2 * 2 <= time.monotonic() - began < 0.2 * 2 + 0.5
    assert _entries(scratch) == []
    (record,) = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert record.getMessage() == (
        "process start did not settle within 0.2 s and was given up; its process group could "
        "not be killed and the start may still be running"
    )
    assert record.call_id == "stub01"  # type: ignore[attr-defined]  # logging extra
    (kept,) = keep  # the caller's keeper holds it, no module does
    assert not kept.done()
    assert not hasattr(process_module, "_GIVEN_UP_STARTS")
    release.set()  # the stuck start ends at last: it is released and its outcome consumed
    await asyncio.sleep(0.05)
    assert keep == set()


def _stubborn_start(release: asyncio.Event, *, real: bool = False) -> object:
    """A stand-in for ``create_subprocess_exec`` that ignores cancels until ``release`` is set.

    Then it fails (``real=False``), or hands over the sleeping fake tool it really started at the
    beginning (``real=True``): a start that is only slow, whose process nobody owns by then.
    """
    original = asyncio.create_subprocess_exec

    async def stubborn(*args: object, **kwargs: object) -> object:
        process = await original(*args, **kwargs) if real else None  # type: ignore[arg-type]  # same call as run_process makes
        while not release.is_set():
            with contextlib.suppress(asyncio.CancelledError):
                await release.wait()
        if process is None:
            raise OSError(errno.EMFILE, "released")
        return process

    return stubborn


async def test_the_keeper_is_required() -> None:
    with pytest.raises(TypeError, match="keep"):
        await _run_process({}, "", executable=sys.executable)  # type: ignore[call-arg]  # the missing argument is the point


async def test_the_runtime_holds_a_given_up_start_and_releases_it_when_it_ends(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(process_module, "_START_SETTLE_S", 0.2)
    release = asyncio.Event()
    monkeypatch.setattr(asyncio, "create_subprocess_exec", _stubborn_start(release))
    async with SolverRuntime() as runtime:
        task: asyncio.Task[object] = asyncio.create_task(
            runtime.run_process({}, "", executable=sys.executable)
        )
        await asyncio.sleep(0.05)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            async with asyncio.timeout(3):
                await task
        assert len(runtime._given_up) == 1  # type: ignore[attr-defined]  # the owner's holder, read by the test
        release.set()
        await asyncio.sleep(0.05)
        assert runtime._given_up == set()  # type: ignore[attr-defined]  # as above


async def test_closing_the_runtime_reports_the_starts_still_given_up(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(process_module, "_START_SETTLE_S", 0.2)
    release = asyncio.Event()
    monkeypatch.setattr(asyncio, "create_subprocess_exec", _stubborn_start(release))
    runtime = SolverRuntime()
    task: asyncio.Task[object] = asyncio.create_task(
        runtime.run_process({}, "", executable=sys.executable)
    )
    await asyncio.sleep(0.05)
    try:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            async with asyncio.timeout(3):
                await task
        with caplog.at_level(logging.DEBUG, logger="aero_kernel"):
            await runtime.aclose()
        closing = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert [r.getMessage() for r in closing] == [
            "process start did not settle within 0.2 s and was given up; its process group "
            "could not be killed and the start may still be running",
            "1 given-up process starts are still pending at close",
        ]
    finally:
        release.set()  # a stuck stub would otherwise outlive the test and block the loop's end
        await asyncio.sleep(0.05)


async def test_a_given_up_start_that_succeeds_later_has_its_group_killed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(process_module, "_START_SETTLE_S", 0.2)
    sleeper = tmp_path / "sleeper.py"
    sleeper.write_text(SLEEP_SCRIPT)
    marker = tmp_path / "marker.txt"
    release = asyncio.Event()
    monkeypatch.setattr(asyncio, "create_subprocess_exec", _stubborn_start(release, real=True))
    keep: set[asyncio.Future[asyncio.subprocess.Process]] = set()
    task: asyncio.Task[object] = asyncio.create_task(
        run_process({}, "", executable=sys.executable, args=[str(sleeper), str(marker)], keep=keep)
    )
    await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        async with asyncio.timeout(3):
            await task
    assert len(keep) == 1
    # Garbage that earlier tests left behind is finalised here, outside the recorded block: a
    # collection inside it would blame this test for their unclosed files (test order, -n 4).
    gc.collect()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        release.set()  # the start succeeds now: a real process nobody owns
        pid, grandchild, _ = await asyncio.to_thread(_read_marker, marker)
        assert await _wait_dead(pid)
        assert await _wait_dead(grandchild)
        assert keep == set()
        gc.collect()
    # only this test's own process: its transport names the pid, foreign garbage does not
    own = [
        str(w.message)
        for w in caught
        if issubclass(w.category, ResourceWarning) and f"pid={pid}" in str(w.message)
    ]
    assert own == []


async def test_the_runtime_forwards_the_call_id_to_the_process_log(
    tmp_path: Path,
    start_fails_after_the_spawn: None,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(process_module, "_START_SETTLE_S", 0.2)
    async with SolverRuntime() as runtime:
        task: asyncio.Task[object] = asyncio.create_task(
            runtime.run_process(
                {}, "", executable=sys.executable, args=["-c", "pass"], call_id="rt7"
            )
        )
        await asyncio.sleep(0.1)
        with caplog.at_level(logging.DEBUG, logger="aero_kernel"):
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                async with asyncio.timeout(3):
                    await task
    (record,) = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert record.call_id == "rt7"  # type: ignore[attr-defined]  # logging extra


async def test_a_start_that_fails_without_a_cancel_is_not_tool_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))

    async def refuse(*args: object, **kwargs: object) -> object:
        raise OSError(errno.EMFILE, "Too many open files")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", refuse)
    with pytest.raises(OSError, match="Too many open files") as caught:
        await run_process({}, "", executable=sys.executable)
    assert not isinstance(caught.value, FormulaError)
    assert caught.value.errno == errno.EMFILE
    assert _entries(scratch) == []


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


async def test_a_normal_start_is_far_below_the_settle_bound() -> None:
    """The measurement behind ``_START_SETTLE_S`` (see the comment there): median of 20 starts."""
    latencies: list[float] = []
    for _ in range(20):
        began = time.perf_counter()
        child = await asyncio.create_subprocess_exec(
            sys.executable,
            "-c",
            "pass",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=True,
        )
        latencies.append(time.perf_counter() - began)
        await child.communicate(b"")
    latencies.sort()
    assert latencies[len(latencies) // 2] < process_module._START_SETTLE_S / 100  # type: ignore[attr-defined]  # module constant read by the test


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

"""Async subprocess helper for external binaries such as AVL (ARCHITECTURE ch. 8.8, 8.10)."""

import asyncio
import contextlib
import errno
import logging
import os
import shutil
import signal
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path

from aero_kernel.errors import ErrorCategory, FormulaError
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

__all__ = ["ProcessRun", "run_process"]


class ProcessRun(BaseModel):
    """The outcome of one external process.

    Attributes:
        returncode: Exit code. A non-zero code is not an error here: a tool may exit non-zero with
            usable output, so the caller decides.
        stdout: Standard output, decoded as UTF-8 (undecodable bytes replaced).
        stderr: Standard error, decoded as UTF-8 (undecodable bytes replaced).
        files: The collected output files by name, read before the temp directory was removed.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    returncode: int
    stdout: str
    stderr: str
    files: Mapping[str, bytes]


def _check_file_name(name: str) -> None:
    """Raise ``ValueError`` unless ``name`` is a plain file name inside the directory."""
    if not name or Path(name).name != name or name in {".", ".."}:
        msg = f"file name must be a plain file name, got {name!r}"
        raise ValueError(msg)


def _unavailable(executable: str | Path) -> FormulaError:
    """The ``tool_unavailable`` error of a binary that cannot be started."""
    name = Path(executable).name
    return FormulaError(
        ErrorCategory.TOOL_UNAVAILABLE,
        "tool_unavailable",
        f"external tool {name} could not be started",
        "install the tool or check that it is executable",
        detail={"executable": name},
    )


def _kill_group(process: asyncio.subprocess.Process) -> None:
    """Kill the process and everything it started (own session, see :func:`run_process`)."""
    with contextlib.suppress(ProcessLookupError):
        os.killpg(process.pid, signal.SIGKILL)


def _remove_directory(directory: Path) -> None:
    """Remove the temp directory; a failure is logged, never raised.

    Raising would mask the ``CancelledError`` or ``TimeoutError`` in flight (ADR 0020: not silent).
    """
    try:
        shutil.rmtree(directory)
    except OSError:
        logger.warning("temp directory of external process not removed: %s", directory.name)


# How long a cancelled process start may take to settle before it counts as hung. A normal start
# (spawn and connect the pipes) took a median of 1.6 ms and at most 6.8 ms over 40 starts on the
# development machine (macOS, 11 cores; recorded by test_a_normal_start_is_far_below_the_bound),
# so 5 s separates "done" from "hung" by about three orders of magnitude. Not configurable: it is
# no tuning knob of a computation, it only bounds the cleanup of a cancel.
_START_SETTLE_S = 5.0


Start = asyncio.Future[asyncio.subprocess.Process]


def _adopt(start: Start, keep: set[Start] | None) -> None:
    """Take over a start that was given up on: hold it, and clean up after it if it ends well.

    The holder belongs to the caller (``keep``), because the owner of a resource holds it, not a
    module (ch. 8.10). A direct call without one keeps nothing: the start stays alive through the
    future it awaits. If the start succeeds after all, nobody owns the process it made, so its
    whole group is killed and its transport closed; its failure is consumed.
    """
    if keep is not None:
        keep.add(start)

    def release(done: Start) -> None:
        if keep is not None:
            keep.discard(done)
        if done.cancelled() or done.exception() is not None:
            return
        process = done.result()
        _kill_group(process)
        # the transport is asyncio's internal handle; it must be closed or it warns when collected
        process._transport.close()  # type: ignore[attr-defined]  # pyright: ignore[reportPrivateUsage]  # no public way to close it
        logger.debug("killed external process %s of a start that ended late", process.pid)

    start.add_done_callback(release)


async def _settle_start(
    start: Start, tool: str, call_id: str | None, keep: set[Start] | None
) -> asyncio.subprocess.Process | None:
    """Wait, within a bound, for a process start that a cancellation interrupted.

    ``create_subprocess_exec`` must not be cancelled half way: asyncio then kills only the direct
    child and waits for the pipes of its descendants, and the caller never gets the process whose
    group it has to kill (GH #1188). A normal start is short, so it is awaited to its end here,
    shielded from further cancellations, which the caller re-raises once the group is dead.

    A start that fails or stalls after the spawn never ends on its own (asyncio waits for pipes
    that never connect). Past ``_START_SETTLE_S`` it is cancelled again on every pass, because a
    second cancel interrupts the wait that the first one lands in. Past twice the bound the start
    is given up on and handed to ``keep`` (see :func:`_adopt`). Either way its process group is lost,
    and the operator is told once with a ``WARNING`` (ch. 8.14).

    Args:
        start: The start, running as a task of its own.
        tool: Base name of the executable, for the log.
        call_id: Id of the ``compute()`` call, for the log.
        keep: The caller's holder for starts that are given up on, if it has one.

    Returns:
        The started process, or ``None`` if the start failed, hung or was cancelled itself.
    """
    loop = asyncio.get_running_loop()
    began = loop.time()
    while not start.done() and loop.time() < began + _START_SETTLE_S:
        with contextlib.suppress(asyncio.CancelledError):
            await asyncio.wait([start], timeout=began + _START_SETTLE_S - loop.time())
    hung = not start.done()
    while not start.done() and loop.time() < began + 2 * _START_SETTLE_S:
        start.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await asyncio.wait([start], timeout=_START_SETTLE_S / 10)
    given_up = not start.done()
    if given_up:
        _adopt(start, keep)
    if hung:
        logger.warning(
            "process start did not settle within %.1f s%s; its process group could not be killed%s",
            _START_SETTLE_S,
            " and was given up" if given_up else "",
            " and the start may still be running" if given_up else "",
            extra={"call_id": call_id, "tool": tool},
        )
    if given_up or start.cancelled() or start.exception() is not None:
        return None
    return start.result()


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
    """Run an external binary in a fresh temp directory and return its output.

    The directory holds ``files`` and is the working directory; ``commands`` go to stdin. The
    process runs in its own session, so cancellation (or an expired ``asyncio.timeout``) kills it
    and everything it started, removes the directory and re-raises (Q17, ch. 8.10). Never blocks
    the event loop for the run itself.

    POSIX only (macOS, Linux and the Linux containers, ARCHITECTURE ch. 7): the process group is
    killed with ``os.killpg``, and there is no Windows fallback.

    Args:
        files: Input files by plain file name; ``str`` is written as UTF-8.
        commands: Text written to stdin.
        executable: The binary to start.
        args: Its command-line arguments.
        collect: Names of output files to read back; files the tool did not write are absent
            from the result.
        call_id: Id of the ``compute()`` call, for the log lines of this run (ch. 8.14).
        keep: A set that holds a process start this call had to give up on (a start that hung
            while the call was cancelled) until it ends, so the owner (``SolverRuntime``) can
            count what is still pending at close. Without one, nothing is held.

    Returns:
        The exit code, the output streams and the collected files.

    Raises:
        ValueError: If a file name is not a plain file name.
        FormulaError: ``tool_unavailable`` if the binary cannot be started because it does not
            exist, may not be executed or is not an executable format.
        OSError: Any other failure to start the process (no file descriptors, no memory): an
            internal defect of the environment, which the engine reports as ``internal``.
    """
    for name in (*files, *collect):
        _check_file_name(name)
    directory = Path(tempfile.mkdtemp(prefix="aero_kernel_"))
    process: asyncio.subprocess.Process | None = None
    try:
        for name, content in files.items():
            data = content.encode() if isinstance(content, str) else content
            (directory / name).write_bytes(data)
        start = asyncio.ensure_future(
            asyncio.create_subprocess_exec(
                executable,
                *args,
                cwd=directory,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                start_new_session=True,
            )
        )
        try:
            # shielded: a cancel during the start must not abort it (see _settle_start)
            started = await asyncio.shield(start)
        except asyncio.CancelledError:
            process = await _settle_start(start, Path(executable).name, call_id, keep)
            raise
        except OSError as error:
            if (
                isinstance(error, FileNotFoundError | PermissionError)
                or error.errno == errno.ENOEXEC
            ):
                raise _unavailable(executable) from error
            raise  # not Popen's own refusal of the binary: the environment failed (internal)
        process = started
        stdout, stderr = await process.communicate(commands.encode())
        returncode = await process.wait()
        outputs = {
            name: (directory / name).read_bytes()
            for name in collect
            if (directory / name).is_file()
        }
        return ProcessRun(
            returncode=returncode,
            stdout=stdout.decode(errors="replace"),
            stderr=stderr.decode(errors="replace"),
            files=outputs,
        )
    finally:
        # Cancelled, timed out or finished: the process is gone and the directory removed before
        # the exception continues. Kill first so rmtree never races a writer.
        if process is not None and process.returncode is None:
            _kill_group(process)
            logger.debug("killed external process %s", process.pid)
        _remove_directory(directory)
        if process is not None and process.returncode is None:
            await process.wait()

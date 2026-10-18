"""Async subprocess helper for external binaries such as AVL (ARCHITECTURE ch. 8.8, 8.10)."""

import asyncio
import concurrent.futures
import contextlib
import errno
import logging
import os
import shutil
import signal
import subprocess
import tempfile
import time
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


def _is_refusal(error: BaseException) -> bool:
    """Whether an error of the start is Popen's own refusal of the binary (``tool_unavailable``)."""
    return isinstance(error, FileNotFoundError | PermissionError) or (
        isinstance(error, OSError) and error.errno == errno.ENOEXEC
    )


# How long a cancelled run waits for the killed process to be reaped (``communicate`` returning in
# its pool thread) before it gives up and tells the operator. A killed group is reaped within
# milliseconds; only a descendant that left the group with a session of its own keeps the pipes
# open and the thread blocked.
_REAP_BOUND_S = 5.0


def _kill_group(process: subprocess.Popen[bytes]) -> None:
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


async def _reap(
    pending: concurrent.futures.Future[tuple[bytes, bytes]],
    process: subprocess.Popen[bytes],
    tool: str,
) -> None:
    """Kill the process group, then wait, within a bound, for ``communicate`` to return.

    Cancellations that arrive during the wait are swallowed (the caller re-raises the original
    one afterwards). Past the bound the thread is left to finish by itself and the operator is
    told (ADR 0020).
    """
    _kill_group(process)
    deadline = time.monotonic() + _REAP_BOUND_S
    while not pending.done() and time.monotonic() < deadline:
        with contextlib.suppress(asyncio.CancelledError):
            await asyncio.wait([asyncio.wrap_future(pending)], timeout=deadline - time.monotonic())
    if not pending.done():
        logger.warning("process not reaped (%s)", tool)


async def run_process(
    files: Mapping[str, str | bytes],
    commands: str,
    *,
    executable: str | Path,
    args: Sequence[str] = (),
    collect: Sequence[str] = (),
    executor: concurrent.futures.Executor,
) -> ProcessRun:
    """Run an external binary in a fresh temp directory and return its output.

    The directory holds ``files`` and is the working directory; ``commands`` go to stdin. The
    process runs in its own session, so cancellation (or an expired ``asyncio.timeout``) kills it
    and everything it started, removes the directory and re-raises (Q17, ch. 8.10). Never blocks
    the event loop for the run itself.

    The process is started with ``subprocess.Popen`` on the calling thread and
    ``Popen.communicate`` runs in a thread of ``executor``, so nothing of asyncio's subprocess
    machinery (child watcher, pipe transports) is involved: cancelling every task of a loop
    (``asyncio.run`` shutdown) cannot leave the run hanging (GH #1188). After a cancel the group
    is killed and the run waits at most ``_REAP_BOUND_S`` for the thread to return.

    POSIX only (macOS, Linux and the Linux containers, ARCHITECTURE ch. 7): the process group is
    killed with ``os.killpg``, and there is no Windows fallback.

    Args:
        files: Input files by plain file name; ``str`` is written as UTF-8.
        commands: Text written to stdin.
        executable: The binary to start.
        args: Its command-line arguments.
        collect: Names of output files to read back; files the tool did not write are absent
            from the result.
        executor: The thread pool that runs ``communicate``; the runtime's own, never asyncio's
            default executor.

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
    process: subprocess.Popen[bytes] | None = None
    pending: concurrent.futures.Future[tuple[bytes, bytes]] | None = None
    try:
        for name, content in files.items():
            data = content.encode() if isinstance(content, str) else content
            (directory / name).write_bytes(data)
        try:
            process = subprocess.Popen(  # noqa: ASYNC220  # spawning is millisecond work, done on the loop thread by design (GH #1188)
                [str(executable), *args],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=directory,
                start_new_session=True,
            )
        except OSError as error:
            if _is_refusal(error):
                raise _unavailable(executable) from error
            raise  # not Popen's own refusal of the binary: the environment failed (internal)
        pending = executor.submit(process.communicate, commands.encode())
        stdout, stderr = await asyncio.wrap_future(pending)
        outputs = {
            name: (directory / name).read_bytes()
            for name in collect
            if (directory / name).is_file()
        }
        return ProcessRun(
            returncode=process.returncode,
            stdout=stdout.decode(errors="replace"),
            stderr=stderr.decode(errors="replace"),
            files=outputs,
        )
    finally:
        # Cancelled, timed out or finished: the process is gone and the directory removed before
        # the exception continues. Kill first so rmtree never races a writer.
        if process is not None and pending is not None and process.returncode is None:
            await _reap(pending, process, Path(executable).name)
        _remove_directory(directory)

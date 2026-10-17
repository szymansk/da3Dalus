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
from typing import BinaryIO

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


def _warn_start_failed(executable: str | Path) -> None:
    """Tell the operator that a failed start may have left a child running (ch. 8.10, ADR 0020).

    asyncio registers its child watcher after the spawn; if that fails, the start raises and no
    pid reaches us, so the child cannot be killed. The failure itself is ``internal``.
    """
    logger.warning(
        "process start failed; a child may have been left running (%s)", Path(executable).name
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


async def _await_start(
    start: asyncio.Future[asyncio.subprocess.Process],
) -> asyncio.subprocess.Process | None:
    """Wait for a process start to its end after a cancellation interrupted the caller.

    ``create_subprocess_exec`` must not be cancelled half way: asyncio then kills only the direct
    child and the caller never gets the process whose group it has to kill (GH #1188). With the
    pipes created by :func:`run_process` itself asyncio has none to wait for, so the start
    provably ends; it is awaited to its end here, shielded from further cancellations, which the
    caller re-raises once the group is dead.

    Args:
        start: The start, running as a task of its own.

    Returns:
        The started process, or ``None`` if the start failed or was cancelled itself.
    """
    while not start.done():
        with contextlib.suppress(asyncio.CancelledError):
            await asyncio.wait([start])
    if start.cancelled() or start.exception() is not None:
        return None
    return start.result()


async def _read_all(pipe: BinaryIO, close: list[asyncio.BaseTransport]) -> bytes:
    """Read a pipe to EOF through asyncio's public pipe API; the transport is registered to close."""
    loop = asyncio.get_running_loop()
    reader = asyncio.StreamReader()
    transport, _ = await loop.connect_read_pipe(lambda: asyncio.StreamReaderProtocol(reader), pipe)
    close.append(transport)
    return await reader.read()


async def _feed(pipe: BinaryIO, data: bytes, close: list[asyncio.BaseTransport]) -> None:
    """Write ``data`` to a pipe and close it; a child that stopped reading is not an error."""
    loop = asyncio.get_running_loop()
    protocol = asyncio.StreamReaderProtocol(asyncio.StreamReader())
    transport, _ = await loop.connect_write_pipe(lambda: protocol, pipe)
    close.append(transport)
    writer = asyncio.StreamWriter(transport, protocol, None, loop)
    with contextlib.suppress(BrokenPipeError, ConnectionResetError):
        writer.write(data)
        await writer.drain()
    writer.close()
    with contextlib.suppress(BrokenPipeError, ConnectionResetError):
        await writer.wait_closed()


async def run_process(
    files: Mapping[str, str | bytes],
    commands: str,
    *,
    executable: str | Path,
    args: Sequence[str] = (),
    collect: Sequence[str] = (),
) -> ProcessRun:
    """Run an external binary in a fresh temp directory and return its output.

    The directory holds ``files`` and is the working directory; ``commands`` go to stdin. The
    process runs in its own session, so cancellation (or an expired ``asyncio.timeout``) kills it
    and everything it started, removes the directory and re-raises (Q17, ch. 8.10). Never blocks
    the event loop for the run itself.

    The pipes of the child are created here (``os.pipe``) and read and written through
    ``connect_read_pipe`` / ``connect_write_pipe``; every descriptor is closed in the ``finally``.
    So a start that fails after the spawn leaks no descriptor and cannot hang, and a cancel
    arriving during the start waits for it to end and then kills the group (GH #1188).

    POSIX only (macOS, Linux and the Linux containers, ARCHITECTURE ch. 7): the process group is
    killed with ``os.killpg``, and there is no Windows fallback.

    Args:
        files: Input files by plain file name; ``str`` is written as UTF-8.
        commands: Text written to stdin.
        executable: The binary to start.
        args: Its command-line arguments.
        collect: Names of output files to read back; files the tool did not write are absent
            from the result.

    Returns:
        The exit code, the output streams and the collected files.

    Raises:
        ValueError: If a file name is not a plain file name.
        FormulaError: ``tool_unavailable`` if the binary cannot be started because it does not
            exist, may not be executed or is not an executable format.
        OSError: Any other failure to start the process (no file descriptors, no memory), and
            ``RuntimeError`` or the like when asyncio's child-watcher registration fails after the
            spawn: an internal defect of the environment, which the engine reports as
            ``internal``. One ``WARNING`` then says that a child may have been left running, since
            no pid reached the caller (ch. 8.10).
    """
    for name in (*files, *collect):
        _check_file_name(name)
    directory = Path(tempfile.mkdtemp(prefix="aero_kernel_"))
    process: asyncio.subprocess.Process | None = None
    # every descriptor of this run: wrapped at creation, so closing is idempotent and one place
    owned: list[BinaryIO] = []
    transports: list[asyncio.BaseTransport] = []

    def pipe() -> tuple[BinaryIO, BinaryIO]:
        read, write = os.pipe()
        ends = (os.fdopen(read, "rb", buffering=0), os.fdopen(write, "wb", buffering=0))
        owned.extend(ends)
        return ends

    try:
        for name, content in files.items():
            data = content.encode() if isinstance(content, str) else content
            (directory / name).write_bytes(data)
        stdin_read, stdin_write = pipe()
        stdout_read, stdout_write = pipe()
        stderr_read, stderr_write = pipe()
        start = asyncio.ensure_future(
            asyncio.create_subprocess_exec(
                executable,
                *args,
                cwd=directory,
                stdin=stdin_read,
                stdout=stdout_write,
                stderr=stderr_write,
                start_new_session=True,
            )
        )
        try:
            # asyncio.wait never cancels what it waits on: a cancel during the start must not
            # abort it (see _await_start). Unlike asyncio.shield it logs nothing (3.14) when the
            # start then fails; start.result() re-raises the start's own exception below.
            await asyncio.wait([start])
            started = start.result()
        except asyncio.CancelledError:
            process = await _await_start(start)
            if process is None and not start.cancelled():
                failure = start.exception()
                if failure is not None and not _is_refusal(failure):
                    _warn_start_failed(executable)
            raise
        except Exception as error:
            if _is_refusal(error):
                raise _unavailable(executable) from error
            _warn_start_failed(executable)
            raise  # the environment failed, not the binary: internal
        process = started
        # the child's ends are the child's now: closing ours is what lets the reads see EOF
        for end in (stdin_read, stdout_write, stderr_write):
            end.close()
        try:
            async with asyncio.TaskGroup() as group:
                stdout_task = group.create_task(_read_all(stdout_read, transports))
                stderr_task = group.create_task(_read_all(stderr_read, transports))
                group.create_task(_feed(stdin_write, commands.encode(), transports))
                returncode_task = group.create_task(process.wait())
        except BaseExceptionGroup as failures:
            if len(failures.exceptions) == 1:
                only = failures.exceptions[0]
                raise only from only.__cause__
            raise
        outputs = {
            name: (directory / name).read_bytes()
            for name in collect
            if (directory / name).is_file()
        }
        return ProcessRun(
            returncode=returncode_task.result(),
            stdout=stdout_task.result().decode(errors="replace"),
            stderr=stderr_task.result().decode(errors="replace"),
            files=outputs,
        )
    finally:
        # Cancelled, timed out or finished: the process is gone and the directory removed before
        # the exception continues. Kill first so rmtree never races a writer.
        if process is not None and process.returncode is None:
            _kill_group(process)
            logger.debug("killed external process %s", process.pid)
        for transport in transports:
            transport.close()
        for end in owned:
            end.close()
        _remove_directory(directory)
        if process is not None and process.returncode is None:
            await process.wait()

"""Async subprocess helper for external binaries such as AVL (ARCHITECTURE ch. 8.8, 8.10)."""

import asyncio
import contextlib
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


def _kill_group(process: asyncio.subprocess.Process) -> None:
    """Kill the process and everything it started (own session, see :func:`run_process`)."""
    with contextlib.suppress(ProcessLookupError):
        os.killpg(process.pid, signal.SIGKILL)


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
        FormulaError: ``tool_unavailable`` if the binary cannot be started.
    """
    for name in (*files, *collect):
        _check_file_name(name)
    directory = Path(tempfile.mkdtemp(prefix="aero_kernel_"))
    process: asyncio.subprocess.Process | None = None
    try:
        for name, content in files.items():
            data = content.encode() if isinstance(content, str) else content
            (directory / name).write_bytes(data)
        try:
            process = await asyncio.create_subprocess_exec(
                executable,
                *args,
                cwd=directory,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                start_new_session=True,
            )
        except OSError as error:
            name = Path(executable).name
            raise FormulaError(
                ErrorCategory.TOOL_UNAVAILABLE,
                "tool_unavailable",
                f"external tool {name} could not be started",
                "install the tool or check that it is executable",
                detail={"executable": name},
            ) from error
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
        shutil.rmtree(directory, ignore_errors=True)
        if process is not None and process.returncode is None:
            await process.wait()

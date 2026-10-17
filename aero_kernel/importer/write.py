"""Stage 5 of the import: write the outputs all at once, each file atomically (ch. 8.9)."""

import contextlib
import os
import tempfile
from pathlib import Path

__all__ = ["PartialWriteError", "write_outputs"]


class PartialWriteError(OSError):
    """A rename failed after an earlier file had already been replaced.

    Attributes:
        written: Names of the files that now hold the new content.
        unwritten: Names of the files that still hold the previous content.
    """

    def __init__(self, cause: OSError, written: list[str], unwritten: list[str]) -> None:
        """Create the error.

        Args:
            cause: The failing rename.
            written: Names of the files that were replaced.
            unwritten: Names of the files that were not.
        """
        super().__init__(str(cause))
        self.written = tuple(written)
        self.unwritten = tuple(unwritten)


def write_outputs(out_dir: Path, files: dict[str, str]) -> None:
    """Write ``files`` into ``out_dir``: every file to a temporary name first, then renamed.

    Each file is replaced atomically; the pair is not. Nothing is renamed until every file is
    written, and a failure while writing removes the temporary files, so a failed write leaves the
    previous outputs untouched. A rename that fails after the first one leaves the first file new
    and the second old. The files get the permissions of a normal file under the umask.

    Args:
        out_dir: Target directory; created if missing.
        files: File name to text.

    Raises:
        PartialWriteError: If a rename fails after another file was already replaced.
        OSError: If a file cannot be written or the first rename fails; nothing was replaced.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    umask = os.umask(0)  # read the umask; the only way is to set it
    os.umask(umask)
    pending: dict[str, Path] = {}
    try:
        for name, text in files.items():
            handle, temporary = tempfile.mkstemp(dir=out_dir, prefix=f".{name}.", suffix=".tmp")
            pending[name] = Path(temporary)
            with os.fdopen(handle, "wb") as stream:
                stream.write(text.encode("utf-8"))
            os.chmod(temporary, 0o666 & ~umask)  # mkstemp makes the file private (0600)
        for name, temporary in list(pending.items()):
            try:
                os.replace(temporary, out_dir / name)
            except OSError as exc:
                done = [other for other in files if other not in pending]
                if done:
                    raise PartialWriteError(exc, done, list(pending)) from exc
                raise
            del pending[name]
    finally:
        for temporary in pending.values():
            with contextlib.suppress(OSError):
                temporary.unlink()

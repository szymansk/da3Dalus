"""Stage 5 of the import: write the outputs all at once, each file atomically (ch. 8.9)."""

import contextlib
import os
import tempfile
from pathlib import Path

__all__ = ["write_outputs"]


def write_outputs(out_dir: Path, files: dict[str, str]) -> None:
    """Write ``files`` into ``out_dir``: every file to a temporary name first, then renamed.

    Nothing is renamed until every file is written, and a failure removes the temporary files,
    so a failed write leaves the previous outputs untouched.

    Args:
        out_dir: Target directory; created if missing.
        files: File name to text.

    Raises:
        OSError: If a file cannot be written or renamed.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    pending: dict[str, Path] = {}
    try:
        for name, text in files.items():
            handle, temporary = tempfile.mkstemp(dir=out_dir, prefix=f".{name}.", suffix=".tmp")
            pending[name] = Path(temporary)
            with os.fdopen(handle, "wb") as stream:
                stream.write(text.encode("utf-8"))
        for name, temporary in list(pending.items()):
            os.replace(temporary, out_dir / name)
            del pending[name]
    finally:
        for temporary in pending.values():
            with contextlib.suppress(OSError):
                temporary.unlink()

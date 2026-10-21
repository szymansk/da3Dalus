"""Regenerates the golden outputs of the mini canon: ``python -m aero_kernel.tests.importer_golden``.

Run it only after a deliberate change of the importer's output (or of the mini canon), and review
the diff of the two files: they pin every byte of what the importer writes.
"""

import tempfile
from pathlib import Path

from aero_kernel.importer.cli import main
from aero_kernel.tests.importer_builders import write_canon

__all__ = ["GOLDEN_DIR", "regenerate"]

GOLDEN_DIR = Path(__file__).resolve().parent / "fixtures" / "importer_mini"


def regenerate() -> None:
    """Import the mini canon and store the two outputs as the golden files."""
    with tempfile.TemporaryDirectory() as work:
        canon = write_canon(Path(work))
        status = main([str(canon), "--out", str(GOLDEN_DIR)])
    if status != 0:
        raise SystemExit(status)


if __name__ == "__main__":
    regenerate()

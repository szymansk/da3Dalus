"""The canon importer: turns the canon document into the packaged canon model (ARCHITECTURE ch. 8.9).

A dev-time tool. No runtime module imports it (test Q12), so the kernel runs without PyYAML.
Run ``python -m aero_kernel.importer <canon-dir> [--out <dir>] [--source-commit <sha>] [--check]``.
"""

__all__ = ["IMPORTER_VERSION"]

# Written into every model; raised when the importer's output for the same canon changes.
IMPORTER_VERSION = "1.0.0"

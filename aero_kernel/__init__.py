"""Aerodynamic calculation kernel of da3Dalus.

Interprets the machine-readable canon model and computes aircraft quantities on request.
The kernel is independent of the application: it never imports from ``app``,
``cad_designer`` or ``scripts`` (ARCHITECTURE ch. 3, test Q9).

The package configures no logging; it only attaches a ``logging.NullHandler`` to the
``aero_kernel`` logger, so handlers and levels are the caller's decision (ARCHITECTURE
ch. 8.14).
"""

import logging

logging.getLogger("aero_kernel").addHandler(logging.NullHandler())

# The repository is ``package-mode = false``, so the package is never installed and has no
# distribution metadata to read the version from.
__version__ = "0.1.0"

__all__: list[str] = []

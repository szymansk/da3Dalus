"""Thin adapter shim around the optional `openvsp` Python package.

The `openvsp` PyPI package is built against a specific CPython version
and is not always available on PyPI for our Python 3.11/3.12 runtime
(see gh-639 for the install-strategy discussion). The OpenVSP importer
(gh-637) needs a deterministic way to:

1. Detect whether the dependency is installed.
2. Import the module without crashing the whole service when it is
   missing (the importer is an optional feature, not a hard runtime
   dependency).
3. Provide a clear, actionable error message when a caller tries to
   use the importer without the dependency installed.

Usage
-----

>>> from app.converters.openvsp_adapter import get_vsp, is_available
>>> if is_available():
...     vsp = get_vsp()
...     vsp.ClearVSPModel()
... else:
...     # graceful fallback / 503 / skip in tests
...     ...

Tests should use ``pytest.importorskip("openvsp")`` at module level
(or ``pytest.skip(...)`` keyed off ``is_available()``) to skip when
the dependency is missing.

Install paths
-------------

See ``docs/md/openvsp-import-setup.md`` and README for the three
supported install paths (PyPI wheel when matching, source build,
Docker microservice).
"""

from __future__ import annotations

import importlib
from types import ModuleType
from typing import Optional

_OPENVSP_MISSING_MSG = (
    "OpenVSP Python bindings are not installed. The `.vsp3` importer "
    "is an optional feature. Install via `poetry run pip install openvsp` "
    "(only works when a matching wheel exists for your Python version), "
    "build OpenVSP from source, or use the Docker microservice fallback. "
    "See docs/md/openvsp-import-setup.md for details."
)


_cached_module: Optional[ModuleType] = None
_import_attempted: bool = False
_import_error: Optional[BaseException] = None


def _attempt_import() -> Optional[ModuleType]:
    """Try once to import `openvsp` and memoise the result."""
    global _cached_module, _import_attempted, _import_error
    if _import_attempted:
        return _cached_module
    _import_attempted = True
    try:
        _cached_module = importlib.import_module("openvsp")
    except ImportError as exc:
        _cached_module = None
        _import_error = exc
    return _cached_module


def is_available() -> bool:
    """Return True iff the `openvsp` Python package can be imported."""
    return _attempt_import() is not None


def get_vsp() -> ModuleType:
    """Return the imported `openvsp` module.

    Raises
    ------
    ImportError
        If the `openvsp` package is not installed. The error message
        points the caller at the install documentation.
    """
    mod = _attempt_import()
    if mod is None:
        raise ImportError(_OPENVSP_MISSING_MSG) from _import_error
    return mod


def reset_for_tests() -> None:
    """Reset the memoised import state — for use in tests only."""
    global _cached_module, _import_attempted, _import_error
    _cached_module = None
    _import_attempted = False
    _import_error = None

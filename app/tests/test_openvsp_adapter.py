"""Unit tests for the `openvsp` adapter shim (gh-639).

The shim must:

* report ``is_available() == False`` when the optional package is not
  installed, without raising at import time.
* report ``is_available() == True`` and return a working module when
  the package IS installed (smoke-tested via the real package; skipped
  when missing — verifying the gracefully-skip behaviour itself is the
  point of the test).
* raise an ``ImportError`` with an actionable, install-path-pointing
  message when ``get_vsp()`` is called without the dependency present.
"""

from __future__ import annotations

import importlib
import sys
from unittest.mock import patch

import pytest

from app.converters import openvsp_adapter


@pytest.fixture(autouse=True)
def _reset_adapter_state():
    """Each test starts with a fresh memoised import state."""
    openvsp_adapter.reset_for_tests()
    yield
    openvsp_adapter.reset_for_tests()


class TestIsAvailable:
    def test_returns_false_when_openvsp_missing(self):
        """When the import fails the shim must not raise."""
        with patch.object(
            openvsp_adapter.importlib,
            "import_module",
            side_effect=ImportError("No module named 'openvsp'"),
        ):
            assert openvsp_adapter.is_available() is False

    def test_returns_true_when_openvsp_available(self):
        """When the import succeeds, is_available returns True."""
        fake = type(sys)("openvsp")  # minimal ModuleType
        with patch.object(openvsp_adapter.importlib, "import_module", return_value=fake):
            assert openvsp_adapter.is_available() is True

    def test_memoises_import_attempt(self):
        """Two calls trigger exactly one import attempt."""
        with patch.object(
            openvsp_adapter.importlib,
            "import_module",
            side_effect=ImportError("missing"),
        ) as mock_import:
            openvsp_adapter.is_available()
            openvsp_adapter.is_available()
            assert mock_import.call_count == 1


class TestGetVsp:
    def test_raises_import_error_with_install_hint_when_missing(self):
        """get_vsp must point the user at the install docs."""
        with patch.object(
            openvsp_adapter.importlib,
            "import_module",
            side_effect=ImportError("No module named 'openvsp'"),
        ):
            with pytest.raises(ImportError) as exc_info:
                openvsp_adapter.get_vsp()
        msg = str(exc_info.value)
        # Actionable: must mention the package, the docs file, and a hint
        # about the install path.
        assert "openvsp" in msg.lower()
        assert "openvsp-import-setup" in msg
        assert "pip install openvsp" in msg

    def test_returns_module_when_available(self):
        """get_vsp returns the imported module verbatim."""
        fake = type(sys)("openvsp")
        fake.GetVSPVersion = lambda: "fake-3.99"  # type: ignore[attr-defined]
        with patch.object(openvsp_adapter.importlib, "import_module", return_value=fake):
            mod = openvsp_adapter.get_vsp()
        assert mod is fake
        assert mod.GetVSPVersion() == "fake-3.99"


class TestSmoke:
    """Smoke-test the real `openvsp` package when installed.

    Skipped automatically in environments without the optional dependency
    (the common case for CI and most developer machines until OpenVSP
    publishes a wheel for our Python version).
    """

    def test_real_openvsp_smoke(self):
        vsp = pytest.importorskip("openvsp")
        # Just touch a couple of well-known entry points — we don't need
        # to verify behaviour here, just that the binding loads.
        assert callable(getattr(vsp, "ClearVSPModel", None))
        assert callable(getattr(vsp, "GetVSPVersion", None))


class TestModuleImport:
    def test_shim_imports_without_openvsp(self):
        """Importing the shim module must NOT require openvsp installed."""
        # If the shim ever triggers `import openvsp` at module level,
        # re-importing under a sys.modules block would fail. We verify
        # the lazy semantics by reloading the shim with openvsp masked.
        original = sys.modules.pop("openvsp", None)
        sys.modules["openvsp"] = None  # type: ignore[assignment]
        try:
            importlib.reload(openvsp_adapter)
            # Should not raise.
            assert openvsp_adapter.is_available() is False
        finally:
            if original is None:
                sys.modules.pop("openvsp", None)
            else:
                sys.modules["openvsp"] = original
            importlib.reload(openvsp_adapter)

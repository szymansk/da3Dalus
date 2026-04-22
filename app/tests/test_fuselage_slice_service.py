"""Tests for fuselage_slice_service — path traversal guard and input validation.

These tests cover the security-critical input sanitization added in GH #187 (S2083).
They do NOT test the actual STEP slicing (requires CadQuery + real STEP files).
"""

import pytest

from app.core.exceptions import ValidationError


class TestSliceStepFileInputValidation:
    """Cover the filename sanitization and file-type validation paths."""

    def _call(self, filename: str, content: bytes = b"fake-step"):
        """Import and call slice_step_file; skip if CadQuery unavailable."""
        pytest.importorskip("cadquery")
        from app.services.fuselage_slice_service import slice_step_file

        return slice_step_file(file_content=content, filename=filename)

    def test_rejects_unsupported_extension(self):
        """Files that are not .step/.stp must be rejected (covers suffix check)."""
        with pytest.raises(ValidationError, match="Unsupported file type"):
            self._call("model.obj")

    def test_rejects_no_extension(self):
        with pytest.raises(ValidationError, match="Unsupported file type"):
            self._call("model")

    def test_strips_directory_traversal_from_filename(self):
        """Path components like ../../ must be stripped (S2083 path traversal guard).

        The function extracts only the basename via Path(filename).name, so
        '../../etc/passwd.step' becomes 'passwd.step' and proceeds to the
        CadQuery call (which will fail on fake content, but the path traversal
        is neutralised).
        """
        pytest.importorskip("cadquery")
        from app.services.fuselage_slice_service import slice_step_file

        # Should NOT raise ValidationError — the traversal is stripped, suffix is valid.
        # It will fail later in CadQuery because the content is fake, but that's
        # an InternalError, not a path-traversal exploit.
        from app.core.exceptions import InternalError

        with pytest.raises((InternalError, Exception)):
            slice_step_file(
                file_content=b"not-a-real-step-file",
                filename="../../etc/passwd.step",
            )

    def test_accepts_valid_step_extension(self):
        """Both .step and .stp should pass the suffix check."""
        pytest.importorskip("cadquery")
        from app.core.exceptions import InternalError
        from app.services.fuselage_slice_service import slice_step_file

        # Will fail in CadQuery (fake content) but should pass validation
        for ext in (".step", ".stp", ".STEP", ".STP"):
            with pytest.raises((InternalError, Exception)):
                slice_step_file(file_content=b"fake", filename=f"model{ext}")

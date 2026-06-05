"""gh-861: the OP generator must capture CL/CD/Cm at the trimmed point so the
OP Comparison table shows them instead of "—".

`_aero_coefficients_at` runs one AeroBuildup eval and returns finite CL/CD/Cm.
These tests mock the asb module so they run in the fast tier.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services import operating_point_generator_service as opg


def _fake_asb(run_result):
    fake = MagicMock()
    inst = MagicMock()
    inst.run.return_value = run_result
    fake.AeroBuildup.return_value = inst
    fake.OperatingPoint.return_value = MagicMock()
    fake.Atmosphere.return_value = MagicMock()
    return fake


def _airplane():
    ap = MagicMock()
    ap.with_control_deflections.return_value = ap
    ap.xyz_ref = [0.0, 0.0, 0.0]
    return ap


class TestAeroCoefficientsAt:
    def test_returns_finite_cl_cd_cm(self):
        ap = _airplane()
        fake = _fake_asb({"CL": 0.531, "CD": 0.0234, "Cm": -0.012, "CY": 0.0})
        with patch.object(opg, "asb", fake):
            out = opg._aero_coefficients_at(ap, 0.0, 14.0, 4.0, 0.0, {"[elevator]Elev": -2.0})
        assert out == {"CL": 0.531, "CD": 0.0234, "Cm": -0.012}
        ap.with_control_deflections.assert_called_once_with({"[elevator]Elev": -2.0})

    def test_omits_non_finite_coefficients(self):
        ap = _airplane()
        fake = _fake_asb({"CL": float("nan"), "CD": 0.02, "Cm": float("inf")})
        with patch.object(opg, "asb", fake):
            out = opg._aero_coefficients_at(ap, 0.0, 14.0, 4.0, 0.0, None)
        # only the finite CD survives; NaN/Inf are dropped (→ "—" in the table)
        assert out == {"CD": 0.02}
        # no controls → no deflection application
        ap.with_control_deflections.assert_not_called()

    def test_returns_empty_on_solver_failure(self):
        ap = _airplane()
        fake = MagicMock()
        fake.AeroBuildup.side_effect = RuntimeError("solver blew up")
        fake.OperatingPoint.return_value = MagicMock()
        fake.Atmosphere.return_value = MagicMock()
        with patch.object(opg, "asb", fake):
            out = opg._aero_coefficients_at(ap, 0.0, 14.0, 4.0, 0.0, None)
        assert out == {}

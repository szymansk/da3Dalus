"""Tests for control surface deflection override logic in solvers (#416).

Tests cover:
- build_control_deflection_commands() with overrides parameter
- _build_control_run_command() with overrides parameter
- analyse_aerodynamics() applying overrides before dispatching to solvers
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.core.platform import aerosandbox_available

pytestmark = pytest.mark.skipif(
    not aerosandbox_available(),
    reason="requires aerosandbox",
)


def _make_airplane_with_controls(controls: list[tuple[str, float]]):
    """Create a mock airplane with named control surfaces.

    Each tuple is (name, deflection).
    """
    import aerosandbox as asb

    xsecs = []
    for name, defl in controls:
        xsecs.append(
            asb.WingXSec(
                xyz_le=[0, len(xsecs) * 0.25, 0],
                chord=0.3,
                airfoil=asb.Airfoil("naca0012"),
                control_surfaces=[
                    asb.ControlSurface(name=name, symmetric=True, deflection=defl, hinge_point=0.7),
                ],
            )
        )
    # Add a tip xsec without controls
    xsecs.append(
        asb.WingXSec(
            xyz_le=[0, len(xsecs) * 0.25, 0],
            chord=0.2,
            airfoil=asb.Airfoil("naca0012"),
        )
    )
    return asb.Airplane(
        name="test",
        wings=[asb.Wing(name="W", symmetric=True, xsecs=xsecs)],
    )


class TestBuildControlDeflectionCommandsOverrides:
    """Test the overrides parameter on build_control_deflection_commands."""

    def test_no_overrides_uses_geometry_defaults(self):
        from app.services.avl_strip_forces import build_control_deflection_commands

        airplane = _make_airplane_with_controls([("elevator", 5.0), ("aileron", 0.0)])
        commands = build_control_deflection_commands(airplane)
        assert commands == ["d1 d1 5.0", "d2 d2 0.0"]

    def test_overrides_replace_geometry_values(self):
        from app.services.avl_strip_forces import build_control_deflection_commands

        airplane = _make_airplane_with_controls([("elevator", 5.0), ("aileron", 0.0)])
        commands = build_control_deflection_commands(
            airplane, overrides={"elevator": -2.0, "aileron": 3.0}
        )
        assert commands == ["d1 d1 -2.0", "d2 d2 3.0"]

    def test_partial_override_only_changes_matched(self):
        from app.services.avl_strip_forces import build_control_deflection_commands

        airplane = _make_airplane_with_controls([("elevator", 5.0), ("aileron", 0.0)])
        commands = build_control_deflection_commands(airplane, overrides={"aileron": 7.5})
        assert commands == ["d1 d1 5.0", "d2 d2 7.5"]

    def test_override_nonexistent_surface_ignored(self):
        from app.services.avl_strip_forces import build_control_deflection_commands

        airplane = _make_airplane_with_controls([("elevator", 5.0)])
        commands = build_control_deflection_commands(airplane, overrides={"rudder": 10.0})
        assert commands == ["d1 d1 5.0"]

    def test_empty_overrides_dict_same_as_none(self):
        from app.services.avl_strip_forces import build_control_deflection_commands

        airplane = _make_airplane_with_controls([("flap", 15.0)])
        commands_none = build_control_deflection_commands(airplane, overrides=None)
        commands_empty = build_control_deflection_commands(airplane, overrides={})
        assert commands_none == commands_empty == ["d1 d1 15.0"]


class TestBuildControlRunCommandOverrides:
    """Test _build_control_run_command passes overrides through."""

    def test_overrides_passed_through(self):
        from app.api.utils import _build_control_run_command

        airplane = _make_airplane_with_controls([("elevator", 5.0)])
        result = _build_control_run_command(airplane, overrides={"elevator": -3.0})
        assert result == "d1 d1 -3.0"

    def test_none_overrides_uses_defaults(self):
        from app.api.utils import _build_control_run_command

        airplane = _make_airplane_with_controls([("elevator", 5.0)])
        result = _build_control_run_command(airplane, overrides=None)
        assert result == "d1 d1 5.0"


class TestAnalyseAerodynamicsDeflectionOverrides:
    """Test that analyse_aerodynamics applies control_deflections before dispatch."""

    def _make_operating_point(self, control_deflections=None):
        from app.schemas.aeroanalysisschema import OperatingPointSchema

        return OperatingPointSchema(
            velocity=20.0,
            alpha=5.0,
            beta=0.0,
            altitude=0.0,
            control_deflections=control_deflections,
        )

    @patch("app.api.utils._run_aerobuildup")
    def test_aerobuildup_gets_deflected_airplane(self, mock_run_abu):
        import aerosandbox as asb

        from app.api.utils import analyse_aerodynamics
        from app.schemas.AeroplaneRequest import AnalysisToolUrlType

        airplane = _make_airplane_with_controls([("elevator", 5.0)])
        op = self._make_operating_point(control_deflections={"elevator": -2.0})

        mock_run_abu.return_value = (MagicMock(), None)

        analyse_aerodynamics(AnalysisToolUrlType.AEROBUILDUP, op, airplane)

        called_airplane = mock_run_abu.call_args[0][0]
        # The airplane passed to the solver should have overridden deflection
        elevator_deflection = called_airplane.wings[0].xsecs[0].control_surfaces[0].deflection
        assert elevator_deflection == -2.0

    @patch("app.api.utils._run_aerobuildup")
    def test_aerobuildup_no_overrides_leaves_airplane_unchanged(self, mock_run_abu):
        from app.api.utils import analyse_aerodynamics
        from app.schemas.AeroplaneRequest import AnalysisToolUrlType

        airplane = _make_airplane_with_controls([("elevator", 5.0)])
        op = self._make_operating_point(control_deflections=None)

        mock_run_abu.return_value = (MagicMock(), None)

        analyse_aerodynamics(AnalysisToolUrlType.AEROBUILDUP, op, airplane)

        called_airplane = mock_run_abu.call_args[0][0]
        elevator_deflection = called_airplane.wings[0].xsecs[0].control_surfaces[0].deflection
        assert elevator_deflection == 5.0

    @patch("app.api.utils._run_vlm")
    def test_vlm_gets_deflected_airplane(self, mock_run_vlm):
        from app.api.utils import analyse_aerodynamics
        from app.schemas.AeroplaneRequest import AnalysisToolUrlType

        airplane = _make_airplane_with_controls([("aileron", 0.0)])
        op = self._make_operating_point(control_deflections={"aileron": 10.0})

        mock_run_vlm.return_value = (MagicMock(), None)

        analyse_aerodynamics(AnalysisToolUrlType.VORTEX_LATTICE, op, airplane)

        called_airplane = mock_run_vlm.call_args[0][0]
        aileron_deflection = called_airplane.wings[0].xsecs[0].control_surfaces[0].deflection
        assert aileron_deflection == 10.0

    @patch("app.api.utils._run_avl")
    def test_avl_gets_deflected_airplane(self, mock_run_avl):
        from app.api.utils import analyse_aerodynamics
        from app.schemas.AeroplaneRequest import AnalysisToolUrlType

        airplane = _make_airplane_with_controls([("elevator", 5.0)])
        op = self._make_operating_point(control_deflections={"elevator": -1.0})

        mock_run_avl.return_value = (MagicMock(), None)

        analyse_aerodynamics(AnalysisToolUrlType.AVL, op, airplane)

        called_airplane = mock_run_avl.call_args[0][0]
        elevator_deflection = called_airplane.wings[0].xsecs[0].control_surfaces[0].deflection
        assert elevator_deflection == -1.0

    @patch("app.api.utils._run_aerobuildup")
    def test_empty_dict_overrides_leaves_airplane_unchanged(self, mock_run_abu):
        from app.api.utils import analyse_aerodynamics
        from app.schemas.AeroplaneRequest import AnalysisToolUrlType

        airplane = _make_airplane_with_controls([("elevator", 5.0)])
        op = self._make_operating_point(control_deflections={})

        mock_run_abu.return_value = (MagicMock(), None)

        analyse_aerodynamics(AnalysisToolUrlType.AEROBUILDUP, op, airplane)

        called_airplane = mock_run_abu.call_args[0][0]
        elevator_deflection = called_airplane.wings[0].xsecs[0].control_surfaces[0].deflection
        assert elevator_deflection == 5.0

    @patch("app.api.utils._run_avl")
    def test_original_airplane_not_mutated(self, mock_run_avl):
        from app.api.utils import analyse_aerodynamics
        from app.schemas.AeroplaneRequest import AnalysisToolUrlType

        airplane = _make_airplane_with_controls([("elevator", 5.0)])
        op = self._make_operating_point(control_deflections={"elevator": -2.0})

        mock_run_avl.return_value = (MagicMock(), None)

        analyse_aerodynamics(AnalysisToolUrlType.AVL, op, airplane)

        # Original airplane should still have the original deflection
        assert airplane.wings[0].xsecs[0].control_surfaces[0].deflection == 5.0

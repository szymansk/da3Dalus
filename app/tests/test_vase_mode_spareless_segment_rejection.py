"""gh-361 regression — VaseModeWingCreator must reject spareless
non-tip segments with a clear ``ValueError`` instead of crashing
deep in the CAD pipeline.

A VaseModeWing is structurally inseparable from its spar — the spar
is the load-bearing element that holds the hollow vase-printed shell
together at the rib interfaces. A non-tip segment with no
``spare_list`` is therefore an invalid construction input, not a
geometry we can quietly degrade. Pre-fix, the pipeline crashed with:

- ``IndexError: list index out of range`` on ``spare_list[0]``
- ``ValueError: Cannot find a solid on the stack`` later (any
  attempt to "skip" the spar pipeline and feed empty Workplanes
  downstream fails inside ``raw_ribs.cut(wing_cutout)``)

Both surfaces are opaque to the user. The fix validates up front and
raises a ``ValueError`` that names the offending segment indices and
states the constraint + remediation.

Why this is the right place for the validator: ``VaseModeWingCreator``
owns the VaseMode construction contract. Other creators may accept
spareless segments — the constraint belongs on the creator that
enforces it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cad_designer.airplane.aircraft_topology.wing import (
    Spare,
    TrailingEdgeDevice,
    WingConfiguration,
)
from cad_designer.airplane.aircraft_topology.wing.Airfoil import Airfoil
from cad_designer.airplane.creator.wing.VaseModeWingCreator import (
    VaseModeWingCreator,
)


_AIRFOIL_PATH = str(
    (Path(__file__).resolve().parents[2] / "components" / "airfoils" / "mh32.dat").resolve()
)


def _spar() -> Spare:
    return Spare(
        spare_support_dimension_width=4.0,
        spare_support_dimension_height=4.0,
        spare_position_factor=0.25,
    )


def _aileron() -> TrailingEdgeDevice:
    """Minimal TED — used only to prove the validator fires BEFORE
    the TED pipeline runs."""
    return TrailingEdgeDevice(
        name="aileron",
        rel_chord_root=0.7,
        rel_chord_tip=0.7,
        hinge_spacing=0.5,
        side_spacing_root=2.0,
        side_spacing_tip=2.0,
        servo=1,
        servo_placement="top",
        rel_chord_servo_position=0.414,
        rel_length_servo_position=0.486,
        positive_deflection_deg=20,
        negative_deflection_deg=15,
        trailing_edge_offset_factor=1.2,
        hinge_type="top",
        symmetric=False,
    )


class TestSparelessNonTipSegmentRejection:
    """gh-361: the validator must reject any WingConfiguration whose
    non-tip / non-root segments carry an empty ``spare_list``.

    These tests pin the *contract*: they call the validator directly
    so the test is fast (no CadQuery build) and the assertion is on
    the error message, not on a downstream IndexError / ValueError
    that could shift across CadQuery versions.
    """

    @staticmethod
    def _build_wing_with_spareless_outer_segment() -> WingConfiguration:
        """Two-segment wing — root with spar + outer segment with ONLY
        a TED (no spars). This is the gh-361 trigger."""
        wing_config = WingConfiguration(
            nose_pnt=(0, 0, 0),
            root_airfoil=Airfoil(airfoil=_AIRFOIL_PATH, chord=120.0, incidence=0),
            length=10.0,
            sweep=0,
            tip_airfoil=Airfoil(chord=120.0, incidence=0),
            number_interpolation_points=101,
            spare_list=[_spar()],
        )
        wing_config.add_segment(
            length=150,
            sweep=2.0,
            tip_airfoil=Airfoil(chord=110, incidence=0),
            spare_list=[_spar()],
        )
        # Outer segment — TED only, no spares. Pre-fix: IndexError.
        # Post-broken-fix: opaque CadQuery error. Post-real-fix:
        # ValueError at validation time.
        wing_config.add_segment(
            length=100,
            sweep=3.0,
            tip_airfoil=Airfoil(chord=90, incidence=0),
            spare_list=None,
            trailing_edge_device=_aileron(),
        )
        return wing_config

    def test_validator_raises_value_error_on_spareless_non_tip_segment(self):
        """The minimum bar from gh-361: a clear ValueError when any
        non-tip segment is missing its ``spare_list``."""
        wing_config = self._build_wing_with_spareless_outer_segment()
        with pytest.raises(ValueError, match=r"spar"):
            VaseModeWingCreator._validate_all_non_tip_segments_have_spares(wing_config)

    def test_error_message_names_offending_segment_indices(self):
        """The error message must enumerate the bad segments so the
        user knows WHICH segment to fix. Pre-fix the user saw only
        ``IndexError: list index out of range`` — no signal."""
        wing_config = self._build_wing_with_spareless_outer_segment()
        with pytest.raises(ValueError) as exc:
            VaseModeWingCreator._validate_all_non_tip_segments_have_spares(wing_config)
        message = str(exc.value)
        # The outer segment is index 2 (root + add_segment + add_segment).
        assert "[2]" in message, f"missing segment index in {message!r}"
        # Message must point at the spare_list field by name so the UI
        # can highlight it.
        assert "spare_list" in message, f"field name missing from {message!r}"

    def test_validator_accepts_wing_where_every_non_tip_segment_has_spar(self):
        """Control case: a well-formed wing (root + 2 segments, all
        with spars, no tip cap) must pass the validator silently."""
        wing_config = WingConfiguration(
            nose_pnt=(0, 0, 0),
            root_airfoil=Airfoil(airfoil=_AIRFOIL_PATH, chord=120.0, incidence=0),
            length=10.0,
            tip_airfoil=Airfoil(chord=120.0, incidence=0),
            number_interpolation_points=101,
            spare_list=[_spar()],
        )
        wing_config.add_segment(
            length=150,
            tip_airfoil=Airfoil(chord=110, incidence=0),
            spare_list=[_spar()],
        )
        # No exception.
        VaseModeWingCreator._validate_all_non_tip_segments_have_spares(wing_config)

    def test_validator_accepts_spareless_tip_segment(self):
        """Tip segments are cosmetic wing-end caps — they do NOT need
        a spar. The validator must skip them."""
        wing_config = WingConfiguration(
            nose_pnt=(0, 0, 0),
            root_airfoil=Airfoil(airfoil=_AIRFOIL_PATH, chord=120.0, incidence=0),
            length=10.0,
            tip_airfoil=Airfoil(chord=120.0, incidence=0),
            number_interpolation_points=101,
            spare_list=[_spar()],
        )
        wing_config.add_segment(
            length=150,
            tip_airfoil=Airfoil(chord=110, incidence=0),
            spare_list=[_spar()],
        )
        # Tip cap — no spar. Must NOT trigger the validator.
        wing_config.add_tip_segment(
            tip_type="round",
            length=20,
            tip_airfoil=Airfoil(chord=50, incidence=0),
        )
        # No exception.
        VaseModeWingCreator._validate_all_non_tip_segments_have_spares(wing_config)

    def test_validator_reports_all_offending_segments_at_once(self):
        """If multiple non-tip segments are spareless, the error
        message must list ALL of them in one go — the user should not
        have to iterate one fix at a time."""
        wing_config = WingConfiguration(
            nose_pnt=(0, 0, 0),
            root_airfoil=Airfoil(airfoil=_AIRFOIL_PATH, chord=120.0, incidence=0),
            length=10.0,
            tip_airfoil=Airfoil(chord=120.0, incidence=0),
            number_interpolation_points=101,
            spare_list=[_spar()],
        )
        # Two consecutive spareless segments — both with a TED so the
        # add_segment call succeeds (it doesn't enforce spare presence
        # itself — that's VaseMode's contract, not the topology's).
        wing_config.add_segment(
            length=80,
            tip_airfoil=Airfoil(chord=110, incidence=0),
            spare_list=None,
            trailing_edge_device=_aileron(),
        )
        wing_config.add_segment(
            length=80,
            tip_airfoil=Airfoil(chord=100, incidence=0),
            spare_list=None,
            trailing_edge_device=_aileron(),
        )
        with pytest.raises(ValueError) as exc:
            VaseModeWingCreator._validate_all_non_tip_segments_have_spares(wing_config)
        message = str(exc.value)
        assert "[1, 2]" in message, (
            f"both offending segment indices must be listed, got: {message!r}"
        )

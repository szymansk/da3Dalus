"""Rear-spar control-surface clearance + secondary Option-B spares (gh-1059).

Two pure (fast) concerns, both with no CAD dependency:

* **Rear/torsion-spar clearance:** a *computed* spar must never overlap a
  control surface. The rear spar's chordwise location must stay forward of the
  control surface's hinge line (with a margin). A designer may still place a
  reinforcing spar *inside* a control surface manually — that is not a computed
  spar — so the guard only applies to the solver's chosen ``x_c``.
* **Secondary spars → Option B:** rear / reinforcement spars persist as
  partial-span ``Spare`` objects (``spare_start`` + ``spare_length``) under
  their own ids (rear root index 1, further pieces next free ids). No segment
  split.
"""

from __future__ import annotations

import pytest

from cad_designer.airplane.geometry.spar_solver import (
    RearSparClearanceInfeasible,
    SparPiece,
    SparRole,
    rear_spar_x_c_with_clearance,
)
from cad_designer.airplane.geometry.spar_cad_insertion import (
    secondary_spare_option_b,
)


# ---------------------------------------------------------------------------
# Rear-spar control-surface clearance
# ---------------------------------------------------------------------------


class TestRearSparClearance:
    def test_requested_x_c_kept_when_already_forward(self):
        # control surface hinge at 0.75; a rear spar at 0.55 is already clear.
        x_c = rear_spar_x_c_with_clearance(0.55, control_surface_hinge_x_c=0.75)
        assert x_c == pytest.approx(0.55)

    def test_x_c_pulled_forward_of_hinge(self):
        # requested 0.80 is *behind* a hinge at 0.75 -> must move forward.
        x_c = rear_spar_x_c_with_clearance(0.80, control_surface_hinge_x_c=0.75)
        assert x_c < 0.75

    def test_clearance_margin_applied(self):
        x_c = rear_spar_x_c_with_clearance(0.80, control_surface_hinge_x_c=0.70, clearance=0.05)
        assert x_c == pytest.approx(0.65)

    def test_no_control_surface_keeps_request(self):
        x_c = rear_spar_x_c_with_clearance(0.85, control_surface_hinge_x_c=None)
        assert x_c == pytest.approx(0.85)

    def test_hinge_near_the_le_is_infeasible_not_floored(self):
        """gh-1096: the LE floor must NOT override the control-surface clearance.

        This test previously asserted only ``x_c > 0.0``, which the old
        ``max(safe, _MIN_REAR_X_C)`` satisfied by returning 0.05 — *behind* a
        hinge at 0.02. That put the spar inside the control surface and called
        it success. ``Q-WD-8`` ② records the clamp order as a confirmed defect.

        When the clearance line and the LE floor cannot both be honoured there
        is no buildable position, and per RF-SP-20 the verdict is reported, not
        clamped to something that merely looks buildable.
        """
        with pytest.raises(RearSparClearanceInfeasible) as exc:
            rear_spar_x_c_with_clearance(0.5, control_surface_hinge_x_c=0.02, clearance=0.10)
        # the message is read by a builder: it must name the numbers involved.
        msg = str(exc.value)
        assert "0.02" in msg and "0.10" in msg

    def test_clearance_wins_over_the_floor_when_both_fit(self):
        """A hinge that leaves room still yields the clearance line, not the floor."""
        x_c = rear_spar_x_c_with_clearance(0.5, control_surface_hinge_x_c=0.10, clearance=0.03)
        assert x_c == pytest.approx(0.07)
        assert x_c < 0.10, "the spar must sit forward of the hinge"

    def test_exactly_at_hinge_pulled_forward(self):
        x_c = rear_spar_x_c_with_clearance(0.75, control_surface_hinge_x_c=0.75, clearance=0.03)
        assert x_c == pytest.approx(0.72)

    def test_build_stations_applies_clearance(self):
        """The station builder pulls a rear spar forward of the control surface."""
        from cad_designer.airplane.geometry import spar_solver

        sampled_x_cs: list[float] = []

        class _Pt:
            def __init__(self, y_span, x_c):
                self.y_span = y_span
                self.x_c = x_c
                self.thickness = 20.0
                self.center_z = 0.0
                self.bottom_z = -10.0
                self.top_z = 10.0

        class _FakeGeometry:
            _segment_lengths = [500.0]

            def at(self, y_span, x_c):
                sampled_x_cs.append(x_c)
                return _Pt(y_span, x_c)

        spar_solver.build_stations_from_geometry(
            _FakeGeometry(),
            moment_fn=lambda y: 1000.0 * (1.0 - y),
            sigma_allow_mpa=300.0,
            n_span=3,
            x_c=0.80,  # requested behind the hinge
            control_surface_hinge_x_c=0.75,
        )
        # every sampled x_c must be forward of (hinge - clearance) = 0.72
        assert sampled_x_cs
        assert all(x <= 0.72 + 1e-9 for x in sampled_x_cs)


# ---------------------------------------------------------------------------
# Secondary spars → Option B (partial-span Spare)
# ---------------------------------------------------------------------------


def _rear_piece(*, origin_y: float = 100.0, length: float = 300.0, od: float = 8.0) -> SparPiece:
    return SparPiece(
        role=SparRole.REAR,
        spare_origin=(0.0, origin_y, 0.0),
        spare_vector=(0.0, 1.0, 0.0),
        outer_d=od,
        inner_d=od * 0.6,
        shape="tube",
        governing_y=origin_y,
        utilisation=0.5,
        length=length,
    )


class TestSecondaryOptionB:
    def test_partial_span_start_and_length(self):
        piece = _rear_piece(origin_y=100.0, length=300.0)
        # the secondary spare starts 100mm into the segment (its origin offset
        # from the segment root) and spans the piece length.
        spare = secondary_spare_option_b(piece, segment_root_y=0.0)
        assert spare.spare_start == pytest.approx(100.0)
        assert spare.spare_length == pytest.approx(300.0)

    def test_start_is_relative_to_segment_root(self):
        piece = _rear_piece(origin_y=600.0, length=200.0)
        spare = secondary_spare_option_b(piece, segment_root_y=500.0)
        assert spare.spare_start == pytest.approx(100.0)  # 600 - 500
        assert spare.spare_length == pytest.approx(200.0)

    def test_round_tube_maps_to_equal_width_height(self):
        piece = _rear_piece(od=8.0)
        spare = secondary_spare_option_b(piece, segment_root_y=0.0)
        assert spare.spare_support_dimension_width == pytest.approx(8.0)
        assert spare.spare_support_dimension_height == pytest.approx(8.0)

    def test_uses_normal_mode_with_explicit_origin_vector(self):
        piece = _rear_piece()
        spare = secondary_spare_option_b(piece, segment_root_y=0.0)
        assert spare.spare_mode == "normal"
        assert spare.spare_vector is not None
        assert spare.spare_origin is not None

    def test_negative_start_clamped_to_zero(self):
        # piece origin inboard of the segment root (mirror / rounding) -> clamp.
        piece = _rear_piece(origin_y=480.0)
        spare = secondary_spare_option_b(piece, segment_root_y=500.0)
        assert spare.spare_start == pytest.approx(0.0)

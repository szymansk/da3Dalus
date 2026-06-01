"""gh-806: pin the stall-in-turn boundary EXACTLY against ``_apply_turn_feasibility``.

Flight-mechanics ground truth (steady coordinated level turn, right turn phi>0):

    n = 1 / cos(phi)               20deg -> 1.064, 40deg -> 1.305, 60deg -> 2.000
    V_stall_turn = V_stall_1g * sqrt(n)

The function must flag a turn as stall-limited iff the target speed is *below*
the in-turn stall speed: V < vs_clean * sqrt(n). At exactly V = vs_clean*sqrt(n)
the wing can (marginally) sustain the turn, so the boundary is a strict
less-than — AT the boundary it must NOT be flagged.

These tests are pure: ``_apply_turn_feasibility`` only touches ``point.warnings``
(a list) and ``point.status``, and reads the load factor from the real
``turn_kinematics``. No AeroSandbox / trimmer needed.
"""

from __future__ import annotations

import math

import pytest

from app.schemas.aeroanalysisschema import OperatingPointStatus
from app.services.operating_point_generator_service import _apply_turn_feasibility
from app.services.turn_kinematics import turn_kinematics


class _StubPoint:
    """Minimal duck-typed operating point: the function only needs these two."""

    def __init__(self, status=OperatingPointStatus.TRIMMED):
        self.warnings: list[str] = []
        self.status = status


# Use the REAL load factor from turn_kinematics so the boundary is defined by the
# same physics the production code uses, not a re-implemented n.
_VS_CLEAN = 12.0  # m/s, an arbitrary but fixed clean stall speed
_BANKS = [20.0, 40.0, 60.0]


def _n_for(bank_deg: float) -> float:
    return turn_kinematics(bank_deg=bank_deg, velocity=50.0).n


def _v_stall_turn(bank_deg: float, vs_clean: float = _VS_CLEAN) -> float:
    return vs_clean * math.sqrt(_n_for(bank_deg))


@pytest.mark.parametrize(
    "bank, expected_n",
    [(20.0, 1.0 / math.cos(math.radians(20.0))),
     (40.0, 1.0 / math.cos(math.radians(40.0))),
     (60.0, 2.0)],
)
def test_load_factor_matches_sadraey(bank, expected_n):
    """Sanity-anchor the n we build the boundary on: n=1/cos(phi)."""
    assert _n_for(bank) == pytest.approx(expected_n, rel=1e-9)


@pytest.mark.parametrize("bank", _BANKS)
def test_just_below_boundary_is_flagged(bank):
    """V infinitesimally below vs_clean*sqrt(n) => LIMIT_REACHED + STALL_IN_TURN."""
    v_boundary = _v_stall_turn(bank)
    v_below = v_boundary * (1.0 - 1e-6)

    point = _StubPoint()
    _apply_turn_feasibility(point, bank, v_below, _VS_CLEAN)

    assert point.status == OperatingPointStatus.LIMIT_REACHED
    assert any("STALL_IN_TURN" in w for w in point.warnings)


@pytest.mark.parametrize("bank", _BANKS)
def test_just_above_boundary_is_not_flagged(bank):
    """V infinitesimally above vs_clean*sqrt(n) => sustainable, no flag."""
    v_boundary = _v_stall_turn(bank)
    v_above = v_boundary * (1.0 + 1e-6)

    point = _StubPoint()
    _apply_turn_feasibility(point, bank, v_above, _VS_CLEAN)

    assert point.status == OperatingPointStatus.TRIMMED
    assert not any("STALL_IN_TURN" in w for w in point.warnings)


@pytest.mark.parametrize("bank", _BANKS)
def test_exactly_at_boundary_is_not_flagged(bank):
    """At V == vs_clean*sqrt(n) the criterion is strict (<), so it is sustainable."""
    v_boundary = _v_stall_turn(bank)

    point = _StubPoint()
    _apply_turn_feasibility(point, bank, v_boundary, _VS_CLEAN)

    assert point.status == OperatingPointStatus.TRIMMED
    assert not any("STALL_IN_TURN" in w for w in point.warnings)


def test_boundary_rises_with_bank_41pct_at_60deg():
    """Physical: stall speed in a 60deg turn (n=2) is 41% above the 1g stall."""
    assert _v_stall_turn(60.0) == pytest.approx(_VS_CLEAN * math.sqrt(2.0), rel=1e-9)
    # Monotonic increase of the in-turn stall speed with bank.
    boundaries = [_v_stall_turn(b) for b in _BANKS]
    assert boundaries == sorted(boundaries)
    # Offset zip is intentionally ragged (pairs of consecutive banks).
    assert all(b2 > b1 for b1, b2 in zip(boundaries, boundaries[1:], strict=False))


@pytest.mark.parametrize("bank", _BANKS)
def test_warning_message_contains_bank_and_v_stall_turn(bank):
    """The warning must name the bank angle and the computed V_stall_turn."""
    v_boundary = _v_stall_turn(bank)
    v_below = v_boundary * (1.0 - 1e-3)

    point = _StubPoint()
    _apply_turn_feasibility(point, bank, v_below, _VS_CLEAN)

    msg = next(w for w in point.warnings if "STALL_IN_TURN" in w)
    # bank angle rendered with %.0f
    assert f"{bank:.0f} deg bank" in msg
    # the computed in-turn stall speed, rendered with %.1f
    assert f"V_stall_turn={v_boundary:.1f} m/s" in msg
    # load factor n with %.2f
    assert f"n={_n_for(bank):.2f}" in msg


def test_no_flag_when_vs_clean_nonpositive():
    """Guard: no reference stall speed => cannot judge feasibility, leave untouched."""
    point = _StubPoint()
    _apply_turn_feasibility(point, 60.0, 1.0, 0.0)
    assert point.status == OperatingPointStatus.TRIMMED
    assert point.warnings == []


def test_no_flag_when_bank_is_none():
    """Guard: a non-turn point (no bank) is never a stall-in-turn candidate."""
    point = _StubPoint()
    _apply_turn_feasibility(point, None, 1.0, _VS_CLEAN)
    assert point.status == OperatingPointStatus.TRIMMED
    assert point.warnings == []


def test_warning_not_duplicated_on_reapply():
    """Idempotent: re-applying the same stall condition must not stack warnings."""
    bank = 60.0
    v_below = _v_stall_turn(bank) * 0.5
    point = _StubPoint()
    _apply_turn_feasibility(point, bank, v_below, _VS_CLEAN)
    _apply_turn_feasibility(point, bank, v_below, _VS_CLEAN)
    stall_warnings = [w for w in point.warnings if "STALL_IN_TURN" in w]
    assert len(stall_warnings) == 1

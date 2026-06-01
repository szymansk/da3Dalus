"""gh-806: a turn whose required CL exceeds CL_max is flagged, not silently trimmed."""

from app.schemas.aeroanalysisschema import OperatingPointStatus
from app.services.operating_point_generator_service import _apply_turn_feasibility


class _Pt:
    def __init__(self):
        self.warnings = []
        self.status = OperatingPointStatus.TRIMMED


def test_low_speed_high_bank_flagged():
    pt = _Pt()
    # vs_clean=12, n(60)=2 -> vs_turn=12*sqrt(2)=16.97; V=14 < that -> infeasible
    _apply_turn_feasibility(pt, bank_deg=60.0, velocity=14.0, vs_clean=12.0)
    assert pt.status == OperatingPointStatus.LIMIT_REACHED
    assert any("STALL_IN_TURN" in w for w in pt.warnings)


def test_adequate_speed_not_flagged():
    pt = _Pt()
    _apply_turn_feasibility(pt, bank_deg=60.0, velocity=25.0, vs_clean=12.0)
    assert pt.status == OperatingPointStatus.TRIMMED
    assert not any("STALL_IN_TURN" in w for w in pt.warnings)


def test_non_turn_noop():
    pt = _Pt()
    _apply_turn_feasibility(pt, bank_deg=None, velocity=14.0, vs_clean=12.0)
    assert pt.status == OperatingPointStatus.TRIMMED

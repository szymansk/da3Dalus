"""Fast (no CadQuery / AeroSandbox) unit tests for gh-1053 normal-mode
spare-geometry preservation decision + DB(mm)→config(scale) origin scaling.

These guard the core of the gh-1053 fix in the CI fast tier, which excludes the
heavy CAD/aero dependencies that the full converter path needs.
"""

from __future__ import annotations

import pytest

from app.converters.spare_origin_preservation import (
    scale_db_origin_to_config,
    should_preserve_normal_spare,
)


class TestShouldPreserveNormalSpare:
    def test_normal_with_explicit_origin_and_vector_is_preserved(self):
        assert should_preserve_normal_spare("normal", [40.5, 0.75, 3.69], [0.0, 0.9999, 0.0155])

    @pytest.mark.parametrize(
        "mode", ["standard", "follow", "standard_backward", "orthogonal_backward"]
    )
    def test_non_normal_modes_are_never_preserved(self, mode):
        # gh-352/gh-362 guard: these always go through recompute.
        assert not should_preserve_normal_spare(mode, [40.5, 0.75, 3.69], [0.0, 1.0, 0.0])

    def test_normal_without_origin_is_not_preserved(self):
        assert not should_preserve_normal_spare("normal", None, [0.0, 1.0, 0.0])

    def test_normal_without_vector_is_not_preserved(self):
        assert not should_preserve_normal_spare("normal", [40.5, 0.75, 3.69], None)

    def test_partial_origin_is_not_preserved(self):
        assert not should_preserve_normal_spare("normal", [40.5, 0.75], [0.0, 1.0, 0.0])

    def test_none_mode_is_not_preserved(self):
        assert not should_preserve_normal_spare(None, [40.5, 0.75, 3.69], [0.0, 1.0, 0.0])

    def test_non_sequence_origin_is_not_preserved(self):
        # A scalar (or any non-sequence) is not an explicit triplet.
        assert not should_preserve_normal_spare("normal", 40.5, [0.0, 1.0, 0.0])

    def test_string_origin_is_not_preserved(self):
        # A 3-char string is a Sequence of len 3 but not numeric coords.
        assert not should_preserve_normal_spare("normal", "abc", [0.0, 1.0, 0.0])

    def test_nan_component_is_not_preserved(self):
        assert not should_preserve_normal_spare(
            "normal", [float("nan"), 0.75, 3.69], [0.0, 1.0, 0.0]
        )

    def test_non_numeric_component_is_not_preserved(self):
        # A component that cannot be coerced to float (TypeError) → not preserved.
        assert not should_preserve_normal_spare("normal", [object(), 0.75, 3.69], [0.0, 1.0, 0.0])


class TestScaleDbOriginToConfig:
    def test_scale_one_converts_mm_to_metres(self):
        # DB mm → metre-scale config (scale=1.0): the recompute path.
        out = scale_db_origin_to_config([40.5, 750.0, 3690.0], scale=1.0)
        assert out == pytest.approx((0.0405, 0.75, 3.69))

    def test_scale_thousand_keeps_mm_verbatim(self):
        # DB mm → mm-scale config (scale=1000.0): the CAD path.
        out = scale_db_origin_to_config([40.5, 750.0, 3690.0], scale=1000.0)
        assert out == pytest.approx((40.5, 750.0, 3690.0))

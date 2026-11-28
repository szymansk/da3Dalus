"""gh-1481: the backward spar rule of the model -> config converter, on a stand-in wing.

The round-trip against a real ``WingConfiguration`` is in
``test_spar_backward_mode_roundtrip.py``. These tests need no CAD stack: the
wing is a stand-in that records what the converter asks of it.
"""

from types import SimpleNamespace

from app.converters.model_schema_converters import (
    _backward_spare_anchor_segment,
    _resolve_backward_spare_run,
    _resolve_single_spare,
)


def _spar(mode: str, position_factor: float | None = 0.3) -> SimpleNamespace:
    return SimpleNamespace(
        spare_mode=mode,
        spare_position_factor=position_factor,
        spare_vector=None,
        spare_origin=None,
    )


class _Wing:
    """Stand-in for WingConfiguration: segments with spars, and a call record."""

    def __init__(self, modes_per_segment: list[list[str]], position_factor: float | None = 0.3):
        self.segments = [
            SimpleNamespace(spare_list=[_spar(mode, position_factor) for mode in modes])
            for modes in modes_per_segment
        ]
        self.calls: list[tuple] = []

    def _set_standard_spare_origin_vector(self, segment_index, spare):
        self.calls.append(("standard", segment_index))

    def _set_follow_spare_origin_vector(self, segment_index, spare, spare_index):
        self.calls.append(("follow", segment_index, spare_index))

    def _get_standard_spare_origin_and_vector(
        self, start_segment, end_segment, spare_position_factor
    ):
        self.calls.append(("aim", start_segment, end_segment, spare_position_factor))
        return "vector", "origin", "orthogonal_vector", "orthogonal_origin"


def test_the_anchor_is_the_nearest_earlier_spar_that_does_not_follow():
    wing = _Wing([["standard"], ["standard"], ["follow"], ["standard_backward"]])

    assert _backward_spare_anchor_segment(wing, segment_index=3, spare_index=0) == 1


def test_a_segment_without_that_spar_interrupts_the_run():
    wing = _Wing([["standard"], [], ["standard_backward"]])

    assert _backward_spare_anchor_segment(wing, segment_index=2, spare_index=0) is None


def test_a_run_of_followers_only_has_no_anchor():
    wing = _Wing([["follow"], ["standard_backward"]])

    assert _backward_spare_anchor_segment(wing, segment_index=1, spare_index=0) is None


def test_the_anchor_is_aimed_at_the_backward_segment_and_the_run_follows():
    wing = _Wing([["standard"], ["follow"], ["standard_backward"]])

    _resolve_backward_spare_run(wing, anchor_segment=0, segment_index=2, spare_index=0)

    anchor = wing.segments[0].spare_list[0]
    assert (anchor.spare_vector, anchor.spare_origin) == ("vector", "origin")
    assert wing.calls == [("aim", 0, 2, 0.3), ("follow", 1, 0), ("follow", 2, 0)]


def test_an_orthogonal_backward_spar_takes_the_orthogonal_pair():
    wing = _Wing([["standard"], ["orthogonal_backward"]])

    _resolve_backward_spare_run(wing, anchor_segment=0, segment_index=1, spare_index=0)

    anchor = wing.segments[0].spare_list[0]
    assert (anchor.spare_vector, anchor.spare_origin) == ("orthogonal_vector", "orthogonal_origin")


def test_a_missing_position_factor_is_the_quarter_chord_of_add_segment():
    wing = _Wing([["standard"], ["standard_backward"]], position_factor=None)

    _resolve_backward_spare_run(wing, anchor_segment=0, segment_index=1, spare_index=0)

    assert wing.calls[0] == ("aim", 0, 1, 0.25)
    assert [segment.spare_list[0].spare_position_factor for segment in wing.segments] == [
        0.25,
        0.25,
    ]


def test_a_backward_spar_with_nothing_to_continue_is_placed_as_standard_and_says_so(caplog):
    wing = _Wing([["standard_backward"]])
    spare = wing.segments[0].spare_list[0]

    with caplog.at_level("WARNING"):
        _resolve_single_spare(wing, 0, 0, spare)

    assert wing.calls == [("standard", 0)]
    assert "no spar to continue" in caplog.text

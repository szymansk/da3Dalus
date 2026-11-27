"""gh-1475: a ``*_backward`` spar keeps its meaning through the app's converters.

``standard_backward`` / ``orthogonal_backward`` on a spar say: the spar that
started further inboard runs straight to the tip of *this* segment, and every
segment in between follows that line. ``WingConfiguration`` resolves this when
the segment is added. The converters clear and recompute every spar vector
(gh-352, gh-362) and treated the backward modes like ``standard``, so the spar
of a swept wing no longer followed the sweep and left the airfoil further
outboard; the vase-mode ribs could then not be built.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.converters import model_schema_converters as converters


class _FakeWingConfig:
    """Records the topology calls the converter makes; no CAD kernel involved."""

    def __init__(self, modes_per_segment: list[list[str]]):
        self.segments = [
            SimpleNamespace(
                length=100.0,
                spare_list=[
                    SimpleNamespace(
                        spare_mode=mode,
                        spare_position_factor=0.25,
                        spare_vector=None,
                        spare_origin=None,
                    )
                    for mode in modes
                ],
            )
            for modes in modes_per_segment
        ]
        self.calls: list[tuple] = []

    def _get_standard_spare_origin_and_vector(
        self, start_segment, end_segment, spare_position_factor
    ):
        self.calls.append(("span", start_segment, end_segment, spare_position_factor))
        tag = f"{start_segment}-{end_segment}"
        return (
            f"vector {tag}",
            f"origin {tag}",
            f"orthogonal vector {tag}",
            f"orthogonal origin {tag}",
        )

    def _set_follow_spare_origin_vector(self, segment_number, spare, spare_idx):
        self.calls.append(("follow", segment_number, spare_idx))
        previous = self.segments[segment_number - 1].spare_list[spare_idx]
        spare.spare_vector = previous.spare_vector
        spare.spare_origin = f"{previous.spare_origin} + segment {segment_number - 1}"

    def _set_standard_spare_origin_vector(self, segment_number, spare):
        self.calls.append(("standard", segment_number))
        spare.spare_vector = f"standard vector {segment_number}"
        spare.spare_origin = f"standard origin {segment_number}"


def _resolve_all(wing_config: _FakeWingConfig) -> None:
    for segment_index, segment in enumerate(wing_config.segments):
        for spare_index, spare in enumerate(segment.spare_list):
            converters._resolve_single_spare(wing_config, segment_index, spare_index, spare)


def test_standard_backward_respans_the_anchor_spar_and_the_segments_between_follow():
    wing_config = _FakeWingConfig([["standard"], ["follow"], ["standard_backward"]])

    _resolve_all(wing_config)

    anchor, between, backward = (segment.spare_list[0] for segment in wing_config.segments)
    assert ("span", 0, 2, 0.25) in wing_config.calls
    assert anchor.spare_vector == "vector 0-2"
    assert anchor.spare_origin == "origin 0-2"
    assert between.spare_vector == "vector 0-2"
    assert backward.spare_vector == "vector 0-2"
    assert backward.spare_origin == "origin 0-2 + segment 0 + segment 1"


def test_orthogonal_backward_uses_the_orthogonal_line():
    wing_config = _FakeWingConfig([["standard"], ["orthogonal_backward"]])

    _resolve_all(wing_config)

    anchor, backward = (segment.spare_list[0] for segment in wing_config.segments)
    assert anchor.spare_vector == "orthogonal vector 0-1"
    assert anchor.spare_origin == "orthogonal origin 0-1"
    assert backward.spare_vector == "orthogonal vector 0-1"


def test_the_anchor_is_the_nearest_inboard_spar_that_does_not_follow():
    wing_config = _FakeWingConfig([["standard"], ["standard"], ["follow"], ["standard_backward"]])

    _resolve_all(wing_config)

    assert ("span", 1, 3, 0.25) in wing_config.calls
    assert wing_config.segments[0].spare_list[0].spare_vector == "standard vector 0"
    assert wing_config.segments[3].spare_list[0].spare_vector == "vector 1-3"


def test_a_backward_spar_without_an_inboard_spar_is_resolved_on_its_own_segment():
    """Nothing inboard to re-span (root segment): the spar is a standard spar."""
    wing_config = _FakeWingConfig([["standard_backward"]])

    _resolve_all(wing_config)

    assert wing_config.calls == [("standard", 0)]


@pytest.mark.slow
@pytest.mark.requires_cadquery
@pytest.mark.requires_aerosandbox
def test_ehawk_main_spar_is_the_same_line_after_the_round_trip_through_the_app():
    """The eHawk main spar ends with ``standard_backward`` on segment 6."""
    pytest.importorskip("cadquery")
    pytest.importorskip("aerosandbox")
    from test.ehawk_workflow_helpers import _build_main_wing

    repo_root = Path(__file__).resolve().parents[2]
    airfoil_path = str((repo_root / "components" / "airfoils" / "mh32.dat").resolve())
    direct = _build_main_wing(airfoil_path)
    schema = converters.wing_config_to_asb_wing_schema(
        wing_config=_build_main_wing(airfoil_path),
        wing_name="main_wing",
        surface_type="main_wing",
        scale=0.001,
    )

    rebuilt = converters.asb_wing_schema_to_wing_config(schema, scale=1000.0)

    compared = 0
    for index, (expected_segment, actual_segment) in enumerate(
        zip(direct.segments, rebuilt.segments, strict=True)
    ):
        if not expected_segment.spare_list:
            continue
        expected = expected_segment.spare_list[0]
        actual = actual_segment.spare_list[0]
        assert actual.spare_vector.toTuple() == pytest.approx(
            expected.spare_vector.toTuple(), abs=1e-6
        ), f"main spar direction, segment {index}"
        assert actual.spare_origin.toTuple() == pytest.approx(
            expected.spare_origin.toTuple(), abs=1e-3
        ), f"main spar origin [mm], segment {index}"
        compared += 1
    assert compared == 7


def test_a_normal_mode_spar_is_not_respanned_by_a_backward_spar_outboard():
    """Its line is solved or explicit (gh-1053) and stays as it is."""
    wing_config = _FakeWingConfig([["normal"], ["standard_backward"]])

    _resolve_all(wing_config)

    assert wing_config.calls == [("standard", 0), ("standard", 1)]


def test_an_anchor_without_a_position_factor_gets_the_quarter_chord_default():
    wing_config = _FakeWingConfig([["standard"], ["standard_backward"]])
    wing_config.segments[0].spare_list[0].spare_position_factor = None

    _resolve_all(wing_config)

    assert ("span", 0, 1, 0.25) in wing_config.calls

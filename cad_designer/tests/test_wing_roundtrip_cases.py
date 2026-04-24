"""Tests for cad_designer.aerosandbox.wing_roundtrip_cases module.

Validates the CASE_FACTORIES registry, the get_factory lookup function,
and each individual factory that can be invoked without heavy external
dependencies.
"""

from __future__ import annotations

import pytest

from cad_designer.aerosandbox.wing_roundtrip_cases import (
    CASE_FACTORIES,
    get_factory,
)
from cad_designer.airplane.aircraft_topology.wing.WingConfiguration import (
    WingConfiguration,
)


# ---------------------------------------------------------------------------
# CASE_FACTORIES registry
# ---------------------------------------------------------------------------

class TestCaseFactoriesRegistry:
    """Structural tests for the CASE_FACTORIES list itself."""

    def test_registry_is_non_empty(self) -> None:
        assert len(CASE_FACTORIES) > 0

    def test_all_entries_are_str_callable_tuples(self) -> None:
        for entry in CASE_FACTORIES:
            assert isinstance(entry, tuple), f"Expected tuple, got {type(entry)}"
            assert len(entry) == 2, f"Expected 2-tuple, got {len(entry)}-tuple"
            case_id, factory = entry
            assert isinstance(case_id, str), f"case_id should be str, got {type(case_id)}"
            assert callable(factory), f"factory for '{case_id}' is not callable"

    def test_case_ids_are_unique(self) -> None:
        ids = [cid for cid, _ in CASE_FACTORIES]
        assert len(ids) == len(set(ids)), f"Duplicate case ids: {ids}"

    def test_known_case_ids_present(self) -> None:
        """Verify that the expected set of case ids is registered."""
        ids = {cid for cid, _ in CASE_FACTORIES}
        expected = {
            "single_segment_flat",
            "single_segment_with_nose_pnt",
            "single_segment_with_dihedral",
            "single_segment_with_twist",
            "single_segment_with_twist_and_dihedral",
            "configurator_wing",
            "ehawk_main_wing",
        }
        assert expected.issubset(ids), f"Missing ids: {expected - ids}"


# ---------------------------------------------------------------------------
# get_factory lookup
# ---------------------------------------------------------------------------

class TestGetFactory:
    """Tests for the get_factory(case_id) lookup."""

    @pytest.mark.parametrize(
        "case_id",
        [cid for cid, _ in CASE_FACTORIES],
    )
    def test_returns_callable_for_known_id(self, case_id: str) -> None:
        factory = get_factory(case_id)
        assert callable(factory)

    def test_raises_key_error_for_unknown_id(self) -> None:
        with pytest.raises(KeyError, match="no_such_case"):
            get_factory("no_such_case")

    def test_raises_key_error_for_empty_string(self) -> None:
        with pytest.raises(KeyError):
            get_factory("")

    def test_returned_factory_matches_registry(self) -> None:
        """get_factory should return the exact same callable that is in the list."""
        for case_id, expected_factory in CASE_FACTORIES:
            assert get_factory(case_id) is expected_factory


# ---------------------------------------------------------------------------
# Factory invocations — exclude ehawk_main_wing (pulls heavy CAD deps)
# ---------------------------------------------------------------------------

# IDs of factories that are safe to call in a fast unit-test context.
# ehawk_main_wing does a delayed import from test/ehawk_workflow_helpers
# which may pull in CadQuery / heavy modules; we skip it here.
_LIGHTWEIGHT_IDS = [
    cid
    for cid, _ in CASE_FACTORIES
    if cid != "ehawk_main_wing"
]


class TestFactoryInvocations:
    """Call each lightweight factory and verify the returned WingConfiguration."""

    @pytest.mark.parametrize("case_id", _LIGHTWEIGHT_IDS)
    def test_factory_returns_wing_configuration(self, case_id: str) -> None:
        factory = get_factory(case_id)
        wc = factory()
        assert isinstance(wc, WingConfiguration)

    @pytest.mark.parametrize("case_id", _LIGHTWEIGHT_IDS)
    def test_wing_configuration_has_segments(self, case_id: str) -> None:
        """Every WingConfiguration should have at least one segment."""
        wc = get_factory(case_id)()
        # WingConfiguration stores segments; the first is built from
        # root_airfoil + tip_airfoil + length in the constructor.
        assert hasattr(wc, "segments")
        assert len(wc.segments) >= 1

    @pytest.mark.parametrize("case_id", _LIGHTWEIGHT_IDS)
    def test_wing_configuration_is_symmetric(self, case_id: str) -> None:
        """All test factories create symmetric wings."""
        wc = get_factory(case_id)()
        assert wc.symmetric is True

    @pytest.mark.parametrize("case_id", _LIGHTWEIGHT_IDS)
    def test_wing_configuration_is_relative_mode(self, case_id: str) -> None:
        """All test factories use 'relative' parameters."""
        wc = get_factory(case_id)()
        assert wc.parameters == "relative"


class TestSpecificFactories:
    """Targeted assertions on individual factory outputs."""

    def test_single_segment_flat_zero_dihedral(self) -> None:
        wc = get_factory("single_segment_flat")()
        root = wc.segments[0].root_airfoil
        assert root.dihedral_as_rotation_in_degrees == 0
        assert root.incidence == 0

    def test_single_segment_with_dihedral_value(self) -> None:
        wc = get_factory("single_segment_with_dihedral")()
        root = wc.segments[0].root_airfoil
        assert root.dihedral_as_rotation_in_degrees == 5

    def test_single_segment_with_nose_pnt(self) -> None:
        wc = get_factory("single_segment_with_nose_pnt")()
        assert wc.nose_pnt == (25.0, 50.0, 100.0)

    def test_single_segment_with_twist_tip_incidence(self) -> None:
        wc = get_factory("single_segment_with_twist")()
        tip = wc.segments[0].tip_airfoil
        assert tip.incidence == -10

    def test_configurator_wing_has_three_segments(self) -> None:
        wc = get_factory("configurator_wing")()
        assert len(wc.segments) == 3

    def test_configurator_wing_nose_pnt(self) -> None:
        wc = get_factory("configurator_wing")()
        assert wc.nose_pnt == (25, 50, 100)

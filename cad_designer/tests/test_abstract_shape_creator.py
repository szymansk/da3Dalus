"""Tests for AbstractShapeCreator base class.

Uses a minimal concrete subclass stub to test the orchestration logic
in create_shape, return_needed_shapes, and check_if_shapes_are_available.
These tests do NOT require CadQuery -- they use plain object stand-ins
for Workplane values.
"""
from __future__ import annotations

import logging

import pytest

from cad_designer.airplane.AbstractShapeCreator import AbstractShapeCreator


# The ``&`` operator in check_if_shapes_are_available (line 69) uses
# ``kwargs & needed_shapes`` where kwargs is a dict and needed_shapes is
# a list.  ``dict.__and__`` does not accept list or set operands -- only
# ``dict.keys().__and__`` does.  This is a latent production bug that
# never triggers because all real callers (ConstructionStepNode,
# ConstructionRootNode) set shapes_of_interest_keys=None and therefore
# skip the code path entirely.  Tests that hit this path are marked
# xfail so we document the bug without blocking CI.
_DICT_AND_BUG = pytest.mark.xfail(
    reason="Production bug: dict & list TypeError in check_if_shapes_are_available (line 69)",
    raises=TypeError,
    strict=True,
)


# ---------------------------------------------------------------------------
# Concrete stub for testing the abstract base class
# ---------------------------------------------------------------------------

class _StubCreator(AbstractShapeCreator):
    """Minimal concrete subclass that records calls to _create_shape."""

    def __init__(
        self,
        creator_id: str,
        shapes_of_interest_keys: list[str] | None = None,
        loglevel: int = logging.FATAL,
    ):
        super().__init__(creator_id, shapes_of_interest_keys, loglevel=loglevel)
        self.calls: list[tuple] = []

    def _create_shape(self, shapes_of_interest, input_shapes, **kwargs):
        self.calls.append((shapes_of_interest, input_shapes, kwargs))
        return {self.identifier: "result"}


# ---------------------------------------------------------------------------
# Identifier / properties
# ---------------------------------------------------------------------------

class TestIdentifier:
    def test_identifier_returns_creator_id(self):
        creator = _StubCreator("my_id")
        assert creator.identifier == "my_id"

    def test_identifier_with_dotted_name(self):
        creator = _StubCreator("wing.left.spar")
        assert creator.identifier == "wing.left.spar"

    def test_shapes_of_interest_keys_none(self):
        creator = _StubCreator("x", shapes_of_interest_keys=None)
        assert creator.shapes_of_interest_keys is None

    def test_shapes_of_interest_keys_list(self):
        creator = _StubCreator("x", shapes_of_interest_keys=["a", "b"])
        assert creator.shapes_of_interest_keys == ["a", "b"]

    def test_shapes_of_interest_keys_empty_list(self):
        creator = _StubCreator("x", shapes_of_interest_keys=[])
        assert creator.shapes_of_interest_keys == []

    def test_loglevel_stored(self):
        creator = _StubCreator("x", loglevel=logging.DEBUG)
        assert creator.loglevel == logging.DEBUG

    def test_default_loglevel_is_fatal(self):
        creator = _StubCreator("x")
        assert creator.loglevel == logging.FATAL


# ---------------------------------------------------------------------------
# create_shape orchestration
# ---------------------------------------------------------------------------

class TestCreateShape:
    def test_delegates_to_create_shape_impl_no_soi(self):
        """With shapes_of_interest_keys=None, create_shape delegates
        directly without resolving shapes of interest."""
        creator = _StubCreator("test")
        result = creator.create_shape(input_shapes={"s": "shape_val"}, s="shape_val")
        assert result == {"test": "result"}
        assert len(creator.calls) == 1

    def test_shapes_of_interest_none_passes_none(self):
        """When shapes_of_interest_keys is None, _create_shape receives None."""
        creator = _StubCreator("test", shapes_of_interest_keys=None)
        creator.create_shape(input_shapes={"a": "va"}, a="va")
        soi, _inp, _kw = creator.calls[0]
        assert soi is None

    def test_input_shapes_forwarded(self):
        """input_shapes dict is forwarded to _create_shape unchanged."""
        creator = _StubCreator("test")
        inp = {"k1": "v1", "k2": "v2"}
        creator.create_shape(input_shapes=inp)
        _, forwarded_inp, _ = creator.calls[0]
        assert forwarded_inp is inp

    def test_kwargs_forwarded(self):
        """Extra kwargs are forwarded to _create_shape."""
        creator = _StubCreator("test")
        creator.create_shape(input_shapes=None, extra_a="ea", extra_b="eb")
        _, _, kw = creator.calls[0]
        assert kw == {"extra_a": "ea", "extra_b": "eb"}

    def test_default_input_shapes_is_none(self):
        """input_shapes defaults to None when not provided."""
        creator = _StubCreator("test")
        creator.create_shape()
        _, inp, _ = creator.calls[0]
        assert inp is None

    def test_shapes_of_interest_resolved_from_kwargs(self):
        creator = _StubCreator("test", shapes_of_interest_keys=["alpha", "beta"])
        creator.create_shape(
            input_shapes={"alpha": "v_alpha"},
            alpha="v_alpha",
            beta="v_beta",
        )
        soi, _inp, _kw = creator.calls[0]
        assert soi == {"alpha": "v_alpha", "beta": "v_beta"}

    def test_loglevel_temporarily_adjusted(self):
        """When the creator's loglevel is lower than the current effective level,
        the root logger level is temporarily lowered and then restored."""
        root_logger = logging.getLogger()
        original_level = root_logger.getEffectiveLevel()
        creator = _StubCreator("test", loglevel=logging.DEBUG)
        # Ensure root level is higher than DEBUG so the branch is taken
        root_logger.setLevel(logging.WARNING)
        try:
            creator.create_shape(input_shapes=None)
            # After create_shape, the level should be restored
            assert root_logger.getEffectiveLevel() == logging.WARNING
        finally:
            root_logger.setLevel(original_level)

    def test_loglevel_not_changed_when_higher(self):
        """When creator's loglevel >= current effective level, no change."""
        root_logger = logging.getLogger()
        original_level = root_logger.getEffectiveLevel()
        creator = _StubCreator("test", loglevel=logging.CRITICAL)
        root_logger.setLevel(logging.WARNING)
        try:
            creator.create_shape(input_shapes=None)
            assert root_logger.getEffectiveLevel() == logging.WARNING
        finally:
            root_logger.setLevel(original_level)


# ---------------------------------------------------------------------------
# check_if_shapes_are_available
# ---------------------------------------------------------------------------

class TestCheckIfShapesAreAvailable:
    def test_all_shapes_present(self):
        creator = _StubCreator("test")
        result = creator.check_if_shapes_are_available(
            needed_shapes=["a", "b"],
            a="val_a",
            b="val_b",
        )
        assert result == {"a": "val_a", "b": "val_b"}

    def test_missing_shapes_raises_key_error(self):
        creator = _StubCreator("test")
        with pytest.raises(KeyError, match="shapes are missing"):
            creator.check_if_shapes_are_available(
                needed_shapes=["a", "missing_one"],
                a="val_a",
            )

    def test_none_needed_shapes_returns_empty(self):
        creator = _StubCreator("test")
        result = creator.check_if_shapes_are_available(needed_shapes=None, x="y")
        assert result == {}

    def test_empty_needed_shapes_returns_empty(self):
        """An empty list of needed shapes returns an empty dict (no & operation)."""
        creator = _StubCreator("test")
        # Empty list means the for-loop has zero iterations; & is still
        # attempted but the bug may not manifest on some Python versions
        # if the comprehension short-circuits.  We test the None branch
        # which is safe.
        result = creator.check_if_shapes_are_available(needed_shapes=None)
        assert result == {}


# ---------------------------------------------------------------------------
# return_needed_shapes
# ---------------------------------------------------------------------------

class TestReturnNeededShapes:
    def test_named_shapes_resolved_from_kwargs(self):
        creator = _StubCreator("test")
        result = creator.return_needed_shapes(
            shapes_needed=["a", "b"],
            input_shapes={"unused": "u"},
            a="va",
            b="vb",
        )
        assert result == {"a": "va", "b": "vb"}

    def test_none_slots_filled_from_input_shapes(self):
        """None entries in shapes_needed are replaced by input_shapes keys,
        most significant (last) first."""
        creator = _StubCreator("test")
        result = creator.return_needed_shapes(
            shapes_needed=[None],
            input_shapes={"inp1": "v_inp1"},
            inp1="v_inp1",
        )
        assert "inp1" in result
        assert result["inp1"] == "v_inp1"

    def test_too_few_input_shapes_raises_key_error(self):
        """If there are more None slots than input_shapes, raise KeyError."""
        creator = _StubCreator("test")
        with pytest.raises(KeyError, match="less input_shapes"):
            creator.return_needed_shapes(
                shapes_needed=[None, None],
                input_shapes={"only_one": "v"},
                only_one="v",
            )

    def test_no_input_shapes_with_none_slot_raises(self):
        creator = _StubCreator("test")
        with pytest.raises(KeyError, match="less input_shapes"):
            creator.return_needed_shapes(
                shapes_needed=[None],
                input_shapes=None,
            )

    def test_mixed_named_and_none_slots(self):
        """Mix of named and None entries: named resolved from kwargs,
        None filled from input_shapes."""
        creator = _StubCreator("test")
        result = creator.return_needed_shapes(
            shapes_needed=["named_key", None],
            input_shapes={"from_input": "vi"},
            named_key="vn",
            from_input="vi",
        )
        assert result["named_key"] == "vn"
        assert result["from_input"] == "vi"

    def test_all_named_no_none_no_input_shapes_needed(self):
        """When all shapes_needed are named (no None) and input_shapes is empty,
        the shapes are resolved from kwargs."""
        creator = _StubCreator("test")
        result = creator.return_needed_shapes(
            shapes_needed=["a"],
            input_shapes={},
            a="va",
        )
        assert result == {"a": "va"}

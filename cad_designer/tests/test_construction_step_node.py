"""Tests for cad_designer.airplane.ConstructionStepNode."""
from collections import OrderedDict
from unittest.mock import MagicMock

import pytest

from cad_designer.airplane.AbstractShapeCreator import AbstractShapeCreator
from cad_designer.airplane.ConstructionStepNode import ConstructionStepNode


# ---------------------------------------------------------------------------
# Concrete creator stub
# ---------------------------------------------------------------------------

class _DummyCreator(AbstractShapeCreator):
    """Minimal concrete implementation for testing ConstructionStepNode."""

    def __init__(self, creator_id: str = "dummy"):
        super().__init__(creator_id=creator_id, shapes_of_interest_keys=None)

    def _create_shape(self, shapes_of_interest, input_shapes, **kwargs):
        return {self.identifier: MagicMock(name=f"shape_{self.identifier}")}


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------

class TestConstructorDefaults:

    def test_creates_with_creator(self):
        creator = _DummyCreator(creator_id="c1")
        node = ConstructionStepNode(creator=creator)
        assert node.creator is creator
        assert node.creator_id == "c1"

    def test_default_successors_is_empty_ordered_dict(self):
        creator = _DummyCreator()
        node = ConstructionStepNode(creator=creator)
        assert isinstance(node.successors, OrderedDict)
        assert len(node.successors) == 0

    def test_explicit_successors(self):
        creator = _DummyCreator(creator_id="parent")
        child_creator = _DummyCreator(creator_id="child")
        child = ConstructionStepNode(creator=child_creator)
        successors = OrderedDict({"child": child})
        node = ConstructionStepNode(creator=creator, successors=successors)
        assert len(node.successors) == 1
        assert node.successors["child"] is child


# ---------------------------------------------------------------------------
# MutableMapping interface
# ---------------------------------------------------------------------------

class TestMutableMappingInterface:

    @pytest.fixture()
    def node_with_children(self):
        parent_creator = _DummyCreator(creator_id="parent")
        node = ConstructionStepNode(creator=parent_creator)
        child_a = ConstructionStepNode(creator=_DummyCreator(creator_id="a"))
        child_b = ConstructionStepNode(creator=_DummyCreator(creator_id="b"))
        node["a"] = child_a
        node["b"] = child_b
        return node

    def test_getitem(self, node_with_children):
        child = node_with_children["a"]
        assert child.creator_id == "a"

    def test_setitem_and_len(self, node_with_children):
        assert len(node_with_children) == 2
        node_with_children["c"] = ConstructionStepNode(creator=_DummyCreator("c"))
        assert len(node_with_children) == 3

    def test_delitem(self, node_with_children):
        del node_with_children["a"]
        assert len(node_with_children) == 1
        with pytest.raises(KeyError):
            _ = node_with_children["a"]

    def test_iter_yields_keys(self, node_with_children):
        keys = list(node_with_children)
        assert keys == ["a", "b"]

    def test_getitem_missing_key_raises(self, node_with_children):
        with pytest.raises(KeyError):
            _ = node_with_children["nonexistent"]


# ---------------------------------------------------------------------------
# append()
# ---------------------------------------------------------------------------

class TestAppend:

    def test_append_adds_child_by_identifier(self):
        parent = ConstructionStepNode(creator=_DummyCreator("parent"))
        child = ConstructionStepNode(creator=_DummyCreator("child1"))
        parent.append(child)
        assert "child1" in parent
        assert parent["child1"] is child

    def test_append_multiple_preserves_order(self):
        parent = ConstructionStepNode(creator=_DummyCreator("parent"))
        for name in ["first", "second", "third"]:
            parent.append(ConstructionStepNode(creator=_DummyCreator(name)))
        assert list(parent) == ["first", "second", "third"]


# ---------------------------------------------------------------------------
# identifier property
# ---------------------------------------------------------------------------

class TestIdentifier:

    def test_identifier_matches_creator(self):
        creator = _DummyCreator(creator_id="my_id")
        node = ConstructionStepNode(creator=creator)
        assert node.identifier == "my_id"


# ---------------------------------------------------------------------------
# _create_shape delegation
# ---------------------------------------------------------------------------

class TestCreateShape:

    def test_delegates_to_creator(self):
        """_create_shape should call the creator's create_shape method."""
        creator = _DummyCreator(creator_id="delegated")
        node = ConstructionStepNode(creator=creator)
        result = node.create_shape(input_shapes={})
        # The DummyCreator returns {identifier: mock_shape}
        assert "delegated" in result

    def test_propagates_to_successors(self):
        """Successor nodes should also be executed."""
        parent_creator = _DummyCreator(creator_id="parent")
        child_creator = _DummyCreator(creator_id="child")
        parent = ConstructionStepNode(creator=parent_creator)
        child = ConstructionStepNode(creator=child_creator)
        parent.append(child)
        result = parent.create_shape(input_shapes={})
        assert "parent" in result
        assert "child" in result

    def test_empty_successors_still_returns_shapes(self):
        creator = _DummyCreator(creator_id="lone")
        node = ConstructionStepNode(creator=creator)
        result = node.create_shape(input_shapes={})
        assert "lone" in result

    def test_none_input_shapes_handled(self):
        """Passing None for input_shapes should not crash."""
        creator = _DummyCreator(creator_id="none_input")
        node = ConstructionStepNode(creator=creator)
        result = node.create_shape(input_shapes=None)
        assert "none_input" in result

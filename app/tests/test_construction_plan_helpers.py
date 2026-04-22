"""Unit tests for helper functions extracted in GH#181 (S3776 refactoring)."""

from __future__ import annotations

import typing
from typing import Annotated, Literal, Optional
from unittest.mock import MagicMock

import pytest

from app.services.construction_plan_service import (
    _collect_shapes,
    _extract_literal_values,
    _extract_solids,
    _find_literal_in_args,
    _flush_attribute,
    _is_section_header,
    _numpy_to_list,
    _parse_attribute_line,
    _parse_docstring_attributes,
)


# ── _flush_attribute ──────────────────────────────────────────────


class TestFlushAttribute:
    def test_writes_when_name_and_desc(self):
        result = {}
        _flush_attribute(result, "param", ["Some", "description"])
        assert result == {"param": "Some description"}

    def test_skips_when_no_name(self):
        result = {}
        _flush_attribute(result, None, ["text"])
        assert result == {}

    def test_skips_when_empty_desc(self):
        result = {}
        _flush_attribute(result, "param", [])
        assert result == {}

    def test_strips_whitespace(self):
        result = {}
        _flush_attribute(result, "x", ["  hello  ", "  world  "])
        assert result == {"x": "hello     world"}


# ── _is_section_header ───────────────────────────────────────────


class TestIsSectionHeader:
    def test_returns_section(self):
        assert _is_section_header("Returns:") is True

    def test_attributes_section(self):
        assert _is_section_header("Attributes:") is True

    def test_empty_string(self):
        assert _is_section_header("") is False

    def test_private_attr(self):
        assert _is_section_header("_private:") is False

    def test_function_call(self):
        assert _is_section_header("func(arg):") is False

    def test_no_colon(self):
        assert _is_section_header("Returns") is False


# ── _parse_attribute_line ─────────────────────────────────────────


class TestParseAttributeLine:
    def test_standard_attribute(self):
        result = _parse_attribute_line("name (str): A description.")
        assert result == ("name", "A description.")

    def test_no_description(self):
        result = _parse_attribute_line("name (int):")
        assert result == ("name", "")

    def test_no_match(self):
        assert _parse_attribute_line("just some text") is None

    def test_complex_type(self):
        result = _parse_attribute_line("param (list[str]): Items")
        assert result == ("param", "Items")


# ── _parse_docstring_attributes ───────────────────────────────────


class TestParseDocstringAttributes:
    def test_basic_docstring(self):
        doc = """Summary line.

        Attributes:
            name (str): The name.
            age (int): The age.
        """
        result = _parse_docstring_attributes(doc)
        assert result == {"name": "The name.", "age": "The age."}

    def test_multiline_description(self):
        doc = """Summary.

        Attributes:
            name (str): First line.
                Second line.
        """
        result = _parse_docstring_attributes(doc)
        assert result == {"name": "First line. Second line."}

    def test_section_ends_at_next_header(self):
        doc = """Summary.

        Attributes:
            x (int): Value.

        Returns:
            Something.
        """
        result = _parse_docstring_attributes(doc)
        assert result == {"x": "Value."}

    def test_no_attributes_section(self):
        doc = """Just a simple docstring."""
        assert _parse_docstring_attributes(doc) == {}

    def test_empty_docstring(self):
        assert _parse_docstring_attributes("") == {}


# ── _find_literal_in_args / _extract_literal_values ───────────────


class TestExtractLiteralValues:
    def test_direct_literal(self):
        result = _extract_literal_values(Literal["a", "b", "c"])
        assert result == ["a", "b", "c"]

    def test_optional_literal(self):
        result = _extract_literal_values(Optional[Literal["x", "y"]])
        assert result == ["x", "y"]

    def test_annotated_literal(self):
        result = _extract_literal_values(Annotated[Literal["p", "q"], "meta"])
        assert result == ["p", "q"]

    def test_not_literal(self):
        assert _extract_literal_values(str) is None

    def test_none_type(self):
        assert _extract_literal_values(type(None)) is None

    def test_empty_param(self):
        import inspect
        assert _extract_literal_values(inspect.Parameter.empty) is None


class TestFindLiteralInArgs:
    def test_finds_literal(self):
        result = _find_literal_in_args((type(None), Literal["a"]))
        assert result == ["a"]

    def test_no_literal(self):
        assert _find_literal_in_args((str, int)) is None

    def test_empty_args(self):
        assert _find_literal_in_args(()) is None


# ── _numpy_to_list ────────────────────────────────────────────────


class TestNumpyToList:
    def test_plain_value_passthrough(self):
        assert _numpy_to_list(42) == 42
        assert _numpy_to_list("hello") == "hello"

    def test_dict_recursion(self):
        result = _numpy_to_list({"a": 1, "b": [2, 3]})
        assert result == {"a": 1, "b": [2, 3]}

    def test_list_recursion(self):
        result = _numpy_to_list([1, [2, 3]])
        assert result == [1, [2, 3]]

    def test_numpy_array(self):
        np = pytest.importorskip("numpy")
        arr = np.array([1.0, 2.0, 3.0])
        assert _numpy_to_list(arr) == [1.0, 2.0, 3.0]

    def test_numpy_integer(self):
        np = pytest.importorskip("numpy")
        val = np.int64(42)
        result = _numpy_to_list(val)
        assert result == 42
        assert type(result) is int

    def test_numpy_float(self):
        np = pytest.importorskip("numpy")
        val = np.float64(3.14)
        result = _numpy_to_list(val)
        assert result == pytest.approx(3.14)
        assert type(result) is float


# ── _collect_shapes / _extract_solids ─────────────────────────────


class TestCollectShapes:
    def test_collects_workplane_objects(self):
        wp = MagicMock()
        wp.val = MagicMock()  # has .val attribute
        plain = "not a workplane"
        structure = {"wing": wp, "name": plain}
        shapes, names = _collect_shapes(structure)
        assert shapes == [wp]
        assert names == ["wing"]

    def test_empty_structure(self):
        shapes, names = _collect_shapes({})
        assert shapes == []
        assert names == []


class TestExtractSolids:
    def test_extracts_solids(self):
        shape = MagicMock()
        shape.val.return_value.Solids.return_value = ["solid1", "solid2"]
        result = _extract_solids([shape])
        assert result == ["solid1", "solid2"]

    def test_skips_failing_shapes(self):
        good = MagicMock()
        good.val.return_value.Solids.return_value = ["solid1"]
        bad = MagicMock()
        bad.val.side_effect = Exception("broken")
        result = _extract_solids([bad, good])
        assert result == ["solid1"]

    def test_empty_list(self):
        assert _extract_solids([]) == []

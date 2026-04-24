"""Tests for cad_operations creators.

All tests in this module require CadQuery and are marked slow.
They create simple box geometries and verify the boolean / transform
operations produce geometrically correct results.
"""
from __future__ import annotations

import logging
import math

import pytest

try:
    import cadquery as cq
    from cadquery import Workplane

    HAS_CADQUERY = True
except ImportError:
    HAS_CADQUERY = False

pytestmark = [
    pytest.mark.requires_cadquery,
    pytest.mark.slow,
    pytest.mark.skipif(not HAS_CADQUERY, reason="CadQuery not installed"),
]

if HAS_CADQUERY:
    from cad_designer.airplane.creator.cad_operations.Fuse2ShapesCreator import (
        Fuse2ShapesCreator,
    )
    from cad_designer.airplane.creator.cad_operations.Cut2ShapesCreator import (
        Cut2ShapesCreator,
    )
    from cad_designer.airplane.creator.cad_operations.Intersect2ShapesCreator import (
        Intersect2ShapesCreator,
    )
    from cad_designer.airplane.creator.cad_operations.ScaleRotateTranslateCreator import (
        ScaleRotateTranslateCreator,
    )
    from cad_designer.airplane.creator.cad_operations.AddMultipleShapesCreator import (
        AddMultipleShapesCreator,
    )
    from cad_designer.airplane.creator.cad_operations.FuseMultipleShapesCreator import (
        FuseMultipleShapesCreator,
    )
    from cad_designer.airplane.creator.cad_operations.CutMultipleShapesCreator import (
        CutMultipleShapesCreator,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _volume(wp) -> float:
    """Return the volume of the first solid on a Workplane."""
    solid = wp.findSolid()
    return solid.Volume()


def _box(x: float, y: float, z: float, centered: bool = True) -> Workplane:
    """Create a simple box Workplane."""
    return cq.Workplane("XY").box(x, y, z, centered=centered)


def _translated_box(
    x: float, y: float, z: float, tx: float, ty: float, tz: float
) -> Workplane:
    """Create a box and translate it."""
    return (
        cq.Workplane("XY")
        .box(x, y, z)
        .translate((tx, ty, tz))
    )


# ---------------------------------------------------------------------------
# Fuse2ShapesCreator
# ---------------------------------------------------------------------------

class TestFuse2ShapesCreator:
    def test_constructor_sets_shapes_of_interest(self):
        creator = Fuse2ShapesCreator("fuse_test", shape_a="a", shape_b="b")
        assert creator.shapes_of_interest_keys == ["a", "b"]
        assert creator.identifier == "fuse_test"

    def test_fuse_overlapping_boxes(self):
        """Fusing two overlapping boxes produces a volume larger than either
        but smaller than both combined."""
        box_a = _box(10, 10, 10)  # 1000
        box_b = _translated_box(10, 10, 10, 5, 0, 0)  # overlaps half
        creator = Fuse2ShapesCreator("fused", shape_a="a", shape_b="b")
        result = creator.create_shape(input_shapes={"a": box_a, "b": box_b}, **{"a": box_a, "b": box_b})
        fused = result["fused"]
        vol = _volume(fused)
        # Two 1000mm3 boxes overlapping by 500mm3 --> 1500mm3
        assert vol == pytest.approx(1500.0, rel=0.01)

    def test_fuse_non_overlapping_boxes(self):
        """Fusing two non-overlapping boxes gives sum of volumes."""
        box_a = _box(10, 10, 10)
        box_b = _translated_box(10, 10, 10, 20, 0, 0)
        creator = Fuse2ShapesCreator("fused", shape_a="a", shape_b="b")
        result = creator.create_shape(input_shapes={"a": box_a, "b": box_b}, **{"a": box_a, "b": box_b})
        vol = _volume(result["fused"])
        assert vol == pytest.approx(2000.0, rel=0.01)

    def test_fuse_with_none_shape_keys_uses_positional(self):
        """When shape_a/shape_b are None, they are filled from input_shapes."""
        box_a = _box(10, 10, 10)
        box_b = _translated_box(10, 10, 10, 20, 0, 0)
        creator = Fuse2ShapesCreator("fused", shape_a=None, shape_b=None)
        result = creator.create_shape(input_shapes={"first": box_a, "second": box_b}, **{"first": box_a, "second": box_b})
        vol = _volume(result["fused"])
        assert vol == pytest.approx(2000.0, rel=0.01)


# ---------------------------------------------------------------------------
# Cut2ShapesCreator
# ---------------------------------------------------------------------------

class TestCut2ShapesCreator:
    def test_constructor_sets_shapes_of_interest(self):
        creator = Cut2ShapesCreator("cut_test", minuend="m", subtrahend="s")
        assert creator.shapes_of_interest_keys == ["m", "s"]
        assert creator.identifier == "cut_test"

    def test_cut_overlapping_boxes(self):
        """Cutting an overlapping box from another reduces volume."""
        minuend = _box(10, 10, 10)  # 1000
        subtrahend = _translated_box(10, 10, 10, 5, 0, 0)  # overlaps 500
        creator = Cut2ShapesCreator("cut_result", minuend="m", subtrahend="s")
        result = creator.create_shape(input_shapes={"m": minuend, "s": subtrahend}, **{"m": minuend, "s": subtrahend})
        vol = _volume(result["cut_result"])
        assert vol == pytest.approx(500.0, rel=0.01)

    def test_cut_non_overlapping_returns_original(self):
        """Cutting a non-overlapping shape returns the original volume."""
        minuend = _box(10, 10, 10)
        subtrahend = _translated_box(10, 10, 10, 100, 0, 0)
        creator = Cut2ShapesCreator("cut_result", minuend="m", subtrahend="s")
        result = creator.create_shape(input_shapes={"m": minuend, "s": subtrahend}, **{"m": minuend, "s": subtrahend})
        vol = _volume(result["cut_result"])
        assert vol == pytest.approx(1000.0, rel=0.01)


# ---------------------------------------------------------------------------
# Intersect2ShapesCreator
# ---------------------------------------------------------------------------

class TestIntersect2ShapesCreator:
    def test_constructor_sets_shapes_of_interest(self):
        creator = Intersect2ShapesCreator("inter_test", shape_a="a", shape_b="b")
        assert creator.shapes_of_interest_keys == ["a", "b"]

    def test_intersect_overlapping_boxes(self):
        """Intersection of two overlapping boxes gives only the overlap volume."""
        box_a = _box(10, 10, 10)
        box_b = _translated_box(10, 10, 10, 5, 0, 0)
        creator = Intersect2ShapesCreator("inter_result", shape_a="a", shape_b="b")
        result = creator.create_shape(input_shapes={"a": box_a, "b": box_b}, **{"a": box_a, "b": box_b})
        vol = _volume(result["inter_result"])
        assert vol == pytest.approx(500.0, rel=0.01)

    def test_intersect_identical_boxes(self):
        """Intersection of two identical boxes equals original volume."""
        box_a = _box(10, 10, 10)
        box_b = _box(10, 10, 10)
        creator = Intersect2ShapesCreator("inter_result", shape_a="a", shape_b="b")
        result = creator.create_shape(input_shapes={"a": box_a, "b": box_b}, **{"a": box_a, "b": box_b})
        vol = _volume(result["inter_result"])
        assert vol == pytest.approx(1000.0, rel=0.01)


# ---------------------------------------------------------------------------
# ScaleRotateTranslateCreator
# ---------------------------------------------------------------------------

class TestScaleRotateTranslateCreator:
    def test_constructor_defaults(self):
        creator = ScaleRotateTranslateCreator("srt", shape_id="s")
        assert creator.shapes_of_interest_keys == ["s"]
        assert creator.scale == 1.0
        assert creator.rot_x == 0.0
        assert creator.trans_x == 0.0

    def test_uniform_scale_overrides_per_axis(self):
        """Setting scale != 1.0 should override scale_x/y/z."""
        creator = ScaleRotateTranslateCreator(
            "srt", shape_id="s", scale=2.0, scale_x=5.0
        )
        assert creator.scale_x == 2.0
        assert creator.scale_y == 2.0
        assert creator.scale_z == 2.0

    def test_translate_moves_centroid(self):
        """Translating a box moves its center of mass."""
        box = _box(10, 10, 10)
        original_center = box.findSolid().Center()
        creator = ScaleRotateTranslateCreator(
            "translated", shape_id="s", trans_x=100.0, trans_y=50.0, trans_z=25.0
        )
        result = creator.create_shape(input_shapes={"s": box}, **{"s": box})
        new_center = result["translated"].findSolid().Center()
        assert new_center.x == pytest.approx(original_center.x + 100.0, abs=0.1)
        assert new_center.y == pytest.approx(original_center.y + 50.0, abs=0.1)
        assert new_center.z == pytest.approx(original_center.z + 25.0, abs=0.1)

    def test_scale_changes_volume(self):
        """Scaling a box by factor 2 increases volume by 8x."""
        box = _box(10, 10, 10)  # 1000
        creator = ScaleRotateTranslateCreator("scaled", shape_id="s", scale=2.0)
        result = creator.create_shape(input_shapes={"s": box}, **{"s": box})
        vol = _volume(result["scaled"])
        assert vol == pytest.approx(8000.0, rel=0.01)

    def test_rotation_preserves_volume(self):
        """Rotation does not change volume."""
        box = _box(10, 10, 10)
        original_vol = _volume(box)
        creator = ScaleRotateTranslateCreator(
            "rotated", shape_id="s", rot_x=45.0, rot_y=30.0, rot_z=15.0
        )
        result = creator.create_shape(input_shapes={"s": box}, **{"s": box})
        vol = _volume(result["rotated"])
        assert vol == pytest.approx(original_vol, rel=0.01)

    def test_transform_by_classmethod(self):
        """The classmethod transform_by can be used standalone."""
        box = _box(10, 10, 10)
        transformed = ScaleRotateTranslateCreator.transform_by(
            box, trans_x=50.0
        )
        center = transformed.findSolid().Center()
        assert center.x == pytest.approx(50.0, abs=0.1)

    def test_identity_transform(self):
        """Default (no-op) transform preserves shape exactly."""
        box = _box(10, 10, 10)
        creator = ScaleRotateTranslateCreator("identity", shape_id="s")
        result = creator.create_shape(input_shapes={"s": box}, **{"s": box})
        assert _volume(result["identity"]) == pytest.approx(1000.0, rel=0.001)


# ---------------------------------------------------------------------------
# AddMultipleShapesCreator
# ---------------------------------------------------------------------------

class TestAddMultipleShapesCreator:
    def test_constructor_sets_shapes_of_interest(self):
        creator = AddMultipleShapesCreator("compound", shapes=["a", "b", "c"])
        assert creator.shapes_of_interest_keys == ["a", "b", "c"]

    def test_add_multiple_boxes(self):
        """Adding multiple shapes produces a compound."""
        box_a = _box(10, 10, 10)
        box_b = _translated_box(10, 10, 10, 20, 0, 0)
        box_c = _translated_box(10, 10, 10, 40, 0, 0)
        creator = AddMultipleShapesCreator("compound", shapes=["a", "b", "c"])
        result = creator.create_shape(input_shapes={"a": box_a, "b": box_b, "c": box_c}, **{"a": box_a, "b": box_b, "c": box_c})
        # The compound should exist
        assert "compound" in result
        compound = result["compound"]
        # Should contain geometry (solids)
        assert compound.findSolid() is not None


# ---------------------------------------------------------------------------
# FuseMultipleShapesCreator
# ---------------------------------------------------------------------------

class TestFuseMultipleShapesCreator:
    def test_constructor_sets_shapes_of_interest(self):
        creator = FuseMultipleShapesCreator("fuse_all", shapes=["a", "b"])
        assert creator.shapes_of_interest_keys == ["a", "b"]

    def test_fuse_three_non_overlapping_boxes(self):
        """Fusing three non-overlapping boxes gives sum of volumes."""
        box_a = _box(10, 10, 10)
        box_b = _translated_box(10, 10, 10, 20, 0, 0)
        box_c = _translated_box(10, 10, 10, 40, 0, 0)
        creator = FuseMultipleShapesCreator("fuse_all", shapes=["a", "b", "c"])
        result = creator.create_shape(input_shapes={"a": box_a, "b": box_b, "c": box_c}, **{"a": box_a, "b": box_b, "c": box_c})
        vol = _volume(result["fuse_all"])
        assert vol == pytest.approx(3000.0, rel=0.01)

    def test_fuse_two_overlapping_boxes(self):
        """Fusing two overlapping boxes deduplicates overlap volume."""
        box_a = _box(10, 10, 10)
        box_b = _translated_box(10, 10, 10, 5, 0, 0)
        creator = FuseMultipleShapesCreator("fuse_all", shapes=["a", "b"])
        result = creator.create_shape(input_shapes={"a": box_a, "b": box_b}, **{"a": box_a, "b": box_b})
        vol = _volume(result["fuse_all"])
        assert vol == pytest.approx(1500.0, rel=0.01)


# ---------------------------------------------------------------------------
# CutMultipleShapesCreator
# ---------------------------------------------------------------------------

class TestCutMultipleShapesCreator:
    def test_constructor_sets_shapes_of_interest(self):
        creator = CutMultipleShapesCreator(
            "cut_all", subtrahends=["s1", "s2"], minuend="m"
        )
        assert creator.shapes_of_interest_keys == ["m", "s1", "s2"]

    def test_cut_two_subtrahends_from_minuend(self):
        """Cutting two non-overlapping subtrahends from a large box
        reduces volume by both subtrahend volumes."""
        # Large minuend: 100x100x10 = 100000
        minuend = _box(100, 100, 10)
        # Two small subtrahends inside the minuend, non-overlapping
        sub1 = _translated_box(10, 10, 10, -20, 0, 0)  # 1000
        sub2 = _translated_box(10, 10, 10, 20, 0, 0)  # 1000
        creator = CutMultipleShapesCreator(
            "cut_all", subtrahends=["s1", "s2"], minuend="m"
        )
        result = creator.create_shape(input_shapes={"m": minuend, "s1": sub1, "s2": sub2}, **{"m": minuend, "s1": sub1, "s2": sub2})
        vol = _volume(result["cut_all"])
        assert vol == pytest.approx(100000.0 - 2 * 1000.0, rel=0.01)

    def test_cut_with_positional_minuend(self):
        """When minuend is None, it is filled from input_shapes."""
        minuend = _box(100, 100, 10)
        sub1 = _translated_box(10, 10, 10, 0, 0, 0)
        creator = CutMultipleShapesCreator(
            "cut_all", subtrahends=["s1"], minuend=None
        )
        result = creator.create_shape(
            input_shapes={"base": minuend},
            **{"base": minuend, "s1": sub1},
        )
        vol = _volume(result["cut_all"])
        assert vol == pytest.approx(100000.0 - 1000.0, rel=0.01)

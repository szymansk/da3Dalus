"""Tests for CoordinateSystem class."""

import json
import math

import numpy as np
import pytest

from cad_designer.airplane.aircraft_topology.wing.CoordinateSystem import (
    CoordinateSystem,
    InvalidRotationMatrixException,
)


class TestCoordinateSystemConstructor:
    """Test CoordinateSystem initialization."""

    def test_identity_axes(self):
        """Identity axes should produce zero Euler angles."""
        cs = CoordinateSystem(
            xDir=[1, 0, 0],
            yDir=[0, 1, 0],
            zDir=[0, 0, 1],
            origin=[0, 0, 0],
        )
        assert cs.xDir == [1, 0, 0]
        assert cs.yDir == [0, 1, 0]
        assert cs.zDir == [0, 0, 1]
        assert cs.origin == [0, 0, 0]
        np.testing.assert_allclose(cs.euler_xyz, [0.0, 0.0, 0.0], atol=1e-10)

    def test_custom_origin(self):
        """Origin should be stored as a list."""
        cs = CoordinateSystem(
            xDir=[1, 0, 0],
            yDir=[0, 1, 0],
            zDir=[0, 0, 1],
            origin=[10.5, -3.2, 7.0],
        )
        assert cs.origin == [10.5, -3.2, 7.0]

    def test_tuple_inputs_converted_to_lists(self):
        """Tuple inputs should be stored as lists."""
        cs = CoordinateSystem(
            xDir=(1, 0, 0),
            yDir=(0, 1, 0),
            zDir=(0, 0, 1),
            origin=(1, 2, 3),
        )
        assert isinstance(cs.xDir, list)
        assert isinstance(cs.yDir, list)
        assert isinstance(cs.zDir, list)
        assert isinstance(cs.origin, list)

    def test_90_degree_rotation_about_z(self):
        """90-degree rotation about Z: x->y, y->-x, z->z."""
        cs = CoordinateSystem(
            xDir=[0, 1, 0],
            yDir=[-1, 0, 0],
            zDir=[0, 0, 1],
            origin=[0, 0, 0],
        )
        # Rotation about Z by 90 degrees => euler_xyz z component ~90
        np.testing.assert_allclose(cs.euler_xyz[2], 90.0, atol=1e-6)
        np.testing.assert_allclose(cs.euler_xyz[0], 0.0, atol=1e-6)
        np.testing.assert_allclose(cs.euler_xyz[1], 0.0, atol=1e-6)

    def test_90_degree_rotation_about_x(self):
        """90-degree rotation about X: y->z, z->-y."""
        cs = CoordinateSystem(
            xDir=[1, 0, 0],
            yDir=[0, 0, 1],
            zDir=[0, -1, 0],
            origin=[0, 0, 0],
        )
        np.testing.assert_allclose(cs.euler_xyz[0], 90.0, atol=1e-6)

    def test_90_degree_rotation_about_y(self):
        """90-degree rotation about Y: x->-z, z->x."""
        cs = CoordinateSystem(
            xDir=[0, 0, -1],
            yDir=[0, 1, 0],
            zDir=[1, 0, 0],
            origin=[0, 0, 0],
        )
        np.testing.assert_allclose(cs.euler_xyz[1], 90.0, atol=1e-6)

    def test_180_degree_rotation_about_z(self):
        """180-degree rotation about Z: x->-x, y->-y."""
        cs = CoordinateSystem(
            xDir=[-1, 0, 0],
            yDir=[0, -1, 0],
            zDir=[0, 0, 1],
            origin=[0, 0, 0],
        )
        np.testing.assert_allclose(abs(cs.euler_xyz[2]), 180.0, atol=1e-6)

    def test_invalid_rotation_matrix_raises(self):
        """Non-orthogonal axes should raise InvalidRotationMatrixException."""
        with pytest.raises(InvalidRotationMatrixException):
            CoordinateSystem(
                xDir=[1, 1, 0],
                yDir=[0, 1, 0],
                zDir=[0, 0, 1],
                origin=[0, 0, 0],
            )

    def test_non_unit_vectors_raise(self):
        """Scaled (non-unit) vectors should raise InvalidRotationMatrixException."""
        with pytest.raises(InvalidRotationMatrixException):
            CoordinateSystem(
                xDir=[2, 0, 0],
                yDir=[0, 2, 0],
                zDir=[0, 0, 2],
                origin=[0, 0, 0],
            )

    def test_left_handed_system_raises(self):
        """Left-handed coordinate system (det = -1) should raise."""
        with pytest.raises(InvalidRotationMatrixException):
            CoordinateSystem(
                xDir=[1, 0, 0],
                yDir=[0, 0, 1],
                zDir=[0, 1, 0],  # swapped y and z => det = -1
                origin=[0, 0, 0],
            )


class TestCoordinateSystemEulerAngles:
    """Test Euler angle computation for various rotations."""

    @pytest.mark.parametrize(
        "angle_deg",
        [0, 15, 30, 45, 60, 75, 89],
    )
    def test_rotation_about_z_parametric(self, angle_deg):
        """Rotation about Z by various angles should produce correct euler_xyz[2]."""
        rad = math.radians(angle_deg)
        c, s = math.cos(rad), math.sin(rad)
        cs = CoordinateSystem(
            xDir=[c, s, 0],
            yDir=[-s, c, 0],
            zDir=[0, 0, 1],
            origin=[0, 0, 0],
        )
        np.testing.assert_allclose(cs.euler_xyz[2], angle_deg, atol=1e-6)

    def test_combined_rotation(self):
        """A combined rotation should round-trip through euler angles correctly."""
        from scipy.spatial.transform import Rotation

        angles = [10.0, 20.0, 30.0]  # degrees
        r = Rotation.from_euler("xyz", angles, degrees=True)
        mat = r.as_matrix()

        cs = CoordinateSystem(
            xDir=mat[:, 0].tolist(),
            yDir=mat[:, 1].tolist(),
            zDir=mat[:, 2].tolist(),
            origin=[0, 0, 0],
        )
        np.testing.assert_allclose(cs.euler_xyz, angles, atol=1e-6)


class TestIsValidRotationMatrix:
    """Test the _is_valid_rotation_matrix class method."""

    def test_identity_is_valid(self):
        assert CoordinateSystem._is_valid_rotation_matrix(np.eye(3)) == True

    def test_wrong_shape_is_invalid(self):
        assert CoordinateSystem._is_valid_rotation_matrix(np.eye(2)) == False

    def test_scaling_matrix_is_invalid(self):
        assert CoordinateSystem._is_valid_rotation_matrix(2 * np.eye(3)) == False

    def test_reflection_is_invalid(self):
        """Reflection has det = -1, should be invalid."""
        R = np.diag([1, 1, -1])
        assert CoordinateSystem._is_valid_rotation_matrix(R) == False

    def test_singular_matrix_is_invalid(self):
        assert CoordinateSystem._is_valid_rotation_matrix(np.zeros((3, 3))) == False


class TestRotationMatrixToEulerAngles:
    """Test the _rotation_matrix_to_euler_angles class method."""

    def test_identity_gives_zero_angles(self):
        angles = CoordinateSystem._rotation_matrix_to_euler_angles(np.eye(3))
        np.testing.assert_allclose(angles, [0, 0, 0], atol=1e-10)

    def test_invalid_matrix_raises(self):
        with pytest.raises(InvalidRotationMatrixException):
            CoordinateSystem._rotation_matrix_to_euler_angles(np.zeros((3, 3)))

    def test_different_order(self):
        """Requesting ZYX order should still work for identity."""
        angles = CoordinateSystem._rotation_matrix_to_euler_angles(np.eye(3), order="ZYX")
        np.testing.assert_allclose(angles, [0, 0, 0], atol=1e-10)


class TestSerialization:
    """Test JSON serialization and deserialization."""

    def test_getstate_returns_correct_keys(self):
        cs = CoordinateSystem(
            xDir=[1, 0, 0],
            yDir=[0, 1, 0],
            zDir=[0, 0, 1],
            origin=[5, 6, 7],
        )
        state = cs.__getstate__()
        assert set(state.keys()) == {"xDir", "yDir", "zDir", "origin", "euler_xyz"}
        assert state["origin"] == [5, 6, 7]

    def test_from_json_dict_identity(self):
        data = {
            "xDir": [1, 0, 0],
            "yDir": [0, 1, 0],
            "zDir": [0, 0, 1],
            "origin": [1, 2, 3],
        }
        cs = CoordinateSystem.from_json_dict(data)
        assert cs.origin == [1, 2, 3]
        np.testing.assert_allclose(cs.euler_xyz, [0, 0, 0], atol=1e-10)

    def test_from_json_dict_defaults(self):
        """Missing keys should default to identity axes and zero origin."""
        cs = CoordinateSystem.from_json_dict({})
        assert cs.xDir == [1, 0, 0]
        assert cs.yDir == [0, 1, 0]
        assert cs.zDir == [0, 0, 1]
        assert cs.origin == [0, 0, 0]

    def test_save_and_load_json_roundtrip(self, tmp_path):
        """Save to JSON, load back, verify identical."""
        cs_original = CoordinateSystem(
            xDir=[1, 0, 0],
            yDir=[0, 1, 0],
            zDir=[0, 0, 1],
            origin=[10, 20, 30],
        )
        filepath = str(tmp_path / "cs.json")
        cs_original.save_to_json(filepath)

        cs_loaded = CoordinateSystem.from_json(filepath)
        assert cs_loaded.xDir == cs_original.xDir
        assert cs_loaded.yDir == cs_original.yDir
        assert cs_loaded.zDir == cs_original.zDir
        assert cs_loaded.origin == cs_original.origin
        np.testing.assert_allclose(cs_loaded.euler_xyz, cs_original.euler_xyz, atol=1e-10)

    def test_save_to_json_creates_valid_json(self, tmp_path):
        """The saved file should be valid JSON."""
        cs = CoordinateSystem(
            xDir=[1, 0, 0],
            yDir=[0, 1, 0],
            zDir=[0, 0, 1],
            origin=[0, 0, 0],
        )
        filepath = str(tmp_path / "cs.json")
        cs.save_to_json(filepath)

        with open(filepath) as f:
            data = json.load(f)
        assert "xDir" in data
        assert "euler_xyz" in data

    def test_roundtrip_with_rotation(self, tmp_path):
        """Roundtrip a rotated coordinate system through JSON."""
        from scipy.spatial.transform import Rotation

        angles = [15.0, -25.0, 40.0]
        r = Rotation.from_euler("xyz", angles, degrees=True)
        mat = r.as_matrix()

        cs_original = CoordinateSystem(
            xDir=mat[:, 0].tolist(),
            yDir=mat[:, 1].tolist(),
            zDir=mat[:, 2].tolist(),
            origin=[100, 200, 300],
        )
        filepath = str(tmp_path / "rotated_cs.json")
        cs_original.save_to_json(filepath)

        cs_loaded = CoordinateSystem.from_json(filepath)
        np.testing.assert_allclose(cs_loaded.euler_xyz, angles, atol=1e-6)

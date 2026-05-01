"""Tests for intelligent AVL spacing optimisation."""
from __future__ import annotations

from app.avl.geometry import AvlControl, AvlSection, AvlSurface
from app.schemas.aeroanalysisschema import SpacingConfig


class TestControlSurfaceDetection:
    def test_increases_nchord_when_controls_present(self):
        from app.avl.spacing import optimise_surface_spacing

        surface = AvlSurface(
            name="Wing",
            n_chord=12,
            c_space=1.0,
            n_span=20,
            s_space=1.0,
            sections=[
                AvlSection(
                    xyz_le=(0, 0, 0),
                    chord=0.2,
                    controls=[AvlControl("aileron", 1.0, 0.8, (0, 0, 0), -1.0)],
                ),
                AvlSection(xyz_le=(0, 1, 0), chord=0.15),
            ],
        )
        config = SpacingConfig(n_chord=12, auto_optimise=True)
        result = optimise_surface_spacing(surface, config)
        assert result.n_chord >= 16

    def test_no_increase_without_controls(self):
        from app.avl.spacing import optimise_surface_spacing

        surface = AvlSurface(
            name="Wing",
            n_chord=12,
            c_space=1.0,
            n_span=20,
            s_space=1.0,
            sections=[
                AvlSection(xyz_le=(0, 0, 0), chord=0.2),
                AvlSection(xyz_le=(0, 1, 0), chord=0.15),
            ],
        )
        config = SpacingConfig(n_chord=12, auto_optimise=True)
        result = optimise_surface_spacing(surface, config)
        assert result.n_chord == 12


class TestAutoOptimiseDisabled:
    def test_base_values_preserved(self):
        from app.avl.spacing import optimise_surface_spacing

        surface = AvlSurface(
            name="Wing",
            n_chord=8,
            c_space=1.0,
            n_span=10,
            s_space=1.0,
            sections=[
                AvlSection(
                    xyz_le=(0, 0, 0),
                    chord=0.2,
                    controls=[AvlControl("aileron", 1.0, 0.8, (0, 0, 0), -1.0)],
                ),
                AvlSection(xyz_le=(0, 1, 0), chord=0.15),
            ],
        )
        config = SpacingConfig(n_chord=8, n_span=10, auto_optimise=False)
        result = optimise_surface_spacing(surface, config)
        assert result.n_chord == 8
        assert result.n_span == 10


class TestUnsweptWingSpacing:
    def test_unswept_uses_neg_sine(self):
        from app.avl.spacing import optimise_surface_spacing

        surface = AvlSurface(
            name="Wing",
            n_chord=12,
            c_space=1.0,
            n_span=20,
            s_space=1.0,
            sections=[
                AvlSection(xyz_le=(0, 0, 0), chord=0.2),
                AvlSection(xyz_le=(0, 1, 0), chord=0.15),
            ],
        )
        config = SpacingConfig(auto_optimise=True)
        result = optimise_surface_spacing(surface, config)
        assert result.s_space == -2.0

    def test_swept_keeps_cosine(self):
        from app.avl.spacing import optimise_surface_spacing

        surface = AvlSurface(
            name="Wing",
            n_chord=12,
            c_space=1.0,
            n_span=20,
            s_space=1.0,
            sections=[
                AvlSection(xyz_le=(0, 0, 0), chord=0.3),
                AvlSection(xyz_le=(0.15, 1.0, 0), chord=0.2),  # significant sweep
            ],
        )
        config = SpacingConfig(auto_optimise=True)
        result = optimise_surface_spacing(surface, config)
        assert result.s_space == 1.0

    def test_centreline_break_keeps_cosine(self):
        from app.avl.spacing import optimise_surface_spacing

        surface = AvlSurface(
            name="Wing",
            n_chord=12,
            c_space=1.0,
            n_span=20,
            s_space=1.0,
            sections=[
                AvlSection(xyz_le=(0, 0, 0), chord=0.2),
                AvlSection(xyz_le=(0, 0, 0), chord=0.25),  # centreline break at y=0
                AvlSection(xyz_le=(0, 1, 0), chord=0.15),
            ],
        )
        config = SpacingConfig(auto_optimise=True)
        result = optimise_surface_spacing(surface, config)
        assert result.s_space == 1.0


class TestHelperFunctions:
    def test_has_control_surfaces_true(self):
        from app.avl.spacing import _has_control_surfaces

        surface = AvlSurface(
            name="W",
            n_chord=12,
            c_space=1.0,
            sections=[
                AvlSection(
                    xyz_le=(0, 0, 0),
                    chord=0.2,
                    controls=[AvlControl("a", 1, 0.8, (0, 0, 0), -1)],
                ),
            ],
        )
        assert _has_control_surfaces(surface)

    def test_has_control_surfaces_false(self):
        from app.avl.spacing import _has_control_surfaces

        surface = AvlSurface(
            name="W",
            n_chord=12,
            c_space=1.0,
            sections=[
                AvlSection(xyz_le=(0, 0, 0), chord=0.2),
            ],
        )
        assert not _has_control_surfaces(surface)

    def test_is_unswept_true(self):
        from app.avl.spacing import _is_unswept

        surface = AvlSurface(
            name="W",
            n_chord=12,
            c_space=1.0,
            sections=[
                AvlSection(xyz_le=(0, 0, 0), chord=0.2),
                AvlSection(xyz_le=(0, 1, 0), chord=0.15),
            ],
        )
        assert _is_unswept(surface)

    def test_is_unswept_false(self):
        from app.avl.spacing import _is_unswept

        surface = AvlSurface(
            name="W",
            n_chord=12,
            c_space=1.0,
            sections=[
                AvlSection(xyz_le=(0, 0, 0), chord=0.3),
                AvlSection(xyz_le=(0.2, 1.0, 0), chord=0.2),
            ],
        )
        assert not _is_unswept(surface)

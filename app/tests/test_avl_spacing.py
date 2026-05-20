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


class TestSectionDensityNspanBump:
    """gh-590: AVL refuses with 'Cannot adjust spanwise spacing at section N'
    when the surface-level Nspan cannot fit at least one spanwise panel into
    the tightest inter-section gap. The optimiser must bump Nspan to satisfy
    AVL whenever the configured value is too low for the actual geometry.
    """

    def _rv7_like_wing(self, *, n_span: int = 20):
        """Six-section main wing mirroring the RV-7 layout: two near-coincident
        section pairs at root (Y=0, Y=0.005) and tip (Y=0.399, Y=0.409) on a
        semispan of 0.409 m. min_gap / span = 1.2 % → AVL needs Nspan ≥ 82.
        """
        ys = [0.0, 0.005, 0.070, 0.235, 0.399, 0.409]
        return AvlSurface(
            name="main_wing",
            n_chord=16,
            c_space=1.0,
            n_span=n_span,
            s_space=-2.0,
            sections=[AvlSection(xyz_le=(0.19, y, 0.0), chord=0.183) for y in ys],
        )

    def test_bumps_nspan_when_sections_too_tight(self):
        from app.avl.spacing import optimise_surface_spacing

        surface = self._rv7_like_wing(n_span=20)
        config = SpacingConfig(n_span=20, auto_optimise=True)
        result = optimise_surface_spacing(surface, config)
        # span = 0.409, min_gap = 0.005 → ceil(span/min_gap) + 2 = 84
        assert result.n_span >= 82, (
            f"Optimiser must bump Nspan to satisfy AVL's section-density "
            f"constraint; got {result.n_span}, need >= 82 for this geometry."
        )

    def test_does_not_lower_user_configured_nspan(self):
        """If the caller already configured a generous Nspan, don't downgrade."""
        from app.avl.spacing import optimise_surface_spacing

        # Clean wing — only 2 sections, no tight gaps. Required is small.
        surface = AvlSurface(
            name="W",
            n_chord=16,
            c_space=1.0,
            n_span=200,
            s_space=1.0,
            sections=[
                AvlSection(xyz_le=(0, 0, 0), chord=0.3),
                AvlSection(xyz_le=(0, 1, 0), chord=0.2),
            ],
        )
        config = SpacingConfig(n_span=200, auto_optimise=True)
        result = optimise_surface_spacing(surface, config)
        assert result.n_span == 200

    def test_no_bump_for_clean_wing(self):
        from app.avl.spacing import optimise_surface_spacing

        # Uniformly-spaced 3-section wing — min_gap / span = 0.5 → Nspan=20 plenty.
        surface = AvlSurface(
            name="W",
            n_chord=16,
            c_space=1.0,
            n_span=20,
            s_space=1.0,
            sections=[
                AvlSection(xyz_le=(0, 0.0, 0), chord=0.3),
                AvlSection(xyz_le=(0, 0.5, 0), chord=0.25),
                AvlSection(xyz_le=(0, 1.0, 0), chord=0.2),
            ],
        )
        config = SpacingConfig(n_span=20, auto_optimise=True)
        result = optimise_surface_spacing(surface, config)
        assert result.n_span == 20

    def test_auto_optimise_false_honours_user_nspan(self):
        from app.avl.spacing import optimise_surface_spacing

        surface = self._rv7_like_wing(n_span=20)
        config = SpacingConfig(n_span=20, auto_optimise=False)
        result = optimise_surface_spacing(surface, config)
        assert result.n_span == 20  # opt-out: no bump even if AVL would crash

    def test_coincident_sections_are_ignored_in_min_gap(self):
        """Two sections at exactly the same Y (chord/twist change) must not
        produce min_gap=0 → infinite Nspan. They're ignored in the calculation.
        """
        from app.avl.spacing import optimise_surface_spacing

        surface = AvlSurface(
            name="W",
            n_chord=16,
            c_space=1.0,
            n_span=20,
            s_space=1.0,
            sections=[
                AvlSection(xyz_le=(0, 0.0, 0), chord=0.3),
                AvlSection(xyz_le=(0, 0.0, 0), chord=0.25),  # coincident
                AvlSection(xyz_le=(0, 1.0, 0), chord=0.2),
            ],
        )
        config = SpacingConfig(n_span=20, auto_optimise=True)
        result = optimise_surface_spacing(surface, config)
        # Real min_gap is 1.0, span is 1.0 → bump not required; stay at 20.
        assert result.n_span == 20


class TestRequiredNspanHelper:
    """Direct coverage of the early-return branches in
    ``_required_nspan_for_section_density`` so SonarQube ``new_coverage`` lands
    above the 80 % gate. The main paths are exercised end-to-end by
    ``TestSectionDensityNspanBump`` above; these tests pin the corner cases.
    """

    def test_returns_zero_for_empty_surface(self):
        from app.avl.spacing import _required_nspan_for_section_density

        surface = AvlSurface(name="W", n_chord=12, c_space=1.0, sections=[])
        assert _required_nspan_for_section_density(surface) == 0

    def test_returns_zero_for_single_section(self):
        from app.avl.spacing import _required_nspan_for_section_density

        surface = AvlSurface(
            name="W",
            n_chord=12,
            c_space=1.0,
            sections=[AvlSection(xyz_le=(0, 0, 0), chord=0.2)],
        )
        assert _required_nspan_for_section_density(surface) == 0

    def test_returns_zero_for_zero_span_surface(self):
        """All sections at the same Y (e.g. a rudder declared as two coincident
        sections) → no spanwise constraint to satisfy."""
        from app.avl.spacing import _required_nspan_for_section_density

        surface = AvlSurface(
            name="rudder",
            n_chord=12,
            c_space=1.0,
            sections=[
                AvlSection(xyz_le=(0, 0.0, 0), chord=0.2),
                AvlSection(xyz_le=(0, 0.0, 0.3), chord=0.18),
            ],
        )
        assert _required_nspan_for_section_density(surface) == 0

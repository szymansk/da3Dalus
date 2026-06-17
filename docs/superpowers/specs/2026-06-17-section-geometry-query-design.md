# Section Geometry Query — design spec

**Date:** 2026-06-17
**Status:** Draft for review
**Related:** follow-up of #1008 (spar sizing), consumed by #1011 (buckling),
serves the spar-sizing `_get_tc_by_y_for_surface` stub.

## Problem

The spar-sizing feature (#1008) needs the **local section thickness** at every
spanwise load station to cap the spar's outer dimension. Today
`analysis_service._get_tc_by_y_for_surface()` is a stub that returns `{}`, so
every station falls back to a constant `t/c = 0.12`:

```
t/c=0.12 fallback applied at y=0.49, 0.48, … 0.01 m — no airfoil thickness data available.
```

The wing's real section geometry (airfoils + their relative twist/incidence,
dihedral, sweep, loft) is never consulted. A naive airfoil-to-airfoil t/c
interpolation that ignores the segment/surface geometry would be wrong, because
the rotations of the sections relative to each other change the built section.

## Goal

A **general, reusable geometry primitive in `cad_designer`** that, for a given
wing, returns at a parametric location `(y/span, x/c)`:

- `thickness` — vertical extent of the built section at that chord location
- `top_z`, `bottom_z` — upper/lower surface heights
- `center_z` — section mid-height (spar placement reference)

Available **per segment** and **for the whole surface**, exposed via a v2
endpoint, and consumed by spar sizing (and later by construction: ribs, spar
placement, fittings).

## Key decision (approved)

**Measure on the real lofted CAD solid** (not analytic two-airfoil
interpolation). The solid built by `WingLoftCreator` already encodes every
relative rotation (dihedral via R_x, incidence/twist via R_y, sweep via the
plane origin) and the ruled loft between sections. Slicing it gives the exact
built geometry, including non-linearities the analytic blend misses.

Trade-offs accepted: building CAD is CPU-bound and unavailable on
`linux/aarch64` (cadquery excluded). Mitigated below.

### Slice orientation

A slice at **constant world-x** would cut obliquely through a swept/twisted
wing and distort the section. Instead, for each `y/span` station we cut with the
**local section plane** at that station — normal = the local spanwise direction
from the cached segment frame (`get_wing_workplane`). That yields the true
built cross-section perpendicular to the span; `x/c` is then sampled along that
section's chord.

> Reviewer: if you actually want constant-fuselage-y "rib" cuts instead, say so
> — that changes the cut normal and the chord parameterisation.

## Architecture

```
endpoint (POST /aeroplanes/{id}/section-geometry)
  → analysis/wing service (resolve wing → WingConfiguration, units)
    → cad_designer.section_geometry  (NEW, read-only topology respected)
       → WingLoftCreator (build solid ONCE)
       → per-station section-plane slice → outline → sample x/c
```

### 1. `cad_designer` primitive (new module)

New module, e.g. `cad_designer/airplane/geometry/section_geometry.py`. No
topology class is modified (Airfoil / WingSegment / WingConfiguration stay
read-only); the primitive operates on them.

```python
@dataclass
class SectionPoint:
    y_span: float        # 0..1 across the whole surface
    x_c: float           # 0..1 along the local chord
    thickness: float     # mm
    top_z: float         # mm, wing frame
    bottom_z: float      # mm, wing frame
    center_z: float      # mm, wing frame

class SectionGeometry:
    def __init__(self, wing_config: WingConfiguration):
        # builds + caches the lofted solid once
    def at(self, y_span: float, x_c: float) -> SectionPoint: ...
    def sample(self, y_spans: list[float], x_cs: list[float]) -> list[SectionPoint]:
        # slices each unique y_span ONCE, samples all x_c on that outline
    def per_segment(self, n_span: int, n_chord: int) -> dict[int, list[SectionPoint]]: ...
```

- **Build once, slice many.** The solid is created once per `SectionGeometry`
  instance; `sample()` groups requests by `y_span` so each section plane is cut
  once and all `x_c` are read off the same outline.
- **Frame:** wing-local, origin at wing-root LE, `z` vertical (normal to the
  root plane). Internally **mm**; the service layer converts to **m** for the
  API (project convention).
- **y/span → segment mapping:** accumulate segment lengths; locate the segment
  and `relative_length` for a given `y_span` (reuse the math already in
  `_get_relative_segment_coordinate_system` / wing_service).
- **Slicing:** reuse / extend `cad_designer/aerosandbox/slicing.py`
  (`slice_at_x` pattern) with a section-plane cut helper. Outline → for an
  `x_c`, intersect the chord ordinate with upper/lower edges → `top_z`,
  `bottom_z`, `thickness = top_z − bottom_z`, `center_z = (top_z+bottom_z)/2`.
- **Platform guard:** import cadquery lazily; raise a clear, typed error when
  unavailable so the endpoint returns a 503/422 rather than crashing.

### 2. v2 endpoint

`POST /aeroplanes/{id}/section-geometry`

Request (all optional with sensible defaults):
```json
{
  "y_over_span": [0.1, 0.2, ...],   // default: evenly spaced N
  "x_over_chord": [0.25, 0.3, ...], // default: evenly spaced M (+ max-thickness)
  "per_segment": false              // also return per-segment grids
}
```
Response: `{ surface: SectionPoint[], segments?: {idx: SectionPoint[]} }`
(`top_z/bottom_z/center_z/thickness` in **metres**).

Thin endpoint → service → cad_designer (layered convention). Pydantic schemas
in `app/schemas/section_geometry.py`.

### 3. Spar-sizing wire-in

Replace `_get_tc_by_y_for_surface()`'s `return {}`:

- Build a `SectionGeometry` for the surface's wing once.
- For each load-station `y`, query thickness at the spar's chordwise location.
  Default: the **max-thickness** `x/c` on that section (deepest available
  section). `outer_mm = thickness × packing_factor`; expose `center_z` for spar
  placement.
- Stations with no geometry (e.g. cadquery unavailable) keep the documented
  0.12 fallback + warning — so behaviour degrades gracefully, never crashes.
- The existing `tc_ratio` field becomes `thickness/chord` derived from the real
  query (keeps the response shape stable for the frontend).

## Testing strategy

Per the CI coverage rule (fast tier runs **without** cadquery/aerosandbox; the
SonarCloud `new_coverage` gate is computed there):

- **Slow / `requires_cadquery`:** real solid build + slice on a known wing
  (e.g. a NACA box wing with twist+dihedral) — assert thickness at root ≈ t/c·chord,
  monotonic taper, twist tilts top_z/bottom_z, dihedral lifts center_z.
- **Fast (mocked):** stub `SectionGeometry` at the service boundary to test the
  endpoint contract, unit conversion, y/span→segment mapping, the spar wire-in
  (real thickness replaces fallback; fallback still triggers when the stub
  yields nothing), and error paths (wing not found, cadquery unavailable).
  These keep `new_coverage ≥ 80%` without CAD.

## Out of scope

- Constant-fuselage-y rib cuts (offer as a future option).
- Caching across requests (build-once-per-request is enough for now).
- Spar buckling check (#1011).
- Changing the spar's chordwise position model beyond "max thickness" default.

## Decomposition (epic + sub-issues)

1. `cad_designer` `SectionGeometry` primitive + slow/fast tests.
2. v2 `section-geometry` endpoint + schemas + fast tests.
3. Spar-sizing wire-in (replace the stub) + fast tests; UAT vs personas.

# ADR 0002 — `cad_designer/` is frozen: read-only topology, new Creators only

- **Status:** Accepted — in force
- **Decided:** policy predates the current history; formalised 2026-07-14 (`docs/decisions/2026-07-14-exclude-cad-designer-from-sonarcloud.md`, commit `cd0cf7fb`)
- **Deciders:** Marc Szymanski (maintainer)
- **Confidence:** 🟢 CONFIRMED (an in-repo ADR exists for the Sonar half; the read-only policy is stated in `cad_designer/CLAUDE.md`)

## Context

`cad_designer/` is ~22 000 lines of CadQuery/OCCT geometry by several
contributors, and the only thing that turns a parametric description into a
manufacturable solid. It is fragile in an unusual way: **its failure mode is
silent wrongness, not an exception** — a plausible cleanup can change the geometry
out of a loft with no test failing, because the tests that would catch it are slow
volume/centroid builds. The forcing function was tooling: in July 2026 the
SonarCloud gate on `main` went ERROR, and ~18 of the 32 gate-breakers were latent
2024–2025 findings inside `cad_designer/`, swept in only because the new-code
baseline moved.

## Decision

1. **Read-only, never modified:** the topology classes under
   `airplane/aircraft_topology/` (`Airfoil`, `WingSegment`, `WingConfiguration`,
   `Spare`, `TrailingEdgeDevice`, `Servo`, `CoordinateSystem`, the `*Information`
   classes, `AirplaneConfiguration`, `FuselageConfiguration`) and
   `airplane/GeneralJSONEncoderDecoder.py`, the serialisation contract.
   **Bugs and static-analysis findings inside these are deliberately not fixed.**
2. **The sanctioned extension point is a new Creator** — a subclass of
   `AbstractShapeCreator`, started from `airplane/creator/_creator_template.py`
   and registered in its subpackage `__init__.py`.
3. **`airplane/geometry/` is explicitly *not* frozen.** `section_geometry.py`,
   `segment_split.py`, `spar_solver.py`, `spar_cad_insertion.py` — the
   #1008/#1030/#1075/#1076 spar pipeline — are actively developed feature code.
   `cq_plugins/` and `decorators/` are open too.
4. **Validation lives above this layer**, in `app/schemas/` (Pydantic) and in
   frontend UX — never inside the topology classes.
5. **Green the quality gate by configuration, not by edits:**
   `sonar.exclusions = …,cad_designer/**` and ruff `extend-exclude`.
6. **One approved exception (gh-934):** `Turbulator`, a new per-segment optional
   element analogous to `TrailingEdgeDevice`/`Spare`, required extending
   `WingSegment` and `WingConfiguration` with a `turbulator` parameter. It is the
   single permitted addition to existing topology classes.

## Consequences

- A red `main` gate is an actionable signal again, and the extension path is well
  exercised — 29 Creators ship today.
- ~22 000 LOC is **neither linted nor statically analysed nor coverage-measured**;
  Sonar will not flag *new* issues there either.
- **Known defects are permanent by policy** and documented rather than fixed —
  the unreachable perpendicular-spare branch, the corrupted `gp_DX/DY/DZ`
  singletons, the unregistered `scaleXyz` plugin,
  `AirplaneConfiguration._main_wing_index = 0` (a dormant copy of the gh-788
  ≈8× reference-area bug), and nine removed Creators still referenced by three
  shipped plan JSONs. Catalogued in [`../code-analysis.md`](../code-analysis.md).
- **Enforcement is prose, not code.** Nothing prevents an edit; the exclusions
  only hide the consequences from Sonar.
- The frozen boundary is not visible in the layout: `airplane/aircraft_topology/`
  (frozen) and `airplane/geometry/` (open) sit side by side.

## Related

[ADR 0001](0001-millimetres-in-cad-metres-in-db-and-aerosandbox.md) ·
[ADR 0005](0005-cad-in-a-spawned-process-pool.md) ·
[ADR 0015](0015-tiered-ci-fast-full-nightly.md) ·
[ADR 0021](0021-complete-but-unreachable-code-is-deleted-by-default.md) (removals
here are spec-only). Evidence and the four rejected alternatives:
`docs/decisions/2026-07-14-exclude-cad-designer-from-sonarcloud.md`; commits
`cd0cf7fb`, `606273b5` (gh-934); `sonar-project.properties:10`;
`pyproject.toml:122-129`; `cad_designer/CLAUDE.md`.

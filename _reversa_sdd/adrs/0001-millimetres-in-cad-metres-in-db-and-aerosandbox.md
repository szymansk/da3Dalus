# ADR 0001 — Millimetres in the CAD topology, metres in the DB and AeroSandbox

- **Status:** Accepted — in force (retroactively reconstructed)
- **Decided:** incrementally, 2026-04 → 2026-05 (crystallised by gh-352 / gh-362 / gh-402)
- **Deciders:** Marc Szymanski (maintainer)
- **Confidence:** 🟢 CONFIRMED (code, migration, commit bodies)

## Context

Two worlds disagree about length. `cad_designer/` is a CadQuery library, frozen by
[ADR 0002](0002-cad-designer-is-frozen-new-creators-only.md), and CAD /
3-D-printing practice is millimetre-native; AeroSandbox and every sizing formula
are strictly SI. They meet in `app/converters/`, and getting that seam wrong
produced a recognisable bug class — a spar origin computed in metres written into a
millimetre column, so the spar appeared 1000× away (gh-352, gh-362). The gh-402
investigation found the root cause was the *storage*, not the conversion code:
`wing_xsec_spares` held four fields in mm and two in metres.

## Decision

1. **`cad_designer` topology and `WingConfig` speak millimetres**, in a wing-local
   frame (origin at the root leading edge, z up).
2. **The database and AeroSandbox speak metres.**
3. **Conversion happens only at named boundaries** — `app/converters/`
   (`scale = 0.001` mm→m, `scale = 1000.0` m→mm) and the
   `_convert_spare_to_meters` / `_convert_spare_to_mm` helpers in `wing_service`.
4. **Within one table, one unit.** `wing_xsec_spares` is unified to **millimetres
   for all six dimensional fields** — a deliberate mm island inside the metre
   database, because five of its six consumers are CAD-side (commit `3785057c`,
   with an Alembic data migration).
5. **`spare_vector` is dimensionless** — a unit direction vector, never scaled.
6. **The API contract does not change.** All spar endpoints deliver metres; the mm
   storage is invisible to clients.

## Consequences

- The frozen CAD layer is never touched, DB and solver agree, and a mixed-unit
  spares row is now impossible.
- **The rule is convention, not type.** Nothing prevents a metre value reaching a
  millimetre column; only review and tests do. Every contributor must know which
  unit context they are in.
- 🔴 The self-describing units block is **wrong** — `WingUnitsSchema` /
  `WingModel.units` still report `detail_length: "m"` and `SpareDetailSchema` says
  "in meters". It cannot express a per-table exception.
- The frontend exposes the duality (`treeMode: "wingconfig"` vs `"asb"`);
  `WingOutlineViewer` uses metres directly.

## Related

[ADR 0002](0002-cad-designer-is-frozen-new-creators-only.md) ·
[ADR 0005](0005-cad-in-a-spawned-process-pool.md) · domain rules BR-1, BR-2, BR-3.
Evidence: commit `3785057c` (gh-402) and the gh-352 / gh-362 bug pair;
`app/services/wing_service.py:43-88`;
[`../code-analysis.md`](../code-analysis.md).

---

## Amendment — 2026-08-15 — externally ingested geometry

**Source:** [`../questions.md`](../questions.md) §Q-FD-2. **Confidence:** 🟢
CONFIRMED (both upload paths verified in code).

The rules above govern units *inside* the system. Imported geometry is the case
they do not cover, and the most reachable silent-1000× path:
`slice_step_to_fuselage` takes **no unit parameter** and persists native STEP
coordinates as metres — safe only on the OpenVSP path, where BR-OV13 forces
`LEN_M`. The two upload paths assume opposite units, neither verified:

| Path | Assumption | Failure mode |
|---|---|---|
| Fuselage slicing | metres | a millimetre STEP yields a fuselage **1000× too large** |
| Construction parts (`volume_mm3`, `area_mm2`, `bbox_*_mm`) | millimetres | a metre STEP records a volume **10⁹× too small** |

**Rule: for imported geometry, unify the *mechanism*, not the assumed unit.**
Storage stays as it is; conversion happens at import, through one shared
three-layer mechanism used by both paths, because no single layer is reliable
alone:

1. **Read the unit from the STEP header** (`SI_UNIT` in the
   `GEOMETRIC_REPRESENTATION_CONTEXT`).
2. **Explicit user override at upload**, pre-filled with the detected value —
   headers are not trustworthy in practice: the project's own RV-7 fixture carries
   **contradictory** `SI_UNIT` declarations.
3. **A plausibility check on absolute dimensions**, emitting a `DesignWarning` when
   implausible. An RC fuselage is **0.3–3 m**, so 1700 m or 1.7 mm is unambiguous.
   It must test **absolute** dimensions, not a ratio: `volume_ratio` / `area_ratio`
   compare reconstruction against original, so a uniform scale error cancels out
   and both stay ≈ 1.0.

**Rejected:** an explicit parameter only (a mis-stated unit still propagates
silently) and "metres only, enforced" (millimetres are the normal CAD convention).

**Related:** [ADR 0018](0018-openvsp-import-scope-is-rc-scaling-inspiration.md) ·
[ADR 0020](0020-one-designwarning-channel-no-undeclared-fallbacks.md) ·
[`../questions.md`](../questions.md) §Q-FD-2, §Q-FD-4, §Q-CG-1 (the same ambiguity
in export: STL is unitless, 3MF carries units).

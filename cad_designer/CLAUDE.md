# `cad_designer/` — CadQuery CAD engine

Parametric aircraft geometry (wings, fuselages, assemblies) built with
**CadQuery**. **Read the root `CLAUDE.md` first.** This layer is **fragile and
largely read-only on purpose** — validation/constraints are enforced *above* it
(Pydantic schemas in `app/schemas/`, frontend UX).

## 🚫 Read-only — never modify

- **Topology classes** in `airplane/aircraft_topology/`:
  `Airfoil`, `WingSegment`, `WingConfiguration`, `Spare`, `TrailingEdgeDevice`,
  `Servo`, `CoordinateSystem`, … (`wing/`, `components/`).
- **`airplane/GeneralJSONEncoderDecoder.py`** — the serialisation contract.
- Do **not** fix bugs or SonarQube findings inside these — the code is fragile
  and deliberately frozen. Green the quality gate via config exclusion, not edits
  (e.g. the known dead perpendicular-spare branch in `WingConfiguration` stays).

**Approved exception (gh-934):** `Turbulator` — a new per-segment element that
required extending `WingSegment`/`WingConfiguration` with a `turbulator` param.

## ✅ What you MAY add / change

- **New Creators:** subclass `AbstractShapeCreator` (`airplane/AbstractShapeCreator.py`);
  start from `airplane/creator/_creator_template.py`.
- **`airplane/geometry/`** is **new, actively-developed feature code — NOT locked
  topology.** Safe to modify: `section_geometry.py`, `segment_split.py`,
  `spar_solver.py`, `spar_cad_insertion.py` (the #1008/#1030/#1075/#1076 spar
  pipeline). Don't confuse it with the frozen topology classes above.
- **`cq_plugins/` + `decorators/`** — reuse these geometry helpers before writing
  new ones.

## Conventions

- **Units: millimetres throughout**, wing-local frame (origin root-LE, z up).
  The `app/converters/` layer scales to metres for DB/ASB.
- Geometry decision logic (e.g. `spar_solver`) is kept pure and CAD-free behind a
  thin seam so it runs on the CI fast tier with hand-built inputs; the real
  lofted-geometry path is exercised by `@slow @requires_cadquery` tests.

## Commands

```bash
poetry run pytest cad_designer/tests/          # fast
poetry run pytest cad_designer/tests/ -m slow  # real CadQuery build
```

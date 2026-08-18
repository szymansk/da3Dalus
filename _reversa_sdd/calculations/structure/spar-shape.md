---
name: spar-shape
kind: parameter
unit: -
cluster: structure
user_visible: true
source_status: SOURCED
node_class: unclassified-parameter
tags:
  - cluster/structure
  - class/unclassified-parameter
  - source/sourced
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Spar cross-section shape

**Definition.** Cross-section shape requested for both spars in the plan path.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `"tube"`

**Formula — as the code writes it.**

```
shape: Literal["tube", "rod", "rectangular", "capped"] = Field(
    "tube",
    ...
)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/schemas/spar_plan.py:166` — `SparPlanRequest.shape`

**Consumed by.**

- outside it: `app/services/spar_plan_service.py:600` · `app/services/spar_plan_service.py:601` · `cad_designer/airplane/geometry/spar_solver.py:416` · `cad_designer/airplane/geometry/spar_solver.py:439` · `cad_designer/airplane/geometry/spar_solver.py:630` · `frontend/hooks/useSparPlan.ts:33`

**Source.** 🟢 SOURCED

> RC-Network Wiki, "Holm (Flugzeugkonstruktion)", https://wiki.rc-network.de/wiki/Holm — spar configurations: Rohrholm (tubular CFK/composite tube, ribs threaded onto it, carries bending AND torsion) and Kastenholm (box / double-tee, upper and lower Holmgurte at maximum separation plus a Holmsteg web); Kirch, "Hauptholm", https://www.flugmodellbau-kirch.de/Hauptholm.htm (two-flange section, formula given); Lennon, The Basics of R/C Model Aircraft Design (1996), Ch. 13 (D-spar: flanges plus vertical-grain shear web)
>
> — via `rc-aircraft-designer + direct verification of the kirch source`

**The source states it as.**

```
The RC literature recognises exactly this family of spar cross-sections; 'tube' = Rohrholm, 'capped' = Kastenholm/Doppel-T, and Kirch gives the capped section modulus in closed form.
```

**⚠️ Divergence from the source.** The shape TAXONOMY is well sourced. Its implementation is not honoured: `shape` is absent from the `common` dict at app/services/spar_plan_service.py:567-573, so strength sizing is always solve_dimension(shape="rod", ...) at cad_designer/airplane/geometry/spar_solver.py:767. A 'capped' request — the ONE shape for which the cited source supplies an exact formula — is sized as a round rod, and SparPiece.width/height/cap_width are never assigned by any production code.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Only partially honoured. `shape` is NOT forwarded to build_stations_from_geometry (it is absent from the `common` dict at app/services/spar_plan_service.py:567-573), so the strength sizing is always solve_dimension(shape="rod", ...) at spar_solver.py:767. A 'rectangular' or 'capped' request is sized as a round rod; only the bore-propagation and joint-type branches see the shape.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `gh-1080: Cross-section shape for both spars. 'tube' (default) — hollow round tube, telescoping-capable; 'rod' — solid round, no bore, joiner connections; 'rectangular' — solid rectangular box; 'capped' — I/C beam with flanges.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*

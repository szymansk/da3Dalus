# ADR 0003 — AeroSandbox is the default solver; AVL is the exception

- **Status:** Accepted — in force
- **Decided:** progressively; the decisive step is gh-674 (2026-06-05, commit `d1f81229`)
- **Deciders:** Marc Szymanski (maintainer)
- **Confidence:** 🟢 CONFIRMED (commit body, call-site audit, project memory `asb_over_avl`)

## Context

AVL was the original engine, vendored as an `avl-binary` wheel with a large amount
of supporting code (a `.avl` emitter, a keystroke-driven subprocess runner, an
stdout state-machine parser). Every run means writing a geometry file, spawning a
process and parsing unformatted stdout — **~1–3 s** for a three-surface aircraft —
and it cannot sweep: `analyse_aerodynamics` rejects array-valued `alpha`/`beta`.
AeroSandbox provides the same Trefftz-plane core in-process plus vectorised
`AeroBuildup`: the same case takes **~58 ms** with the VLM, and AeroBuildup took
the assumption recompute from ~150 solver calls to one (gh-690).

## Decision

**Prefer AeroSandbox. Reach for AVL only where AeroSandbox cannot cover the case,
and make that an explicit, opt-in choice by the caller.**

| Path | Default | AVL reachable? |
|---|---|---|
| α sweep, simple sweep | `AEROBUILDUP` (hard-coded) | **no** — AVL rejects array sweeps |
| streamlines, four-view | `VORTEX_LATTICE` (hard-coded) | **no** |
| `recompute_assumptions` (the gh-924 context) | `AEROBUILDUP` | **no** |
| operating-point generation, background retrim | AeroBuildup / `asb.Opti` | **no** |
| strip forces, spanwise loads | `solver="vlm"` | yes — `?solver=avl` |
| `analyze_wing` / `analyze_airplane`, stability summary | caller-selected | yes — `analysis_tool=avl` |
| `trim_with_avl` | — | this endpoint **is** the AVL path |

AVL's retained, genuine advantages: native **indirect constraints**
(`d1 PM 0`-style trim), per-section **CDCL** viscous polars, and the
**lateral-directional (roll/yaw) axis of mixed surfaces**. The compatibility
strategy that makes the switch possible: `vlm_strip_forces.py` reconstructs
**AVL-equivalent** per-strip data from VLM panels using only public,
version-stable geometry, producing a byte-compatible dict so existing consumers
work unchanged.

## Consequences

- Interactive latency collapses; no subprocess, temp directory or stdout parsing
  on the default path. `AnalysisModel` normalises all three solvers
  (`avl | aerobuildup | vortex_lattice`), so downstream code is solver-agnostic.
- **The VLM is inviscid.** `cdv`, `cm_c/4` and `cm_LE` are emitted as `0.0` and
  `C.P.x/c` as a constant `0.25` — a real fidelity loss, documented not hidden.
- **Dual-role surfaces are degraded on the default path**: the antisymmetric axis
  carries `deflection = 0`, and `compute_enrichment` warns that an AeroBuildup
  trim solved only the symmetric axis (see
  [ADR 0008](0008-control-surface-roles-decompose-into-axes.md)).
- A large AVL codebase remains on a rarely exercised path, with dead ends
  (`AvlBody`/`BFIL` never built, `.mass`/`.run` never produced, `AvlArtefact` with
  no production caller) — see
  [ADR 0021](0021-complete-but-unreachable-code-is-deleted-by-default.md).
- `aerosandbox>=4.0.7` is pinned for the VLM `Cnbeta` sign fix, so correctness now
  depends on ASB version semantics, not just API.
- The CI fast tier runs **without** AeroSandbox, so ASB-dependent service code is
  only covered when it has mocked fast tests that stub the solver boundary
  ([ADR 0015](0015-tiered-ci-fast-full-nightly.md)).

**Not chosen:** dropping AVL entirely — three capabilities have no ASB equivalent,
and AVL remains the reference the strip-force output shape is validated against.

## Related

[ADR 0004](0004-one-aero-truth-per-aircraft.md) ·
[ADR 0008](0008-control-surface-roles-decompose-into-axes.md) ·
[ADR 0015](0015-tiered-ci-fast-full-nightly.md) · domain rule BR-15.
Evidence: commits `d1f81229` (gh-674, with the measured 58 ms vs 1–3 s),
`803b0236` (gh-690), `724a9ec8` (gh-855); `app/api/utils.py:97-127` (the single
solver dispatcher); project memory `feedback_asb_over_avl`.

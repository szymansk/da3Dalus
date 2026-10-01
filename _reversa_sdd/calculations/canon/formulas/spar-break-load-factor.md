---
canon: spar-break-load-factor
entry: formula
kind: procedure
shape: law
status: draft
output: break-load-factor-positive, break-load-factor-negative
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/procedure
  - status/draft
tex: n_{break,\pm} = \min_{y}\; \frac{M_{cap,\pm}(y)}{\lvert M_{1g,\pm}(y) \rvert}
---

# Break load factor of the spar, upward and downward

**Canonical form**

```
n_break,+ = min over y:  M_cap,+(y) / |M_1g,+(y)|
n_break,- = min over y:  M_cap,-(y) / |M_1g,-(y)|
```

**Produces** [[break-load-factor-positive]] · [[break-load-factor-negative]]  ·  **from** [[airplane]] · [[aircraft-mass]] · [[gravity]]

**Kind: a procedure — an evaluation of the airplane's structure.** At every spanwise station the bending capacity of the spar actually fitted (`M_cap`, from its section and material) against the bending moment of a 1 g load (`M_1g`, from the spanwise lift distribution). The smallest ratio over the span is the load factor at which the spar breaks. Upward (`+`) and downward (`−`) separately: for a symmetric spar — a carbon tube, an I-spar with equal flanges like BRYAN's — both have the same magnitude; for an asymmetric one they differ.

**Replaces** `n_neg = −0.4 · n_lim` (deleted 2026-10-01, maintainer). That ratio came from FAR 23.337 (normal category; 0.5 aerobatic) — a statement about how often a certified aircraft is loaded downward, not about what it holds (ADR 0023). An aerobatic model flies inverted as much as upright; a trainer rarely. How much downward load a model sees is a question of its character and belongs to the evaluation, not to this core.

**Scope, by decision.** The spar only. **Attachments are ignored** — rubber bands, wing bolts, joiners and their fixings (maintainer, 2026-10-01). Strength only, no stiffness (BR-W18). `n_break` is the number RC practice reasons in and the only one verifiable on a bench: invert the wing, support at the joiner, load to `n_break · m · g` (BR-W17, `wing-design/spar-sizing/requirements.md`).

**Soll, with its execution path.** Capacity per station from the spars actually on the wing is #1139 (`reserve(y) = M_cap / M_design`, read-only verification); rectangular and capped spars — BRYAN's I-spar — need #1106 to be solved for real instead of as a rod equivalent. Whether the allowable stress already carries the resistance factor `k` is BR-W17's business (today it is pre-divided into `allowable_bending_stress_mpa`) — this entry does not decide it.

**Where it enters.** The structural edges of the V-n envelope: `n_break,+` above, `n_break,−` below, against the user's requirement `n_lim` in the Probe. The negative stall edge comes from [[inverted-max-lift-coefficient]].

**Source.** 🟢 Beam bending, `M_cap = W · sigma_allow`; the station-wise reserve is the existing sizing chain read the other way (BR-W5, #1139).

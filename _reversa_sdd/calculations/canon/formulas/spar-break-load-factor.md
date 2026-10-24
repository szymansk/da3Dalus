---
canon: spar-break-load-factor
entry: formula
kind: procedure
tool: APP
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
inputs:
  airplane: airplane
  m: aircraft-mass
  g: gravity
  rho: air-density
  v_a: maneuvering-speed
outputs: {n_break_pos: break-load-factor-positive, n_break_neg: break-load-factor-negative}
embeds: [spanwise-loads]
variables: [load-factor, flight-speed]
---

# Break load factor of the spar, upward and downward

**Canonical form**

```
M_1g,+(y) := spanwise-loads(airplane, m, g, rho; n = +1, V = V_A).M(y)    (embedded, main wing)
M_1g,-(y) := spanwise-loads(airplane, m, g, rho; n = -1, V = V_A).M(y)    (embedded, main wing)
n_break,+ = min over y:  M_cap,+(y) / |M_1g,+(y)|
n_break,- = min over y:  M_cap,-(y) / |M_1g,-(y)|
```

**Produces** [[break-load-factor-positive]] · [[break-load-factor-negative]]  ·  **from** [[airplane]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[maneuvering-speed]]

**Kind: a procedure — an evaluation of the airplane's structure.** At every spanwise station the bending capacity of the spar actually fitted (`M_cap`, from its section and material) against the bending moment of a 1 g load (`M_1g`, from the spanwise lift distribution). The smallest ratio over the span is the load factor at which the spar breaks. Upward (`+`) and downward (`−`) separately: for a symmetric spar — a carbon tube, an I-spar with equal flanges like BRYAN's — both have the same magnitude; for an asymmetric one they differ.

**The 1 g bending moments come from [[spanwise-loads]]** (maintainer, 2026-10-19, #1174): embedded and
evaluated twice, at `n = +1` and `n = −1`, both at `V = V_A`, instead of a distribution computed here —
one producer of the bending moment (ADR 0022). Load factor and speed are this entry's variables,
fixed in its form. The spanload is AVL's: main wing only, normal force only, aerodynamic load only (no
inertial relief), pitch untrimmed — see [[spanwise-loads]]. `n_break` scales each 1 g moment linearly.
**Linear scaling is an approximation, declared (ADR 0020):** on a twisted wing the spanload shape
changes with α, so the moment at `n_break·g` is not exactly `n_break` times the 1 g moment; on an
untwisted wing in attached flow it is.

**Replaces** `n_neg = −0.4 · n_lim` (deleted 2026-10-01, maintainer). That ratio came from FAR 23.337 (normal category; 0.5 aerobatic) — a statement about how often a certified aircraft is loaded downward, not about what it holds (ADR 0023). An aerobatic model flies inverted as much as upright; a trainer rarely. How much downward load a model sees is a question of its character and belongs to the evaluation, not to this core.

**Scope, by decision.** The spar only. **Attachments are ignored** — rubber bands, wing bolts, joiners and their fixings (maintainer, 2026-10-01). Strength only, no stiffness (BR-W18). `n_break` is the number RC practice reasons in and the only one verifiable on a bench: invert the wing, support at the joiner, load to `n_break · m · g` (BR-W17, `wing-design/spar-sizing/requirements.md`).

**Soll, with its execution path.** Capacity per station from the spars actually on the wing is #1139 (`reserve(y) = M_cap / M_design`, read-only verification); rectangular and capped spars — BRYAN's I-spar — need #1106 to be solved for real instead of as a rod equivalent. Whether the allowable stress already carries the resistance factor `k` is BR-W17's business (today it is pre-divided into `allowable_bending_stress_mpa`) — this entry does not decide it.

**Where it enters.** The structural edges of the V-n envelope: `n_break,+` above, `n_break,−` below, against the user's requirement `n_lim` in the Probe. The negative stall edge comes from [[inverted-max-lift-coefficient]].

**Source.** 🟢 Beam bending, `M_cap = W · sigma_allow`; the station-wise reserve is the existing sizing chain read the other way (BR-W5, #1139).

## Implementations (0)

None in aero_kernel yet; no register node is mapped to this entry.

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Regime** — holds in the RC/UAV regime (Reynolds, Mach, equipment), or the limitation is written down (ADR 0028)
- [ ] **Relation and method** — which equation it solves, and by which named method
- [ ] **Assumptions** — the conditions the method requires (bracketing, continuity, range)
- [ ] **Convergence** — the criterion, and what is returned and declared on failure
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

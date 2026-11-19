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
  components: components
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

**Produces** [[break-load-factor-positive]] · [[break-load-factor-negative]]  ·  **from** [[airplane]] · [[components]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[maneuvering-speed]]

**Kind: a procedure — an evaluation of the airplane's structure.** At every spanwise station the bending capacity of the spar actually fitted (`M_cap`, from its section and material) against the bending moment of a 1 g load (`M_1g`, from the spanwise lift distribution). The smallest ratio over the span is the load factor at which the spar breaks. Upward (`+`) and downward (`−`) separately: for a symmetric spar — a carbon tube, an I-spar with equal flanges like BRYAN's — both have the same magnitude; for an asymmetric one they differ.

**The 1 g bending moments come from [[spanwise-loads]]** (maintainer, 2026-10-19, #1174): embedded and
evaluated twice, at `n = +1` and `n = −1`, both at `V = V_A`, instead of a distribution computed here —
one producer of the bending moment (ADR 0022). Load factor and speed are this entry's variables,
fixed in its form. The spanload is AVL's: main wing only, normal force only, aerodynamic load only (no
inertial relief), pitch untrimmed — see [[spanwise-loads]]. `n_break` scales each 1 g moment linearly.
**Linear scaling is an approximation, declared (ADR 0020):** on a twisted wing the spanload shape
changes with α, so the moment at `n_break·g` is not exactly `n_break` times the 1 g moment; on an
untwisted wing in attached flow it is.

**Replaces** `n_neg = −0.4 · n_lim` (deleted 2026-10-01, maintainer). That ratio came from FAR 23.337 (normal category; 0.5 aerobatic) — a statement about how often a certified aircraft is loaded downward, not about what it holds (ADR 0028). An aerobatic model flies inverted as much as upright; a trainer rarely. How much downward load a model sees is a question of its character and belongs to the evaluation, not to this core.

**Scope, by decision.** The spar only. **Attachments are ignored** — rubber bands, wing bolts, joiners and their fixings (maintainer, 2026-10-01). Strength only, no stiffness (BR-W18). `n_break` is the number RC practice reasons in and the only one verifiable on a bench: invert the wing, support at the joiner, load to `n_break · m · g` (BR-W17, `wing-design/spar-sizing/requirements.md`).

**Soll, with its execution path.** Capacity per station from the spars actually on the wing is #1139 (`reserve(y) = M_cap / M_design`, read-only verification); rectangular and capped spars — BRYAN's I-spar — need #1106 to be solved for real instead of as a rod equivalent. Whether the allowable stress already carries the resistance factor `k` is BR-W17's business (today it is pre-divided into `allowable_bending_stress_mpa`) — this entry does not decide it.

**Where it enters.** The structural edges of the V-n envelope: `n_break,+` above, `n_break,−` below, against the user's requirement `n_lim` in the Probe. The negative stall edge comes from [[inverted-max-lift-coefficient]].

**Source.** 🟢 Beam bending, `M_cap = W · sigma_allow`; the station-wise reserve is the existing sizing chain read the other way (BR-W5, #1139).

**Validity in the RC/UAV regime (ADR 0028).** Beam bending, `M_cap = W·σ_allow`, is structural and independent of the flow regime; treating the wing skin as non-structural matches both build routes. The aerodynamic regime enters only through the 1 g spanload from [[spanwise-loads]] (AVL: inviscid, attached flow). At model Reynolds numbers local `c_l,max` is lower (Anderson §4.3), and narrow tips run at a lower Re than the root, which makes them prone to tip stall (Lennon Ch. 1–3); a distribution computed without local stall is valid only while every section stays below its own Re-dependent `c_l,max`. The declared linear scaling is exact only for an untwisted wing. Real model loads of 6–19 g lie far above FAR 23 category values, which are not regulation for models [no source: maintainer measurement].

Maintainer decisions (2026-11-19, #1427): **the kernel computes `M_cap` itself** from the airplane document, as `W · strength`, and not from a curve the app supplies. A material carries its **published breaking strength in bending** (`components.materials[key].bending_strength_pa`, Pa), and **no safety, resistance or knock-down factor is folded in anywhere** — no `j`, no `k`, no 2/3; the canon computes, it does not judge. Strength only (BR-W18): no buckling, no stiffness, no modulus of elasticity; attachments are ignored. This settles the question left open above (whether the allowable already carries `k`): in the kernel there is no `k`; BR-W17 is the app's business.

Remark (gh-1427, undated; the implementer's choices, not decisions of the maintainer — each can be reopened): the section modulus per shape is `rod: π d³/32` (exact, not the app's `d³/10`), `tube: π (D⁴−d⁴)/(32 D)`, `rectangular: b h²/6`, `capped: b (H³−h³)/(6 H)` with `h = H − 2 t`; `height` is in the airfoil thickness direction and the spar bends about the chordwise axis; for `capped` **only the flanges count, the web does not** (as the app's capped formula defines it). A spar without a `section` is valid and has no capacity. A segment's `section` is the **smallest** the spar has within that segment (the producer of the document is responsible), held constant, never interpolated. **BR-W16** (front spar bends, rear spar twists) decides how several spars combine: the capacities are *not* added; the front spar at a station is the one with the smallest `spare_position_factor` among those **present at that station** (a spar ended by `spare_start`/`spare_length` is not present; the remaining one is then the front spar); a present front spar without a section means the capacity is **unknown** — the rear spar never stands in for a present front spar. A spar that continues through several segments is read from the entry of the segment that owns the station. The spanwise extent follows the creator (`VaseModeWingCreator.py:807-819`): a partial extent in the chained modes `follow`, `standard_backward`, `orthogonal_backward` cannot be placed and fails. The spar's angle to the y axis is ignored (against the moment about the y direction that is conservative by its cosine). The function returns a typed outcome — capacity value, no spar at the station, capacity unknown — so that no caller can skip an unknown station by accident; a station outside the half span is an error. Failures, declared and never substituted (rules `spar-capacity-material`, `spar-front-determinable`, `spar-section-admissible`, `spar-extent-admissible`): a section without a material, an unknown material key, a material without a strength, a front spar that cannot be told, an extent that cannot be placed. The pure functions exist in `aero_kernel/spar_capacity.py`; the formula itself is not implemented (#1429).

## Implementations (0)

None in aero_kernel yet; no register node is mapped to this entry. The capacity function it will read is `aero_kernel/spar_capacity.py` (#1427), unreachable until #1429 (ADR 0021, rule 2).

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

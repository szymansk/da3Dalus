---
canon: maneuvering-speed
entry: formula
kind: optimization
tool: OPT
shape: law
status: draft
output: maneuvering-speed
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/optimization
  - status/draft
tex: \begin{aligned}V_A = \min_{V,\,\alpha}\; & V \\ \text{u.d.N.}\; & L(V,\alpha) = n_{lim}\,m\,g\end{aligned}
inputs:
  airplane: airplane
  m: aircraft-mass
  g: gravity
  n_lim: limit-load-factor
  rho: air-density
outputs: {v_a: maneuvering-speed}
---

# Manoeuvring speed — the corner of stall line and load limit

**Canonical form**

```
minimize over V, alpha:   V
subject to:               L(V, alpha) = n_lim * m * g
```

**Produces** [[maneuvering-speed]]  ·  **from** [[airplane]] · [[aircraft-mass]] · [[gravity]] · [[limit-load-factor]] · [[air-density]]

**Kind: an optimisation problem — the [[stall-speed]] problem bound at `n = n_lim`.** The smallest speed at which the wing can carry the limit load: below it a full pull stalls the wing before the structure reaches `n_lim`; above it a full elevator input can overstress the aircraft. RC practice knows it under this name with the rule "above V_A pull out gently" (RC-Network, *Manövergeschwindigkeit*, *Abfangen*).

**One authority.** The textbook form `V_A = V_S · sqrt(n_lim)` (FAR 23.335(c)) is this problem with the straight-flight `C_L,max`; the problem evaluates `C_L,max` at the Reynolds number of `V_A` itself — the same reason `stall-speed-in-turn` was deleted. It stays as the Probe: plugging the optimum's `C_L` into the closed form must return the same speed.

**It is only as good as `n_lim`.** The limit load factor is a user input (default 3); real models carry far more (measured 6–19 g, see the spar sizing). The statement reads: "above V_A, a full pull exceeds the load the user declared".

**Source.** 🟢 FAR 23.335(c) for the definition; the lift balance as in [[stall-speed]] (Sadraey Eq. 4.30).

**Validity in the RC/UAV regime (ADR 0028).** The relation is regime-independent: it is the [[stall-speed]] lift balance bound at `n = n_lim`, and the dynamic pressure behind it is exact below M ≈ 0.3 (Anderson §1.10.3). What bites at model scale is `C_L,max`: section `c_l,max` depends strongly on the Reynolds number while the lift slope does not (Anderson §4.3); Lennon (*Basics of R/C Model Aircraft Design*, Ch. 1–3) documents NACA 0012 `C_L,max` falling from 1.55 to 0.83 at low model Rn. The problem evaluates `C_L,max` at the Reynolds number of `V_A` itself, so it carries this effect as far as the polar does; near `C_L ≈ 1` at `Re_c ≈ 8·10⁴`, where a laminar separation bubble forms, NeuralFoil flags its prediction as low-confidence (Sharpe 2024 §7.2.4). `V_A` is exactly as meaningful as the user's `n_lim`: Sadraey's `n_max = 1.5–2` for remote-controlled models (§10.4.1) is not a measured load, and model loads have been measured at 6–19 g [no source: maintainer measurement].

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

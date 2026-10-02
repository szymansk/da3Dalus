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

---
canon: spiral-parameter
entry: formula
kind: law
tool: APP
shape: law
status: draft
output: spiral-parameter
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/law
  - status/draft
---

# Spiral parameter (Drela's B)

**Canonical form**

```
l_V, Gamma_eq, S, b := geometry(airplane)   # tail arm, (equivalent) dihedral in degrees, wing area, span
C_L = m * g / (0.5 * rho * V_md^2 * S)
B   = l_V * Gamma_eq / (b * C_L)
```

**Produces** [[spiral-parameter]]  ·  **from** [[airplane]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[minimum-drag-speed]]

**Kind: a law.** A geometric spiral-stability measure for aircraft with a tail, deterministic and
independent of any solver — the RC practice's counterpart to the spiral criterion of
[[lateral-static-stability-md]] (K27).

**Precondition.** The aircraft has a fin or a V-tail behind the wing (`l_V` is a tail arm). Not computed
for tailless aircraft.

**Values, not verdicts (A10).** Drela: B > 5 spirally stable, ≈ 5 neutral, 3–4 no difficulty for an
experienced pilot; rudder-only models V_V·B = 0.10–0.20 for roll authority. Bands belong to the evaluation.

**Dimensional check.** 🟢 balances by hand — m / m; `Γ_eq` enters as a number in degrees (Drela's definition); the checker sees a geometry extraction (procedural).

**Source.** 🟢 SOURCED — Drela, MIT 16.Unified *Design Rules*, Eqs 8–10; Beron-Rawdon, *Model Aviation*
9/1990 (equivalent dihedral for polyhedral).

**Validity at 0.5–15 kg.** Stated for RC sailplanes and models; the stability threshold is empirical.

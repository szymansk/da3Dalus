---
canon: forward-cg-limit
entry: formula
kind: procedure
tool: AB
shape: law
status: draft
output: forward-cg-limit
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/procedure
  - status/draft
---

# Forward CG limit from elevator authority

**Canonical form**

```
at the stall in landing configuration (flaps / butterfly as set, power idle), elevator at full up deflection as constructed:
  C_m,ref, C_L := AeroBuildup(airplane, x_ref, V_S0, alpha_stall)
  x_fwd = x_ref - c_MAC * C_m,ref / C_L                 (C_m is linear in the CG position)
```

**Produces** [[forward-cg-limit]]  ·  **from** [[airplane]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[stall-speed-landing]] · [[mean-aerodynamic-chord]]

**Kind: a procedure — one solver evaluation and a closed step.** The most forward CG at
which the elevator, at its full up deflection **as constructed** (a construction parameter,
like the aileron throws), can still trim the aircraft (`C_m = 0`) at the stall in landing
configuration. Because `C_m` is linear in the CG position, no optimisation is needed.

**Why this condition.** Sadraey (§11.6.3, §12.4) sets the forward limit by take-off rotation on
a tricycle gear — most models in this class have no rotation. The RC sources describe the case
that remains: not enough elevator to hold the nose up in a slow, flapped flare (Lennon). Domain
review 2026-10-02.

**A property, not a judgement (A10).** The entry reports `x_fwd`. Whether the designer's CG lies
behind it — and how far — is evaluation.

**Validity conditions, declared (ADR 0020).** (1) The horizontal tail must not itself be stalled
at that point (Sadraey Table 12.19, Eqs 12.91–12.92) — if it is, `x_fwd` is not valid and is
reported as such. (2) Ground effect is not modelled; it gives a nose-down tendency in the flare,
so the result is somewhat optimistic. (3) At model scale the tail runs at low Reynolds number;
the elevator effectiveness is only as good as NeuralFoil's flap model there.

**Source.** 🟡 PARTIAL — Sadraey §11.6.3, §12.4 for the principle; the landing-flare condition is
the RC reading (Lennon) adopted for models without rotation.

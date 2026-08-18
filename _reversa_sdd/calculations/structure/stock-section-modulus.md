---
name: stock-section-modulus
symbol: W_stock
kind: quantity
unit: mm³
cluster: structure
user_visible: false
source_status: PARTIAL
node_class: derived
tags:
  - cluster/structure
  - class/derived
  - source/partial
  - flag/anomaly
  - flag/divergence
---

# Section modulus of a real stock item

**Definition.** The bending capacity a Component-Library spar_tube stock item provides, used as the strength filter when snapping a solved piece to real stock.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
di = inner_d_mm if inner_d_mm is not None else 0.0
if di <= 0.0:
    # Solid rod: use the same formula the solver uses for required OD sizing.
    return outer_d_mm**3 / 10.0
# Hollow tube: exact section-modulus formula.
return math.pi * (outer_d_mm**4 - di**4) / (32.0 * outer_d_mm)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/spar_plan_service.py:76` — `_w_stock`

**Consumed by.**

- outside it: `app/services/spar_plan_service.py:158` · `app/services/spar_plan_service.py:202`

**Source.** 🟡 PARTIAL

> Kirch, "Hauptholm", Flugmodellbau Kirch, https://www.flugmodellbau-kirch.de/Hauptholm.htm — the rod branch (d³/10) matches the source's tabulated rod values (see `section-modulus-rod`). The TUBE branch is unattributed: no source read states W = π(Da⁴−Di⁴)/(32·Da).
>
> — via `aircraft-design-scholz (Sadraey text searched directly) + aerodynamics-expert (Anderson 6e chapter 5 title verified: "Incompressible Flow over Finite Wings") + direct verification of the kirch source`

**The source states it as.**

```
Kirch gives a rod table whose values equal d³/10 (d=3→2.7, d=5→12.5, d=6→21.6) and gives NO tube formula.
```

**⚠️ Divergence from the source.** THE CODE'S OWN CITATION IS FALSE AND MUST BE REMOVED. The docstring at app/services/spar_plan_service.py:62 reads "[Sadraey eq. 10.x / Anderson ch.5]". Both halves are refuted: (1) the string "section modulus" returns ZERO hits across the entire Sadraey text, and §10.4 is "Weight of Components" (10.4.1 Wing Weight, 10.4.2 Horizontal Tail Weight, ... 10.4.8 Other Equipment) — beam section modulus appears nowhere in Sadraey's chapter 10 or anywhere else; (2) Anderson, Fundamentals of Aerodynamics 6e, Chapter 5 is "Incompressible Flow over Finite Wings" — lifting-line and induced-drag theory, containing no beam mechanics at all. Separately, the docstring's own arithmetic contradicts its opening claim: it says "the formula unifies" and then derives "π·Da³/32 ≠ Da³/10". And the directional problem stands — here d³/10 computes what stock PROVIDES, where a 1.9% overstatement is UN-conservative, the opposite sign to _erf_w_for_piece (spar_plan_service.py:218) which uses the identical literal as a requirement and correctly calls it conservative.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Three problems. (1) Second independent producer of section_modulus_tube (app/services/spar_sizing.py:70) and section_modulus_rod (:62). (2) The cited source is unusable: 'Sadraey eq. 10.x' is a placeholder, and Anderson ch.5 is finite-wing aerodynamics, not beam section modulus. (3) The d³/10 approximation is used here to compute what stock PROVIDES, where overstating by ~1.9 % is UN-conservative — the opposite direction from _erf_w_for_piece:218, which uses the same literal as a requirement and correctly calls it conservative. The docstring's own arithmetic ('≠ Da³/10', 'π/32≈0.0982≈1/10.18') contradicts its opening claim that 'the formula unifies'.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `Tube:  W = π·(Da⁴ − Di⁴) / (32·Da)   [Sadraey eq. 10.x / Anderson ch.5]
Rod:   W = d³ / 10   (solid round, Di=0)

The formula unifies because a solid rod is a tube with Di=0:
  π·(Da⁴ − 0) / (32·Da) = π·Da³/32 ≠ Da³/10.
For a rod the standard formula (solid circular) W = π·d³/32 ≈ d³/10.05 ≈
d³/10 (the 1/10 approximation is from d³·π/32 with π/32≈0.0982≈1/10.18 but
the solver uses d³/10 throughout; we stay consistent with that convention).`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*

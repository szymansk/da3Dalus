---
name: lfop-brentq-bracket
symbol: —
kind: constant
unit: deg / iterations
cluster: aero-strips
user_visible: false
source_status: PARTIAL
node_class: unclassified-constant
tags:
  - cluster/aero-strips
  - class/unclassified-constant
  - source/partial
  - flag/divergence
---

# Brent bracket and tolerances

**Definition.** Root-search bracket [-5°, 15°] with xtol 0.05° and 30 iterations.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `-5.0, 15.0, xtol=0.05, maxiter=30`

**Formula — as the code writes it.**

```
brentq(_cl_at_alpha, -5.0, 15.0, xtol=0.05, maxiter=30)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/section_aoa_service.py:526` — `_resolve_level_flight_op`

**Consumed by.**

- 🔴 **nothing found.** A computed value nothing reads is a finding (ADR 0021).

**Source.** 🟡 PARTIAL

> Brent, Algorithms for Minimization without Derivatives (Prentice-Hall, 1973), Ch. 4 (the bracketing root-finder that scipy.optimize.brentq implements); Anderson, Fundamentals of Aerodynamics 6e, §4.12.4 (stall from boundary-layer separation)
>
> — via `aerodynamics-expert`

**The source states it as.**

```
Brent's method requires a sign change across the bracket and guarantees convergence within it
```

**⚠️ Divergence from the source.** The algorithm is properly cited; the numbers are not. The upper bracket of +15 deg lies past stall for typical sections, where AeroBuildup's CL(alpha) is no longer monotone — Brent's guarantee only covers a sign change, not uniqueness, so a post-stall root can be returned as the trim point. xtol = 0.05 deg and maxiter = 30 are unattributable.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/section_aoa_service.py:526`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*

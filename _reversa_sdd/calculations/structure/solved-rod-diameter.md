---
name: solved-rod-diameter
symbol: d
kind: quantity
unit: mm
cluster: structure
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/structure
  - class/derived
  - source/partial
  - surface/user-visible
  - flag/divergence
---

# Solved rod diameter

**Definition.** Minimum solid-round-rod diameter that provides the required section modulus. Inverse of W = d³/10.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
d = (10.0 * erf_w) ** (1.0 / 3.0)
```

**Inputs.**

- [[required-section-modulus|Required section modulus]]

**Produced by.** `app/services/spar_sizing.py:159` — `_solve_rod`

**Consumed by.**

- in this graph: `Rod cross-section area` · `Station strength-required OD`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/spar_sizing.py:160` · `app/services/spar_sizing.py:167` · `app/services/spar_sizing.py:170` · `cad_designer/airplane/geometry/spar_solver.py:768`

**Source.** 🟡 PARTIAL

> Kirch, "Hauptholm", https://www.flugmodellbau-kirch.de/Hauptholm.htm — inverse of the rod relation whose tabulated values equal d³/10 (see `section-modulus-rod`)
>
> — via `direct verification of the kirch source; rc-aircraft-designer vault has no rod sizing relation`

**The source states it as.**

```
The source does not invert. It gives a table of W(d) and a procedure (step 4: verify W_available > W_required), i.e. the designer picks a rod from the table rather than solving for d.
```

**⚠️ Divergence from the source.** The code SOLVES d = (10·erf_w)^(1/3) analytically instead of the source's select-from-stock check. Because d³/10 overstates the true W by ~1.9%, the solved d is ~0.6% SMALLER than the exact π·d³/32 inversion would give — i.e. the analytic inversion is marginally UN-conservative, the opposite sign to the source's tabulated select-and-verify workflow. Small, but it is a real reversal of the error direction the source's own procedure had.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `rod: solve d = (10·erf_w)^(1/3), check d ≤ outer`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*

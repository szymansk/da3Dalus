---
name: solved-rectangular-width
symbol: b
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
  - flag/anomaly
  - flag/divergence
---

# Solved rectangular width

**Definition.** Width of a solid rectangular spar whose height h is fixed by the section depth; the free dimension reported as solved_mm for shape='rectangular'.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
b = 6.0 * erf_w / h**2 if h > 0.0 else 0.0
```

**Inputs.**

- [[required-section-modulus|Required section modulus]]
- [[spar-outer-dimension|Spar outer dimension]]

**Produced by.** `app/services/spar_sizing.py:182` — `_solve_rectangular`

**Consumed by.**

- in this graph: `Rectangular cross-section area`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/spar_sizing.py:183` · `app/services/spar_sizing.py:344`

**Source.** 🟡 PARTIAL

> Kirch, "Hauptholm", https://www.flugmodellbau-kirch.de/Hauptholm.htm — inversion of the h→0 limit of the source's two-flange formula W = b(H³−h³)/(6H)
>
> — via `direct verification of the kirch source`

**The source states it as.**

```
Source gives only the forward form; b = 6·erf_w/h² is its inversion for the solid case.
```

**⚠️ Divergence from the source.** The source's procedure (step 5) tapers flange dimensions LINEARLY outboard from the root. The code instead re-solves b at every station independently, producing a non-linear width distribution the source's build method would not produce.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Undeclared fallback: h ≤ 0 silently yields b = 0.0 and the result is still returned with feasible=True (spar_sizing.py:185), i.e. a zero-width spar is reported as buildable. No DesignWarning (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `rectangular: h = outer, solve b = 6·erf_w / h²`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*

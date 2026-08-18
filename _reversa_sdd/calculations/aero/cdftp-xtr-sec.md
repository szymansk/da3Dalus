---
name: cdftp-xtr-sec
symbol: xtr_sec
kind: quantity
unit: x/c
cluster: aero-strips
user_visible: false
source_status: PARTIAL
code_audit: WRONG_LINE
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/partial
  - audit/wrong-line
  - flag/divergence
---

# Section trip position from the installed turbulator

**Definition.** Linearly interpolated x/c trip position between the turbulator's root and tip settings.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
xtr_sec = xtr_root + frac * (xtr_tip - xtr_root); xtr_sec = float(np.clip(xtr_sec, 0.0, 1.0))
```

**Inputs.**

- [[cdftp-frac|Span fraction of a section]]

**Produced by.** `app/services/turbulator_optimizer_service.py:689` — `compute_delta_cd0_from_turbulator_position`

🟠 **Corrected by the audit** — the extraction claimed `WRONG_LINE`. Original line was `688`. 

**Consumed by.**

- in this graph: `Tripped section drag (installed-turbulator path)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟡 PARTIAL

> RC-Network Wiki, 'Turbulator (Aerodynamik)' (turbulators are applied as tape strips, historically as wire/thread fences across the span); Anderson, Fundamentals of Aerodynamics 6e, §4.12.3 (transition location is governed by the LOCAL pressure gradient, roughness and Re)
>
> — via `rc-aircraft-designer, aerodynamics-expert`

**The source states it as.**

```
A physical turbulator strip runs as a line across the span between a root and a tip x/c
```

**⚠️ Divergence from the source.** Linear root-to-tip interpolation is a faithful model of a straight tape strip and matches the cited physical device. It is NOT a model of the aerodynamically optimal trip line, which follows the local separation/transition point and is generally non-linear in y. The clip to [0, 1] is a valid domain constraint but is applied silently.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:688-689`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*

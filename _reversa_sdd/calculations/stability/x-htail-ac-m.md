---
name: x-htail-ac-m
symbol: x_AC,H
kind: quantity
unit: m
cluster: stability
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/sourced
  - audit/confirmed
  - flag/divergence
---

# Horizontal tail aerodynamic centre x

**Definition.** Longitudinal position of the horizontal tail aerodynamic centre, at 25 % of the tail MAC aft of its leading edge.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
x_htail_ac_m = x_htail_le_m + 0.25 * htail_mac_m
```

**Inputs.**

- [[htail-mac-approx|Horizontal tail MAC (mean chord approximation)]]

**Produced by.** `app/services/tail_sizing_service.py:197` — `compute_tail_volumes`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Effective tail arm from aft CG` · `Horizontal tail moment arm`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/tail_sizing_service.py:200,213`

**Source.** 🟢 SOURCED

> Anderson, "Fundamentals of Aerodynamics" 6e §4.9 (aerodynamic centre at quarter chord); Scholz 07_WingDesign §7.1 (AC at 0.25·c_MAC aft of the MAC leading edge). Sadraey §6.6 defines the tail arm as the distance to the tail aerodynamic centre. The code's own citation 'Roskam Vol II §8.2.1' could not be verified in any consulted vault.
>
> — via `aerodynamics-expert + aircraft-design-scholz`

**The source states it as.**

```
x_AC,H = x_LE,MAC(H) + 0.25 · c_MAC(H)
```

**⚠️ Divergence from the source.** Same leading-edge reference issue as the wing (offset taken from the tail's LE x rather than the tail MAC's LE), compounded here because htail_mac_m is not the MAC but an arithmetic mean chord (see htail-mac-approx).

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `# Tail AC = leading-edge X + 25 % tail MAC (Roskam Vol II §8.2.1)`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*

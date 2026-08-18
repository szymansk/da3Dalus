---
name: x-wing-ac-m
symbol: x_AC,wing
kind: quantity
unit: m
cluster: stability
user_visible: false
source_status: SOURCED
---

# Wing aerodynamic centre x

**Definition.** Longitudinal position of the main wing aerodynamic centre, taken at 25 % MAC aft of the root leading edge.

**Formula — as the code writes it.**

```
x_wing_ac_m = float(root_le[0]) + 0.25 * (mac_m or 0.0)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/tail_sizing_service.py:424` — `build_tail_sizing_context_from_aeroplane`

**Consumed by.**

- in this graph: [[l-h-m|Horizontal tail moment arm]] · [[l-v-m|Vertical tail moment arm]]
- outside it: `app/services/tail_sizing_service.py:200,224,460`

**Source.** 🟢 SOURCED

> Anderson, "Fundamentals of Aerodynamics" 6e §4.9 — thin airfoil theory places the aerodynamic centre at the quarter-chord point. Scholz 07_WingDesign §7.1: "The aerodynamic center (AC) lies on the MAC, typically at the quarter-chord point (0.25 × c_MAC from the leading edge)." Sadraey §11.4: wing ac at 25 % MAC subsonically; §6.7.1: h_o (X_ac,wf/C̄) typically 0.20–0.25.
>
> — via `aerodynamics-expert + aircraft-design-scholz`

**The source states it as.**

```
x_AC = x_LE,MAC + 0.25 · c_MAC   (Scholz 07_WingDesign §7.1)
```

**⚠️ Divergence from the source.** The source measures the 25 % offset from the leading edge OF THE MAC. The code measures it from the ROOT leading edge (root_le[0] at tail_sizing_service.py:424). On any swept or tapered wing the MAC leading edge lies aft of the root LE, so x_wing_ac is placed too far forward, l_H is overstated and V_H with it. Sadraey §11.4 additionally notes the wing/fuselage AC differs from the wing-alone AC by the Munk shift (h_o = 0.20–0.25, i.e. up to 5 % MAC forward), which the code does not model. A second, different fallback exists at line 178 (x_wing_ac_m = 0.25·mac_m, root LE assumed at x = 0).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Uses the ROOT leading edge, not the MAC leading edge — on any swept or tapered wing the MAC's leading edge is aft of the root's, so l_H (and therefore V_H) is systematically overstated. A second, different fallback exists at line 178: `x_wing_ac_m = 0.25 * mac_m` (root LE assumed at x=0).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Wing AC: first x_sec leading-edge X + 25% MAC`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*

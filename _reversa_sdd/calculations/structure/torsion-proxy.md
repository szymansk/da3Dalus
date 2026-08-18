---
name: torsion-proxy
symbol: T(y)
kind: quantity
unit: N·m
cluster: structure
user_visible: false
source_status: NO_SOURCE_FOUND
node_class: derived
tags:
  - cluster/structure
  - class/derived
  - source/no-source-found
  - flag/anomaly
---

# Torsion proxy from bending moment

**Definition.** Estimated section torsion about the front spar when no explicit torsion distribution is supplied: a fixed fraction of the local bending moment.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
def torsion_fn(y_span: float) -> float:
    return proxy_ratio * bending_fn(y_span)
```

**Inputs.**

- [[pitching-moment-proxy-ratio|Pitching-moment proxy ratio]]
- [[front-moment-fn|Front-spar bending moment interpolator]]  — *⊣ limit*

**Produced by.** `app/services/spar_plan_service.py:450` — `_make_rear_moment_fn`

**Consumed by.**

- in this graph: `Rear-spar torsion reaction`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/spar_plan_service.py:453`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer. No source read gives any torsion-to-bending ratio. Worse, the two RC sources that address wing torsion directly do NOT support a rear spar as the torsion member: RC-Network Wiki "Torsion" (https://wiki.rc-network.de/wiki/Torsion) states torsion is carried by CLOSED sections (D-box, planked wings, shell wings, tubes) and says explicitly "without spar boxing, the wing is effectively an open section (assuming the rear wing portion carries no torsional load)"; RC-Network Wiki "Holm" says a Rohrholm "simultaneously carries bending moments and torsional loads, eliminating the need for a separate torsion-carrying skin"; Lennon Ch. 13 attributes torsion resistance to the leading-edge D-tube, not an aft spar. The project's own settled record (BR-W16, gh-1079) is what justifies the rear-spar-torsion model here — neither manufacturing route builds a D-box — and that is a project decision, not literature.`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** This proxy is ALWAYS the active path in the UI: frontend/hooks/useSparPlan.ts buildPlanBody never sends torsion_moments, so no browser-originated request can reach the explicit-T(y) branch. The response carries no marker saying the proxy was used.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `Documented proxy — when no T(y) is given, estimate T(y) ≈ ``pitching_moment_proxy_ratio`` · M(y). This keeps the rear spar torsion-driven (front ≠ rear) rather than silently a bending twin. **Follow-up:** extend #1002 to integrate section pitching moments into a real T(y) and feed it here, retiring the proxy.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*

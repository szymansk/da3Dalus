---
name: target_flap_landing_deg
kind: constant
unit: deg
cluster: perf-oppoints
user_visible: true
source_status: PARTIAL
---

# Landing flap deflection target

**Definition.** Fixed flap deflection requested for the approach and flapped-stall points before TED clipping.

**Value.** `30.0`

**Formula — as the code writes it.**

```
"flap_deflection_deg": 30.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/operating_point_generator_service.py:478` — `_build_target_definitions`

**Consumed by.**

- in this graph: [[flap_deflection_clipped_value|Clipped flap deflection]]
- outside it: `app/services/operating_point_generator_service.py:75-114` · `app/services/operating_point_generator_service.py:635-647`

**Source.** 🟡 PARTIAL

> (transport) Scholz 08_HighLift §8.2: DATCOM reference deflection for slotted flaps is 'typically 30–40°'; method valid to ~50°, and not for plain flaps beyond ~40°. (RC) Lennon: '40° deflection — full landing flap'. Sadraey §12.2/§5.12: plain flap ΔCl ≈ 0.7–0.9 at ~60°.
>
> — via `aircraft-design-scholz, rc-aircraft-designer`

**The source states it as.**

```
delta_f,L ≈ 30–40° (slotted) / 40° (RC landing)
```

**⚠️ Divergence from the source.** 30° is at the low edge of the transport band and 10° below the RC-scale landing recommendation. Like the takeoff value it is type-independent, whereas both sources make the required deflection a function of flap type.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*

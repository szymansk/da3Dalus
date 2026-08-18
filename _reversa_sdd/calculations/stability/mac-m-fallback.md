---
name: mac-m-fallback
symbol: —
kind: constant
unit: m
cluster: stability
user_visible: false
source_status: NO_SOURCE_FOUND
---

# MAC fallback

**Definition.** MAC used when the context value is missing or non-positive.

**Value.** `0.30`

**Formula — as the code writes it.**

```
mac_m: float = float(mac_m_raw) if mac_m_raw and float(mac_m_raw) > 0 else 0.30
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/sm_sizing_service.py:138` — `_dsm_dx_wing`

**Consumed by.**

- in this graph: [[delta-x-clipped|Clipped wing shift]] · [[dsm-dsh|SM sensitivity to horizontal tail area]] · [[dsm-dx-wing|SM sensitivity to wing longitudinal shift]] · [[l-h-m-fallback|Tail arm fallback]] · [[sm-at-aft|Static margin at aft CG]] · [[sm-at-fwd-after-shift|Forward-CG SM after wing shift]] · [[sm-fwd|Static margin at forward CG]] · [[sm-max-fwd|Maximum forward-CG static margin]]
- outside it: `app/services/sm_sizing_service.py:138,154,600,640,678,706`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** 0.30 m is a plausible RC-model MAC but is not attributable to any source; it is an arbitrary stand-in repeated six times as an inline literal. The MAC itself is computable from Scholz 07_WingDesign §7.1 (c_MAC = (2/3)c_r(1+λ+λ²)/(1+λ)), so a fallback is avoidable in principle.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The same magic literal is repeated six times as an inline default rather than a named constant. Docstring claims it is only for unit-test paths, but lines 600, 640, 678 and 706 are production option-builders.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `Callers in suggest_corrections / apply_* are guarded by _is_not_applicable,
so mac_m is always valid there.  The fallback covers unit-test call paths.`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*

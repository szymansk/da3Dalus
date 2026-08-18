---
name: vtail-mac-approx
symbol: c_V
kind: quantity
unit: m
cluster: stability
user_visible: false
source_status: SOURCED
---

# Vertical tail MAC (mean chord approximation)

**Definition.** Stands in for the vertical tail mean aerodynamic chord.

**Formula — as the code writes it.**

```
vtail_mac_m = _wing_mac_approx(vtail)
```

**Inputs.** [[htail-mac-approx|Horizontal tail MAC (mean chord approximation)]]

**Produced by.** `app/services/tail_sizing_service.py:446` — `build_tail_sizing_context_from_aeroplane`

**Consumed by.**

- in this graph: [[l-v-m|Vertical tail moment arm]]
- outside it: `app/services/tail_sizing_service.py:467` · `app/services/tail_sizing_service.py:223 (x_vtail_ac_m)`

**Source.** 🟢 SOURCED

> Scholz HAW Hamburg, 07_WingDesign §7.1 (MAC definition, as above), applied to the vertical surface; Sadraey §6.7 uses the vertical-tail MAC to place its aerodynamic centre.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
c_MAC = (2/S)·∫₀^(b/2) c² dy  ;  tapered: (2/3)·c_r·(1+λ+λ²)/(1+λ)
```

**⚠️ Divergence from the source.** Identical misnaming and identical error to htail-mac-approx — it is the arithmetic mean chord, not the MAC.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Same misnaming as htail-mac-approx.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*

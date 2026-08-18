---
name: s_ref
symbol: S_ref
kind: quantity
unit: m²
cluster: perf-oppoints
user_visible: false
source_status: SOURCED
---

# Reference wing area

**Definition.** Reference area taken from the ASB airplane for CL_target.

**Formula — as the code writes it.**

```
s_ref = float(getattr(asb_airplane, "s_ref", 0.0) or 0.0)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/operating_point_generator_service.py:885` — `_trim_or_estimate_point`

**Consumed by.**

- in this graph: [[cl_target|Target lift coefficient]]
- outside it: `app/services/operating_point_generator_service.py:794-797`

**Source.** 🟢 SOURCED

> AeroSandbox 4.2 Airplane data structure: 's_ref, c_ref, b_ref are the reference area / chord / span used to nondimensionalize coefficients. If not specified, they are auto-computed from the first wing.'
>
> — via `aerosandbox-expert`

**The source states it as.**

```
s_ref = area of wings[0] when not explicitly set
```

**⚠️ Divergence from the source.** The AeroSandbox documentation confirms the inventory's anomaly as a real defect, not a suspicion: reading airplane.s_ref takes the FIRST wing's area, not the main wing's. For a tail-first geometry CL_target is wrong by the ratio S_tail/S_wing (potentially ~8×), and every trim solved against it is wrong. app/services/assumption_compute_service.py:1046 documents this exact trap and works around it with _select_main_wing; the OPG does not.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** asb.Airplane.s_ref defaults to the FIRST wing's area, not the main wing (documented in assumption_compute_service.py:1046-1055 _select_main_wing); a tail-first geometry yields a wrong CL_target here.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*

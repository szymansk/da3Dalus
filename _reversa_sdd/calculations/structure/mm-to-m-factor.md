---
name: mm-to-m-factor
kind: constant
unit: m/mm
cluster: structure
user_visible: false
source_status: SOURCED
---

# Millimetre-to-metre conversion factor

**Definition.** Converts the solver's millimetre plan lengths into the metre unit of the API response.

**Value.** `0.001`

**Formula — as the code writes it.**

```
_MM_TO_M = 0.001
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/spar_plan_service.py:32` — `_MM_TO_M`

**Consumed by.**

- in this graph: [[piece-y-end|Spar piece tip spanwise position]] · [[piece-y-start|Spar piece root spanwise position]] · [[subsegment-lengths-m|Post-split sub-segment lengths]]
- outside it: `app/services/spar_plan_service.py:498-516` · `app/services/spar_plan_service.py:650` · `app/services/spar_plan_service.py:653` · `app/services/spar_insert_service.py:53`

**Source.** 🟢 SOURCED

> BIPM, The International System of Units (SI), 9th edition 2019, §3.1 Table 7 — SI prefixes: milli = 10⁻³
>
> — via `none required (SI definition)`

**⚠️ Anomaly.** Two producers of the same conversion constant: app/services/spar_plan_service.py:32 and app/services/spar_insert_service.py:53.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*

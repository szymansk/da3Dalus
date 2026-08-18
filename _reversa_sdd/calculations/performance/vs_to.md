---
name: vs_to
symbol: V_s,TO
kind: quantity
unit: m/s
cluster: perf-oppoints
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-oppoints
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
---

# Takeoff-config stall speed reference

**Definition.** Takeoff-configuration stall speed, falling back to the clean value.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
vs_to = _pick("v_s_to_mps") or vs_clean ... "vs_to": max(2.5, vs_to)
```

**Inputs.**

- [[vs_clean|Clean stall speed reference]]

**Produced by.** `app/services/operating_point_generator_service.py:355` — `_estimate_reference_speeds`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `takeoff_climb target speed`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/operating_point_generator_service.py:402 (takeoff velocity)`

**Source.** 🟡 PARTIAL

> Scholz, Flugzeugentwurf, 05_PreliminarySizing §5.2 — CL_max,TO is the takeoff-configuration maximum lift coefficient (typically 15–25° flap), distinct from CL_max,L; V_S,TO follows from Eq. 4.30 with CL_max,TO
>
> — via `aircraft-design-scholz`

**⚠️ Divergence from the source.** The quantity is standard. Falling back to the clean value when no takeoff polar exists understates the benefit of flaps and makes V_takeoff = 1.25·V_S1 instead of 1.25·V_S,TO — conservative, but silent (no warning).

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*

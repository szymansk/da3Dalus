---
name: fe_dive_factor
symbol: 1.4
kind: constant
unit: -
cluster: perf-envelope
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: regulatory-constant
tags:
  - cluster/perf-envelope
  - class/regulatory-constant
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Dive-speed factor

**Definition.** Multiplier converting maximum level speed into design dive speed.

**Regulatory constant.** Taken from a standard. It carries the clause *and* the class of aircraft that clause applies to.

**Value.** `1.4`

**Formula — as the code writes it.**

```
v_dive = 1.4 * v_max_mps
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/flight_envelope_service.py:315` — `compute_vn_curve`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Cruise speed (back-derived)` · `Dive speed` · `KPI: dive speed`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🔴 NO SOURCE FOUND

> 1.4 is not attributable. Nearest regulatory anchor is FAR 23.335(b)(1) / CS-VLA 335(b): V_D >= 1.25*V_C — a different factor applied to a different base speed.
>
> — via `scholz, rc`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Two independent defects. (a) The factor: 1.4 has no source; 1.25 does. (b) The base: the regulation scales V_D from V_C, the code scales it from V_max. RC vault gives no VNE-to-V_max convention either (RC-Network 'Manoevergeschwindigkeit' discusses V_A qualitatively only). The same 1.4 lives in assumption_compute_service._compute_v_dive documented as 'heuristic (gh-476)' — one of the two copies is honest about being a guess, the other is silent. Make the honest label the shared one.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Magic number with no citation in this file. assumption_compute_service._compute_v_dive carries the same 1.4 and documents it as 'heuristic (gh-476)' — the constant exists twice with only one of the two documented.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*

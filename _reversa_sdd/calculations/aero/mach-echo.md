---
name: mach-echo
symbol: M
kind: quantity
unit: -
cluster: aero-spanwise
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/aero-spanwise
  - class/derived
  - source/partial
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Mach number echo

**Definition.** Mach number echoed from the solver result, defaulting to 0.

**Derived quantity.** Computed from the inputs below.

**Value.** `0`

**Formula — as the code writes it.**

```
mach=avl_result.get("mach", 0)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:1755` — `_build_strip_forces_response`

**Consumed by.**

- outside it: `StripForcesResponse.mach` · `frontend AnalysisViewerPanel.tsx:582`

**Source.** 🟡 PARTIAL

> Scholz 05_PreliminarySizing §5.6.2 (M = V/a, a² = γ·R·T, a₀ = 340.3 m/s at T = 288.15 K)
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
M = V/a
```

**⚠️ Divergence from the source.** The quantity is sourced; the default 0 when the solver dict has no 'mach' key is not. The UI prints 'Mach = 0.000' as though computed. For RC/UAV speeds (M < 0.1) the true value is small but never exactly zero.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Defaults to 0 when the solver dict has no 'mach' key, and the UI prints 'Mach = 0.000' as though it were computed.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*

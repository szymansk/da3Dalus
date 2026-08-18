---
name: cdftp-section-skip-warnings
symbol: all_warnings
kind: quantity
unit: n/a
cluster: aero-strips
user_visible: false
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/no-source-found
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Per-section failure warnings

**Definition.** Warning strings emitted when an airfoil build fails or cd is NaN for a section.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
msg = f"Turbulator ΔCD0: NaN cd at y={sec.y_m:.3f}m (Re={sec.re_local:.0f}, CL={sec.cl:.3f}, xtr={xtr_sec:.3f})"
```

**Inputs.**

- [[cdftp-cd-clean|Clean section drag (installed-turbulator path)]]
- [[cdftp-cd-tripped|Tripped section drag (installed-turbulator path)]]

**Produced by.** `app/services/turbulator_optimizer_service.py:702` — `compute_delta_cd0_from_turbulator_position`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/assumption_compute_service.py:2148 (logger.warning only)`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Diagnostic strings, no formula to source. The finding stands: they reach only logger.warning, so the recompute path shows an adjusted cd0 with no indication that sections were dropped from the integral.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** These warnings are only logged, never surfaced as a DesignWarning on the recompute path, so the user sees an adjusted cd0 with no indication that sections were skipped (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:696-706`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*

---
name: divide-guard-epsilon
kind: constant
unit: -
cluster: aero-spanwise
user_visible: false
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: numerical-tolerance
tags:
  - cluster/aero-spanwise
  - class/numerical-tolerance
  - source/no-source-found
  - audit/confirmed
  - flag/anomaly
---

# Division guard epsilon

**Definition.** Threshold below which \|CD\| (or \|D\|) is treated as zero so the ratio becomes NaN.

**Numerical tolerance.** A solver or comparison epsilon, not a domain value. ADR 0023 does not apply.

**Value.** `1e-12`

**Formula — as the code writes it.**

```
np.abs(cd) > 1e-12
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:108` — `_compute_cl_cd_points`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Drag at zero lift point` · `Lift-to-drag ratio (coefficient form)` · `Glide ratio from forces`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🔴 NO SOURCE FOUND

> Pure floating-point guard; no aerodynamic literature basis. Repeated verbatim at analysis_service.py:108, 149, 198, 1154.
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** Magic number, NO_SOURCE_FOUND; repeated verbatim at lines 108, 149, 198, 1154.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*

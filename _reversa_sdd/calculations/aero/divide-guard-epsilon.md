---
name: divide-guard-epsilon
kind: constant
unit: -
cluster: aero-spanwise
user_visible: false
source_status: NO_SOURCE_FOUND
---

# Division guard epsilon

**Definition.** Threshold below which \|CD\| (or \|D\|) is treated as zero so the ratio becomes NaN.

**Value.** `1e-12`

**Formula — as the code writes it.**

```
np.abs(cd) > 1e-12
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:108` — `_compute_cl_cd_points`

**Consumed by.**

- in this graph: [[drag-at-zero-lift-point|Drag at zero lift point]] · [[ld-ratio-coefficient|Lift-to-drag ratio (coefficient form)]] · [[ld-ratio-force|Glide ratio from forces]]

**Source.** 🔴 NO SOURCE FOUND

> Pure floating-point guard; no aerodynamic literature basis. Repeated verbatim at analysis_service.py:108, 149, 198, 1154.
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** Magic number, NO_SOURCE_FOUND; repeated verbatim at lines 108, 149, 198, 1154.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*

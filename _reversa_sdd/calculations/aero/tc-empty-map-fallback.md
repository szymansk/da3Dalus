---
name: tc-empty-map-fallback
kind: constant
unit: -
cluster: aero-spanwise
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/aero-spanwise
  - class/unclassified-constant
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
---

# Empty thickness-map fallback

**Definition.** When no station thickness resolves, empty maps are returned so the spar service applies its own t/c fallback.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Formula — as the code writes it.**

```
if not thickness_by_y: return {}, {}
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:2248` — `_get_tc_by_y_for_surface`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `compute_spar_sizing`

**Source.** 🔴 NO SOURCE FOUND

> Silent degradation to the downstream 0.12 default has no source. Since EI ∝ h³ (Scholz §7.4), substituting t/c changes the required spar dimension by the cube root of the ratio — a real sizing error delivered with only a per-station log warning (ADR 0020).
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** Silent geometry-failure path: cadquery unavailable or wing not found degrades every station to the 0.12 default with only a per-station log warning from the spar service.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*

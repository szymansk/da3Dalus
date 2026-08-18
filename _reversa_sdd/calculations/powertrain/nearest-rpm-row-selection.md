---
name: nearest-rpm-row-selection
symbol: nearest_rpm
kind: quantity
unit: rpm
cluster: powertrain
user_visible: false
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/no-source-found
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Nearest-RPM polar row group

**Definition.** The polar RPM group closest to the operating RPM; only its rows are used for the Ct/Cp interpolation.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
rpms = sorted({s.rpm for s in request.polar_samples}) ; nearest_rpm = min(rpms, key=lambda r: abs(r - point_rpm)) ; rpm_rows = [s for s in request.polar_samples if s.rpm == nearest_rpm]
```

**Inputs.**

- [[curve-prop-rpm|Fixed operating RPM (non-QPROP branch)]]
- [[qprop-rpm-solution|Solved operating RPM]]  — *⊣ limit*

**Produced by.** `app/services/powertrain_performance.py:738` — `compute_performance_curve`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/powertrain_performance.py:743`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `rc-aircraft-designer`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**The source states it as.**

```
Brandt & Selig, AIAA 2011-1255, §III: 'Reynolds number strongly affects eta; low-Reynolds-number propellers (Re_c ~ 50,000-100,000 at the 75% span station) experience degradation in efficiency.' Deters/Ananda/Selig 2014 §VI: 'As Reynolds number increases along a given propeller design, thrust coefficient rises and power coefficient decreases.'
```

**⚠️ Divergence from the source.** Snapping to the nearest measured RPM group rather than interpolating between them is an implementation choice with no source. Both sources state that C_T and C_P vary systematically with RPM (through Reynolds number) — Deters reports the GWS 5x4.3 eta_max moving from ~62% to ~66% across RPM groups — so the snap discards a documented, monotonic trend and reports no measure of how far it snapped.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Snaps to the nearest RPM group with no interpolation between RPM groups and no warning about how far the snap was — a silent substitution (ADR 0020). The same three-line block is written three times (lines 396-399, 459-462, 736-739).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `interpolate_ct_cp_pe docstring: "compute_prop_operating_point and compute_performance_curve each pre-filter by nearest RPM before calling this helper when they know the operating RPM."`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*

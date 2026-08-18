---
name: tos-result-placeholder-geometry
symbol: y_m, chord_m, section_area_m2
kind: constant
unit: m / m / m²
cluster: aero-strips
user_visible: false
source_status: NO_SOURCE_FOUND
---

# Placeholder y/chord/area in the raw section result

**Definition.** optimize_section_xtr always returns y_m, chord_m and section_area_m2 as 0.0.

**Value.** `0.0`

**Formula — as the code writes it.**

```
y_m=0.0, chord_m=0.0, … section_area_m2=0.0,
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/turbulator_optimizer_service.py:276` — `optimize_section_xtr`

**Consumed by.**

- outside it: `app/services/turbulator_optimizer_service.py:run_turbulator_optimizer (overwrites them)`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Placeholder zeros in fields named y_m / chord_m / section_area_m2. Not a modelling choice; a direct-caller trap, since section_area_m2 = 0 makes the delta_cd0 area weighting vanish.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Fields named y_m/chord_m/section_area_m2 never carry their namesake values here; if a caller used optimize_section_xtr directly the ΔCD0 weighting would be zero.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:242-252,276-286`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*

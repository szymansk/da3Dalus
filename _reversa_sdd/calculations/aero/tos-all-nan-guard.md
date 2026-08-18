---
name: tos-all-nan-guard
symbol: finite_mask
kind: quantity
unit: n/a
cluster: aero-strips
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
---

# All-NaN sweep guard

**Definition.** When every cd in the sweep is NaN the section returns NaN optima with an explicit warning.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
finite_mask = np.isfinite(cd_values); if not finite_mask.any(): …
```

**Inputs.**

- [[tos-cd-values|cd sweep over the trip grid]]

**Produced by.** `app/services/turbulator_optimizer_service.py:235` — `optimize_section_xtr`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `SectionOptimizerResult.warnings`

**Source.** 🟡 PARTIAL


**⚠️ Divergence from the source.** Declared-failure guard with an explicit warning — this is the ADR 0020-compliant path and the correct pattern; the other fallbacks in the same module are not. No external source needed.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:235-252`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*

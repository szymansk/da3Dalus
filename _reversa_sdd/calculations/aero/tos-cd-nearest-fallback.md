---
name: tos-cd-nearest-fallback
symbol: cd
kind: quantity
unit: dimensionless
cluster: aero-strips
user_visible: false
source_status: NO_SOURCE_FOUND
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/no-source-found
  - flag/anomaly
  - flag/divergence
---

# Nearest-neighbour cd fallback

**Definition.** When the target CL lies outside the finite polar band, the nearest polar cd is returned.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
nearest = int(np.argmin(np.abs(cl_sorted - cl_target))); return float(cd_sorted[nearest])
```

**Inputs.**

- [[tos-cd-at-cl|Section cd at a target CL and trip position]]

**Produced by.** `app/services/turbulator_optimizer_service.py:173` — `_cd_at_cl_xtr`

**Consumed by.**

- 🔴 **nothing found.** A computed value nothing reads is a finding (ADR 0021).

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** No source supports substituting a nearest-neighbour cd for an out-of-range cl. Physically it reports the drag at a DIFFERENT lift coefficient than requested, which then propagates into delta_cd and delta_cd0. Logged at DEBUG only.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Undeclared fallback: an out-of-range CL substitutes a nearest-neighbour cd and only logs at DEBUG level — nothing reaches the response warnings (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:165-173`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*

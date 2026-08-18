---
name: hand_throw_floor
symbol: k_throw_min
kind: constant
unit: dimensionless
cluster: perf-matching
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Hand-launch physics floor

**Definition.** Minimum throw speed as a multiple of V_S below which hand launch is rejected.

**Value.** `1.10`

**Formula — as the code writes it.**

```
_HAND_THROW_FLOOR: float = 1.10
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/field_length_service.py:108` — `_HAND_THROW_FLOOR`

**Consumed by.**

- in this graph: [[v_throw_floor|Hand-launch minimum throw speed]]
- outside it: `compute_field_lengths:378,384 (raises ServiceException)`

**Source.** 🔴 NO SOURCE FOUND

> Scholz and Sadraey have no hand-launch model at all. The only 'catapult' references in the vault are carrier aviation (sadraey-tricycle-gear, sadraey-landing-gear-weight-equation); there is no launch-assist chapter.
>
> — via `aircraft-design-scholz (confirmed gap: no hand-launch coverage)`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Labelled a 'physics floor' with no reference. It is a mission choice, not a derived limit, and should be presented as such.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** NO_SOURCE_FOUND for 1.10 — labelled a 'physics floor' but no reference given.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# physics floor (must be ≥ 1.10·V_S)`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*

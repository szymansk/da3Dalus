---
name: hand_throw_floor
symbol: k_throw_min
kind: constant
unit: dimensionless
cluster: perf-matching
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/perf-matching
  - class/unclassified-constant
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Hand-launch physics floor

**Definition.** Minimum throw speed as a multiple of V_S below which hand launch is rejected.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `1.10`

**Formula — as the code writes it.**

```
_HAND_THROW_FLOOR: float = 1.10
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/field_length_service.py:108` — `_HAND_THROW_FLOOR`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Hand-launch minimum throw speed`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
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

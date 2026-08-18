---
name: hand_launch_ws_max
symbol: (W/S)_max,HL
kind: constant
unit: N/m^2
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

# Hand-launch W/S ceiling

**Definition.** Upper wing-loading bound considered safe for a hand throw.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `80.0`

**Formula — as the code writes it.**

```
_HAND_LAUNCH_WS_MAX: float = 80.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/matching_chart_service.py:589` — `_HAND_LAUNCH_WS_MAX`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `_hand_launch_constraint:598` · `constraints 'Hand-Launch':1184`

**Source.** 🔴 NO SOURCE FOUND

> No hand-launch model in Scholz or Sadraey (confirmed gap). In-code attribution to a 'Lennon practical rule of thumb' is unverified and would in any case be hobbyist-tier.
>
> — via `aircraft-design-scholz (confirmed gap)`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Also inert: 'hand_launch' appears in no _PROFILE_CONSTRAINT_MAP value, so for every known profile the constraint is tagged applicable_for_profile=False and never drawn (ADR 0021).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Emitted only when mode == 'rc_hand_launch', yet 'hand_launch' appears in no _PROFILE_CONSTRAINT_MAP value — so for every known profile the constraint is tagged applicable_for_profile=False and never drawn.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Hand-launch upper W/S bound — Lennon practical rule of thumb.`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*

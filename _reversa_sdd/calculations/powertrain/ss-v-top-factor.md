---
name: ss-v-top-factor
symbol: 1.4
kind: constant
unit: dimensionless
cluster: powertrain
user_visible: true
source_status: SOURCED
code_audit: WRONG_FORMULA
node_class: unclassified-constant
tags:
  - cluster/powertrain
  - class/unclassified-constant
  - source/sourced
  - surface/user-visible
  - audit/wrong-formula
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# Top-speed derivation factor

**Definition.** Multiplier applied to cruise speed to derive top speed when the user does not supply one.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `1.4`

**Formula — as the code writes it.**

```
v_top_mps = v_cruise_mps * 1.4
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_solution_space_service.py:336` — `compute_solution_space`

🟠 **Corrected by the audit** — the extraction claimed `WRONG_FORMULA`. Line 336 is the assignment only; the if is on line 335

**Consumed by.**

- in this graph: `Top speed used for peak sizing`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_solution_space_service.py:350` · `app/services/powertrain_solution_space_service.py:392`

**Source.** 🟢 SOURCED

> Sadraey, Aircraft Design: A Systems Engineering Approach (Wiley 2013), §4.6 (inputs to Eq. 4.56): 'V_max. Given, or V_max ~ 1.2-1.3 V_C if only cruise speed is specified (cruise is at 75-80% power).'
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
V_max ~ 1.2-1.3 x V_C
```

**⚠️ Divergence from the source.** The code uses 1.4, which is ABOVE Sadraey's 1.2-1.3 range. This matters more than the 8-17% speed difference suggests: Sadraey's own note under Eq. 4.56 is that 'a 10% increase in V_max requires roughly 33% more power' because of the cubic V_max^3 term. Taking 1.4 instead of 1.3 therefore inflates the peak-power sizing point by roughly 25%, and against 1.2 by roughly 59%. Every downstream peak quantity (P_top, I_peak, C_min, ESC_min, KV) carries that inflation.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Sadraey's 1.2-1.3 heuristic is derived from transport aircraft cruising at 75-80% power. RC and UAV aircraft in the 0.5-15 kg class are commonly flown at much lower cruise power fractions, so the ratio is not transferable without validation at this scale (ADR 0023). No RC-scale equivalent was found: Lennon Ch. 18 offers only 'add ~25% for climb and maneuvers' over the minimum level-flight speed, which would imply a factor nearer 1.25.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Magic number that drives the entire peak-power branch: P_aero scales roughly as V^3, so 1.4 sets the peak/cruise power ratio at ~2.7x with no stated justification. Marked 'spec default' where the spec is an internal design doc, not a reference (ADR 0023).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# spec default — the referenced spec is docs/superpowers/specs/2026-06-13-powertrain-solution-space-design.md; NO_SOURCE_FOUND for a literature basis`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*

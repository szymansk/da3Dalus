---
name: differential-ratio
symbol: —
kind: parameter
unit: – (ratio)
cluster: stability
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: unclassified-parameter
tags:
  - cluster/stability
  - class/unclassified-parameter
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Aileron differential ratio

**Definition.** Ratio by which the up-going side's throw is scaled relative to the down-going side.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `1.0`

**Formula — as the code writes it.**

```
diff = float(getattr(ted, "differential_ratio", 1.0) or 1.0)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/trim_enrichment_service.py:252` — `build_mix_params_from_schema`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Mixer left/right physical deflections`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/trim_enrichment_service.py:255,260,303,315,317,325`

**Source.** 🟢 SOURCED

> Lennon, "Basics of R/C Model Aircraft Design" (1996) Ch. 10 — Aileron Differential: "the upgoing aileron's angular travel is set to two to three times that of the downgoing aileron"; the author's own modified-Frise setup uses 2.5:1 (25° up, 10° down). Rationale: adverse yaw, because "the downgoing aileron generates more drag than the upgoing aileron." Corroborated: Sadraey §12.4 (aileron design, adverse yaw).
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
up-travel : down-travel = 2:1 to 3:1 (Lennon Ch. 10); 2.5:1 typical
```

**⚠️ Divergence from the source.** Two divergences. (a) Default: the code defaults to 1.0, i.e. NO differential — Lennon's whole point is that equal throws produce adverse yaw, and he reports that with proper differential "turns can be made without use of rudder." (b) Scope: the code marks it 'reporting-only', so it changes the displayed left/right angles but is never fed back into the aerodynamic solve — the displayed deflections do not correspond to the aerodynamics that produced the trim. Also, `or 1.0` overrides a legitimately stored 0.0.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Explicitly 'reporting-only' — it changes the reported left/right angles but is not fed back into the aerodynamic solve, so the displayed deflections do not correspond to the aerodynamics that produced the trim.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `the (reporting-only) differential
ratio scales the up-going side`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*

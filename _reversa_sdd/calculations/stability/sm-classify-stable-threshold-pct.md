---
name: sm-classify-stable-threshold-pct
symbol: —
kind: constant
unit: % MAC
cluster: stability
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/stability
  - class/unclassified-constant
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
---

# Stable/neutral boundary

**Definition.** Static margin percent above which the aircraft is labelled 'stable'.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `5`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/stability_service.py:77` — `classify_stability`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Stability classification (static margin band)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/stability_service.py:77`

**Source.** 🟢 SOURCED

> Lennon, "Basics of R/C Model Aircraft Design" (Air Age 1996) Ch. 6 — CG Location: "The minimum suggested margin is 5 percent (CG at 30 percent MAC)". Corroborated: rcplanedesigner.com, "Airplane Balance — Finding the First-Flight CG" § Center of Gravity and Static Margin — "place the CG at least 5% of MAC ahead of the neutral point"; mission table gives Trainer minimum 5 % MAC.
>
> — via `rc-aircraft-designer`

**⚠️ Anomaly.** Magic number with no source. Inline literal, not a named constant, unlike every other threshold in this cluster.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*

---
name: sm-classify-stable-threshold-pct
symbol: —
kind: constant
unit: % MAC
cluster: stability
user_visible: true
source_status: SOURCED
---

# Stable/neutral boundary

**Definition.** Static margin percent above which the aircraft is labelled 'stable'.

**Value.** `5`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/stability_service.py:77` — `classify_stability`

**Consumed by.**

- in this graph: [[stability-class|Stability classification (static margin band)]]
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

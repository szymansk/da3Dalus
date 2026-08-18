---
name: min-static-margin-pct-default
symbol: min_margin
kind: parameter
unit: % MAC
cluster: stability
user_visible: true
source_status: SOURCED
node_class: unclassified-parameter
tags:
  - cluster/stability
  - class/unclassified-parameter
  - source/sourced
  - surface/user-visible
  - flag/anomaly
---

# Minimum static margin (CG-range default)

**Definition.** Lower static-margin bound used to place the aft CG limit. Read from a design_assumptions row named 'min_static_margin', otherwise this default.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `5.0`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/stability_service.py:229` — `_get_margin_bounds`

**Consumed by.**

- in this graph: `Aft CG limit from margin bounds`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/stability_service.py:254,331,334` · `app/services/stability_service.py:87 (same literal repeated as compute_cg_range default)`

**Source.** 🟢 SOURCED

> Lennon, "Basics of R/C Model Aircraft Design" (1996) Ch. 6 — minimum suggested static margin 5 % MAC. Corroborated: rcplanedesigner.com "Airplane Balance — Finding the First-Flight CG" (Trainer minimum 5 %, first-flight floor 5 % MAC); Scholz 10_BoxWingSystematic §4.2 ("Typical stability margin requirement: 5-10% mean aerodynamic chord").
>
> — via `rc-aircraft-designer + aircraft-design-scholz`

**⚠️ Anomaly.** No writer for the 'min_static_margin' parameter anywhere in the repo, and no such row in db/test.db — the DB lookup at :231-238 can never return a row, so the default is the only value ever used. The same literal is also hardcoded a second time at :87.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*

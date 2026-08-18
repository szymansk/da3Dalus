---
name: inch-to-metre
symbol: 0.0254
kind: constant
unit: m/in
cluster: powertrain
user_visible: false
source_status: PARTIAL
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/powertrain
  - class/unclassified-constant
  - source/partial
  - audit/confirmed
---

# Inch-to-metre conversion factor

**Definition.** Converts propeller diameter from the catalog's inches to metres.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.0254`

**Formula — as the code writes it.**

```
D_m = request.propeller_diameter_in * 0.0254  # inches → metres
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_performance.py:646` — `compute_performance_curve`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Propeller diameter in metres`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_performance.py:733` · `app/services/powertrain_performance.py:748` · `app/services/powertrain_performance.py:756`

**Source.** 🟡 PARTIAL

> Roxxy Motoren-Fibel, Ch. 1, pp. 6-7 establishes that RC propellers are specified as Diameter x Pitch in inches ('a 10 x 5 propeller has a 10-inch diameter and a 5-inch pitch'), so the conversion is required. The factor 0.0254 m/in itself is the exact international inch (1959 international yard-and-pound agreement) and is not stated in any consulted expert source.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
1 in = 0.0254 m exactly
```

**Cited in the code itself.** `# inches → metres`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*

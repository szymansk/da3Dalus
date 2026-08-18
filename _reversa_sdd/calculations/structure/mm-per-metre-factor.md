---
name: mm-per-metre-factor
kind: constant
unit: mm/m
cluster: structure
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/structure
  - class/unclassified-constant
  - source/sourced
  - audit/confirmed
---

# Metre-to-millimetre conversion factor

**Definition.** Converts the design bending moment from N·m to N·mm so that dividing by σ in N/mm² yields mm³.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `1000.0`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/spar_sizing.py:88` — `required_section_modulus`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Required section modulus`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/spar_sizing.py:88`

**Source.** 🟢 SOURCED

> BIPM, The International System of Units (SI), 9th edition 2019, §3.1 Table 7 — SI prefixes: milli = 10⁻³
>
> — via `none required (SI definition, not an engineering constant)`

**The source states it as.**

```
1 m = 1000 mm by definition of the SI prefix milli.
```

**Cited in the code itself.** `erf_W = M_design [N·m] × 1000 [mm/m] / σ_allow [N/mm²]`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*

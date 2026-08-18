---
name: structure--safety-factor-j
symbol: j
kind: parameter
unit: dimensionless
cluster: structure
user_visible: true
source_status: SOURCED
code_audit: NOT_VERIFIED
node_class: unclassified-parameter
tags:
  - cluster/structure
  - class/unclassified-parameter
  - source/sourced
  - surface/user-visible
  - audit/not-verified
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# Safety factor j

**Definition.** Multiplier applied on top of the limit load factor to form the design moment.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `1.5`

**Formula — as the code writes it.**

```
safety_factor_j: float = Field(
    1.5,
    gt=0,
    description="Safety factor applied to M_design = |M(y)| · g_limit · j.",
)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/schemas/spar_sizing.py:33` — `SparSizingParams.safety_factor_j`

⚪ **Not verified.** This node was not covered by the audit pass; treat its line and formula as extracted-but-unchecked.

**Consumed by.**

- in this graph: `Design bending moment` · `Station design moment (plan path)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/spar_sizing.py:315` · `app/services/spar_sizing.py:378` · `frontend/lib/sparSizingHelpers.ts:118`

**Source.** 🟢 SOURCED

> Sadraey, Aircraft Design: A Systems Engineering Approach (Wiley 2013), §10.4.1, Eq. (10.4), p. 560
>
> — via `aircraft-design-scholz (verified verbatim in the Sadraey source) + rc-aircraft-designer`

**The source states it as.**

```
Verbatim: "For the purpose of structural safety considerations, the ultimate load factor (n_ult) is usually 1.5 times the maximum load factor (i.e., a safety factor of 1.5): n_ult = 1.5 · n_max  (10.4)". Sadraey attributes the 1.5 to "a long-established convention in civil and military airworthiness regulations (e.g., FAR 23 for GA, FAR 25 for transport aircraft)".
```

**⚠️ Divergence from the source.** The default 1.5 is correctly attributable. But Sadraey applies n_ult inside the empirical WEIGHT equations (10.3, 10.5, 10.6, 10.7, 10.8) — he never applies it to an aerodynamic bending-moment distribution to size a section modulus, which is what this code does. Also: the RC literature searched gives NO safety factor at all (grep for "safety factor"/"factor of safety" over Lennon 1996 returns zero hits; kirch "Hauptholm" states load factors and allowables but no separate j).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** ADR 0023 finding. The 1.5 is a transport/GA certification factor (FAR/CS 23.303 and 25.303). Per the project's settled record (BR-W17, gh-1079): CS-23/25's 1.5 sits ON TOP OF A/B-basis statistical material allowables, so the statistical margin lives inside σ_allow. Nobody building a 0.5-15 kg aircraft has A/B-basis allowables, so importing 1.5 alone imports the load-side factor without the resistance-side statistical basis it presupposes. The project's answer is a separate strength-side factor k ≈ 2.5, which the code does not have.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Declared twice with the same default in two schemas: app/schemas/spar_sizing.py:33 and app/schemas/spar_plan.py:122. Magic number: no source cited for 1.5 and no RC/UAV-scale validation note (ADR 0023).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `Safety factor applied to M_design = \|M(y)\| · g_limit · j.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*

---
name: cl_max_clean_mc
symbol: CL_max_clean
kind: parameter
unit: dimensionless
cluster: perf-matching
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: unclassified-parameter
tags:
  - cluster/perf-matching
  - class/unclassified-parameter
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
  - flag/scale
---

# Clean CL_max (matching chart)

**Definition.** Clean-configuration CL_max driving the stall constraint.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `1.4 (fallback)`

**Formula — as the code writes it.**

```
cl_max_clean: float = float(aircraft.get("cl_max_clean", aircraft.get("cl_max", 1.4)))
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/matching_chart_service.py:807` — `compute_chart`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Landing CL_max (matching chart)` · `Takeoff CL_max (matching chart)` · `Stall constraint W/S_max`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `_stall_constraint:868` · `cl_max_to_mc:808` · `cl_max_l_mc:809` · `hover_text:954`

**Source.** 🟡 PARTIAL

> Sadraey Tables 4.10/4.11 §4.3.2 by class (home-built 1.2-1.8; microlight 1.8-2.4; sailplane 1.8-2.5; very light/GA light 1.6-2.2). Scholz Table 5.1. 1.4 sits in the home-built band but is not attributable to a specific entry.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
CL_max by aircraft class, Sadraey Tables 4.10/4.11
```

**⚠️ Divergence from the source.** The code's choice to use CLEAN CL_max for the stall constraint is CORRECT and explicitly supported: Scholz 05_PreliminarySizing §5.1 notes the regulatory stall limits 'can be met in flap-up configuration; flap deflection only relaxes the constraint further'.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** All tabulated classes are manned aircraft; no CL_max band exists in the sources for a 0.5-15 kg low-Re wing, where achievable CL_max is generally lower.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**Cited in the code itself.** `# **Uses CL_max_clean** (clean polar, not landing-flaps CL_max) per spec.`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*

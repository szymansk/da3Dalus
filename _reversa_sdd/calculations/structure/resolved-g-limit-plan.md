---
name: resolved-g-limit-plan
symbol: g_limit
kind: parameter
unit: g
cluster: structure
user_visible: false
source_status: PARTIAL
code_audit: CONFIRMED
node_class: unclassified-parameter
tags:
  - cluster/structure
  - class/unclassified-parameter
  - source/partial
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Limit load factor (plan path)

**Definition.** Limit load factor resolved from the design assumptions for the plan endpoint, falling back to 3.0 with a log warning.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Formula — as the code writes it.**

```
return float(g_limit_raw)
```

**Inputs.**

- [[structure--g-limit-default|Default manoeuvre limit load factor]]  — *⤵ fallback*

**Produced by.** `app/services/spar_plan_service.py:359` — `_resolve_g_limit`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Station design moment (plan path)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/spar_plan_service.py:555` · `app/services/spar_plan_service.py:572` · `cad_designer/airplane/geometry/spar_solver.py:764`

**Source.** 🟡 PARTIAL

> Kirch, "Hauptholm", https://www.flugmodellbau-kirch.de/Hauptholm.htm — tabulated load factors: normal thermal soarers 3 G, motorgliders 2.5 G, F3J >65 G
>
> — via `direct verification of the kirch source + rc-aircraft-designer`

**The source states it as.**

```
Normal thermal soarers: 3 G.
```

**⚠️ Divergence from the source.** Same value and same limitation as `g-limit-default` — attributable to one mission only. Additionally the plan path emits NO g_limit_fallback flag and does not echo g_limit in SparPlanResponse, so a plan silently sized on the 3.0 default is indistinguishable from one sized on a real design assumption. The source treats the load factor as an explicit, mission-selected design input, which this path makes invisible (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Undeclared fallback (ADR 0020): unlike the sizing path, the plan path emits NO g_limit_fallback flag and does not echo g_limit in SparPlanResponse. A plan silently sized on the 3.0 default is indistinguishable from one sized on a real assumption.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*

---
name: resolved-s-ref
symbol: S_ref
kind: quantity
unit: m^2
cluster: powertrain
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
---

# Resolved wing reference area

**Definition.** Wing reference area resolved by the same three-tier priority.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
s_ref_m2 = _pick(request.s_ref_m2, "s_ref_m2", _DEFAULT_S_REF_M2, "Wing reference area (s_ref_m2)", "s_ref_m2")
```

**Inputs.**

- [[default-s-ref-sizing|Default wing reference area (sizing)]]  — *⤵ fallback*

**Produced by.** `app/services/powertrain_sizing_service.py:186` — `_resolve_aero_params`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Estimated cruise power` · `Power required for a motor+battery combo`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_sizing_service.py:248` · `app/services/powertrain_sizing_service.py:312`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `rc-aircraft-designer`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** See default-s-ref-sizing: the RC sources derive wing area from mass and target wing loading, never from a bare default.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*

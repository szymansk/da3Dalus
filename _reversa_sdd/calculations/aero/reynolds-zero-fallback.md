---
name: reynolds-zero-fallback
kind: constant
unit: -
cluster: aero-spanwise
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: WRONG_LINE
node_class: numerical-tolerance
tags:
  - cluster/aero-spanwise
  - class/numerical-tolerance
  - source/no-source-found
  - surface/user-visible
  - audit/wrong-line
  - flag/anomaly
---

# Reynolds zero fallback

**Definition.** Value returned when velocity/cref are non-positive, viscosity is non-positive, or AeroSandbox is unavailable.

**Numerical tolerance.** A solver or comparison epsilon, not a domain value. ADR 0023 does not apply.

**Value.** `0.0`

**Formula — as the code writes it.**

```
return 0.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:1724` — `_reynolds_from_atmosphere`

🟠 **Corrected by the audit** — the extraction claimed `WRONG_LINE`. Original line was `1723`. 

**Consumed by.**

- 🔴 **nothing found.** A computed value nothing reads is a finding (ADR 0021).

**Source.** 🔴 NO SOURCE FOUND

> Returning 0.0 for a failed Reynolds computation has no source; Re = 0 is physically impossible for a flying aircraft. Rendered to the user as 'Re = 0.00e+00' with no warning field (ADR 0020).
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** Undeclared fallback (ADR 0020): a failed Reynolds computation is rendered to the user as 'Re = 0.00e+00' with no warning field.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*

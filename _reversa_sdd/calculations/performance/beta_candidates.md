---
name: beta_candidates
kind: quantity
unit: deg
cluster: perf-oppoints
user_visible: false
source_status: NO_SOURCE_FOUND
---

# Sideslip candidate list

**Definition.** Sideslip angles tried during trim, extended for the dutch-roll point.

**Formula — as the code writes it.**

```
beta_candidates = [float(target.get("beta_target_deg", 0.0))]; if target["name"] == "dutch_role_start": beta_candidates += [0.0, -2.0]
```

**Inputs.** [[dutch_roll_beta_deg|Dutch-roll start sideslip]]

**Produced by.** `app/services/operating_point_generator_service.py:896` — `_trim_or_estimate_point`

**Consumed by.**

- in this graph: [[beta_trimmed|Trimmed sideslip angle]]
- outside it: `app/services/operating_point_generator_service.py:820 (grid loop)` · `app/services/operating_point_generator_service.py:913 (Opti beta)`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aerosandbox-expert`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** The candidate list [β_target, 0.0, −2.0] has no source; it inherits the unsourced 2° dutch-roll amplitude. Note also AeroSandbox has a documented β sign convention — trying ±β without stating the convention makes the sign of the returned sideslip ambiguous.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*

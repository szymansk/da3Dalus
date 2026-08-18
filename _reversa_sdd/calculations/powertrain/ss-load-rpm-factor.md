---
name: ss-load-rpm-factor
symbol: load_rpm_factor
kind: parameter
unit: dimensionless
cluster: powertrain
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: NOT_VERIFIED
node_class: unclassified-parameter
tags:
  - cluster/powertrain
  - class/unclassified-parameter
  - source/no-source-found
  - surface/user-visible
  - audit/not-verified
  - flag/anomaly
  - flag/divergence
---

# Under-load RPM factor

**Definition.** Ratio of loaded to no-load shaft RPM, used to size KV upward for the sag/load penalty.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `0.85`

**Formula — as the code writes it.**

```
kv_approx = rpm_target / (v_nom * load_rpm_factor)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/schemas/powertrain_solution_space.py:69` — `SolutionSpaceAssumptions.load_rpm_factor`

⚪ **Not verified.** This node was not covered by the audit pass; treat its line and formula as extracted-but-unchecked.

**Consumed by.**

- in this graph: `Approximate required motor KV`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_solution_space_service.py:159` · `app/services/powertrain_solution_space_service.py:391`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `rc-aircraft-designer`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**The source states it as.**

```
Drela, 'DC Motor / Propeller Matching' §1.1 gives the physical alternative: Omega = Kv(V - i R), so the loaded/no-load speed ratio follows from R, i and V rather than from a fixed factor.
```

**⚠️ Divergence from the source.** The 0.85 loaded/no-load RPM ratio has no source. Note a near-miss that must NOT be mistaken for one: Lennon (Basics of R/C Model Aircraft Design, Ch. 18) records a legacy '85% prop efficiency' rule, but that is a -15% ADVANCE-PER-REV correction versus nominal pitch (a slip factor), not a shaft-RPM ratio — and Lennon reports that Gierke's measurements overturned it, finding advance per rev EXCEEDS nominal pitch by 7-18%. Lennon separately gives +10% for the static-to-flight rpm gain, i.e. the opposite sign to 0.85. The numerical coincidence with the 0.85 motor efficiency used elsewhere in this cluster is also unexplained.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Magic number, no source, and coincidentally identical to the 0.85 used for motor efficiency everywhere else in the cluster — a reader cannot tell whether that is meaningful or accidental.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `field description: "Motor shaft RPM under load vs. no-load (V_nom × KV × factor)" — NO_SOURCE_FOUND`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*

---
name: ss-rpm-target
symbol: RPM_target
kind: quantity
unit: rpm
cluster: powertrain
user_visible: false
source_status: PARTIAL
---

# Target propeller RPM

**Definition.** Shaft speed needed to reach top speed, assuming the propeller advances one geometric pitch per revolution (J = P/D).

**Formula — as the code writes it.**

```
rpm_target = (v_top_mps / (prop_d * prop_pd)) * 60.0  # rev/min
```

**Inputs.** [[phase1-prop-diameter|Phase-1 propeller diameter estimate]] · [[ss-prop-pd|Propeller pitch-to-diameter ratio]] · [[ss-v-top|Top speed used for peak sizing]]

**Produced by.** `app/services/powertrain_solution_space_service.py:158` — `_per_cell`

**Consumed by.**

- in this graph: [[ss-kv-approx|Approximate required motor KV]]
- outside it: `app/services/powertrain_solution_space_service.py:159`

**Source.** 🟡 PARTIAL

> Roxxy Motoren-Fibel, Ch. 1, pp. 6-7 defines pitch as 'the distance (in inches) that a propeller would move forward in one complete revolution if it were turning in a solid medium with no slip', and adds 'This theoretical advance differs from actual forward movement through air due to various aerodynamic factors.' Lennon, Basics of R/C Model Aircraft Design, Ch. 18 quantifies the difference: the legacy nomograph assumed -15% advance per rev vs nominal pitch (the '85% prop efficiency' rule), while David Gierke's RPM measurements in Model Airplane News found actual advance per rev EXCEEDS nominal pitch by 7-18%.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
Advance per rev (in) = Speed(mph) x 5280 x 12 / (rpm x 60)  (Lennon Ch. 18, after Gierke)
```

**⚠️ Divergence from the source.** The code assumes exactly zero slip: rpm_target = V_top/(D x P/D) x 60, i.e. the prop advances its full geometric pitch every revolution. Both sources say that is not what happens, and they disagree on the sign of the correction (Lennon's legacy rule: 85% of pitch; Gierke's measurements: 107-118% of pitch). Zero slip is a defensible midpoint but is stated by neither source, and no slip factor is exposed. Lennon Ch. 18 also notes the geometric limit that an airplane cannot fly faster than geometric pitch x rpm.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Assumes zero slip (the prop advances its full geometric pitch every revolution) with no slip factor and no source; combined with the fixed 0.30 m diameter this makes the RPM target essentially airframe-independent.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `module docstring: "KV ≈ RPM_target / (V_nom × load_rpm_factor) where RPM_target = V_top / (prop_d_m × prop_pd) × 60   [approximate]"`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*

---
name: ss-i-peak
symbol: I_peak
kind: quantity
unit: A
cluster: powertrain
user_visible: true
source_status: PARTIAL
code_audit: WRONG_LINE
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/wrong-line
  - flag/anomaly
  - flag/divergence
---

# Peak battery current

**Definition.** Battery current at top speed: battery-side electrical power divided by sag voltage. No further efficiency division, because the input power is already battery power.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
i_peak = p_top_elec_w / v_sag
```

**Inputs.**

- [[ss-p-elec|Electrical power required]]
- [[ss-v-sag|Pack voltage under load]]

**Produced by.** `app/services/powertrain_solution_space_service.py:139` — `_per_cell`

🟠 **Corrected by the audit** — the extraction claimed `WRONG_LINE`. Original line was `140`. 

**Consumed by.**

- in this graph: `Hyperbola C-rate samples` · `Minimum ESC current rating` · `Raw required C-rate`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_solution_space_service.py:145` · `app/services/powertrain_solution_space_service.py:149` · `app/services/powertrain_solution_space_service.py:444` · `app/services/powertrain_solution_space_service.py:464` · `frontend/components/workbench/PowertrainTab.tsx:126`

**Source.** 🟡 PARTIAL

> Drela, 'DC Motor / Propeller Matching', §1.2 uses P_in = V I for the electrical input side. The specific decision to divide battery-side power by the sagged pack voltage (and not by further efficiencies) is a correct application of that identity but is not itself stated in any source.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
P = V I  =>  I = P_battery / V_battery
```

**⚠️ Divergence from the source.** The implementation is right and the MODULE docstring is wrong: the docstring still states I_peak = P_top/(V_sag x eta_motor x eta_esc), which double-counts the efficiencies already applied in P_elec. The function docstring records this (gh-978 BLOCKER); the module header was never corrected.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The MODULE docstring at line 27 still states the superseded formula "I_peak  = P_top  / (V_sag · η_motor · η_esc)", which the function docstring calls a double-count blocker. Two contradictory formula statements in the same file, one of them in the file's spec-of-record header.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `function docstring: "``p_top_elec_w`` is the *battery* electrical power at V_top (already P_aero / (η_prop·η_motor·η_esc)).  Battery current is therefore simply ``I = P_bat / V_sag`` — no further division by η_motor·η_esc (that would double-count the efficiencies, gh-978 BLOCKER)."`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*

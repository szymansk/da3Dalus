---
name: qprop-rpm-at-imax
symbol: rpm_at_imax
kind: quantity
unit: rpm
cluster: powertrain
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/sourced
  - audit/confirmed
---

# RPM at the current ceiling

**Definition.** Lower bracket of the RPM search: the speed at which the motor would draw exactly max_current_a.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
rpm_at_imax = max(back_emf_floor, 0.0) * kv_si * 60.0 / (2.0 * math.pi)
```

**Inputs.**

- [[qprop-back-emf-floor|Back-EMF floor at the current ceiling]]  — *⊣ limit*
- [[motor-kv-si|Motor speed constant in SI]]

**Produced by.** `app/services/powertrain_performance.py:549` — `solve_qprop_operating_point`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Solved operating RPM`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_performance.py:550`

**Source.** 🟢 SOURCED

> Drela, 'DC Motor / Propeller Matching', §1.1 and §1.1.3 (K_V = Omega / v_m), applied at i = I_max.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
Omega = v_m * K_V  =>  RPM = (V - I_max R) * Kv_si * 60 / (2 pi)
```

**Cited in the code itself.** `# If a current ceiling is set, the back-EMF floor caps the minimum RPM the motor will run at; current rises as RPM falls (more I·Rm drop).`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*

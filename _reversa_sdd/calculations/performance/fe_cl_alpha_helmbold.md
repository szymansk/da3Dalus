---
name: fe_cl_alpha_helmbold
symbol: CL_alpha
kind: quantity
unit: 1/rad
cluster: perf-envelope
user_visible: false
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-envelope
  - class/derived
  - source/partial
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Finite-span lift-curve slope (Helmbold fallback)

**Definition.** Cold-start lift-curve slope used when no alpha-sweep value is cached.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
return 2.0 * math.pi * ar / (ar + 2.0)
```

**Inputs.**

- [[fe_aspect_ratio|Aspect ratio (gust path)]]  — *⤵ fallback*

**Produced by.** `app/services/flight_envelope_service.py:67` — `_helmbold_cl_alpha`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Effective lift-curve slope for gust`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟡 PARTIAL

> Anderson, Fundamentals of Aerodynamics 6e, §5.3.3 — Prandtl lifting-line result for ELLIPTICAL lift distribution, untwisted wing.
>
> — via `aero`

**The source states it as.**

```
a = a_0 / (1 + a_0/(pi*AR)); with a_0 = 2*pi this is exactly 2*pi*AR/(AR+2)
```

**⚠️ Divergence from the source.** BOTH citations in the docstring are wrong, and so is the function name. The implemented formula is Prandtl's elliptic lifting-line slope with a_0 = 2*pi, not Helmbold. Anderson 6e §5.3.3 gives Helmbold separately as a = a_0/(sqrt(1+(a_0/(pi*AR))^2) + a_0/(pi*AR)), and states it should be preferred for AR < 4 — precisely the regime where the code's formula is worst. Numerically: AR=6 -> code 4.712 vs Helmbold 4.529 (+4%); AR=3 -> code 3.770 vs Helmbold 3.362 (+12%). The name promises the low-AR-accurate form and delivers the one Anderson says to stop using there. Also note 'Introduction to Flight 6e §5.3' names a different book — same book-confusion defect recurs in endurance_service's module header (see end_p_aero).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Citation is internally inconsistent: the docstring names both 'Anderson 6e Eq. 5.81' (Fundamentals of Aerodynamics numbering) and 'Anderson, Introduction to Flight, 6th ed., §5.3' for the same formula. One of the two works is wrong.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"Finite-span CL_α by Helmbold-Diederich (Anderson 6e Eq. 5.81)"; "Sources: Anderson, Introduction to Flight, 6th ed., §5.3."`

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*

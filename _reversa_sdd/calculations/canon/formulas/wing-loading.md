---
canon: wing-loading
entry: formula
kind: law
tool: APP
shape: law
status: approved
output: wing-loading
source_status: SOURCED
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/sourced
  - dim/balances
  - shape/law
  - kind/law
  - status/approved
inputs: {m: aircraft-mass, g: gravity, s_ref: wing-reference-area}
outputs: {w_s: wing-loading}
---

# Wing loading

**Canonical form**

```
W/S = m * g / S_ref
```

**Produces** [[wing-loading]]  ·  **from** [[aircraft-mass]] · [[gravity]] · [[wing-reference-area]]

**Kind: a law.** A closed-form relation. Approval asks for its **source** and its **validity in the RC/UAV regime (ADR 0028)**.

**Dimensional check.** 🟢 balances

**Source.** 🟢 SOURCED

> Sadraey, Aircraft Design: A Systems Engineering Approach (Wiley 2013), §4.3.2, Eq. 4.30-4.31: L = W = 0.5*rho*V_s^2*S*C_L,max, divided by S. Scholz, 05_PreliminarySizing §5.1 uses the mass form m_ML/S_W. RC: RC-Network Wiki, "Flächenbelastung"; Lennon, Basics of R/C Model Aircraft Design (1996), Ch. 4 "Wing Loading Design".

**The source writes it as**

```
Scholz/Sadraey normally write the MASS loading m/S in kg/m^2 (or lb/ft^2), not the force loading N/m^2. RC writes g/dm^2 (Europe) or oz/ft^2 (Lennon: gliders <10-15, sport 15-20, pattern 23-26 oz/ft^2). Conversion, not disagreement - but it is where the second g enters.
```

**Validity in the RC/UAV regime (ADR 0028).** Exact as a definition, independent of Reynolds and Mach number; mass is no criterion (ADR 0028, superseding the former "0.5–15 kg" wording, maintainer 2026-10-27). Presentational caveat: RC users read g/dm² or oz/ft², and Lennon's mission bands are the ones they benchmark against — a unit conversion, not a different quantity.

**Declared deviation (ADR 0022, #1321).** The app produces this quantity in three places (`app/services/flight_envelope_service.py:88`, `app/services/field_length_service.py:200`, `app/services/mission_kpi_service.py:273`, the last with a literal g = 9.81). The canonical producer is this entry; the app duplicates are a ticketed defect, not an approved alternative.

## Implementations (4)

| node | claimed | verified | deviation |
|---|---|---|---|
| `aero_kernel/formulas/wing_loading.py` | EXACT | 🟢 |  |
| [[fe_wing_loading]] | EXACT | 🟢 |  |
| [[wing_loading_fl]] | EXACT | 🟢 |  |
| [[mkpi_wing_loading]] | EXACT | 🟢 |  |

## Approval

- [x] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [x] **Regime** — holds in the RC/UAV regime (Reynolds, Mach, equipment), or the limitation is written down (ADR 0028)
- [x] **Dimensions** — the check balances
- [x] **Implementations** — all agree, or each deviation is declared and justified
- [x] **Preconditions** — every binding condition holds, or the violation is ticketed
- [x] **Inputs approved** — no formula is approvable before its inputs are

> **Approved** (maintainer, 2026-10-27): W/S = m·g/S_ref, the definition (Sadraey Eqs 4.30–4.31; Scholz §5.1;
> Lennon ch. 4), g from [[gravity]] and S_ref from the approved [[airplane-geometry]]. At approval the regime text was
> corrected to ADR 0028 (mass is no criterion) and the app's three producers were recorded as a declared ADR 0022
> deviation, ticketed as #1321. Kernel EXACT (🟢).

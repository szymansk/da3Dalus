---
canon: roll-authority
entry: formula
kind: procedure
shape: law
status: draft
output: max-roll-rate-cruise, max-roll-rate-approach, aileron-throw-fraction-cruise, aileron-throw-fraction-approach
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/procedure
  - status/draft
tex: \begin{aligned}& L(V,\alpha) = m\,g, \quad C_l\big(V,\alpha,\,s\,\delta_{a,max},\,p\big) = 0 \\ & p_{max} = p\big|_{s=1}, \qquad s_{req}:\; p\big|_{s} = p_{req}\end{aligned}
---

# Roll authority with the aileron throws set in the airplane

**Canonical form**

```
solve for alpha, p (steady roll at V):   L(V, alpha) = m * g,   C_l(V, alpha, s * delta_a,max, p) = 0
p_max   = p  at s = 1                         (full set throw)
s_req   = s  with  p(s) = p_req               (fraction of the set throw needed)
evaluated at V = V_cruise and at V = V_app
```

**Produces** [[max-roll-rate-cruise]] · [[max-roll-rate-approach]] · [[aileron-throw-fraction-cruise]] · [[aileron-throw-fraction-approach]]  ·  **from** [[airplane]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[cruise-speed]] · [[approach-speed]] · [[roll-rate-requirement-cruise]] · [[roll-rate-requirement-approach]]

**Kind: a procedure — a closure by a prescribed value.** The steady roll: the rolling moment from the ailerons balances the roll damping, lift carries the weight. `s` scales the **throws set in the airplane** — up and down as constructed, a differential included — from 0 to the full throw.

**The throws are construction parameters, not results** (maintainer, 2026-10-01). `delta_a,max` up and down (`positive/negative_deflection_deg` on the trailing-edge device) are fixed by the construction: clearance at the aileron, servo kinematics, horn placement. The canon checks against them; it does not size them.

**Two answers per operating point.**
- `p_max` — the roll rate the set throws deliver. A property of the airplane.
- `s_req` — the fraction of the set throw the requirement needs. `s_req ≤ 1`: reachable, and the rest is reserve (a dual rate or expo can take it away). `s_req > 1`, or no solution: **not reachable with these throws** — declared, never clipped (ADR 0020).

**The requirement names its speed (A2).** At fixed throw `pb/2V` is nearly independent of speed, so the roll rate in °/s grows with `V`. "Roll rate at cruise" is the character statement RC pilots make; "roll rate on approach" is the controllability statement where Sadraey sizes the aileron (§12.3.3, Phase C — slowest, fewest °/s per degree). Either requirement may be given; each is checked at its own speed.

**AeroBuildup is adequate here** — unlike for adverse yaw. Aileron rolling moment (section lift from NeuralFoil with the deflection) and roll damping (roll rate in the local onset flow, `aero_buildup.py:719-731`) both come from lift, not from induced drag. AVL can cross-check. Declared limit: NeuralFoil's flap model at large throws and low Reynolds number is unvalidated, and aileron stall beyond about 25° (Sadraey §12.4.3) is only as good as that model.

**Source.** 🟢 Sadraey §12.4 (aileron design; steady roll from `C_l,δa · δa + C_l,p · pb/2V = 0`), with the rate requirement made scale-free per the domain expert (time-to-bank does not transfer to model scale).

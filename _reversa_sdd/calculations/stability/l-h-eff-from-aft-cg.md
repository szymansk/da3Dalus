---
name: l-h-eff-from-aft-cg
symbol: l_H,eff
kind: quantity
unit: m
cluster: stability
user_visible: true
source_status: SOURCED
---

# Effective tail arm from aft CG

**Definition.** Distance from the aft-loading CG to the horizontal tail aerodynamic centre; display-only cross-check against static margin.

**Formula — as the code writes it.**

```
result.l_h_eff_from_aft_cg_m = round(x_htail_ac_m - cg_aft_m, 4)
```

**Inputs.** [[x-htail-ac-m|Horizontal tail aerodynamic centre x]]

**Produced by.** `app/services/tail_sizing_service.py:213` — `compute_tail_volumes`

**Consumed by.**

- outside it: `app/api/v2/endpoints/aeroplane/tail_sizing.py:84` · `frontend/hooks/useTailSizing.ts`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §6.6: "The tail arm l_t is the distance between the tail aerodynamic center and the aircraft cg"; §11.6.2 Eq. 11.20 uses the same l_h in V̄_H. rcplanedesigner.com, "Fuselage — Tail Lever Arm" § Design envelope states the same CG-referenced definition with the envelope L_h ≥ 2 × MAC and ≤ 60 % of fuselage length.
>
> — via `aircraft-design-scholz + rc-aircraft-designer`

**The source states it as.**

```
l_h = x_AC,tail − x_cg   (Sadraey §6.6)
```

**⚠️ Divergence from the source.** This is the definition Sadraey and rcplanedesigner use for V_H itself, but the code marks it display-only and computes V_H from the wing-AC convention instead (see l-h-m). It is also evaluated only at the aft cg; both sources treat the arm as a fixed geometric property referenced to the design cg.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `l_h_eff_from_aft_cg_m — aft-CG → tail-AC  (display-only, for SM cross-check)`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*

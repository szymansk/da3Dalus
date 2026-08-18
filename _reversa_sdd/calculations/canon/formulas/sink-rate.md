---
canon: sink-rate
entry: formula
kind: law
shape: law
status: draft
output: sink-rate
source_status: PARTIAL
dimensional_check: UNPARSEABLE
tags:
  - canon/formula
  - source/partial
  - dim/unparseable
  - shape/law
  - kind/law
---

# Steady-glide sink rate

**Canonical form**

```
w = V * C_D / C_L   (small glide-angle form of w = V * sin(gamma), tan(gamma) = C_D/C_L)
```

**Produces** [[sink-rate]]  ·  **from** [[flight-speed]] · [[lift-coefficient]] · [[drag-coefficient]]

**Kind: a law.** A closed-form relation. Approval asks for its **source** and its **validity at 0.5–15 kg**.

ℹ️ **Reclassified** from `procedure` by the trial of 2026-08-18. A single vectorised product: `w = v * (cd_pos / cl_pos)` (app/services/analysis_service.py:515), with V from `v = np.sqrt(2.0 * weight_n / (rho * s_ref_m2 * cl_pos))` (line 514). Closed form evaluated elementwise over the polar; no method involved.

> 🔴 **An assumption of this entry is broken in the code.**
>
> app/services/analysis_service.py:514-515 applies the small-glide-angle form across the ENTIRE sweep, including the low-CL / high-speed end of every curve. At the characteristic points this is harmless (L/D ~ 10-20 => gamma ~ 3-6°, error < 0.5%). At the fast end of an RC polar L/D falls to order 2-5, i.e. gamma = 11-27°, where w = V*CD/CL overstates the true V*sin(gamma) by the dropped cos(gamma) factor (2% at L/D=5, ~10% at L/D=2) and V itself is overstated because line 514 sets L = W rather than W cos(gamma). Consequence: the right-hand tail of the plotted speed polar is optimistically steep, and the validity limit is stated nowhere in the code or the response schema.

**Evaluated by.** None — direct elementwise evaluation over the sampled drag polar (numpy). The argmin/argmax that pick V_min_sink and V_best_glide from w and CL/CD (analysis_service.py:521-523) are exhaustive grid searches, but those belong to the minimum-sink-speed-from-polar / minimum-drag-speed-from-polar entries, not to this one.

**Accuracy.** Not applicable — exact evaluation, no iteration and no tolerance. The result is exact at each sampled polar point and is defined nowhere between them; the returned V/w arrays are the sample points themselves (analysis_service.py:517-519, ordered by V), so the plotted curve is a straight-line interpolation of the alpha-sweep discretisation.

**On failure.** Non-positive-CL points are silently dropped (analysis_service.py:479-481). If no positive-CL point survives, or S_ref <= 0, rho <= 0 or m <= 0, an empty SpeedPolarCurve is emitted with every characteristic value None (lines 493-512) and no warning. The whole builder is wrapped in `except Exception ... return None` with a `logger.error` only (analysis_service.py:667-669), so a failed polar reaches the user as an absent chart. Neither path emits a DesignWarning — ADR 0020 is not satisfied.

**Dimensional check.** ⚪ not machine-checkable as written

**Source.** 🟡 PARTIAL

> RC-Network Wiki, "Gleitzahl" (Aerodynamik): tan(glide angle) = 1/E = altitude lost / horizontal distance, with E = C_L/C_D. Anderson's Fundamentals of Aerodynamics 6e does NOT cover glide performance - that material is in Anderson's Introduction to Flight / Aircraft Performance and Design, which are not the works this project's aerodynamics-expert authority covers. Scholz treats glide ratio only in the climb-gradient sense (18_Klausur SS19 §2.1).

**The source writes it as**

```
The sourced relation is the glide-angle one, tan(gamma) = C_D/C_L, from which w = V*sin(gamma). The proposal's w = V*C_D/C_L is its small-angle form (sin ~ tan), correctly labelled as such in the skeleton.
```

**Validity at 0.5–15 kg.** The small-angle step is benign for RC gliders (E = 10-20 gives gamma = 3-6 deg, error under 0.5%) but not for draggy powered models: at E = 5 the error is ~2%, at E = 3 it is ~5%, and 3-6 is a realistic E for a sport RC model at low Re. Second-order point: the exact steady glide has L = W*cos(gamma), so V itself is slightly overstated by the level-flight lift balance at low E. Both errors push sink rate the same way (optimistic). Acceptable with a stated E floor; below E ~ 5 report the trigonometric form.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[speed-polar-w]] | EXACT | 🟢 |  |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.


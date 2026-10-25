---
canon: sink-rate
entry: formula
kind: law
tool: APP
shape: law
status: draft
output: sink-rate
source_status: PARTIAL
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/partial
  - dim/balances
  - shape/law
  - kind/law
  - status/draft
inputs: {v: flight-speed, cl: lift-coefficient, cd: drag-coefficient-parabolic}
outputs: {w_sink: sink-rate}
preconditions:
  - {id: small_glide_angle, parameter: cd, on_violation: warning}
---

# Steady-glide sink rate

**Canonical form**

```
w_sink = V * C_D,par / C_L
# small glide-angle form of w_sink = V * sin(gamma), tan(gamma) = C_D,par/C_L
```

**Produces** [[sink-rate]]  ·  **from** [[flight-speed]] · [[lift-coefficient]] · [[drag-coefficient-parabolic]]

**Kind: a law.** A closed-form relation. Approval asks for its **source** and its **validity in the RC/UAV regime (ADR 0028)**.

ℹ️ **Reclassified** from `procedure` by the trial of 2026-08-18. A single vectorised product: `w = v * (cd_pos / cl_pos)` (app/services/analysis_service.py:515), with V from `v = np.sqrt(2.0 * weight_n / (rho * s_ref_m2 * cl_pos))` (line 514). Closed form evaluated elementwise over the polar; no method involved.

> 🔴 **An assumption of this entry is broken in the code.** *(Ist ≠ Soll: the canon now states the
> limit as the precondition `small_glide_angle` below; this block records only that the app departs from it.)*
>
> app/services/analysis_service.py:514-515 applies the small-glide-angle form across the ENTIRE sweep, including the low-CL / high-speed end of every curve. At the characteristic points this is harmless (L/D ~ 10-20 => gamma ~ 3-6°, error < 0.5%). At the fast end of an RC polar L/D falls to order 2-5, i.e. gamma = 11-27°, where w = V*CD/CL overstates the true V*sin(gamma) by the dropped cos(gamma) factor (2% at L/D=5, ~12% at L/D=2) and V itself is overstated because line 514 sets L = W rather than W cos(gamma). Consequence: the right-hand tail of the plotted speed polar is optimistically steep, and the validity limit is stated nowhere in the code or the response schema.

**Evaluated by.** None — direct elementwise evaluation over the sampled drag polar (numpy). The argmin/argmax that pick V_min_sink and V_best_glide from w and CL/CD (analysis_service.py:521-523) are exhaustive grid searches, but those belong to the minimum-sink-speed-from-polar / minimum-drag-speed-from-polar entries, not to this one.

**Accuracy.** Not applicable — exact evaluation, no iteration and no tolerance. The result is exact at each sampled polar point and is defined nowhere between them; the returned V/w arrays are the sample points themselves (analysis_service.py:517-519, ordered by V), so the plotted curve is a straight-line interpolation of the alpha-sweep discretisation.

**On failure.** Non-positive-CL points are silently dropped (analysis_service.py:479-481). If no positive-CL point survives, or S_ref <= 0, rho <= 0 or m <= 0, an empty SpeedPolarCurve is emitted with every characteristic value None (lines 493-512) and no warning. The whole builder is wrapped in `except Exception ... return None` with a `logger.error` only (analysis_service.py:667-669), so a failed polar reaches the user as an absent chart. Neither path emits a DesignWarning — ADR 0020 is not satisfied.

**Dimensional check.** 🟢 balances

**Source.** 🟡 PARTIAL

> RC-Network Wiki, "Gleitzahl" (Aerodynamik): tan(glide angle) = 1/E = altitude lost / horizontal distance, with E = C_L/C_D. Anderson's Fundamentals of Aerodynamics 6e does NOT cover glide performance - that material is in Anderson's Introduction to Flight / Aircraft Performance and Design, which are not the works this project's aerodynamics-expert authority covers. Scholz treats glide ratio only in the climb-gradient sense (18_Klausur SS19 §2.1).

**The source writes it as**

```
The sourced relation is the glide-angle one, tan(gamma) = C_D/C_L, from which w = V*sin(gamma). The proposal's w = V*C_D/C_L is its small-angle form (sin ~ tan), correctly labelled as such in the skeleton.
```

**Validity in the RC/UAV regime (ADR 0028).** The small-angle step is benign for RC gliders (E = 10-20 gives gamma = 3-6 deg, error under 0.5%) but not for draggy powered models: at E = 5 the error is ~2%, at E = 3 it is ~5%, and 3-6 is a realistic E for a sport RC model at low Re. Second-order point: the exact steady glide has L = W*cos(gamma), so V itself is slightly overstated by the level-flight lift balance at low E. Both errors push sink rate the same way (optimistic). Acceptable with a stated E floor; below E ~ 5 report the trigonometric form. The floor is stated as
the precondition `small_glide_angle` below.

## Preconditions on the bindings

**`small_glide_angle` — the glide angle must be small (on `cd`, with `cl`; warning).** The canonical
form is the small-glide-angle form of the steady glide, valid only where `gamma = atan(C_D/C_L)` is
small. It drops two factors, both of which make the sink rate optimistic:

- `sin(gamma)` is replaced by `tan(gamma)`, overstating `w_sink` by `1/cos(gamma) - 1`;
- the lift balance behind the bound `V` is `L = W` instead of `L = W * cos(gamma)`, overstating `V`
  (and with it `w_sink`) by a further `1/sqrt(cos(gamma)) - 1`.

| E = C_L/C_D | gamma | from `tan` for `sin` | from `L = W` |
|---|---|---|---|
| 10 | 5.7° | 0.5 % | 0.25 % |
| 5 | 11.3° | 2.0 % | 1.0 % |
| 3 | 18.4° | 5.4 % | 2.7 % |
| 2 | 26.6° | 11.8 % | 5.7 % |

The precondition is violated when `C_L/C_D` falls below the floor stated under **Validity**
(E ~ 5, the entry's draft value — fixed at approval); a violated point is reported, not dropped, and
the trigonometric form `w_sink = V * sin(gamma)` with `L = W * cos(gamma)` is what holds there. The
numbers above are exact evaluations of the two dropped factors, not estimates.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[speed-polar-w]] | EXACT | 🟢 |  |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Regime** — holds in the RC/UAV regime (Reynolds, Mach, equipment), or the limitation is written down (ADR 0028)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.


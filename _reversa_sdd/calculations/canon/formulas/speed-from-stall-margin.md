---
canon: speed-from-stall-margin
entry: formula
kind: rating
shape: approximation
status: draft
output: approach-speed, touchdown-speed, takeoff-speed
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/approximation
  - kind/rating
  - status/draft
---

# Named operating-point speeds as a margin over the stall speed

**Canonical form**

```
V = k_S * V_S,cfg      (V_S,cfg = V_S0 for approach and touchdown, V_S,TO for take-off)
```

**Produces** [[approach-speed]] · [[touchdown-speed]] · [[takeoff-speed]]  ·  **from** [[stall-speed-landing]] · [[stall-speed-takeoff]]

**Kind: a rating.** A preference, not physics. The reference values still need an origin and a scale — where does *excellent* come from, and for which aircraft? **On top:** whether **this** weighting is the one you want. That part is a decision, not a fact.

⚠️ **Shape: an approximation.** A rule of thumb standing where a law belongs. It may be the right thing to show, but it is never approved *as* the law for this quantity.

> V_x and V_y are labelled best-angle and best-rate-of-climb but contain no climb relation — no thrust, no excess power.

**Dimensional check.** ⚪ procedural — not an algebraic law

**Source.** 🟢 SOURCED

> The specific multipliers are regulatory and appear in Scholz/Sadraey: CS 25.125 - stabilised approach at not less than 1.3*V_s (Scholz 05_PreliminarySizing §5.1); CS 25.111 - V_2 >= 1.2*V_S (Scholz §5.2); Sadraey §4.3.4 Eq. 4.72 - V_TO = 1.1 to 1.3*V_s, with V_LOF ~ 1.2*V_S,TO and V_R ~ 1.1-1.2*V_s; FAR 23.51 - V at 50 ft >= 1.20*V_S1 single-engine.

**The source writes it as**

```
Sources give named speeds with named factors, each tied to a certification requirement. The generalised scheme V_op = k_op*V_S,cfg with an optional V_cruise-fraction floor and an absolute minimum is the app's abstraction over them; the floors have no regulatory counterpart.
```

**Validity at 0.5–15 kg.** The factors are manned-aircraft certification minima. Two RC-specific cautions. (1) A 1.3 margin over a stall speed whose C_L,max is uncertain by 30-45% at model Reynolds number (see stall-speed) is thinner than the same 1.3 on a certified aircraft with a flight-tested V_S - at model scale the margin should arguably be larger, not equal. (2) Vx/Vy for a propeller model are properly the minimum-drag and minimum-power speeds (Sadraey Eq. 4.80/4.85), not multiples of V_S; and hand-launched models have no V_LOF or ground roll at all, so takeoff-derived operating points are undefined for that launch mode.


## Rebuilt 2026-10-01 — named outputs, no cruise floor, no climb speeds

**There is no generic operating-point speed.** The entry used to produce `V_op`, a
collective quantity without its condition in its name — the A2 violation that also put a
false cycle into the graph through `flight-speed`. It now produces three **named**
quantities, one per operating point, each with its own binding of `k_S` and of the
configuration:

| output | binds | configuration |
|---|---|---|
| [[approach-speed]] `V_app` | `k_S` approach margin | landing |
| [[touchdown-speed]] `V_TD` | `k_S` touchdown margin | landing |
| [[takeoff-speed]] `V_TO` | `k_S` take-off margin | take-off |

The factors themselves stay open — the sources give an RC rule-of-thumb band of 1.2–1.25
for landing and 1.3 from regulation for approach; choosing is the maintainer's call.

**The cruise-speed floor is gone.** It came only from the two climb bindings
(`max(1.35·V_S1, 0.85·V_cruise)`, `max(1.50·V_S1, 0.95·V_cruise)`), and the source note
already said those floors have no regulatory counterpart. With them gone the formula hangs
on the stall speed alone, as a margin over stall should.

**V_x and V_y are gone from this entry.** They are climb speeds, not stall margins, and
they contained no climb relation — no thrust, no excess power. Their home is the climb
operating point, which has been computed since 2026-10-01 (§3.10).

## Implementations (5)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[v_approach]] | EXACT | 🟢 |  |
| [[v_stall_near_clean]] | EXACT | 🟢 |  |
| [[v_stall_with_flaps]] | DEVIATES | 🟢 | k_op = 1.05 over V_S0 leaves only a 10% load-factor margin to stall (1.05^2 = 1.10 g); the |
| [[v_best_angle_climb_vx]] | DEVIATES | 🟢 | max(1.35*V_S1, 0.85*V_cruise). Labelled best-angle-of-climb but derived from no climb quan |
| [[v_best_rate_climb_vy]] | DEVIATES | 🟢 | max(1.50*V_S1, 0.95*V_cruise). Labelled best-rate-of-climb but derived from no climb quant |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Ownership** — the weighting is the maintainer's decision, recorded as such
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.


# Path 1 — the speeds

> **65 canonical quantities · 46 formulas** — 39 laws, 3 routes, 4 approximations.
> Collapsed from 157 register nodes. Every entry is `status: draft`.

## Where it stands

| | |
|---|---|
| dimensional check | 🟢 29 balance · ⚪ 15 not algebraic · 🔴 2 open |
| provenance | 🟢 28 sourced · 🟡 13 partial · 🔴 5 unsourced |
| **canonical conflicts** | **1** |
| implementation conflicts | 5 — one law, inconsistent call sites |

## The one canonical conflict

**[[zero-lift-drag-coefficient]]** — two laws claim it:
- [[zero-lift-drag-from-sweep]] · `C_D0 := C_D at the C_L = 0 crossing, by linear interpolation between the two bra`
- [[reynolds-scheduled-polar]] · `C_D0(V), e(V) = interp( table, Re(V) ),  Re = rho * V * c_MAC / mu`

## Routes — these generate tests, not decisions

- [[minimum-drag-speed-closed-form]] → [[minimum-drag-speed]]
- [[minimum-drag-speed-from-polar]] → [[minimum-drag-speed]]
- [[minimum-sink-speed-from-polar]] → [[minimum-sink-speed]]

## Approximations — label, never approve as the law

- [[minimum-drag-speed-heuristic]] · V_md = 1.4·V_S carries no polar information — no C_D0, no e, no AR — so it cannot tell a glider from an aerobatic model.
- [[minimum-sink-speed-heuristic]] · V_mp = 1.2·V_S likewise contains no polar information.
- [[operating-point-speed-from-stall-margin]] · V_x and V_y are labelled best-angle and best-rate-of-climb but contain no climb relation — no thrust, no excess power.
- [[climb-speed-for-power-loading]] · A fixed multiple of the target stall speed, not a climb-performance result.

## Implementation conflicts — one law, call sites that disagree

These need no canonical decision. They are resolved by declaring the **applications**:

- [[stall-speed]] — Three genuinely different laws produce V_S across six producers.
- [[high-lift-clmax]] — Two different laws for the same quantity.
- [[max-lift-to-drag-parabolic]] — One user-visible number, two different laws behind it.
- [[cruise-speed-resolution]] — Three incompatible definitions of V_cruise coexist.
- [[zero-lift-drag-from-sweep]] — Two genuinely different laws produce a number labelled C_D0.

## Approval order

A formula is approvable only once its inputs are.

**Layer 1** (14) — [[air-density-isa]] · [[weight-from-mass]] · [[wing-loading]] · [[aspect-ratio]] · [[mean-geometric-chord]] · [[high-lift-clmax]] · [[dive-speed]] · [[climb-speed-for-power-loading]] · [[turn-load-factor]] · [[inverted-max-lift-coefficient]] · [[negative-limit-load-factor]] · [[mean-thrust-derate]] · [[battery-mass-from-capacity]] · [[mass-summation]]

**Layer 2** (6) — [[induced-drag-factor]] · [[stall-speed]] · [[stall-wing-loading-limit]] · [[gust-mass-ratio]] · [[thrust-to-weight]] · [[relative-mass-deviation]]

**Layer 3** (6) — [[minimum-drag-speed-heuristic]] · [[minimum-sink-speed-heuristic]] · [[operating-point-speed-from-stall-margin]] · [[stall-speed-in-turn]] · [[gust-alleviation-factor]] · [[stall-margin-ratio]]

**Layer 4** (1) — [[cruise-speed-resolution]]

**Needs an input this path does not produce (19)** — [[dynamic-pressure]] · [[lift-balance-speed]] · [[clmax-from-polar]] · [[linear-lift-curve-inverse]] · [[lift-to-drag-ratio]] · [[max-lift-to-drag-parabolic]] · [[sink-rate]] · [[minimum-drag-speed-closed-form]] · [[minimum-drag-speed-from-polar]] · [[minimum-sink-speed-from-polar]] · [[lift-coefficient-required]] · [[gust-velocity-schedule]] · [[gust-load-increment]] · [[cruise-thrust-constraint]] · [[power-required-electrical]] · [[endurance-from-battery]] · [[zero-lift-drag-from-sweep]] · [[reynolds-scheduled-polar]] · [[stall-onset-detection]]


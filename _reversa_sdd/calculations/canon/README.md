# The canon — the formulas this application is approved against

> The register below (`../`) records **what the code does**. This directory records
> **what it is supposed to do**. The difference between the two is the finding, and
> the agreement between them is the test.

## Why a second level

The register has 1112 nodes. Reviewing them is not possible and would not help: the
same physics appears many times over. `V_stall` is computed in six files. Sea-level
air density is defined nine times. Gravity eleven times, in two values.

So the review unit is wrong. The right unit is the **distinct statement**: one entry
per quantity, one per relation, with every implementation pointing at it. That
collapses ~1100 nodes into an order of ~200 statements across the whole application,
and roughly 25–35 for a single chain.

Two things follow that the node register could never give:

**An approved formula is a test oracle.** A *fachlicher* test — one that asserts a
domain truth rather than a code path — needs something to assert against. Without a
canon there is only regression testing, which cements whatever the code does today,
including its defects.

**Duplicates stop being opinions.** Once `g` is one canonical quantity, eleven
definitions are eleven implementations of it — a join, not a judgement. Once a
relation is approved, "the code diverges from the literature" becomes "implementation
X does not compute approved formula Y", which is a check.

## Two registers, not one

The duplicates come in two kinds, and one register would hide the second.

**`quantities/`** — the vocabulary. Symbol, unit, meaning, and a role: `input`
(supplied from outside the chain), `derived`, or `output` (reaches the user).
Nine definitions of `ρ₀` are a *quantity* duplicate.

**`formulas/`** — the physics. A relation between canonical quantities, in symbols,
with its source. Every implementing node is listed with how closely it agrees.

The distinction earns itself immediately: static margin has **three producers using
three different relations** — `(X_np − x_ref)/c_ref`, `(x_np − cg_x)/mac·100`, and
`−C_mα/C_Lα`. That is not one quantity computed three times. It is one quantity with
a **conflict**, and a formula-only register would show it as three formulas and lose
the point.

**Identity is the quantity, not the expression.**

## One formula, several applications

A formula can be applied more than once with different inputs. That is not duplication
and it is not a conflict — it is the normal shape of a design calculation, and the canon
has to say so, or it cannot tell the two apart.

**Stall speed is the worked example.** There is one law:

```
v_stall = sqrt(2 · m · g / (rho · S_ref · cl_max))
```

and three **applications** of it, differing only in which `cl_max` is bound:

| application | binds `cl_max` | exists when |
|---|---|---|
| `v_stall_clean_mps` | `cl_max_clean` | always |
| `v_stall_takeoff_mps` | `cl_max_takeoff` | the wing has a flap |
| `v_stall_landing_mps` | `cl_max_landing` | the wing has a flap |

Three **quantities** — they have different values. One **formula**. Three
**applications** binding one input differently.

Two consequences follow, and both are mechanical:

**In the code there should be three calls to one function**, not three implementations of
one law. Three separate implementations where the canon declares one formula is
duplication, and it can be detected by a join rather than by reading.

**A configuration that does not exist is not computed.** The application carries a
condition. A wing with no flap has one stall speed, not three identical ones — and
certainly not three that disagree because one of them fell back to the clean value.

### Application versus conflict

| shape | meaning | verdict |
|---|---|---|
| same formula, different input binding | an application | ✅ expected — record it |
| different formulas, same output quantity | a conflict | ⚠️ decide it |

This is the discriminator the register lacked. The three stall speeds are applications.
The three static margins — `(X_np − x_ref)/c_ref`, `(x_np − cg_x)/mac·100` and
`−C_mα/C_Lα` — are a conflict: different laws claiming one quantity.

## Naming

One readable scheme, `<quantity>_<configuration>_<unit>`:

```
v_stall_clean_mps      v_stall_takeoff_mps      v_stall_landing_mps
cl_max_clean           cl_max_takeoff           cl_max_landing
```

Spelled out. **No regulatory shorthand** (`V_S0`, `V_S1`) and no abbreviations (`to`,
`ldg`) — those are readable only to someone who already knows the convention, which is
the opposite of what a canon is for. The unit suffix stays: in a codebase carrying
millimetres inside a metre model (ADR 0001) it is a guard, and `mass_kg` and
`wing_area_m2` already do it.

The scheme is not new. `field_length_service` already writes `cl_max_landing` on line 361
and `v_s0_mps` on line 368 — seven lines apart, in one function. One of the two
conventions already exists and is the right one; it only has to win.

## Approval

Each formula carries a `status`:

| status | meaning |
|---|---|
| `draft` | proposed by extraction. **Cites nothing, decides nothing.** |
| `approved` | the maintainer has read it, the source is real, and its validity at 0.5–15 kg is stated |
| `superseded` | replaced by another entry, which is named |

Three gates before `approved`:

1. **Source** — a specific citation, or an explicit statement that none exists and the
   relation is adopted on the maintainer's authority. 🔴 NO SOURCE FOUND is a legitimate
   outcome; a fabricated citation is the worst possible entry, because everything
   downstream cites it.
2. **Scale** — does it hold for RC/UAV aircraft of 0.5–15 kg? A relation derived for
   transport aircraft is not disqualified, but the limitation is stated (ADR 0023).
   Low Reynolds number, low wing loading and hand launch are where it usually bites.
3. **Implementations** — every implementing node either agrees, or its deviation is
   declared and justified.

**One rule orders the work: a formula is only approvable once its inputs are approved.**
Otherwise approval rests on unapproved ground. That is what makes the traversal run
from the input parameters to the outputs, and it gives the only honest progress
measure — *what fraction of the paths reaching a user-visible number is approved*.

## The paths

Chains are approved one at a time, in dependency order.

| # | path | why |
|---|---|---|
| 1 | **speeds** — `V_stall`, `V_md`, `V_min_sink`, `V_max`, `V_A`, `V_D`, the V-n envelope | the heart: every published speed, the flight envelope, the operating points and the mission KPIs hang off it |
| … | structure, mass, powertrain, stability | later — each depends on the speeds |

The spar chain is *downstream* of this one: its `M(y)` comes from an operating point
with a velocity, and its design moment is scaled by a load factor. Approving it first
would break the input-first rule.

## What this does not do

It does not decide whether the code is right. It states what right would be, so that
the question becomes answerable — by a test, by a measurement, or by flying the
aircraft and seeing whether it stalls where the canon says it does.

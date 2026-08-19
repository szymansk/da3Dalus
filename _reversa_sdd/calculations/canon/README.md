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

### Two axes, not one

An entry carries two independent classifications, the way the register already carries
confidence and the Ist/Soll axis separately (`../MARKERS.md`).

**`kind`** — what sort of statement it is. This decides **what approval asks**.

**Source and scale are asked of every entry.** Nothing here is source-free: a procedure
implements a published standard or solves an equation that has one, and a fit has an
origin for its fitted model. The kind decides what is asked **in addition**.

| kind | why it exists | asked *in addition* to source and scale |
|---|---|---|
| **law** | a closed-form relation | — |
| **procedure** | *because no closed solution exists* | the **assumptions** under which it holds · **when it converges** · what it returns when it does not |
| **fit** | a regression over computed points, not a derivation | its **domain of validity** · its **rejection criteria** |
| **rating** | a preference, not physics | whether **this** weighting is the one you want — that part is a decision, not a fact |

The procedure row is the one that had to be added — and it is the one most easily
misread. **A procedure is not invented here.** It has two origins, and both are citable:

- the **relation** it solves — an equation, or a published standard such as the U.S. 1976
  atmosphere;
- the **method** it solves it with — bisection, Brent, Newton, Picard, an interior-point
  solver.

Its assumptions and its convergence behaviour then follow from that method. Brent's method
converges when the root is bracketed and the function is continuous on the interval; that
is a published property, not a preference. So "under which assumptions, and when does it
converge" is a question with a **literature answer**, exactly like the source of a law.

Which is what makes an undeclared failure return a defect rather than a style choice: the
method offers a guarantee, and the code either honours it or silently returns something
the method never promised.

That gate finds things immediately. The trim solver runs with `max_iter=120`,
`max_runtime=0.35` and `behavior_on_failure="return_last"`
(`operating_point_generator_service.py:685-687`): a non-converged iterate is returned
**silently**, and because the budget is wall-clock, the same aircraft can trim differently
on a loaded machine. No criterion is declared and no warning is emitted (ADR 0020).

Path 1 splits **32 laws · 10 procedures · 3 fits · 1 rating**.

**`shape`** — how the entry relates to the others. This decides **whether there is
anything to decide**.

### The four shapes

Collapsing the speed chain showed that "two producers of one quantity" hides four
different situations, and only the last is a decision.

| shape | what it is | verdict |
|---|---|---|
| **single** | one relation, applied wherever it is needed | approve it once |
| **route** | the same quantity reached two ways — a closed form and a numerical search | ✅ legitimate, and it **generates a test**: they must agree |
| **approximation** | a rule of thumb standing where a law belongs | ⚠️ label it; never approve it *as* a law |
| **duplicate** | the **same statement** declared in more than one place | ⚠️ consolidate to one authority — and the divergence between the copies is the finding |
| **conflict** | two **different** laws claiming one quantity | ⚠️ decide it |

**Duplicate versus conflict — the discriminator is one question: do the declarations say
the same thing?**

If yes it is a duplicate. That is a maintenance defect while the copies agree, and a
correctness defect the moment they drift — which they do. Gravity is declared eleven times
in two values, sea-level density nine times, and the target static margin four times as
`0.12` seeded, `0.08` substituted by the loading path, `0.10` by the sizing path and
`0.075` in a docstring. An aircraft without the stored row gets a *different design target*
depending on which service asks.

If no it is a conflict, and it is a correctness question today rather than eventually.

A duplicate entry records **whether its copies still agree**. That is the field worth
reading: `duplicate, copies agree` is technical debt, `duplicate, copies have diverged` is
a defect with a reproduction waiting to be written.

This shape also gives the mechanical findings a home. [`../findings.md`](../findings.md)
already computes duplicate literal values across the whole register by a join — those rows
belong on the quantity they duplicate, not only in a findings list. A finding lives where
it binds the calculation.

A fifth situation is not about the canon at all but about the code: one law, implemented
inconsistently across several call sites. That is an **implementation conflict**, and the
application concept is what resolves it — the stall speed is the example.

**The route shape is the one worth dwelling on.** `V_md` is reached both in closed form,
`sqrt(2(W/S) / (rho·sqrt(C_D0/k)))`, and numerically as `V(argmax C_L/C_D)`. Those are not
rivals; they are the same statement under a parabolic-polar assumption. So the canon does
not choose between them — it records that **they must agree**, and where they do not, the
polar is not parabolic. That is a fact about the aircraft, not a defect, and it is exactly
the kind of assertion a *fachlicher* test can carry.

The approximations are the opposite. `V_md = 1.4·V_S` contains no `C_D0`, no `e`, no aspect
ratio; it cannot distinguish a glider from an aerobatic model. It may still be the right
thing to show at cold start — but it is labelled as an approximation, and it never becomes
the approved law for the quantity.

## What may be left out — and what may not

A skeleton that keeps everything is unreadable; one that drops the wrong things is worse
than none. So exclusion needs a **typed reason**, and two kinds are never eligible.

| may be excluded | why |
|---|---|
| an **input quantity** | it belongs to `quantities/`, not to `formulas/`. Excluded from the formula register, not from the canon. |
| a member of **another chain** | say which chain, so a later path picks it up |
| an **echo** — the same value republished under a second key | record the rename on the quantity it echoes |
| **presentation** — colours, labels, axis limits, log lines | nothing downstream reads a number from it |
| **plumbing** — timestamps, CRUD helpers, loop indices | no influence on a result |

**Never excluded:**

**A fallback constant.** It changes the answer. A substituted value is an edge of type
`fallback`, and path 1 found 178 of them — that class *is* the ADR 0020 surface. "It is a
constant, not a relation" is true and beside the point.

**A second declaration of a quantity that already exists.** That is a duplicate, and
surfacing duplicates is why the canon exists at all. "It is a design parameter, not a
formula" is true and beside the point.

The distinction that went wrong on path 3: **"this is not a formula" and "this does not
belong in the canon" are different statements.** Path 3's proposal put five fallback
constants and three competing declarations of the target static margin into `unassigned`,
each with a defensible reason — and the defensible reasons hid that the seeded default is
`0.12`, the loading path substitutes `0.08` when the row is missing, and the sizing path
`0.10`. Two services that both feed the CG envelope, two different answers to the same
missing input.

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

### Preconditions belong to the binding

A formula can be exact and its application still wrong, because the inputs bound to it do
not mean what the law assumes. Those conditions are recorded **on the application**, not
in a separate list of findings — the whole point of the canon is that a finding lives
where it binds the calculation.

The stall speed is the case that made this necessary. `V_S = sqrt(2W/(rho·S·C_L,max))` is
exact. But `C_L,max` is a function of Reynolds number, steeply so in the model range: at
low Re the boundary layer stays laminar further aft, separates against the adverse
gradient, and forms a laminar separation bubble that caps the suction peak. So the law
only means "stall speed" if `C_L,max` was evaluated **at the stall condition** — which
makes `V_S` an implicit equation, since Re depends on `V_S` in turn.

The application therefore carries the requirement, its consequence, whether the code holds
it (🟢 held · 🔴 violated · ⚪ unchecked), and **the test that settles it**. A violated
precondition is a defect of the path, not of the law.

This is what turns the canon into a computation kernel rather than a document: the
formulas say what is true, the applications say under which bindings, and the
preconditions say what has to hold for the binding to mean anything. Each of the three is
separately approvable and separately testable.

### Where the designer decides — the source axis

A quantity in this application does not simply have a producer. It has a **source type**,
and for one of the three the **designer** chooses, not the system.

| source type | what it means | in the code |
|---|---|---|
| **design choice** | only ever set by the designer; never computed | `DESIGN_CHOICE_PARAMS` — 7 entries incl. `target_static_margin`, `g_limit` |
| **dual-sourced** | an estimate *and* a calculated value coexist, and the designer decides which is active | `estimate_value` (never null) · `calculated_value` (nullable) · `active_source` (default `ESTIMATE`) · `divergence_pct` |
| **computed** | no assumption row exists; the value has one producer | `x_np`, `MAC` |

The middle row is the one a graph easily gets wrong. `mass` and `cg_x` are **not** outputs
of the component tree — they are quantities the designer may *let* the tree compute. The
tree's sum is a **candidate**, `divergence_pct` says how far it sits from the estimate, and
`active_source` records the decision. **The system must not make that decision.**

### The loop back to the designer

Not every edge feeds another calculation. Some feed the **designer**, and the graph has to
say which.

The component tree's completeness status — `valid` / `partial` / `invalid`, propagated
bottom-up — is the example. Its purpose is **not** to gate the sum. It tells the maintainer
*where to look next*: which nodes still carry no weight, so the estimate can be improved
where it matters. A green-and-red tree is a working instrument, not a validation rule.

Reading it as a gate is the mistake to avoid: it would make the machine refuse a number the
designer knowingly accepts as provisional. **An estimate is not an error state.** The whole
`estimate_value` / `calculated_value` / `active_source` machinery exists precisely because
provisional is the normal condition of a design in progress (ADR 0010).

So a target graph shows three things a producer-only graph cannot: **where the designer
switches**, **what information that decision rests on**, and **which edges run back to the
human rather than onward to the next formula.**

### What is actually approved: the target graph

The per-formula checklist is the **evidence**. The artefact the maintainer approves is the
**target graph of a path** — the same computation drawn without violated preconditions,
silent substitutions or duplicate authorities (`PFAD3.md` §8 is the first one).

That is the right unit, because the graph is what carries the system-level statements, and
none of them is visible in a single formula file:

- **one authority per quantity** — which producer wins, and which becomes a check
- **which inputs must be supplied**, and from where
- **where an estimate is legitimate** and therefore must declare itself
- **where a check sits** instead of a second producer

Forty-six formula files cannot be judged as a whole. One graph can — and the difference
between the actual graph and the target graph is the work list, item by item, each with its
evidence a page above.

So the order runs: the per-entry gates produce the evidence, the target graph is the
decision, and the entries inherit their approval from it.

### Two stages

Approval happens twice, and the order matters.

**First the formula** — the law itself. Is the relation right, does it have a source, does
it hold at 0.5–15 kg, do the dimensions balance? This is approved once and inherited by
every application.

**Then the application** — the law bound to a specific problem: which `cl_max`, which
density, under which condition. Applications chained together are the **computation
paths**, and those are what can be drawn and checked.

The order reflects where the defects actually are. **Almost every defect found in this
codebase is an application defect, not a formula defect.** The contradiction in
`field_length_service` was never a wrong stall-speed formula — the formula is correct.
What was wrong was which `cl_max` got bound to it. That is why the code reads as
unremarkable: every individual line is right, and only the path shows the error.

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

# Markers — the two axes every spec statement carries

A statement in `_reversa_sdd/` answers two independent questions, and conflating them is
what turns a specification into a wish-list.

| Axis | Question | Values |
|---|---|---|
| **Confidence** | *How well do we know this?* | 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP |
| **Tense** | *Is it true yet?* | **Ist** · **Soll** |

They are orthogonal. A 🟢 **Soll** is entirely normal: the maintainer decided it
explicitly, so our knowledge is certain — and the code has not caught up.

## Confidence — how well we know it

| | meaning | earns it |
|---|---|---|
| 🟢 | CONFIRMED | read from the code with a `file:line` citation, **or** an explicit maintainer decision |
| 🟡 | INFERRED | derived from a pattern, a convention, or reasoning |
| 🔴 | GAP | not established; needs a human |

**A derivation is an inference.** Reasoning your way to an answer produces 🟡, never 🟢 —
however sound the reasoning. Getting this wrong inflates the confidence report precisely
on the statements the extraction produced itself.

> An honest 🔴 is more useful than a misleading 🟡.

## Tense — whether it is true yet

| | meaning | must carry |
|---|---|---|
| **Ist** | this is how the system behaves today | a `file:line` citation |
| **Soll** | decided, not yet built | **a GitHub issue number** |

### A Soll without a ticket number is illegal

Not a style preference — the interlock that keeps the specification and the backlog
honest about each other. `/spec-finder` reports such a statement as a finding, and
`/supercycle-review` treats it as one.

Without it, a decision like

> *The entire wing-tessellation subsystem **is** deleted.* (`Q-CG-4`)

reads as a description of the system while describing a future state. Every reader, human
or agent, then plans against a system that does not exist. That single grammatical habit
is the origin of the whole *decided ≠ implemented* problem.

Write a Soll in the future or modal: *"…**will be** deleted (#1102)"*, *"…**must become** a
derived view (#1103)"*. Present tense is reserved for Ist.

## Who owns what

Applying [ADR 0022](adrs/0022-one-authority-per-user-facing-quantity.md) to our own
process — one authority per fact:

| Fact | Owner |
|---|---|
| A rule or decision — what must hold | **this specification** |
| Current behaviour — what the code does today | **the code**. The spec *describes* it (🟢 Ist + `file:line`); a description can rot, the code cannot |
| Work — whether, when, in what order, done | **GitHub** |

GitHub stays authoritative for *state*. If this specification starts owning "what comes
next", it becomes a worse issue tracker written in Markdown.

## When the spec and a ticket disagree

A ticket that contradicts a spec rule is one of two things:

1. **Stale** — a recorded decision overtook it. Close it, citing the decision.
2. **A new decision** — then **update the spec first**, and let the ticket cite it.

**A ticket never carries a rule.** Same discipline the ADRs follow: a statement here is
superseded only by a new decision recorded here, never by an implementation or an issue
that quietly departs from it.

## Retiring a Soll

When the ticket merges, the statement becomes **Ist**: swap the issue number for the
`file:line` it now lives at. `/supercycle-merge` records the flip in
[`addenda/`](addenda/README.md); the next `/reversa` re-extraction reads the code and
confirms it independently.

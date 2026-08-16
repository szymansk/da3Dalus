# Addenda — what shipped since the extraction

> Seam ③ of the Reversa ↔ Supercycle integration. Written by
> [`/supercycle-merge`](../../.claude/skills/supercycle-merge/SKILL.md), read by
> [`/spec-finder`](../../.claude/skills/spec-finder/SKILL.md).

The extraction in `_reversa_sdd/` is a photograph. The moment a PR merges it is
slightly out of date, and it stays that way until the next full `/reversa` re-extraction
— which is an expensive, whole-repository run, not something done per ticket.

An **addendum** bridges that interval. One file per merged issue, named
`gh-<N>-<slug>.md`, saying: *these units now read differently, and here is why.*
Anyone reading the extraction — human or agent — reads the current addenda with it and
sees the system as it is today.

## What an addendum is not

**An addendum never holds a decision of its own.** It points at one.

This is what makes retiring an addendum safe. If a change departed from a spec rule and
the maintainer approved that departure, the departure is a **new decision** and belongs
where decisions live: an ADR in [`../adrs/`](../adrs/), or an answer in
[`../questions.md`](../questions.md). The addendum cites it. It does not contain it.

So the rule at write time is: **no departure may be recorded in an addendum until its
decision is recorded elsewhere.** A departure with nowhere to point is not ready to
merge — that is the review's job, not the addendum's (see `spec-conformance` in
`/supercycle-review`). The corollary, from ADR 0022's spirit: an addendum is never a
second producer of a fact the extraction already owns.

An addendum also never edits the extraction. `architecture.md`, `domain.md`, the unit
folders and the matrices are read-only here — it annotates, it does not correct.

## Vigência — when an addendum stops counting

Each file opens with:

```
## Vigência

Vigente desde YYYY-MM-DD.
```

An addendum is **current** for exactly as long as that section holds one line. It is
retired by appending a second:

```
Superado pela re-extração de YYYY-MM-DD.
```

**The rule is mechanical: a re-extraction supersedes every addendum dated before it.**
The re-extraction re-reads the code, so it absorbs whatever those addenda described.
Nothing is lost at retirement, because of the previous section — the decisions were
never in here.

**Who writes the supersession line:** whoever runs the next `/reversa` re-extraction, as
its closing step. Reversa's own `step-04-regression-check` will not do it for us — it
keys on `_reversa_forward/<feature>/regression-watch.md`, and this project deliberately
runs no forward cycle (see the memory note `project-reversa-supercycle-integration`).
Until that pass is run, every addendum here counts as current. **Never write the
supersession line at creation time.**

## Language

Prose is **English**, matching `doc_language` in `.reversa/state.json` and the unit
specs. Two things stay in Portuguese on purpose: the heading `## Vigência` and the
impact-type tokens in the table below. They are the framework's vocabulary, shared with
`reversa-sync`, and keeping them verbatim means a future Reversa pass can parse these
files. Do not "fix" them into English.

| token | means |
|---|---|
| `regra-alterada` | an existing business rule changed |
| `regra-removida` | a rule no longer holds |
| `regra-nova` | a rule that did not exist |
| `componente-novo` | a new component / module / service |
| `componente-extinto` | a component was deleted |
| `delta-de-dados` | schema, migration or stored-representation change |
| `delta-de-contrato-externo` | REST, MCP or other outward-facing contract change |

## Template

````markdown
# gh-<N> — <title>

| | |
|---|---|
| Issue | [#<N>](https://github.com/szymansk/da3Dalus/issues/<N>) |
| PR | [#<M>](https://github.com/szymansk/da3Dalus/pull/<M>) |
| Merged | YYYY-MM-DD · `<merge-sha>` |

## Vigência

Vigente desde YYYY-MM-DD.

## Summary

Two or three sentences: what the issue asked for, what actually shipped. Enough that a
planner who reads only this knows whether the area concerns them.

## Impacto por artefato da extração

| Unit | Section | Tipo | Delta |
|---|---|---|---|
| `wing-design/spar-sizing/requirements.md` | §Business rules | `regra-alterada` | BR-W3 now also holds for built spars — read it as covering both paths. |

One row per extraction artefact whose reading changed. `Delta` is one sentence in the
imperative: *how to read that section now*.

## Decisions now implemented

The `## Spec-Anker` in the plan flags decisions as **decided, not implemented**. List the
ones this PR made real, so the next planner is not warned about work that shipped:

- `Q-WD-8 ②` — the `_MIN_REAR_X_C` clamp order is fixed at `spar_solver.py:742`.

*(`none` if this PR implemented no previously-recorded decision.)*

## Approved departures

Spec rules this change deliberately does not follow, each with the decision that
authorises it. **A row without a pointer is not permitted** — see *What an addendum is
not*.

- 🟢 BR-W3 (`wing-design/spar-sizing/requirements.md`) no longer holds for the built
  path → superseded by **ADR 0026**.

*(`none` — and this is the normal case.)*

## Marker candidates for the next re-extraction

A **hint**, not an authority. The re-extraction reads the code and decides for itself.

- `construction-plans/plan-execution/` — 🔴 → likely 🟢: the return contract is now
  instrumented at `AbstractShapeCreator.py:49`.

## Fontes

- Plan: issue comment labelled `has-plan` on #<N>
- Review: issue comment labelled `has-review` on #<N>
- Merge commit `<sha>`
````

## When no addendum is written

Most merges do not need one, and writing an empty addendum is worse than writing none —
`/spec-finder` reads every current addendum on every ticket, so noise here is a tax on
every future plan.

Skip when the PR carried no `## Spec-Anker`, or changed no production code (docs, tests,
chore, lint). `/supercycle-merge` reports the skip explicitly, so it stays a decision
rather than an omission.

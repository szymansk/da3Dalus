# gh-1096 — the rear-spar hinge-clearance guard now runs

| | |
|---|---|
| Issue | [#1096](https://github.com/szymansk/da3Dalus/issues/1096) |
| PR | [#1123](https://github.com/szymansk/da3Dalus/pull/1123) |
| Merged | 2026-08-16 · `608fce87` |

## Vigência

Vigente desde 2026-08-16.

## Summary

The control-surface clearance guard has existed since gh-1059 and **never ran**:
`spar_plan_service` called `build_stations_from_geometry` without
`control_surface_hinge_x_c`, so it defaulted to `None` on every production path and only
tests reached it. A solver-placed rear spar could land inside a control surface.

Two defects fixed, both recorded in `Q-WD-8` ②. The rear call site now passes the wing's
**most forward** hinge (`_wing_hinge_x_c`) — a computed rear spar must clear every control
surface, not the first one found — and the clearance line now wins over the leading-edge
floor. Where the two cannot both be honoured the layout is **infeasible and says so**
(RF-SP-20), translated to a 422 naming the hinge, the clearance and the remedies.

Measured against the live database before merging: of 47 control surfaces carrying a hinge
value, **none** becomes infeasible, and **13** now get a rear spar that no longer sits
inside the movable surface.

## Impacto por artefato da extração

| Unit | Section | Tipo | Delta |
|---|---|---|---|
| `wing-design/spar-sizing/requirements.md` | §Business rules, BR-W8 | `regra-alterada` | Read the clamp as *clearance wins, floor raises infeasibility* — the previous pseudocode `max(min(requested, hinge−0.03), 0.05)` reproduced the defect as if it were the rule. |
| `wing-design/spar-sizing/requirements.md` | §Overview | `regra-alterada` | The bullet "Keep a computed rear spar clear of the hinge line" 🟢 now describes behaviour that actually executes. Before this merge it described a function nobody called. |
| `construction-plans/spar-plan/requirements.md` | §RF-SP-20 | — | Unchanged, and now honoured by one more path: the clearance conflict is reported rather than clamped. |

## Decisions now implemented

- **`Q-WD-8` ②** — the `_MIN_REAR_X_C` clamp order is fixed and the guard is wired.
  `cad_designer/airplane/geometry/spar_solver.py:233-247` (clamp),
  `app/services/spar_plan_service.py:274-294` (`_wing_hinge_x_c`),
  `:583-590` (call site + translation). **No longer "decided, not implemented".**

## Approved departures

`none`.

One **test expectation** changed rather than the code — `test_never_returns_negative_or_zero`
asserted only `x_c > 0.0`, which the old order satisfied by returning `0.05` for a hinge at
`0.02`: a spar inside the control surface, passing. The test encoded the defect, and
`Q-WD-8` ② records that behaviour as wrong, so the expectation moved with the decision.
This is not a departure from the spec — it is the spec being applied — but it is recorded
here because "fix the code, not the tests" is an Iron Law and every exception to it should
be visible.

## Marker candidates for the next re-extraction

A hint, not an authority.

- `wing-design/spar-sizing/` — BR-W8 and the overview bullet stay 🟢, but for the first
  time on the strength of a reachable call path rather than a definition read alone.

## The lesson this merge produced

The 🟢 on that overview bullet was **wrong before this change**, and nothing about it
looked wrong. The extraction read `rear_spar_x_c_with_clearance`, found it correct,
and marked the behaviour confirmed — without checking whether any caller reached it.

**A definition read in isolation is not confirmed behaviour; the call graph is part of the
evidence.** Where the only callers are tests, the honest marker is 🔴 *"implemented, not
reachable"* — which is simultaneously an [ADR 0021](../adrs/0021-complete-but-unreachable-code-is-deleted-by-default.md)
finding. This failure class is mechanically detectable and worth a sweep of its own.

## Fontes

- Issue #1096, created from `_reversa_sdd/audit-2026-08-16-gh-issues.md` §3
- Review: two independent passes, no blocking findings; both verified the ADR 0002
  boundary and the changed-test argument rather than accepting them
- Merge commit `608fce87`

## Nachtrag 2026-08-16 — der Sweep, der daraus folgte

Der Befund oben legte einen Verdacht nahe: Wie viele weitere 🟢-Aussagen beschreiben Code,
den niemand aufruft? Der Sweep lief — und **widerlegte seine eigene Prämisse.**

**Er hätte gh-1096 nie gefunden.** Gemessen: `rear_spar_x_c_with_clearance` hat **2**
Produktionsreferenzen, `build_stations_from_geometry` **5**. Beide waren voll erreichbar.
Abgeschaltet war der Guard durch `control_surface_hinge_x_c: float | None = None` — den
**Default-Wert eines optionalen Parameters**, den kein Produktionsaufrufer je setzte. Ein
Aufrufgraph kann das nicht sehen.

Die Regel ist damit enger und unbequemer als zuerst formuliert: Bei einem Guard, einer
Klemmung oder einer Korrektur zählt nicht *„wird die Funktion aufgerufen"*, sondern
**„welcher Produktionsaufrufer setzt ihr aktivierendes Argument"**.

**Ergebnis des Sweeps selbst — 13 Kandidaten, davon 0 neu:**

| | |
|---|---|
| bereits als **TD-25** in `architecture.md` verzeichnet | 4 (u. a. `compute_recommended_cg`, dort korrekt als zweite Implementierung der CG-Regel benannt) |
| in eingefrorenem `cad_designer/` — unaufgerufen ist dort Politik (ADR 0002) | 8 |
| `reset_for_tests` — Testaffordanz laut Name | 1 |

Die Extraktion hatte die erreichbaren Fälle also bereits gefunden. Der Sweep ist erledigt
und braucht keine Wiederholung; was bleibt, ist die schärfere Frage nach dem aktivierenden
Argument.

**Methodenhinweis für künftige Sweeps:** Diese Codebasis übergibt Services als **bloße
Referenz** an `_call_service(...)`. Wer `name(` zählt, übersieht fast jeden Aufruf — die
erste Fassung des Sweeps meldete deshalb 404 Treffer, von denen keiner stimmte.

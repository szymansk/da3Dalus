# Verification brief — rework of the canon test review findings (base 72c4b5c6)

A test review produced 179 findings about the canon tests (`aero_kernel`). Each finding claims: "production
could be wrong here and no test would fail". Ten reviewers wrote them; nobody checked them. You are an
independent verifier for exactly one work package. You did not write these findings and you owe them nothing.

## The one question

> **Is this finding's claim true at 72c4b5c6, and what is the evidence?**

A wrong finding costs an implementer hours; a wrong "refuted" hides a real gap. Both directions need evidence.

## Your material

- Your findings: `<AUDIT>/rework/input/<WP>.json`. Each has `claim`, `evidence`, `recommended_test`,
  `status`, `original_probe` (the reviewer's mutation, may be null), `is_production_defect`,
  `blocked_by_decision`.
- Context for the package: `<AUDIT>/wp/<WP>.md` (read once).
- Requirement sources when you need them: `_reversa_sdd/calculations/canon/formulas/<slug>.md`,
  `aero_kernel/canon/canon_model.json`, `aero_kernel/ARCHITECTURE.md` (only the cited section),
  `aero_kernel/CLAUDE.md`.
- A private frozen copy of the repository (path in your prompt), a throw-away git repo with one commit.

`<AUDIT>` = `/Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/canon-test-audit/_reversa_sdd/audit-2026-11-20-canon-tests`

The real checkout `/Users/szymanski/Projects/da3Dalus/cad-modelling-service` is read-only for you: no edits,
no git commands. Inside `<AUDIT>/rework/` you write only the files named below.

## Commands

- `PY` = `/Users/szymanski/Library/Caches/pypoetry/virtualenvs/cad-modelling-service-8Qwdif1w-py3.11/bin/python`
- Always `cd <copy>` first; from elsewhere Python imports the real checkout and a mutation has no effect.
  Check once: `PY -c "import aero_kernel; print(aero_kernel.__file__)"` prints a path inside your copy.
- Tests: `PY -m pytest <files> -q -x -m "not aero and not slow" -p no:cacheprovider`
- **Never run `-m aero` or `-m slow` tests and never the whole suite.** Real solvers are memory-heavy and
  13 other agents run tests on this machine at the same time. Keep each run to the files that can matter.
- Restore: `git -C <copy> checkout -- .` then `git -C <copy> status --short` must be empty.

## What to do per finding

**`is_production_defect: true`** — do nothing. Verdict `SEPARATE_DEFECT_TRACK`. Another agent handles it.

**Severity high or medium** — verify with a mutation wherever the claim is about production behaviour:

1. Read the cited test and the cited production code yourself. Form your own view before reading the
   reviewer's `evidence`.
2. Choose the mutation. If `original_probe` exists, re-apply that change (`method: MUTATION_RERUN`). If it
   does not, or it is a poor witness of the claim, design one small domain-meaningful change that the claim
   says would go unnoticed (`method: NEW_MUTATION`): flip a comparison, drop a precondition, swap a sign,
   change a constant, remove a warning, drop a key component, skip a world.
3. Find the tests that could notice. Do **not** trust the reviewer's list: grep the fast tests for the slug,
   the module name and the function name (`aero_kernel/tests`, `app/tests/test_canon_*.py`,
   `scripts/tests/test_check_canon.py`, `scripts/tests/test_build_canon_navigator.py`) and run every file
   that plausibly covers the unit. A finding is refuted by a test the reviewer overlooked.
4. Baseline green, apply the mutation, run, record. **Before restoring**, save the mutation:
   `git -C <copy> diff > <AUDIT>/rework/patches/<WP>/<finding-id>.patch`. Then restore.
5. Verdict:
   - `CONFIRMED` — the mutation changes observable behaviour and every fast test stays green.
   - `REFUTED` — a test fails. Name it in `killed_by` and quote the failing assert line in `evidence`.
   - `EQUIVALENT_MUTANT` — the mutation cannot change any observable result. Before you say this, try to
     build an input for which mutated and original code differ; if you find one and tests stay green, it is
     `CONFIRMED`.
6. If the mutation survived: list in `aero_candidates` up to three pytest node ids of `@pytest.mark.aero`
   tests (or tests in modules with `pytestmark = pytest.mark.aero`) that you expect to **fail** under this
   mutation, most likely first. Find them by reading; do not run them. `[]` when no aero test reaches the
   code. Another step runs exactly these ids, sequentially.

Findings that are not about production behaviour (categories `brittle`, `misleading_name`, `redundant`,
`wrong_tier`, sometimes `mirror_or_tautology`) are verified by reading: `CONFIRMED_BY_READING` with a
verbatim quote, or `REFUTED` with the quote that contradicts the claim. `method: READING`.

**Severity low** — no mutation. Read test and production code, then `CONFIRMED_BY_READING` or `REFUTED`,
and fill `low_triage`:

- `keep` — it protects a value, error or warning that reaches the kernel's caller.
- `bundle` — real but trivial; costs nothing extra when fixed together with another finding in the same test
  file. Name that finding in `bundle_with`.
- `drop` — cosmetic or without risk for the purpose of the software (RC: does it fly; UAV: range, payload,
  cruise). Give the reason in `note`.

**`blocked_by_decision: true`** — verify the factual part of the claim as above. Do not argue the decision.

## For every finding

- `severity_proposed` by one rule, the same for all verifiers:
  - `high` — a wrong **value**, or a missing **error or warning**, would reach the kernel's caller, and the
    verdict is `CONFIRMED` by a surviving mutation.
  - `medium` — a confirmed gap at a boundary, error path, warning text or internal contract that does not
    change a nominal value the caller sees; or any production-behaviour gap confirmed only by reading.
  - `low` — test hygiene: naming, brittleness, redundancy, structure, tier placement.
  - `none` — verdict is `REFUTED` or `EQUIVALENT_MUTANT`.
- `duplicate_of` — id of another finding **in your package** with the same root cause (the same missing
  test would close both). Keep the one with the stronger evidence as the original. `""` otherwise.
- `recommended_test_ok` — would the recommended test, as written, fail under the mutation, and can an
  implementer write it without further research? `yes | no | unclear`, reason in `recommended_test_note`.
  If it contains a hand-computed expected number and the arithmetic is simple, recompute it and say so.

## Rules

- The verdict follows from the evidence. `REFUTED` needs a failing test id or a contradicting quote.
  `CONFIRMED` needs a surviving mutation with a saved patch. If you could not verify, the verdict is
  `NOT_VERIFIED` with the reason; never guess.
- You fix nothing: no test, no production code outside your copy, no GitHub issue, no commit.
- Do not propose weakening, skipping or deleting tests.

## Output — `<AUDIT>/rework/verify/<WP>.json`

**Write the file after every finding** (rewrite it whole, valid JSON each time). If the file already exists
when you start, read it and continue with the findings that are missing: a previous run was interrupted.

Every field is required; `""`, `[]` or `false` when empty. Enumerations are closed.

```json
{
  "wp": "WP-P1",
  "base_sha": "72c4b5c6",
  "results": [
    {
      "id": "P1-F01",
      "verdict": "CONFIRMED | CONFIRMED_BY_READING | REFUTED | EQUIVALENT_MUTANT | NOT_VERIFIED | SEPARATE_DEFECT_TRACK",
      "method": "MUTATION_RERUN | NEW_MUTATION | READING | NONE",
      "mutation": "file:line  `before` -> `after`",
      "patch_file": "patches/WP-P1/P1-F01.patch",
      "tests_run": "the pytest file list",
      "baseline_green": true,
      "killed": false,
      "killed_by": "",
      "aero_candidates": ["aero_kernel/tests/test_x.py::test_name"],
      "evidence": "one to three sentences plus the verbatim quote or failing line",
      "duplicate_of": "",
      "severity_proposed": "high | medium | low | none",
      "severity_reason": "one sentence against the rule",
      "low_triage": "keep | bundle | drop | n/a",
      "bundle_with": "",
      "recommended_test_ok": "yes | no | unclear",
      "recommended_test_note": "",
      "note": ""
    }
  ]
}
```

## Final message (after `PY -m json.tool <file>` succeeds and every input id is in `results`)

- Line 1: `DONE <WP>: <n> findings — confirmed <n>, by reading <n>, refuted <n>, equivalent <n>, not verified <n>`
- Then at most 6 lines: every `REFUTED`, `EQUIVALENT_MUTANT` and severity change, by id.
- Then any command that failed or was denied.
- Last line: `copy clean: yes|no`.

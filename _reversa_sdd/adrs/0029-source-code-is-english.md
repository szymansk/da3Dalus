# ADR 0029 — Everything in the source tree is English

- **Status:** Accepted — new decision.
- **Decided:** 2026-10-14, by the maintainer: "Alles was source Code ist (code, dateinamen, ordnernamen, ...)
  das muss englisch sein … Wir implementieren auf Englisch und nicht auf Deutsch!"
- **Trigger:** the calculation-core package was drafted as `rechenkern/` (Epic #1173); it is now
  `aero_kernel/`.
- **Confidence:** 🟢 (maintainer ruling).

## Context

The maintainer and the specification work in German. The canon and the requirements under
`_reversa_sdd/calculations/canon/` are German. German leaked from there into the source tree:
- a package name (`rechenkern`)
- prototype file names under `scripts/canon_checks/` (`ERGEBNISSE.md`, `LIESMICH.md`,
  `UNSCHAERFE_PRUEFUNG.md`, `spannweiten.json`, `snack_fluegel_*.dat`)
- identifiers in the Urmodell generator (`Tragflaeche`, `Hoehenleitwerk`)

A mixed-language code base is harder to search, review and hand to agents and contributors. The frontend
already follows the same rule for rendered text.

## Decision

**Everything in the source tree is English:**
- identifiers: modules, packages, classes, functions, variables, constants, enum values, error codes
- file and folder names
- code comments and docstrings
- test names and test data **written by the code or hard-wired into tests**
- documentation that lives **inside the source tree**: `README.md`, `ARCHITECTURE.md` and module
  `CLAUDE.md` files in a package; `docs/`
- log messages and messages returned by the API, including the natural-language `message` and `hint` of
  structured errors
- commit messages, branch names and PR texts (already practice)

**Not affected:**
- **The specification** in `_reversa_sdd/`: the canon, `ANFORDERUNGEN.md`, `STAND.md` and the selection
  graph may stay German. It is the maintainer's working language and the source of truth for decisions.
  Identifiers that reach code from there are English: canon slugs (`stall-speed`) and quantity names
  already are.
- **User data.** Names a user gives to aircraft, wings or fuselages (`Tragflaeche`, `BRYAN`) are data, not
  code. They stay as the user wrote them. Code never relies on them.
- **Conversation with the maintainer,** which stays German.

**German domain terms** are translated, with the German term in a docstring or the glossary where it helps:
`Rechenkanon` → canon, `Betriebspunkt` → operating point, `Urmodell` → base model, `Bänder` → bands.

## Consequences

- The calculation core is `aero_kernel/`. Its `ARCHITECTURE.md` and `CLAUDE.md` are English. Epic #1173
  and its sub-issues use the new name.
- **Existing German names** in the source tree are renamed in one sweep (separate ticket), with paths in
  the specification updated. Until then they are known debt, not precedent.
- Reviews treat a German identifier, file name or comment in new code as a finding.

## Related

- [ADR 0019](0019-implementation-details-must-not-leak-into-the-api.md): API texts are part of the
  contract.
- Frontend rule (memory): no German in rendered UI text.

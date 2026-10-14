# aero_kernel/ — module instructions

**Read [`ARCHITECTURE.md`](ARCHITECTURE.md) before changing anything in this package. It is binding.**
If a change contradicts it, change the architecture document first and get the maintainer's approval,
then the code. Epic: #1173.

## Rules that are easy to get wrong

- **Boundary.** Never import from `app/`, `cad_designer/` or `scripts/`. The app calls the core, never
  the other way round (ARCHITECTURE §3, test Q9).
- **The kernel interprets its own canon model** (`canon/canon_model.json`). Quantities, applications,
  dependencies and units come from it. Code only registers implementations via `@formula("<slug>")`.
  Never hard-code a dependency, a unit or a quantity name that the model owns.
- **Canon changes only through the import** (`python -m aero_kernel.importer`, ARCHITECTURE §8.9). Never
  edit `canon_model.json` by hand, and never read `_reversa_sdd/` at runtime. A canon finding is fixed in
  the canon document, then re-imported. A breaking diff means: update the affected implementations and
  golden values in the same change.
- **One file per canon formula** in `formulas/`, file name = slug with underscores (`stall_speed.py`). One implementation per formula;
  applications are bindings, not copies (ARCHITECTURE §8.5).
- **Formulas compute, they do not judge** (canon A10): no thresholds, bands or pass/fail in this package.
- **Solvers only through `solvers/`.** Formulas never import aerosandbox or call AVL directly, so they stay
  mockable and missing tools become `tool_unavailable`.
- **Errors vs warnings.** No value → `KernelError` with category, `message`, `hint` (ARCHITECTURE §8.1).
  Value with a caveat → warning with `severity` (ADR 0020). Never a silent substitute.
- **Validation** rejects only physically inadmissible input. Regime (Re, Mach; ADR 0028) is a warning.
  Mass is not a criterion.
- **Uncertain quantities** (A11, ADR 0027): run each method world through the whole subtree; intervals
  only at the end; never interval arithmetic.
- **English only (ADR 0029).** Identifiers, file names, comments, docstrings, error `message`/`hint`
  and docs in this package are English. Canon slugs are used as they are.
- **Stateless.** No module-level mutable state except the cache; the cache must never change a result.

## Tests

| Marker | Runs | Needs |
|---|---|---|
| (none) | fast tier, mocked solvers | numpy, pydantic |
| `@pytest.mark.aero` | real AeroBuildup/AVL, golden values | aerosandbox, avl-binary |

Every formula: a unit test against a hand-computed value. Golden values of the reference fleet are
**regression, not validation**. Run slow tests sequentially.

```bash
poetry run pytest aero_kernel/tests            # fast
poetry run pytest aero_kernel/tests -m aero    # solvers, golden values
```

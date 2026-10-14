# rechenkern/ — module instructions

**Read [`ARCHITECTURE.md`](ARCHITECTURE.md) before changing anything in this package. It is binding.**
If a change contradicts it, change the architecture document first and get the maintainer's approval,
then the code. Epic: #1173.

## Rules that are easy to get wrong

- **Boundary.** Never import from `app/`, `cad_designer/` or `scripts/`. The app calls the core, never
  the other way round (ARCHITECTURE §3, test Q9).
- **The canon is the structural source.** Quantities, applications, dependencies and units come from the
  manifest generated out of `_reversa_sdd/calculations/canon/`. Code only registers implementations via
  `@formula("<slug>")`. Never hard-code a dependency, a unit or a quantity name that the manifest owns.
- **One file per canon formula** in `formulas/`, file name = slug. One implementation per formula;
  applications are bindings, not copies (ARCHITECTURE §8.5).
- **Formulas compute, they do not judge** (canon A10): no thresholds, bands or pass/fail in this package.
- **Solvers only through `solvers/`.** Formulas never import aerosandbox or call AVL directly, so they stay
  mockable and missing tools become `tool_unavailable`.
- **Errors vs warnings.** No value → `CanonError` with category, `message`, `hint` (ARCHITECTURE §8.1).
  Value with a caveat → warning with `severity` (ADR 0020). Never a silent substitute.
- **Validation** rejects only physically inadmissible input. Regime (Re, Mach; ADR 0028) is a warning.
  Mass is not a criterion.
- **Uncertain quantities** (A11, ADR 0027): run each method world through the whole subtree; intervals
  only at the end; never interval arithmetic.
- **Stateless.** No module-level mutable state except the cache; the cache must never change a result.

## Tests

| Marker | Runs | Needs |
|---|---|---|
| (none) | fast tier, mocked solvers | numpy, pydantic |
| `@pytest.mark.aero` | real AeroBuildup/AVL, golden values | aerosandbox, avl-binary |

Every formula: a unit test against a hand-computed value. Golden values of the reference fleet are
**regression, not validation**. Run slow tests sequentially.

```bash
poetry run pytest rechenkern/tests            # fast
poetry run pytest rechenkern/tests -m aero    # solvers, golden values
```

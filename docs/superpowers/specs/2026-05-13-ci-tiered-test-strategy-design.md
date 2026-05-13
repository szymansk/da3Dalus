# CI: Tiered Backend Test Strategy

**Date:** 2026-05-13
**Type:** Task (CI/CD, tooling)
**Status:** Ready for implementation

## Motivation

The GitHub Actions backend job currently runs **~34 min** on every PR. This
blocks fast feedback, raises iteration cost, and discourages small,
frequent PRs. The root cause is a flat test pipeline: every PR runs the
full suite on a Python 3.11 + 3.12 matrix with coverage instrumentation
and **no parallelization** — and only ~3% of tests carry pytest markers,
so `-m "not slow"` filters almost nothing.

## Diagnose (measured / observed)

| Faktor | Aktuell | Befund |
|---|---|---|
| Python-Matrix | 3.11 + 3.12 parallel | Verdoppelt CI-Compute. 3.11 wird nicht aktiv für Releases verwendet; SonarCloud zieht nur das 3.12-Artefakt (`test.yml:152`). |
| Coverage | `--cov-fail-under=70` auf beiden Matrix-Runs | +10–18 % pro Job. 3.11-Coverage wird verworfen. |
| pytest-xdist | nicht im Einsatz | Sequentielle Tests. GH-Standardrunner: 2 vCPUs → realistisch 1.7× Speedup möglich. |
| Marker-Disziplin | 76 von ~2486 Tests markiert (~3 %) | Keine echte Trennung Unit / Integration / E2E. `-m "not slow"` greift kaum. |
| Heavy Tests ohne Marker | `test_avl_*_integration.py`, `test_tessellation_*.py`, `test_*_e2e.py` | Laufen in der Fast-Suite mit. |
| `clean_cad_task_state` autouse | `conftest.py:104` | shutdown_executor() vor + nach jedem Test, auch bei Tests die kein CAD anrufen. |

## Empfohlene Test-Tiers

### Tier 1 — PR fast (Ziel ≤ 8 min)
- Schemas, Validatoren, Converters
- Service-Tests mit gemockten oder rein-Python-Pfaden
- Endpoint-Tests gegen In-Memory-DB **ohne** CAD/AVL/ASB
- DB-Modell- und Migrations-Smoketests
- Marker-Filter: `not slow and not e2e and not requires_cadquery and not requires_aerosandbox and not requires_avl`

### Tier 2 — PR full / pre-merge (Ziel ≤ 15 min, Label `ci-full`)
Tier 1 + lightweight Integrationspfade die häufig regressieren:
- AVL-Strip-Forces, AVL-Generator-Integration
- Tessellation-Cache (klein parametrisiert)
- Operating-Point-Generator-API (1 Config)

### Tier 3 — Nightly + Pre-Release (~45–60 min, cron `0 3 * * *`)
Alle Tests inkl. `@slow`, voller Smoke-Suite, full Python-Matrix (3.11 + 3.12).

## Scope (konkrete Änderungen)

| Datei | Änderung |
|---|---|
| `.github/workflows/test.yml` | Restrukturierung in 4 Jobs (`fast`, `full`, `nightly`, `frontend`); Matrix-Reduktion auf 3.12 für PR; Coverage-Gate bleibt in `fast`; `slow` wird zu `nightly` per cron. |
| `app/tests/conftest.py` | Neu: `pytest_collection_modifyitems` für Auto-Tagging via Dateiname (`_e2e`, `_smoke`, `_integration`, `tessellation`, `avl_*_integration`). Optional: konditionaler `shutdown_executor()`-Aufruf. |
| `pyproject.toml` | `pytest-xdist ^3.6` in `[tool.poetry.group.dev.dependencies]`; neuer `e2e` Marker in `[tool.pytest.ini_options]`. |
| Heavy Tests | Falls Auto-Tagging eine Datei verpasst: explizites `pytestmark = pytest.mark.e2e` (z.B. `test_aeroplane_wing_from_wingconfig_e2e.py`, `test_construction_parts_step_integration.py`). |

## Implementation Steps

1. **Baseline messen:** `poetry run pytest -m "not slow" --durations=50 -q` lokal — Liste der 50 langsamsten Tests dokumentieren.
2. **Auto-Marker via `pytest_collection_modifyitems`** in `conftest.py` + neuer `e2e` Marker in `pyproject.toml`.
3. **`pytest-xdist`** einführen, `-n auto --dist worksteal` in CI-Aufruf.
4. **Workflow-Restrukturierung** in 4 Jobs (siehe Scope).
5. **Hand-Tagging Heavy Tests**, die Auto-Marker verpasst (über Schritt-1-Output validieren).
6. *(Optional)* `clean_cad_task_state` konditional machen.

## Acceptance Criteria

- [ ] PR-Job `fast` läuft in **≤ 12 min** auf neuem PR (Baseline: 34 min).
- [ ] `fast` Job führt `pytest -m "not slow and not e2e and not requires_cadquery and not requires_aerosandbox and not requires_avl"` mit `pytest-xdist -n auto`.
- [ ] `fast` Job läuft nur auf Python 3.12.
- [ ] `--cov-fail-under=70` bleibt im `fast` Job aktiv, Coverage-XML wird für SonarCloud hochgeladen.
- [ ] `full` Job läuft bei Label `ci-full` oder manuellem Dispatch.
- [ ] `nightly` Job läuft per cron `0 3 * * *` + workflow_dispatch, exekutiert komplette Suite auf Python 3.11 + 3.12.
- [ ] `pytest_collection_modifyitems` taggt automatisch `_e2e`, `_smoke`, `_integration`, `tessellation_*`, `fuselage_slice_*`, `avl_*_(generator|runner|strip_forces)` Dateien.
- [ ] Marker `e2e` ist in `pyproject.toml` registriert.
- [ ] `pytest-xdist` ist als dev dependency in `pyproject.toml` enthalten.
- [ ] Vorher/nachher Vergleich der Job-Dauer im PR-Body dokumentiert.

## Risiken

- **Python-3.11-Abdeckung verzögert sich auf Nightly.** Akzeptabel, da kein Release auf 3.11 läuft.
- **Auto-Marker via Dateinamen ist brittle.** Umbennen einer Datei kann Tier-Wechsel auslösen. Mitigation: explizites `pytestmark` bevorzugen.
- **pytest-xdist + globaler State.** Beim ersten Lauf können Tests scheitern, die auf Reihenfolge gesetzt haben. Mit `--dist worksteal` und ggf. `pytestmark = pytest.mark.no_parallel` für CAD-Pool-Tests lösbar.
- **Coverage-Drift möglich.** Wenn Fast-Tier zu aggressiv schrumpft, fällt `--cov-fail-under=70`. Tier-Zuordnung muss iterativ sein.

## Verifikation

```bash
# Baseline (vor Änderungen)
time poetry run pytest -m "not slow" -q

# Nach Schritt 2 + 3
time poetry run pytest -m "not slow and not e2e" -n auto -q

# Coverage-Gate
poetry run pytest -m "not slow and not e2e" -n auto \
  --cov=app --cov=cad_designer --cov-fail-under=70

# Nightly-Smoke
gh workflow run test.yml -f run_slow=true
```

## Links

- Plan: `/Users/szymanski/.claude/plans/effervescent-finding-valiant.md`
- Aktuelles CI-Workflow: `.github/workflows/test.yml`
- Test-Konfiguration: `pyproject.toml` (`[tool.pytest.ini_options]`)

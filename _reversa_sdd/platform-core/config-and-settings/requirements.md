# platform-core / config-and-settings

> Use-case specification. Parent module: [`../requirements.md`](../requirements.md).
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.

## Overview

Configuration is read through **two `pydantic-settings` classes that are both
called `Settings`**, both read the same `.env`, both use `extra="ignore"`, have
disjoint fields, different naming conventions and different consumers — plus
**three** version strings and **three** environment variables that escape both
classes through bare `os.getenv`. 🟢 🔴

This is the module's most visible anomaly (G-12, TD-39). It is documented here as
the real contract, because both classes have live consumers and merging them is a
behaviour change, not a cleanup. 🟢

## Responsibilities

- Load environment configuration into typed settings objects. 🟢
- Provide the canonical **absolute** project paths `REPO_ROOT` and
  `AIRFOILS_DIR`. 🟢
- Resolve `ARTIFACTS_BASE_DIR` to an absolute path regardless of CWD. 🟢
- Carry the copilot's four hub settings and the airfoil catalogue's 13 low-Re
  tuning constants. 🟢

## Business Rules

- **BR-PC14 — Two `Settings` classes.** 🟢

  | | `app/core/config.py` | `app/settings.py` |
  |---|---|---|
  | Singleton | `settings` | `settings` **and** `@lru_cache get_settings()` |
  | `model_config` | `SettingsConfigDict(env_file=".env", extra="ignore")` | identical |
  | Field naming | SCREAMING_CASE | snake_case |
  | Fields | `PROJECT_NAME`, `VERSION`, `UVICORN_HOST`, `ARTIFACTS_BASE_DIR`, `COPILOT_API_KEY`, `COPILOT_BASE_URL`, `COPILOT_MODEL`, `COPILOT_EMBEDDING_MODEL` | `base_url`, `openai_api_key`, `version`, 13 × `low_re_*` |
  | Also exports | `REPO_ROOT`, `AIRFOILS_DIR` | `_DEFAULT_LOW_RE_GRID`, `_DEFAULT_MISSION_WEIGHTS` |
  | Consumers | `copilot_service`, `openvsp_*`, `artifact_service`, `create_wing_configuration`, `main.run_app` | `mcp_server`, `health`, `cad`, `airfoils`, `aeroanalysis`, `suitability_service`, `airfoil_low_re_service`, `background_jobs` |

- **BR-PC15 — Three version strings.** 🟢 `core.config.VERSION = "1.0.0"`
  (unused), `app.settings.version = "0.1.0"` (what `/health` reports),
  `FastAPI(version="2.0.0")` — 🟢 collapsed to one source derived from `pyproject.toml` (`Q-CC-4`).
- **BR-PC16 — `REPO_ROOT` and `AIRFOILS_DIR` must be absolute.** 🟢
  `REPO_ROOT = Path(__file__).resolve().parents[2]`;
  `AIRFOILS_DIR = REPO_ROOT / "components" / "airfoils"`. The comment records
  the bug that forced it: a CWD-relative airfoils dir made
  procedurally-generated airfoils from the OpenVSP importer (e.g. Spitfire's
  `naca14012`, `naca4-923-a0.6`) land outside the read directory, so they
  appeared **"missing" after import**.
- **BR-PC17 — `ARTIFACTS_BASE_DIR` is resolved by a validator.** 🟢
  `@field_validator("ARTIFACTS_BASE_DIR", mode="after")` calling `.resolve()`,
  so a relative env override becomes absolute regardless of the working
  directory at startup. Default `/tmp/da3dalus_artifacts`.
- **BR-PC33 — `COPILOT_API_KEY` is a `SecretStr`.** 🟢 Masked in `repr`/logs;
  the raw value requires `.get_secret_value()`. It is the only secret modelled
  as such.
- **BR-PC18 — 🟢 All three fold into the one merged `Settings` class (`Q-CC-4`, maintainer-answered). Previously escaping:
  | Variable | Read by | Default | Note |
  |---|---|---|---|
  | `SQLALCHEMY_DATABASE_URL` | `db/session.py:8` | `sqlite:///./db/test.db` | arguably a bootstrap exception — importing settings from `db/session` would invert the dependency |
  | `LOG_LEVEL` | `logging_config.py:7` | `DEBUG` | `getattr(logging, name, DEBUG)` — an invalid name silently falls back |
  | `DISPLAY_CONSTRUCTION_STEP` | `construction_plan_service` | unset | debug flag |
  All three contradict `app/CLAUDE.md`'s rule *"no scattered `os.getenv`"*.
- **BR-PC34 — `extra="ignore"` is deliberate.** 🟢 The comment in
  `app/settings.py` says why: *"developer-local variables in `.env`
  (`GITHUB_TOKEN`, etc.) do not break application startup or test collection."*
- **BR-PC35 — 🟢 Removed with the settings merge (`Q-CC-4`, `P-DEAD-0`). Previously unread: `PROJECT_NAME` (a placeholder
  default `"My FastAPI Project"`) and `openai_api_key` (`"sk*"`). A third,
  `COPILOT_EMBEDDING_MODEL`, is read by nothing in app code.
- **BR-PC36 — `low_re_*` defaults encode two deliberately different NeuralFoil
  model sizes.** 🟢 The per-request endpoint uses `"large"` (interactive, fast)
  while the backfill uses `"xxxlarge"` (CD error ~2 % vs ~8 %) — the comment
  says explicitly: *"These are intentionally different defaults — do NOT
  collapse them."*

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | Load both settings classes from `.env` with `extra="ignore"` | Must | An unknown env var does not break startup |
| RF-02 | Expose `settings` singletons from both modules | Must | Both importable |
| RF-03 | Provide `get_settings()` memoised | Must | `lru_cache` |
| RF-04 | Provide `REPO_ROOT` and `AIRFOILS_DIR` as absolute `Path`s | Must | Independent of CWD |
| RF-05 | Resolve `ARTIFACTS_BASE_DIR` after validation | Must | A relative override becomes absolute |
| RF-06 | Model `COPILOT_API_KEY` as `SecretStr` | Must | Masked in `repr` |
| RF-07 | Default `COPILOT_MODEL` to `"claude-sonnet-4-6"` | Must | |
| RF-08 | Carry the 13 `low_re_*` tuning fields with their documented defaults | Must | Including the two different NeuralFoil model sizes |
| RF-09 | Carry `_DEFAULT_LOW_RE_GRID` (13 log-spaced Re points) and `_DEFAULT_MISSION_WEIGHTS` (6 presets) | Must | Defaults produced via `default_factory` copies |
| RF-10 | Read `SQLALCHEMY_DATABASE_URL`, `LOG_LEVEL`, `DISPLAY_CONSTRUCTION_STEP` from the environment | Must | 🟡 today via bare `os.getenv` |
| RF-11 | Report a single application version | Should | 🟡 **not met** — three values |

## Non-functional Requirements

| Type | Inferred requirement | Evidence | Confidence |
|------|----------------------|----------|-----------|
| Robustness | A developer's personal `.env` entries must not break startup or test collection | `extra="ignore"` + its comment | 🟢 |
| Correctness | Path settings must be CWD-independent | `REPO_ROOT`, `AIRFOILS_DIR`, the `ARTIFACTS_BASE_DIR` validator | 🟢 |
| Security | The hub credential must never appear in a log or `repr` | `SecretStr` | 🟢 |
| Maintainability | 🟡 One name, two classes, disjoint fields, two import paths | `core/config.py` vs `settings.py` | 🟡 |
| Operability | 🟡 "What version is this?" has three answers, and `/health` reports the one nobody else uses | G-12 | 🟡 |
| Consistency | 🟡 Three variables bypass both classes | BR-PC18 | 🟡 |
| Discoverability | New settings are expected in `.env.example` (project rule) | `app/CLAUDE.md` | 🟡 |

## Acceptance Criteria

```gherkin
Feature: Loading

  Scenario: Unknown env vars are ignored
    Given .env contains GITHUB_TOKEN=abc
    When both Settings classes are instantiated
    Then neither raises

  Scenario: get_settings is memoised
    When get_settings() is called twice
    Then the same object is returned

Feature: Paths

  Scenario: AIRFOILS_DIR is absolute and CWD-independent
    Given the process is started from a different working directory
    Then AIRFOILS_DIR still points at <repo>/components/airfoils

  Scenario: A relative artifacts dir becomes absolute
    Given ARTIFACTS_BASE_DIR="./artifacts"
    When the settings are loaded
    Then the value is an absolute resolved path

Feature: Secrets

  Scenario: The copilot key is masked
    Given COPILOT_API_KEY is set
    When the settings object is repr'd or logged
    Then the raw key does not appear
    And .get_secret_value() returns it

Feature: The anomaly   # characterisation

  Scenario: Two classes with one name
    Then app.core.config.Settings and app.settings.Settings both exist
    And both read .env
    And their field sets are disjoint

  Scenario: Three version strings
    Then app.core.config.settings.VERSION is "1.0.0"
    And app.settings.get_settings().version is "0.1.0"
    And the FastAPI app version is "2.0.0"
    And GET /health reports "0.1.0"

  Scenario: Variables that escape both classes
    Then SQLALCHEMY_DATABASE_URL, LOG_LEVEL and DISPLAY_CONSTRUCTION_STEP
      are read with bare os.getenv

  Scenario: An invalid log level degrades silently
    Given LOG_LEVEL="VERBOSE"
    When logging is configured
    Then the level falls back to DEBUG with no warning

Feature: Low-Re tuning

  Scenario: The two model sizes stay different
    Then low_re_neuralfoil_model_size is "xxxlarge"
    And the per-request airfoil endpoint uses "large"

  Scenario: Mutable defaults are copies
    Given two Settings instances
    When one mutates low_re_grid
    Then the other is unaffected
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|---|---|---|
| Absolute `AIRFOILS_DIR` / `REPO_ROOT` (RF-04) | Must | A concrete past bug: airfoils "missing" after an OpenVSP import |
| Resolved `ARTIFACTS_BASE_DIR` (RF-05) | Must | Same class of failure |
| `SecretStr` for the hub key (RF-06) | Must | The only modelled secret |
| `extra="ignore"` (RF-01) | Must | Developer `.env` files break startup otherwise |
| Memoised `get_settings()` (RF-03) | Must | Used as a FastAPI dependency and hand-passed by MCP tools |
| The 13 low-Re fields with their documented defaults (RF-08/RF-09) | Must | Tuning without rerunning the NeuralFoil backfill |
| Reading the three escaped variables (RF-10) | Must | The application does not run without them |
| A single version string (RF-11) | Should | 🟡 not met |
| A single `Settings` class | Should | 🟡 not met — both have live consumers |
| Removing the unread settings (`PROJECT_NAME`, `openai_api_key`, `COPILOT_EMBEDDING_MODEL`) | Could | 🟡 all three are dead |
| Runtime config reload | Won't | Settings are read once per process |
| Per-environment config files beyond `.env` | Won't | Only `.env` is supported |

## Code Traceability

| File | Symbol | Coverage |
|---|---|---|
| `app/core/config.py:13-14` | `REPO_ROOT`, `AIRFOILS_DIR` (+ the "missing airfoils" comment) | 🟢 |
| `…:17-45` | `Settings` #1 incl. the `ARTIFACTS_BASE_DIR` validator and the four `COPILOT_*` | 🟢 |
| `…:48` | the `settings` singleton | 🟢 |
| `app/settings.py:19-56` | `_DEFAULT_MISSION_WEIGHTS` (6 presets) | 🟢 |
| `…:60-74` | `_DEFAULT_LOW_RE_GRID` (13 points) | 🟢 |
| `…:77-118` | `Settings` #2 incl. the 13 `low_re_*` fields and the "do NOT collapse them" comment | 🟢 |
| `…:121-126` | `settings` + `get_settings()` | 🟢 |
| `app/db/session.py:8` | `SQLALCHEMY_DATABASE_URL` via `os.getenv` | 🟡 |
| `app/logging_config.py:7` | `LOG_LEVEL` via `os.getenv` | 🟡 |
| `app/services/construction_plan_service.py` | `DISPLAY_CONSTRUCTION_STEP` via `os.environ` | 🟡 |
| `app/main.py:200` | `FastAPI(version="2.0.0")` | 🟢 |
| `app/api/v2/endpoints/health.py` | reports `get_settings().version` | 🟢 |

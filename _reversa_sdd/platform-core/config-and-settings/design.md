# platform-core / config-and-settings — Technical Design

> Use-case design. Parent module: [`../design.md`](../design.md).
> Configuration surface table: [`../contracts.md`](../contracts.md)
> §"Configuration surface".

## Interface

### `app/core/config.py` (48 l.) 🟢

```python
REPO_ROOT:    Path = Path(__file__).resolve().parents[2]
AIRFOILS_DIR: Path = REPO_ROOT / "components" / "airfoils"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "My FastAPI Project"          # 🟢 removed (Q-CC-4, P-DEAD-0)
    VERSION:      str = "1.0.0"                       # 🟢 one version source, from pyproject.toml (Q-CC-4)
    UVICORN_HOST: str = "127.0.0.1"                   # only main.run_app

    ARTIFACTS_BASE_DIR: Path = Path("/tmp/da3dalus_artifacts")

    @field_validator("ARTIFACTS_BASE_DIR", mode="after")
    @classmethod
    def _resolve_artifacts_dir(cls, v: Path) -> Path:
        return v.resolve()

    COPILOT_API_KEY:        SecretStr | None = None
    COPILOT_BASE_URL:       str | None = None
    COPILOT_MODEL:          str = "claude-sonnet-4-6"
    COPILOT_EMBEDDING_MODEL:str = "text-embedding-3-large"   # 🟡 belongs to the superseded RAG plan (Q-CO-10, residual R2)

settings = Settings()
```

### `app/settings.py` (126 l.) 🟢

```python
_DEFAULT_MISSION_WEIGHTS: dict[str, dict[str, Any]]   # 6 presets:
#   trainer, sport, aerobatic, glider, flying_wing, slope_soarer
#   each: thickness_min_pct, thickness_max_pct, cl_max_weight, preferred_families

_DEFAULT_LOW_RE_GRID: list[int]                       # 13 points, 40k … 750k,
#   dense below 250k where the laminar-separation bubble governs

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    #   extra="ignore" so developer-local .env vars (GITHUB_TOKEN, …) do not break
    #   startup or test collection

    base_url:       str = "http://localhost:8000"     # 🔴 the app listens on 8001
    openai_api_key: str = "sk*"                       # 🔴 no reader
    version:        str = "0.1.0"                     # what /health returns

    low_re_grid:                     list[int] = Field(default_factory=lambda: list(_DEFAULT_LOW_RE_GRID))
    low_re_neuralfoil_model_size:    str   = "xxxlarge"
    low_re_n_crit:                   float = 9.0
    low_re_confidence_gate:          float = 0.90
    low_re_low_confidence_flag:      float = 0.85
    low_re_score_r_poor:             float = 2.5
    low_re_bucket_tolerance_ref:     float = 0.6
    low_re_score_cl_max_safety_band: float = 0.30
    low_re_tip_re_abs_floor:         float = 80_000.0
    low_re_tip_re_rel_drop:          float = 50_000.0
    low_re_mission_weights: dict[str, dict[str, Any]] = Field(
        default_factory=lambda: dict(_DEFAULT_MISSION_WEIGHTS))

settings = Settings()

@lru_cache()
def get_settings() -> Settings: return Settings()
```

Note that `app/settings.py` exposes **both** a module-level `settings` **and** a
memoised `get_settings()` returning a *different* instance — two objects with the
same values, reachable two ways. 🟡

## Main Flow

### F1 — Resolution order 🟢

`pydantic-settings` resolves each field as: environment variable → `.env` entry →
field default. `extra="ignore"` discards anything in `.env` that no field
declares, which is what keeps a developer's `GITHUB_TOKEN` from breaking test
collection. 🟢

### F2 — Path resolution 🟢

```
REPO_ROOT = Path(app/core/config.py).resolve().parents[2]
            #  app/core/config.py -> app/core -> app -> <repo>

AIRFOILS_DIR = REPO_ROOT / "components" / "airfoils"
```

The comment above them is a bug post-mortem, not decoration:

> *"These MUST be absolute and CWD-independent: airfoil `.dat` files are written
> by the OpenVSP importer and read back by analysis/UI from (potentially)
> different working directories. A CWD-relative airfoils dir made
> procedurally-generated airfoils (e.g. Spitfire's `naca14012` /
> `naca4-923-a0.6`) land outside the read directory, so they appeared 'missing'
> after import."*

`ARTIFACTS_BASE_DIR` gets the same guarantee dynamically, through an
`after`-mode validator calling `.resolve()`. 🟢

### F3 — The version question 🟢

```
core.config.Settings.VERSION        = "1.0.0"     # read by nothing
app.settings.Settings.version       = "0.1.0"     # GET /health reports this
FastAPI(version=...)                = "2.0.0"     # the OpenAPI document
```

Three answers, no reconciliation, and the one exposed on `/health` is the one no
other component uses. 🔴 (G-12)

### F4 — What escaped the settings classes 🟢 (`Q-CC-4`)

```
db/session.py:8          SQLALCHEMY_DATABASE_URL = os.getenv(..., "sqlite:///./db/test.db")
logging_config.py:7      LOG_LEVEL              = os.getenv("LOG_LEVEL", "DEBUG")
                         level = getattr(logging, LOG_LEVEL, logging.DEBUG)   # silent fallback
construction_plan_service DISPLAY_CONSTRUCTION_STEP via os.environ
```

The database URL is arguably a legitimate bootstrap exception — importing
`app.core.config` from `app.db.session` would invert the dependency direction.
The other two are not, and both contradict `app/CLAUDE.md`'s explicit rule. 🔴

## Alternative Flows

- **No `.env` present:** every field takes its default; the app runs against
  `sqlite:///./db/test.db` with no copilot key (the copilot then uses the
  `"no-key"` placeholder and fails only on a real hub call). 🟢
- **`.env` contains unknown keys:** ignored. 🟢
- **A malformed typed value** (e.g. `low_re_n_crit=abc`): `pydantic-settings`
  raises at import — the one configuration error that stops the process. 🟡
- **A relative `ARTIFACTS_BASE_DIR`:** resolved against the process CWD by the
  validator — correct only if the process starts in the repo root. 🟡
- **An invalid `LOG_LEVEL`:** 🟡 must report rather than fall back silently (`P-WARN-0`); `LOG_LEVEL` folds into the merged settings (`Q-CC-4`).
- **Both `settings` singletons mutated in a test:** `get_settings()`'s cached
  instance is a **third** object and does not see the change. 🟡

## Dependencies

- `pydantic` (`SecretStr`, `Field`, `field_validator`) and
  `pydantic-settings` (`BaseSettings`, `SettingsConfigDict`).
- `functools.lru_cache` for `get_settings()`.
- Consumers on both sides — see the table in
  [`requirements.md`](requirements.md).

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| `extra="ignore"` so developer `.env` entries cannot break startup | the comment in `settings.py` | 🟢 |
| Canonical absolute project paths as module constants, not settings fields | `REPO_ROOT` / `AIRFOILS_DIR` | 🟢 |
| Resolve `ARTIFACTS_BASE_DIR` in a validator rather than at each use site | `_resolve_artifacts_dir` | 🟢 |
| Model the hub key as `SecretStr` | `COPILOT_API_KEY` | 🟢 |
| Keep the low-Re tuning table in code so it can be tuned without rerunning the backfill | the `_DEFAULT_MISSION_WEIGHTS` comment | 🟢 |
| Two deliberately different NeuralFoil model sizes | the "do NOT collapse them" comment | 🟢 |
| `default_factory` copies for the two mutable defaults | `Field(default_factory=…)` | 🟢 |
| Two `Settings` classes with the same name | — | 🟡 no rationale found; the split appears historical 🟡 |
| Three variables read with bare `os.getenv` | `db/session.py`, `logging_config.py`, `construction_plan_service` | 🟡 |

## Internal State

| State | Where | Lifecycle |
|---|---|---|
| `core.config.settings` | module singleton | constructed at import |
| `app.settings.settings` | module singleton | constructed at import |
| `get_settings()`'s cached instance | `lru_cache` | constructed on first call — a **third** object |
| `REPO_ROOT`, `AIRFOILS_DIR` | module constants | computed at import |

## Observability

- 🔴 Nothing logs the effective configuration at startup — not the database URL,
  not the resolved artifacts directory, not which copilot model is in use, not
  which `Settings` class a value came from.
- 🔴 An invalid `LOG_LEVEL` produces no warning.
- 🟢 The one thing correctly hidden is the hub key (`SecretStr`).

## Risks and Gaps

- 🟢 **One `Settings` class, one instance, one version source** (`Q-CC-4`, maintainer-answered). The current split hides a **double-instance bug**: `app/settings.py` exports a module singleton *and* an `lru_cache`d `get_settings()` returning a **different** object. Previously with the same name** and disjoint fields, both
  reading `.env`, each with its own live consumer set. A reader cannot tell from
  `from ... import settings` which one they got.
- 🟢 **One version source, preferably derived from `pyproject.toml`** (`Q-CC-4`), so release, `/health` and OpenAPI cannot disagree. Previously**, and `/health` reports the unused one (G-12).
- 🔴 **Three variables bypass both classes**, contradicting the project's own
  documented rule.
- 🔴 **An invalid `LOG_LEVEL` degrades silently.**
- 🔴 **Three settings have no reader**: `PROJECT_NAME`, `openai_api_key`,
  `COPILOT_EMBEDDING_MODEL`.
- 🔴 **`base_url` defaults to `http://localhost:8000`** while the service listens
  on 8001, so MCP asset URLs are wrong out of the box whenever the request-derived
  fallback is not available.
- 🔴 **No startup log of the effective configuration.**
- 🟡 **`app/settings.py` exposes two access paths** (`settings` and
  `get_settings()`) that return different instances.
- 🟡 **A relative `ARTIFACTS_BASE_DIR` resolves against the process CWD**, which
  is only correct when the process starts in the repo root.

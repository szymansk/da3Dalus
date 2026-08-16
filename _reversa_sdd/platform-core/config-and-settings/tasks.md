# platform-core / config-and-settings — Implementation Tasks

> Parent module task list: [`../tasks.md`](../tasks.md).

## Prerequisites

- [ ] `pydantic` v2 and `pydantic-settings`.
- [ ] A `.env.example` documenting every setting (project rule in
      `app/CLAUDE.md`).

## Tasks

- [ ] **T-01 — `REPO_ROOT` and `AIRFOILS_DIR`.**
  `REPO_ROOT = Path(__file__).resolve().parents[2]`;
  `AIRFOILS_DIR = REPO_ROOT / "components" / "airfoils"`.
  - Legacy origin: `app/core/config.py:6-14`
  - Definition of done: a test starts the process from a different working
    directory and asserts both paths are unchanged. **Carry the comment
    verbatim** — it records the OpenVSP "airfoils missing after import" bug that
    forced absolute paths.
  - Confidence: 🟢

- [ ] **T-02 — `Settings` #1 (`app/core/config.py`).**
  `PROJECT_NAME`, `VERSION="1.0.0"`, `UVICORN_HOST="127.0.0.1"`,
  `ARTIFACTS_BASE_DIR=Path("/tmp/da3dalus_artifacts")` with the
  `field_validator(mode="after")` calling `.resolve()`, and the four
  `COPILOT_*` fields (`COPILOT_API_KEY: SecretStr | None`).
  `model_config = SettingsConfigDict(env_file=".env", extra="ignore")`.
  Module singleton `settings`.
  - Legacy origin: `app/core/config.py:17-48`
  - Definition of done: a relative `ARTIFACTS_BASE_DIR` override becomes
    absolute; `repr(settings)` never shows the copilot key. Record
    `PROJECT_NAME`, `VERSION` and `COPILOT_EMBEDDING_MODEL` as having no reader.
  - Confidence: 🟢

- [ ] **T-03 — `Settings` #2 (`app/settings.py`).**
  `base_url`, `openai_api_key`, `version="0.1.0"`, the 13 `low_re_*` fields,
  plus `settings` and `@lru_cache get_settings()`.
  - Legacy origin: `app/settings.py:77-126`
  - Definition of done: `get_settings()` is memoised. **Carry the
    `extra="ignore"` comment** (developer `.env` vars must not break test
    collection). Record that `openai_api_key` has no reader and that `base_url`
    defaults to port 8000 while the service listens on 8001.
  - Confidence: 🟢

- [ ] **T-04 — The low-Re default tables.**
  `_DEFAULT_LOW_RE_GRID` (13 log-spaced points, 40 000 … 750 000, dense below
  250 000) and `_DEFAULT_MISSION_WEIGHTS` (6 presets: trainer, sport, aerobatic,
  glider, flying_wing, slope_soarer — each with `thickness_min_pct`,
  `thickness_max_pct`, `cl_max_weight`, `preferred_families`). Both wired
  through `Field(default_factory=…)` **copies**.
  - Legacy origin: `app/settings.py:19-74`
  - Definition of done: two `Settings` instances do not share a mutable default.
    Carry the comments — the grid's density rationale (laminar-separation
    bubble) and the *"do NOT collapse them"* note about the two NeuralFoil model
    sizes (`large` interactive vs `xxxlarge` backfill).
  - Confidence: 🟢

- [ ] **T-05 — The three escaped variables.**
  `SQLALCHEMY_DATABASE_URL` (`db/session.py:8`), `LOG_LEVEL`
  (`logging_config.py:7`, with `getattr(logging, name, DEBUG)`),
  `DISPLAY_CONSTRUCTION_STEP` (`construction_plan_service`).
  - Legacy origin: the three files above
  - Definition of done: reproduced **and recorded as gaps**. The DB URL is
    arguably a bootstrap exception (a settings import from `db/session` would
    invert the dependency); the other two are not. The silent `LOG_LEVEL`
    fallback must be characterised in a test.
  - Confidence: 🟢

- [ ] **T-06 — `.env.example`.**
  One entry per setting, with a placeholder value and a short comment; no real
  secrets.
  - Legacy origin: `.env.example` (documents ~30 hub model ids and the gh-929
    note that superseded the RAG plan)
  - Definition of done: every field of both classes plus the three escaped
    variables appears. This is the project's documented rule for adding a
    setting.
  - Confidence: 🟢

### Remediation (behaviour changes — each needs a decision)

- [ ] **T-07 — Reconcile the version strings.**
  Choose one source and make `/health`, the FastAPI app and `core.config` agree.
  - Legacy origin: G-12; `core/config.py:21`, `settings.py:84`, `main.py:200`
  - Definition of done: one value, one owner, asserted by a test that compares
    `/health`'s `version` with the OpenAPI `info.version`.
  - Confidence: 🟡 (a decision)

- [ ] **T-08 — Merge or clearly separate the two `Settings` classes.**
  Either one class with both field groups, or two classes with **different
  names** and documented scopes.
  - Legacy origin: TD-39
  - Definition of done: no import ambiguity — a reader can tell from
    `from ... import settings` which object they have. Both consumer lists are
    in `requirements.md`; every one must be migrated.
  - Confidence: 🟡 (a decision)

- [ ] **T-09 — Move `LOG_LEVEL` and `DISPLAY_CONSTRUCTION_STEP` into settings**
  and warn on an invalid log level.
  - Legacy origin: `app/CLAUDE.md`'s "no scattered `os.getenv`" rule
  - Definition of done: an invalid level logs a warning instead of silently
    becoming DEBUG.
  - Confidence: 🟡 (a decision)

- [ ] **T-10 — Log the effective configuration at startup.**
  Database URL (credentials masked), resolved artifacts dir, copilot model,
  detected capabilities.
  - Legacy origin: — (nothing exists)
  - Definition of done: one INFO line at startup that answers "what is this
    process configured with?".
  - Confidence: 🟡 (a decision)

## Test Tasks

- [ ] **TT-01 — CWD independence:** `AIRFOILS_DIR` and `REPO_ROOT` unchanged
      from another working directory.
- [ ] **TT-02 — Artifacts resolution:** a relative override becomes absolute.
- [ ] **TT-03 — Secret masking:** the copilot key is absent from `repr` and from
      a formatted log line; `.get_secret_value()` returns it.
- [ ] **TT-04 — `extra="ignore"`:** an unknown `.env` key does not raise.
- [ ] **TT-05 — Memoisation:** `get_settings()` returns the same object twice.
- [ ] **TT-06 — Mutable defaults:** two instances do not share `low_re_grid`.
- [ ] **TT-07 — Version divergence (characterisation):** the three values
      differ and `/health` reports `"0.1.0"`.
- [ ] **TT-08 — `LOG_LEVEL` fallback (characterisation):** an invalid level
      silently becomes DEBUG.
- [ ] **TT-09 — Defaults with no `.env`:** every field takes its documented
      default and the app still starts.
- [ ] **TT-10 — Model sizes:** `low_re_neuralfoil_model_size == "xxxlarge"` and
      the per-request endpoint still uses `"large"`.

## Suggested Order

1. **T-01** the absolute paths first — they are module constants other modules
   import at their own import time.
2. **T-02 → T-03** both `Settings` classes as they are. Do **not** merge them
   while characterising; both have live consumers and merging is T-08.
3. **T-04** the low-Re tables, with TT-06 guarding the mutable defaults.
4. **T-05** the three escaped variables, each with a characterisation test.
5. **T-06** `.env.example`, once the full field set is known.
6. **T-07 → T-10** the remediations, each behind an explicit decision. T-07
   (versions) is the cheapest and most visible; T-08 (merge) is the largest and
   touches every consumer.

## Pending Gaps

- **Which version string is authoritative**, and should `/health`, the OpenAPI
  document and `core.config` all report it?
- **Should the two `Settings` classes merge**, or at least stop sharing a name?
- **Should `LOG_LEVEL` and `DISPLAY_CONSTRUCTION_STEP` move into settings**, per
  the project's own rule?
- **Is `SQLALCHEMY_DATABASE_URL` a permanent bootstrap exception**, or should the
  dependency be inverted?
- **Should an invalid `LOG_LEVEL` warn** instead of silently becoming DEBUG?
- **Should the three unread settings be removed** (`PROJECT_NAME`,
  `openai_api_key`, `COPILOT_EMBEDDING_MODEL`)?
- **Should `base_url` default to port 8001**, matching where the service
  listens?
- **Should the effective configuration be logged at startup?**
- **Should `app/settings.py` expose one access path** instead of both a module
  singleton and a separately-cached `get_settings()`?

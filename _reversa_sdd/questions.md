# Questions for Validation — da3Dalus (cad-modelling-service)

> Reorganised by the **Reversa Reviewer** on 2026-07-31 from the accumulated
> writer-phase notes (2 298 lines, eight clusters), de-duplicated and grouped by
> module.
>
> **These are the questions only you can answer.** Everything that could be
> settled from the source has been settled and moved to
> [`gaps.md`](gaps.md) / [`confidence-report.md`](confidence-report.md). What
> remains is *intent*: which of two plausible behaviours was meant, what a
> constant was calibrated against, and which of several competing sources is
> authoritative.

## How to answer

1. Fill in the `**Answer:**` line under each question. Free text is fine — a
   sentence is usually enough. "Don't care / pick one" is a valid answer.
2. You do **not** have to answer all of them. Start with the **Blocking** list
   below; everything else improves the spec but does not stop a re-implementation.
3. When you are done, type `reversa` and I will fold the answers back into the
   affected specs, reclassify 🔴 → 🟢/🟡, and update the confidence report.

## Blocking — answer these first (12)

These are the ones where a re-implementer would otherwise have to guess, and
where guessing wrong produces silently wrong numbers or a security regression.

| | Question | Why it blocks |
|---|---|---|
| 1 | [Q-CC-1](#q-cc-1--is-no-application-authentication-a-permanent-product-position) | Determines whether ~40 destructive MCP tools may be made to work at all |
| 2 | [Q-MC-1](#q-mc-1--mcp-writes-are-discarded-fix-the-transaction-boundary-or-formalise-mcp-as-read-only) | Fix vs formalise changes the whole module's contract |
| 3 | [Q-FD-2](#q-fd-2--what-unit-is-an-uploaded-step-assumed-to-be-in) | A mm-authored upload is stored 1000× too large, silently |
| 4 | [Q-MB-1](#q-mb-1--two-mass-producers-write-one-column-which-one-wins) | Aircraft mass currently depends on edit order |
| 5 | [Q-MS-1](#q-ms-1--power_to_weight-is-w-kg-in-the-catalogue-and-t-w-shaped-in-seven-presets-which-is-canonical) | The `trainer` preset declares a 0.5 W/kg aircraft |
| 6 | [Q-AA-1](#q-aa-1--_auto_populate_cd0-writes-total-cd-into-the-cd0-assumption-delete-or-rewrite) | Corrupts the single source of truth for nine consumers |
| 7 | [Q-WD-1](#q-wd-1--who-should-own-the-gh-772-mixing-name-mapping-open-bug-955) | Every V-tail / elevon aircraft reports wrong control authority |
| 8 | [Q-VI-1](#q-vi-1--wiring-the-ss_control-post-pass-changes-what-an-import-produces-go-ahead) | Turning it on starts creating TEDs that nothing downstream has seen |
| 9 | [Q-CG-1](#q-cg-1--3mf-export-is-broken-and-a-test-pins-the-bug-fix-the-mapping-or-drop-the-format) | Two of five advertised export formats do not work |
| 10 | [Q-CP-1](#q-cp-1--should-plan-execution-move-into-the-cad-process-pool-or-is-adr-0005-wrong) | ADR 0005 and the code contradict each other |
| 11 | [Q-VS-1](#q-vs-1--snapshots-are-not-actually-immutable-should-the-guard-cover-every-write-path) | The guarantee the whole versioning model rests on |
| 12 | [Q-CC-10](#q-cc-10--should-assumption_computation_context-become-a-versioned-validated-contract) | ~40 keys, 9 consumers, schemaless, silent per-consumer fallbacks |

---

# Cross-cutting — product and platform decisions

## P-WARN-0 — Is there ONE mandatory structured warning channel?

> **Added during the interview** (2026-08-13). This policy was never asked as
> itself — only as 34 separate instances across 13 modules. It is the
> highest-leverage decision in the catalogue.

**Context:** ADR 0012 states that a computation which cannot produce a physically
meaningful number must surface that — categorised and visible — instead of
substituting a default. Two subsystems honour it (the parabolic polar fit's six
categorised `PolarRejection` gates; the turbulator optimiser), and each invented
its own shape. ~30 places violate it, largely because **there is nothing to emit
into**: the ~40-key computation context's per-consumer RC defaults (`cd0 0.03`,
`e 0.8`, `AR 8.0`, `S 0.5 m²`, `mass 1.0 kg`), `_build_speed_polar`'s 1.0 kg,
`DEFAULT_E_OSWALD = 0.8`, the sewing-tolerance retry, `inject_cdcl`'s truncating
loop, per-wing conversion drops, swallowed `ImportError`/`FileNotFoundError`, and
`except Exception: pass` in the copilot retarget.

**Answer:** **(a) One shared, mandatory `DesignWarning` channel — with severity
semantics that distinguish engineering practice from defect.** _Answered by the
maintainer, 2026-08-13._

**The rule is NOT "no fallbacks". It is "no _undeclared_ fallbacks."**
The maintainer's objection is adopted as part of the policy: several substitutions
are legitimate engineering practice and must remain possible. What is forbidden is
performing them *invisibly*.

```
DesignWarning:
  code      stable machine token — OSWALD_FIT_NOT_CONVERGED |
            SEWING_TOLERANCE_RELAXED | ASSUMPTION_KEY_MISSING | …
  category  substituted_assumption | fit_not_converged | geometry_healed |
            input_missing | result_truncated | capability_unavailable
  severity  notice   → legitimate, declared substitution (domain practice)
            warning  → number usable, confidence reduced
            error    → number not physically meaningful; do not build on it
  message   human-readable, including the justification
  context   the concrete numbers (value used, Re regime, residual, missing key)
```

Every response whose numbers were degraded carries `warnings: [DesignWarning]`.
ADR 0012 is amended to name this channel.

**Worked classification (agreed):**

| Case | Classification | Rationale |
|---|---|---|
| Sewing tolerance 1 mm → 5 mm | `notice` · `geometry_healed` | Standard CAD healing; user should still know healing occurred |
| `e = 0.8` because the fit does not converge at **low Re** | `notice` · `fit_not_converged` | Model limitation, not a design fault; 0.8 is a defensible domain value — but `e` was *assumed*, not *determined* |
| `e` fallback masking **`k ≤ 0` / unphysical `e`** | `warning`/`error` · `fit_not_converged` | A design or data problem — must NOT be hidden behind 0.8 (consistent with the maintainer's earlier ruling) |
| `mass = 1.0 kg` because the context key was missing | `error` · `input_missing` | A placeholder unrelated to the aircraft — a defect, not engineering |

Note that the last three cases are **indistinguishable today**: all are the same
silent substitution.

**Why severity is load-bearing, not decoration:** without it the channel becomes
noise. If a routine tolerance heal is as loud as a missing mass, warnings stop
being read within weeks — which is worse than the status quo. `notice` may be
rendered subtly (e.g. an "assumed" marker beside the number); `error` must be
prominent.

**Resolves or constrains (34):** `Q-CC-10` · `Q-AC-7` · `Q-AC-8` · `Q-WD-6` ·
`Q-WD-8` · `Q-WD-10` · `Q-FD-4` · `Q-FD-6` · `Q-AF-8` · `Q-AF-9` · `Q-CP-3` ·
`Q-CP-9` · `Q-VI-3` · `Q-VI-5` · `Q-VI-7` · `Q-AA-1` · `Q-AA-3` · `Q-AV-5` ·
`Q-AV-7` · `Q-MS-4` · `Q-MS-5` · `Q-MS-8` · `Q-MS-9` · `Q-MS-10` · `Q-MS-12` ·
`Q-PT-1` · `Q-PT-2` · `Q-PT-8` · `Q-PT-12` · `Q-CO-2` · `Q-CO-3` · `Q-MC-4` ·
`Q-MC-5` · `Q-PC-1`

---

## P-DEAD-0 — What is the default disposition of complete-but-unreachable code?

> **Added during the interview** (2026-08-13). Like `P-WARN-0`, this policy was
> never asked as itself — only as 30 separate instances.

**Context:** ~30 places in the corpus hold complete but unreachable code. They are
**not equivalent**. Three are *finished safety or confidence mechanisms sitting
switched off*: `Q-AV-3` (AVL replay artefacts), `Q-VI-2` (`validate_geometry`, the
±1 % span/area/MAC cross-check after OpenVSP import, never wired), `Q-CG-4`
(background re-tessellation, GH #202). Others have no retention argument at all
(`Q-CC-16`; `Q-CT-5`'s `scaleXyz` with its typo'd `y_sacle` parameter). A third
group is scaffolding for planned work (mid-wing `AddXsec`, copilot conversation
branching).

**Answer:** **(a) A decision procedure, with "inert" forbidden.** _Answered by the
maintainer, 2026-08-13._

> **Deleting is the default.** Exceptions are allowed, but the **inert** state —
> finished code that is neither active nor removed — is **not**.
>
> 1. **Finished safety/confidence mechanism** → decide **wire it or delete it**.
>    Leaving it in place is not an option.
> 2. **Scaffolding for planned work with a live ticket** → keep, but behind an
>    explicit `# UNREACHABLE(gh-N)` marker **plus a test asserting it stays
>    unreachable**, so it cannot silently half-activate.
> 3. **Anything else** → **delete**, and record it in the spec as removed.

**Rationale:** "inert" is the single state in which all costs are paid — reading
cost, maintenance cost, review cost — for zero benefit, while creating the false
impression that a protection exists. That last point is the decisive one for the
three switched-off safety mechanisms: an unwired `validate_geometry` reads like an
import is being sanity-checked when it is not.

**Applies to (30):** `Q-CC-14` · `Q-CC-16` · `Q-AC-1` · `Q-AC-9` · `Q-CT-1` ·
`Q-CT-3` · `Q-CT-5` · `Q-CG-1` · `Q-CG-4` · `Q-CP-2` · `Q-FD-8` · `Q-VI-1` ·
`Q-VI-2` · `Q-AV-3` · `Q-AV-8` · `Q-AA-2` · `Q-AA-8` · `Q-MS-13` · `Q-MB-2` ·
`Q-MB-3` · `Q-MB-10` · `Q-VS-3` · `Q-CO-1` · `Q-CO-5` · `Q-CO-6` · `Q-CO-8` ·
`Q-CO-10` · `Q-MC-7` · `Q-PT-12` · `Q-FW-8`

**Note:** the three finished mechanisms (`Q-AV-3`, `Q-VI-2`, `Q-CG-4`) still need
an individual wire-or-delete verdict; this policy only forbids the third answer
("leave as is").

---

## Q-CC-1 — Is "no application authentication" a permanent product position?

**Context:** `app/core/security.py` is a 4-line `verify_token` comparing against
the literal `"valid_token"`, with no callers. REST, `/docs`, `/redoc`,
`/static`, `/assets` and `/mcp` are all open. ADR 0016 records that the
deployment tunnel (ngrok + oauth2-proxy + Caddy) is the trust boundary — but
nothing in the application enforces that the tunnel is present: no trusted-proxy
check, no forwarded-identity header, no bind-address restriction, and
`run_mcp_server()` hard-codes `0.0.0.0:8001` ignoring `UVICORN_HOST`.
**Spec affected:** [`_reversa_sdd/platform-core/requirements.md`],
[`_reversa_sdd/permissions.md`], [`_reversa_sdd/adrs/0016-…md`]
**Question:** Is the boundary intended to stay entirely in the proxy chain
permanently, or is auth deferred? And should the app refuse to bind to a
non-loopback interface without an explicit opt-in?
**Impact:** Decides whether the spec describes a deliberately unauthenticated
service (and says so prominently) or an unfinished one. Also gates Q-MC-1 —
fixing the MCP commit bug on an unauthenticated endpoint makes
`delete_aeroplane` genuinely reachable.

**Answer:** **(a) Permanently unauthenticated by design, plus an exposure guard.**
_Answered by the maintainer, 2026-08-13._

**Product position (authoritative):** da3Dalus is a **single-user, standalone
desktop application** run on one machine by one private user. Real multi-user
capability is a *future vision*, to be revisited only once core functionality is
stable — it is deliberately out of scope now. The spec must state
"unauthenticated **by design**", not "unfinished".

**ADR 0016 is to be corrected.** It frames the ngrok + oauth2-proxy + Caddy chain
as *the system's access control*. It is not: it is the **maintainer's own testing
tool** for sharing a preview. `permissions.md` and ADR 0016 must be reworded so
the spec does not claim a protection that does not exist in the product.

**Exposure guard — three concrete changes** (note: an app-side *bind* guard is
impossible when uvicorn is launched from the CLI, because uvicorn opens the socket
before the app loads; so the guard lives at the launch surfaces):

1. **Local / bare uvicorn:** drop `--host 0.0.0.0` from the documented dev command
   in `CLAUDE.md` / `AGENTS.md`. Uvicorn's own default is already `127.0.0.1`, so
   the safe default is obtained by *removing* the flag that currently disables it.
   Binding publicly stays possible by passing the flag deliberately.
2. **Docker:** publish to host loopback only — `ports: ["127.0.0.1:8086:8000"]`.
   `--host 0.0.0.0` **stays** inside the container (mandatory there, otherwise the
   published port is dead). The trust boundary under Docker is the *publish*
   address, not the bind address. Public exposure for ngrok testing is an explicit
   opt-in (edit the line or use a `docker-compose.override.yml`).
3. **`run_mcp_server()`:** stop hard-coding `0.0.0.0:8001`; respect `UVICORN_HOST`
   and default to loopback. This is the one path where the app *does* call
   `uvicorn.run()` itself, so it is genuinely enforceable.

Additionally: emit a **startup log line stating the effective reachability**, and
warn when a non-loopback bind is detected without an explicit `ALLOW_PUBLIC_BIND`
opt-in. The app cannot *prevent* it, but it must not be silent about it.

**Note (Linux):** Docker's published ports install rules in the `DOCKER` iptables
chain that **bypass `ufw`/`firewalld`**, so a host firewall does not protect a
`8086:8000` publish. Recorded because the project may not always run on macOS.

**Consequences for downstream questions:**
- `Q-MC-1` (MCP writes discarded) becomes safe to **fix**: with loopback defaults
  the ~40 destructive tools are not reachable off-box, so it is an ordinary bug fix.
- `created_by` stays **agent provenance** (human vs AI), *not* user identity —
  there is only one user. Feeds `Q-CC-9`.
- Per-user quota (`Q-CO-9`), asset-registry externalisation (`Q-MC-3`), MCP
  standalone exposure (`Q-MC-7`) are **deliberately out of scope, documented as
  such**, to be revisited if and when multi-user arrives.

---

## Q-CC-2 — Should a sanitised copy of `deploy/` be committed?

**Context:** `deploy/` is gitignored, so the only access control the system has
is not reproducible from a clone. A fresh checkout cannot recreate the boundary
that ADR 0016 relies on.
**Spec affected:** [`_reversa_sdd/permissions.md`],
[`_reversa_sdd/platform-core/requirements.md`]
**Question:** Should a secret-free version of the ngrok / oauth2-proxy / Caddy
scaffold be committed so the boundary is version-controlled and reviewable?
**Impact:** Determines whether the deployment topology belongs in the spec at all
or stays an operational secret.

**Answer:** **(c′) Version it — in a separate PRIVATE repository, not as a git
submodule, and not in this repo.** _Answered by the maintainer, 2026-08-13._

**Premise correction:** this question's original justification (ADR 0016 makes the
proxy chain the system's only access control, therefore it must be reviewable) is
**void** after `Q-CC-1`: the tunnel is the maintainer's testing tool, not a product
security control. What remains is a *reproducibility* argument — `deploy/stages.sh`
is live development tooling (PR smoke tests at `https://<domain>/pr-<n>/`) and
would be lost with the machine.

**Decisive context:** `szymansk/da3Dalus` is a **public** repository.
Verified during this interview: `deploy/` has **never** been committed, and the
GitHub client secret does **not** appear anywhere in the last 200 commits — no
remediation is needed.

**Decision:**
- The `deploy/` tooling is versioned in a **separate private repository**, cloned
  into the already-gitignored `deploy/` path of this checkout.
- **Not** a git submodule. Two concrete reasons: (1) `.gitmodules` is committed, so
  a submodule in a public repo **publishes the private repo's URL** and makes
  `git clone --recurse-submodules` fail for everyone without access; (2) `deploy/`
  is already ignored here, so a plain private clone at that path works with none of
  the submodule machinery (no `--init`, no detached HEADs, no sync step).
- In the private repo: `.env` and all `*.log` / `*.out` runtime artefacts stay
  ignored; a secret-free `.env.example` is committed (the existing `.env` already
  carries the TODO placeholder block that becomes its content).
- **Housekeeping:** the accumulated runtime artefacts currently in `deploy/`
  (`backend.log`, `caddy.log`, `ngrok.log`, `frontend.log`, `oauth2-proxy.log`,
  `refresh_*.out`, `stages*.out`, `start.out`) should be cleaned up — they do not
  belong there even locally.

**What the public spec records:** `permissions.md` states that the preview/tunnel
configuration is **private maintainer tooling held outside this repository**, and
does not describe it as an access-control mechanism of the product.

**Rejected:** (a) committing a sanitised scaffold here — on a public repo it keeps
a live "one careless `git add` leaks the client secret" failure mode, for no
benefit to a re-implementer; (b) prose-only — loses the tooling on machine loss.

---

## Q-CC-3 — Which HTTP error envelope is the contract?

**Context:** Two shapes coexist. The three global handlers in `app/main.py` emit
`{"error": {code, message, details}}`. Per-module `_raise_http` / `_call` helpers
emit FastAPI's `{"detail": …}` — `mission-and-sizing` alone ships **five**
distinct local mappers across nine endpoint modules, and `mass-and-balance`,
`versioning`, `ai-copilot` and `construction-plans` each have their own. The
frontend's `lib/parseApiError.ts` exists solely to absorb the difference.
Additionally, `matching_chart.py` and `field_lengths.py` deliberately map a bare
`ServiceException` to **422** while every other handler maps it to **500**.
**Spec affected:** [`_reversa_sdd/platform-core/contracts.md`] and every module's
`contracts.md`
**Question:** Which envelope should a client code against — and should the
deliberate 422 semantics survive as an explicit `ValidationDomainError`?
**Impact:** Every module's `contracts.md` error table, and whether
`parseApiError.ts` can be deleted.

**Answer:** **(a) `{"error": {code, message, details}}` is the single contract,
everywhere — and the deliberate 422 becomes an explicit exception type.**
_Answered by the maintainer, 2026-08-13._

**Required:**
- One envelope for every error response. The per-module `_raise_http` / `_call`
  mappers are **deleted** — including the five distinct local mappers in
  `mission-and-sizing` and the separate ones in `mass-and-balance`, `versioning`,
  `ai-copilot` and `construction-plans`.
- The frontend's `lib/parseApiError.ts` is **removed**; it exists only to absorb the
  divergence being eliminated.
- The deliberate 422 semantics of `matching_chart.py` and `field_lengths.py` are
  preserved as a **named type** — `ValidationDomainError → 422` — so the behaviour
  is reproducible and applies uniformly, rather than surviving as a habit in two
  files. Everywhere else a bare `ServiceException` continues to map to 500.
- Every module's `contracts.md` error table is updated to the single envelope.

**Why the usual objection does not apply:** "changing the envelope is a breaking
change for clients parsing `detail`" — per `Q-CC-1` this is a **single-user
application with no external API consumers**. Every consumer (the frontend and the
MCP layer) lives in this repository, so the migration is internal and mechanical.

**User-visible motivation:** the same cold-start mistake — e.g. requesting a
matching chart before design assumptions exist — currently yields a helpful 422
with a remediation hint on two endpoints and a bare 500 on every other. Identical
user error, entirely different feedback (this is the cost recorded in `Q-MS-8`).

**Consequences for downstream questions:** settles the envelope half of `Q-CC-6`,
`Q-AC-2`, `Q-AC-6`, `Q-FD-1`, `Q-WD-9`, `Q-AF-5`, `Q-MS-8`, `Q-MB-10`, `Q-PT-11`,
`Q-VS-3`, `Q-MC-4`, `Q-FW-2` — those now reduce to "which status code", not "which
shape".

---

## Q-CC-4 — Two `Settings` classes and three version strings: which is canonical?

**Context:** `app/core/config.py` and `app/settings.py` both define a class named
`Settings`, both export a module-level `settings`, both read `.env`, with
disjoint fields and different naming conventions (SCREAMING_CASE vs snake_case)
and live consumers on both sides. `app/settings.py` additionally exposes a module
singleton **and** a separately-`lru_cache`d `get_settings()` returning a
*different* instance. Three version strings coexist:
`core.config.VERSION = "1.0.0"`, `settings.version = "0.1.0"` (the one `/health`
reports) and `FastAPI(version="2.0.0")`. Three more settings escape both classes
via bare `os.getenv`: `SQLALCHEMY_DATABASE_URL`, `LOG_LEVEL`,
`DISPLAY_CONSTRUCTION_STEP`.
**Spec affected:** [`_reversa_sdd/platform-core/config-and-settings/requirements.md`]
**Question:** Should the two classes merge, and which version string identifies a
release? Is the DB URL a deliberate bootstrap exception?
**Impact:** The spec currently has to document both classes as equally real.

**Answer:** **(a) Merge into one `Settings` class with one instance, and one
version source.** _Answered by the maintainer, 2026-08-13._

**Required:**
1. **One class, one instance.** `app/core/config.py` and `app/settings.py` are
   merged. Critically, the current **double-instance bug** disappears:
   `app/settings.py` today exports a module-level singleton *and* an
   `lru_cache`d `get_settings()` that returns a **different object**, so
   `from app.settings import settings` and `get_settings()` observe different
   state — they diverge the moment either is adjusted (notably in tests).
2. **One naming convention** (the merged class picks one; today it is
   `SCREAMING_CASE` on one side and `snake_case` on the other).
3. **One version source.** The three coexisting strings —
   `core.config.VERSION = "1.0.0"`, `settings.version = "0.1.0"` (the value
   `/health` actually reports) and `FastAPI(version="2.0.0")` (the value in the
   OpenAPI document) — collapse to a single source, preferably derived from
   `pyproject.toml`, so release, `/health` and OpenAPI cannot disagree. Today a
   response cannot be attributed to a build.
4. **Fold in the three `os.getenv` escapees** — `SQLALCHEMY_DATABASE_URL`,
   `LOG_LEVEL`, `DISPLAY_CONSTRUCTION_STEP`.

**Permitted exception, to be verified during implementation:**
`SQLALCHEMY_DATABASE_URL` may remain a bare `os.getenv` bootstrap read **if**
Alembic requires it before the settings object can be constructed. If so, it is
documented as a deliberate bootstrap exception rather than an oversight.

**Related:** the `base_url` 8000-vs-8001 defect is a symptom of the same missing
ownership and should be re-checked once the merge lands.

---

## Q-CC-5 — Should the German user-facing strings be translated?

**Context:** In an otherwise English product with an explicit English-only UI
rule: `"name existiert bereits"` (IntegrityError → 409) and
`"Ungültige Eingabedaten"` (RequestValidationError → 422) in `app/main.py`; the
`PolarRejection.hint` strings surfaced to the UI whenever
`category == "design"`; the seeded component-type labels (`"Durchmesser"`,
`"Steigung"`, `"Blätter"`, `"Dauerstrom"`) rendered directly in the component
editor; and the `flight_profiles` handler docstrings, which appear verbatim in
the OpenAPI document.
**Spec affected:** [`_reversa_sdd/platform-core/requirements.md`],
[`_reversa_sdd/powertrain/cots-powertrain-components/requirements.md`],
[`_reversa_sdd/aero-analysis/aero-context-single-source/requirements.md`]
**Question:** Translate all of them? Changing the two handler messages is a
client-visible change; changing the seeded labels needs a data migration.
**Impact:** Whether the spec records these as behaviour to reproduce or as debt
to fix.

**Answer:** **(a) Translate all of them.** _Answered by the maintainer, 2026-08-13._

Consistent with the project's existing English-only UI rule; the current mixture is
recorded as **debt to fix**, not behaviour to reproduce.

Scope:
- `"name existiert bereits"` (IntegrityError -> 409) and `"Ungueltige Eingabedaten"`
  (RequestValidationError -> 422) in `app/main.py` -- client-visible change, accepted
  (no external API consumers, per `Q-CC-1`).
- `PolarRejection.hint` strings surfaced whenever `category == "design"` -- these are
  **deliberately user-facing** (gh-956), so they matter most.
- Seeded `component_types` labels -- `Durchmesser` -> Diameter, `Steigung` -> Pitch,
  `Blaetter` -> Blades, `Dauerstrom` -> Continuous current. Requires a small data
  migration.
- `flight_profiles` handler docstrings -- they appear verbatim in the OpenAPI
  document, which is now a spec artefact, so they are in scope too.

Domain terms are translated by meaning rather than transliterated.

---

## Q-CC-6 — Is the `/api/v2` prefix on the importer the mistake, or are the other 229 routes missing one?

**Context:** 229 of 230 route decorators are mounted at the application root
(`/aeroplanes/…`, `/airfoils/…`, `/components/…`); `openvsp_import` alone is
included with `prefix="/api/v2"` and answers at `/api/v2/import/openvsp`. Every
client must special-case it.
**Spec affected:** [`_reversa_sdd/openapi/da3dalus-v2.yaml`],
[`_reversa_sdd/platform-core/requirements.md`] (BR-PC2)
**Question:** Which is the intended public shape?
**Impact:** Whichever way it is resolved, it is a breaking change for someone —
the spec should say which direction was intended.

**Answer:** **(a) Align the outlier — drop the `/api/v2` prefix so all 230 routes
sit at the application root.** _Answered by the maintainer, 2026-08-14._

229 of 230 route decorators are mounted at the root (`/aeroplanes/…`,
`/airfoils/…`, `/components/…`); only `openvsp_import` is included with
`prefix="/api/v2"`. Removing that prefix is **one line in the backend and one call
site in the frontend**; the reverse (lifting 229 routes) would touch every route
plus all 48 SWR hooks for no benefit.

**Why now:** `Q-CC-11` introduces a **generated** TypeScript client. Whatever shape
the OpenAPI document has at that point gets baked into generated code, so the
inconsistency must be removed before generation, not after.

**Why the usual objection does not apply:** per `Q-CC-1` there are **no external API
consumers**, so a URL change is cheap in either direction. This is purely a
consistency decision. Explicit URL versioning (option b) buys little without third
parties, and the API version remains visible in the OpenAPI document itself.

---

## Q-CC-7 — Will PostgreSQL ever actually be used?

**Context:** `construction_plans.aeroplane_id` is a `String` FK onto an `Integer`
PK — SQLite tolerates it, PostgreSQL would reject the constraint outright. Two
more tables (`component_tree`, `construction_parts`) reference the aeroplane by
an unconstrained `String` UUID with no FK at all, so deleting an aeroplane
orphans tree nodes, parts and their files. `.env.example` mentions PostgreSQL.
**Spec affected:** [`_reversa_sdd/erd-complete.md`],
[`_reversa_sdd/aeroplane-core/requirements.md`],
[`_reversa_sdd/construction-plans/construction-parts/requirements.md`]
**Question:** If PostgreSQL is a real target these three tables need a migration
to real FKs; if it is not, the `.env.example` mention should go. Which?
**Impact:** Also decides Q-VS-4 — the clone-coverage test can only *see* tables
with real `ForeignKey` objects, so real FKs would close that blind spot too.

**Answer:** **(b) SQLite now, PostgreSQL left open — but migrate the three tables
to real foreign keys now.** _Answered by the maintainer, 2026-08-13._

The decision is **not** motivated by PostgreSQL. It is motivated by two defects
that exist today under SQLite:

1. **Orphaned rows and files.** Deleting an aeroplane leaves `component_tree` nodes
   and `construction_parts` rows — including their files on disk — behind, because
   there is no FK and therefore no cascade.
2. **The versioning clone-coverage test is blind to exactly these tables.** It
   discovers related tables by introspecting SQLAlchemy `ForeignKey` objects, so
   soft `String` references are invisible to it. That test is the only structural
   guard against silently dropping a table's data when branching or snapshotting —
   i.e. this directly endangers epic #901.

**Required:**
- Migrate `construction_plans.aeroplane_id` (currently a `String` FK pointing at an
  `Integer` PK — an invalid constraint that only SQLite tolerates),
  `component_tree.aeroplane_id` and `construction_parts.aeroplane_id` to **real
  `ForeignKey` columns with an explicit `ondelete` policy**.
- Decide and document the delete policy per table (cascade vs restrict); for
  `construction_parts`, the on-disk file lifecycle must follow the row lifecycle.
- Keep the `.env.example` PostgreSQL mention — PostgreSQL stays a *possible* future
  target, deliberately neither committed to nor excluded.
- Do it **now, while single-user**: the data volume is small and the migration is
  cheap; it gets progressively more expensive later.

**Consequences for downstream questions:** resolves the structural half of
`Q-VS-4` (soft refs → real FKs) and `Q-VS-5` (clone coverage for
`construction_parts`); constrains `Q-CP-9` (construction-part storage lifecycle)
and `Q-AF-7`. Does **not** by itself decide `Q-CC-9` (closed-set CHECK constraints)
— that remains open and is asked separately in Wave 1.

---

## Q-CC-8 — Is single-process operation a permanent constraint?

**Context:** The `JobTracker`, the CAD task registry, the MCP `ASSET_REGISTRY`
and the frontend tessellation cache are all per-process with no persistence. A
restart loses every pending retrim/recompute; a task started before a reload
becomes unqueryable (404) though its worker may still run; an `img://…` URI
minted by one worker is a 404 in another; and a cross-thread schedule is dropped
silently after a 2 s timeout.
**Spec affected:** [`_reversa_sdd/platform-core/background-jobs-invalidation/requirements.md`],
[`_reversa_sdd/cad-generation/requirements.md`],
[`_reversa_sdd/mcp-server/requirements.md`]
**Question:** Is single-worker deployment a permanent assumption, or should these
become persisted job rows / a real queue?
**Impact:** Decides whether ~8 separate gaps are "won't fix, documented" or one
shared work item.

**Answer:** **(a) Single-worker operation is permanent, and asserted at startup.**
_Answered by the maintainer, 2026-08-13._

Follows directly from the product position in `Q-CC-1`: a single-user standalone
desktop application. Per-process state is therefore **legitimate architecture, not
debt** — but it must be *enforced* rather than merely assumed.

**Required:**
- The application **refuses to start** when configured with more than one worker
  (`--workers > 1` / equivalent env). Failing loudly at boot is preferable to the
  silent, data-dependent breakage that a second worker causes today.
- Process-locality is recorded in the spec as a **deliberate architectural
  constraint**, with the four in-memory stores named explicitly (`JobTracker`, the
  CAD task registry, the MCP `ASSET_REGISTRY`, the frontend tessellation cache).
- The known consequences are documented as accepted behaviour, not as open bugs:
  a restart drops pending retrim/recompute jobs; a task started before a `--reload`
  becomes unqueryable; `img://…` asset URIs are process-scoped.

**No conflict with ADR 0005:** that ADR's `ProcessPoolExecutor` is *intra*-process
(worker processes owned by the one server process), which is unaffected.

**Explicit caveat — this does NOT resolve `Q-CG-2`.** The CAD export race is
between the four workers *inside* the pool of a single process, all writing to the
same `./tmp/exports` directory. It remains a real defect and must be fixed
independently (per-task directory), regardless of this answer.

**Consequences for downstream questions:** the multi-process framing of `Q-CG-5`,
`Q-CO-5`, `Q-MC-3`, `Q-PC-2`, `Q-PC-3`, `Q-PC-4`, `Q-PC-5`, `Q-FW-5` collapses to
"documented single-process constraint"; only defects that are *intra*-process
(notably `Q-CG-2`) survive as real work.

---

## Q-CC-9 — Should the closed sets become database enums or check constraints?

**Context:** `component_tree.node_type`, `weight_items.category`,
`construction_plans.plan_type`, the TED `role` and `created_by` are all validated
in Pydantic only; the DB columns are plain `String`. The sharpest case is
`created_by`: **four writers, three vocabularies** — the column comment and
`BranchRequest` document `'human' | 'ai'`, `copilot_apply_service` writes
`'copilot'`, and legacy `aeroplanes.created_by` is `NULL` and unbackfilled.
**Any UI filtering on `'ai'` misses every copilot branch.**
**Spec affected:** [`_reversa_sdd/versioning/copilot-provenance/requirements.md`],
[`_reversa_sdd/erd-complete.md`], [`_reversa_sdd/permissions.md`]
**Question:** What is the intended `created_by` vocabulary, and should it become
a constrained enum before the UI filters on it? Same question for the other four
columns.
**Impact:** `permissions.md` §6 notes this is the seam any future identity model
would attach to.

**Answer:** **(a) Canonical vocabulary `human` | `ai` (agent detail in a separate
field), NULLs backfilled, and DB CHECK constraints on the genuinely closed
columns.** _Answered by the maintainer, 2026-08-13._

**Vocabulary.** Per `Q-CC-1`, `created_by` is **originator class (human vs AI), not
user identity**. The canonical set is therefore exactly two values:

- `created_by ∈ {'human', 'ai'}` — the class.
- The specific agent goes in a **separate detail field** (e.g.
  `created_by_agent = 'copilot' | 'mcp' | …`), *not* into `created_by`.

Rationale: `'copilot'` as a third class value breaks the "made by AI" filter again
the moment a second AI writer appears (MCP agent, an autonomous optimiser). With
the class/detail split the filter keeps working, and specificity is still available.

**Required migration:**
- `copilot_apply_service` writes `created_by='ai'` + `created_by_agent='copilot'`
  instead of `'copilot'`.
- Backfill legacy `aeroplanes.created_by IS NULL` → `'human'` (those rows predate
  the copilot).
- Fix the column comment and `BranchRequest` documentation to match.

**Enforcement.** DB-level `CHECK` constraints on the genuinely closed columns —
`created_by`, `component_tree.node_type`, `construction_plans.plan_type`, the TED
`role`. Consistent with the FK migration accepted in `Q-CC-7`; works in both SQLite
and PostgreSQL. Accepted cost: adding a value later requires a migration.

**Caveat:** check whether `weight_items.category` is genuinely closed before
constraining it. If it is intended to grow, leave it unconstrained and rely on
Pydantic plus a contract test rather than paying a migration per new category.

**Motivating defect:** today a UI filter on `'ai'` **misses every copilot branch**,
because four writers use three vocabularies.

---

## Q-CC-10 — Should `assumption_computation_context` become a versioned, validated contract?

**Context:** It is the single most important coupling surface in the system —
~40 keys produced once at the cruise point by
`assumption_compute_service._cache_context()` and read by nine consumers (speed
polar, V-n envelope, matching chart, mission KPIs, endurance, spar sizing,
powertrain solution space, and two copilot tools). It is a schemaless JSON
column, and **every consumer falls back to an RC-typical default on a missing
key** — `cd0 0.03`, `e 0.8`, `AR 8.0`, `S 0.5 m²`, `mass 1.0 kg` — with only a
log warning. A rename degrades silently: the answer stays structurally valid and
physically meaningless.
**Spec affected:** [`_reversa_sdd/aero-analysis/aero-context-single-source/design.md`],
[`_reversa_sdd/traceability/spec-impact-matrix.md`] (CS-2)
**Question:** Would a Pydantic model + a `context_version` key + a
producer/consumer contract test be worth the migration, or is the looseness
deliberate because the key set is still growing?
**Impact:** This is the highest-leverage structural question in the corpus.

**Answer:** **(a) Full contract: Pydantic model + `context_version` + a
producer/consumer contract test + a freshness marker.** _Answered by the
maintainer, 2026-08-13._

**Maintainer's input:** the fundamental key set is **considered finished**; further
keys may still be added, but only occasionally and in manageable numbers.

That settles it in favour of the model, without the usual trade-off: a Pydantic
model is **insensitive to additions** (adding a field is trivial). What it prevents
is **silent renames and typos** — precisely the failure mode here. The "still
growing" argument would only speak against a model if the shape were volatile,
which it is not.

**Required:**
1. **Typed model** for the context in one shared location, with **`extra="allow"`**
   so an occasional new key produced by a newer version never breaks an older
   consumer, while every known key is typed and validated.
2. **`context_version`** — the *schema* version, so a consumer can detect a context
   produced under an older shape and act deliberately.
3. **Producer/consumer contract test** — asserts that every key the nine consumers
   read is a key the producer actually writes. This is the mechanism that would
   have caught all three live consequences below.
4. **Freshness marker** — see the distinction below.
5. **No defaults on a missing key** — a missing key emits a `DesignWarning`
   (`input_missing`, severity `error`) per `P-WARN-0`. The RC-typical fallbacks
   (`cd0 0.03`, `e 0.8`, `AR 8.0`, `S 0.5 m²`, `mass 1.0 kg`) are removed.

**Schema version ≠ freshness — these are two different failure modes:**
- `context_version` (schema) catches **renames and shape drift**.
- A freshness marker (`computed_at` plus a hash of the inputs it was derived from)
  catches **staleness**. This is the sharper of the two: today a *stale* context is
  **indistinguishable from a fresh one**, because fallbacks fire only on *missing*
  values, never on outdated ones. Change the wing geometry without recomputing and
  all nine consumers silently continue with the old numbers. Same danger class as
  `mass = 1.0 kg`, but far harder to notice (this is `Q-PT-8`).

**Three live consequences already in the corpus** — all preventable by the above:
`Q-AA-1` (a second writer corrupting `cd0`), `Q-PT-8` (stale context
indistinguishable from fresh), `Q-MS-8` (`assumptions_snapshot` records only
`{mass, cl_max, g_limit}` although `cl_alpha_per_rad`, `v_md_mps` and
`v_min_sink_mps` also shape the output).

**Related:** the shared model should live in one owned location — feeds `Q-CC-15`
(the five ownerless schema files).

---

## Q-CC-11 — Should a generated TypeScript client replace the hand-written mirrors?

**Context:** 48 SWR hooks each redeclare their own response interfaces; only
`types/versioning.ts` and `types/versionGraph.ts` are shared, and nothing is
generated from `/openapi.json` (which the backend publishes). `npx tsc --noEmit`
against hand-written test fixtures is the only detector of a backend schema
change — which is exactly why that CI gate exists.
**Spec affected:** [`_reversa_sdd/frontend-workbench/data-fetching-swr/requirements.md`]
**Question:** Is the hand-mirroring a deliberate cost (it keeps the frontend
independent of a generator's output shape), or simply never automated?
**Impact:** Decides whether the spec prescribes a generator for the
re-implementation.

**Answer:** **(a) Generate the client types from `/openapi.json`; retire the
hand-written mirrors.** _Answered by the maintainer, 2026-08-13._

The hand-mirroring is recorded as **never automated**, not as a deliberate cost.
48 SWR hooks each redeclare their own response interfaces; only
`types/versioning.ts` and `types/versionGraph.ts` are shared. Schema drift is
currently detected only by `npx tsc --noEmit` failing against hand-written test
fixtures — which is precisely why that CI gate exists, and why a new required field
breaks fixtures while vitest and eslint stay green.

**Required:**
- Introduce a generator (e.g. `openapi-typescript`) driven by the backend's
  published `/openapi.json`, and replace the hand-written response interfaces.
- **Prerequisite:** fill the missing `response_model` annotations first. A
  generator is only as good as the OpenAPI document, and several endpoints
  currently return untyped dicts — e.g. `GET /aeroplanes/{id}/tessellation` and
  `GET /airfoils/{name}/coordinates` declare no response model. Closing those gaps
  is worthwhile in itself and also improves the generated
  `_reversa_sdd/openapi/da3dalus-v2.yaml`.
- Keep the `tsc --noEmit` gate: with generated types it becomes a *build-time*
  drift detector rather than an accidental one.

**Benefit:** removes a recurring class of defect (silent backend/frontend schema
divergence) in exchange for one-time setup.

---

## Q-CC-12 — Should the MCP tool contract be pinned by a golden-file test?

**Context:** FastMCP derives each tool's input schema from the Python handler
signature, so renaming an endpoint parameter is a silent contract break for every
external agent, with no compile-time or test signal. `MCP_TOOL_NAMES` exists but
nothing asserts the generated schemas.
**Spec affected:** [`_reversa_sdd/mcp-server/tool-registration/tasks.md`]
**Question:** Is a golden-file test over `MCP_TOOL_NAMES` + the generated schemas
wanted?
**Impact:** The only proposed mechanism for detecting MCP contract drift.

**Answer:** **(c) No golden-file test — the premise of the question is wrong.**
_Answered by the maintainer, 2026-08-14._

**Correction to the question's premise.** MCP clients fetch `tools/list`
**including each tool's input schema** when they connect, and generate their calls
from what they read. A renamed parameter is therefore **not a silent contract
break** for an LLM-driven agent — it simply uses the current schema. The question
treated the MCP surface like a conventional API with hard-coded clients, which it
is not. There are no non-LLM MCP consumers here, and no stored tool calls are
replayed.

**What that leaves — and why a golden file would not help anyway:**
- **Semantic drift under an unchanged signature** — a parameter keeps its name but
  changes meaning (e.g. a unit moving from mm to m). The schema is byte-identical,
  the agent calls it the same way, the result is wrong. A schema snapshot cannot
  detect this.
- **Accidental tool loss during a refactor** — a name-level check would catch it,
  but with a single user this is noticed immediately in normal use.

So the proposed test would report exactly the harmless change and miss the
dangerous one. `MCP_TOOL_NAMES` stays as-is, unasserted.

**Recorded so the question does not resurface.** Should a non-LLM MCP consumer ever
appear (a script, another service), this decision must be revisited — that is the
condition under which the original reasoning would become valid.

---

## Q-CC-13 — Should the `cad_designer/**` quality-gate exclusion be narrowed?

**Context:** ADR 0002 freezes `airplane/aircraft_topology/**` and
`GeneralJSONEncoderDecoder.py`. But `sonar.exclusions` (`sonar-project.properties:10`)
and ruff's `extend-exclude` (`pyproject.toml:122-129`) cover the whole of
`cad_designer/**` — including `geometry/`, `creator/`, `cq_plugins/` and
`aerosandbox/`, where the actively developed #1008/#1030/#1075/#1076 spar
pipeline lives. ≈22 000 LOC is neither linted nor measured.
**Spec affected:** [`_reversa_sdd/cad-designer-topology/requirements.md`] (BR-CT1),
[`_reversa_sdd/adrs/0002-…md`], [`_reversa_sdd/adrs/0015-…md`]
**Question:** Narrowing the exclusion to `aircraft_topology/**` plus
`GeneralJSONEncoderDecoder.py` would put new feature code back under the gate. Is
that wanted? (It would surface hundreds of findings on first run.)
**Impact:** Determines whether new geometry code is spec'd as gated or ungated.

**Answer:** **(a) Narrow the exclusion to exactly what ADR 0002 freezes.**
_Answered by the maintainer, 2026-08-13._

`sonar.exclusions` and ruff's `extend-exclude` are reduced to
`cad_designer/airplane/aircraft_topology/**` plus `GeneralJSONEncoderDecoder.py`.
Everything else in `cad_designer/` — `airplane/geometry/`, `airplane/creator/`,
`cq_plugins/`, `aerosandbox/` — returns under lint and coverage.

**No conflict with the existing "don't fix findings inside `cad_designer/`" rule:**
that rule protects the *frozen, fragile topology layer*. Measuring newly written
feature code is a different matter; the exclusion was simply far broader than the
freeze it was meant to implement.

**Measured during the interview** (rather than estimated):

| Area (actively developed, **not** frozen) | LOC |
|---|---|
| `cad_designer/airplane/geometry` (spar pipeline #1008/#1030/#1075/#1076) | 1 952 |
| `cad_designer/airplane/creator` | 3 600 |
| `cad_designer/cq_plugins` | 968 |
| `cad_designer/aerosandbox` | 2 899 |
| **Total** | **9 419** |

`ruff check` against these four directories under the project's own rules reports
**32 findings — not "hundreds"**. The remaining ~13 k LOC of the quoted 22 k is the
frozen topology, which stays excluded.

**Findings worth immediate attention** (independent of the gate decision):
- **3 × `F821` undefined-name** — a runtime `NameError` on the affected path.
  *Caveat:* the same directories show 6 × `F403` / 3 × `F405` (star imports), which
  ruff cannot resolve, so some or all `F821` may be star-import artefacts. To be
  verified, not assumed.
- **4 × `E722` bare-except** — precisely the silent swallowing forbidden by
  `P-WARN-0`.

**Why this area specifically:** `geometry/` holds the spar sizing. A mis-sized spar
means a wing failure — the worst possible place for a lint and coverage blind spot.

**On the migration cost:** SonarCloud gates on **new code** by default, so the
existing backlog does not suddenly block the gate; only code written from now on is
measured. Ruff needs a one-time cleanup of the 32 findings.

---

## Q-CC-14 — Housekeeping decisions (bundle)

**Context:** Four independent items, each cheap to decide and each currently
documented as an open 🔴:
- **Docker geometry kernel:** the container runs CadQuery 2.6.1 /
  cadquery-ocp 7.9.3.0 / VTK 9.5.2 while the lock (and therefore CI and local
  dev) runs 2.7.0 / 7.8.1.1 / 9.3.1, so a CAD defect may be unreproducible across
  environments. Was the pin chosen for a specific OCCT bug, and can the lock move
  to match?
- **`azure-pipelines.yml`:** references a Dockerfile path that does not exist and
  triggers on a non-default branch. Delete?
- **Committed database:** `db/test.db` plus dated backups and WAL files are in
  Git and copied into the Docker image. Intentional seed data, or should it be a
  seeded fixture removed from history?
- **The `test/` root:** 23 files, excluded from ruff but not from pytest, mixing
  uncollected `Test_*.py` scripts with collected `test_*.py` modules. It authored
  the three undecodable plan JSONs. Archive, migrate, or add to `norecursedirs`?

**Spec affected:** [`_reversa_sdd/architecture.md`] §12,
[`_reversa_sdd/adrs/0015-…md`], [`_reversa_sdd/cad-designer-topology/tasks.md`]
**Question:** A one-line decision on each.
**Impact:** Removes four items from the debt register without design work.

**Answer:** **All four decided.** _Answered by the maintainer, 2026-08-14._

**① Docker geometry-kernel pin — historical ARM constraint, to be re-tested.**
The pin was **not** chosen to work around a specific OCCT defect. It exists because
of **compatibility of CadQuery and its dependencies with Docker on linux/arm64**.
The maintainer expects this may no longer apply — *"kann sein, dass das Problem
nicht mehr besteht, müsste man testen."*

→ Action: verify whether the locked versions (CadQuery 2.7.0 / cadquery-ocp
7.8.1.1 / VTK 9.3.1) build and run on linux/arm64 in the container. If they do,
**drop the `pip --no-deps` force-install and let the container use the lock**,
removing the environment split (container 2.6.1 / 7.9.3.0 / 9.5.2 vs lock+CI+local
2.7.0 / 7.8.1.1 / 9.3.1) that currently makes a CAD defect potentially
irreproducible across environments. This is a **test task, not an open question**.

**② `db/test.db` — remove from the image; use a mount plus an env var.**
The database is **not** in Git (`db/` is gitignored, `.gitignore:285` — the earlier
claim that it was committed is incorrect), but `Dockerfile:124` does
`COPY db/test.db ./db/test.db`, baking the maintainer's **183 MB working database
with 29 real aircraft** into every image.

→ Action: remove that `COPY`; supply the database via a **volume mount**, with the
path/URL configured through an **environment variable**. This composes with
`Q-CC-4`, which folds the stray `SQLALCHEMY_DATABASE_URL` `os.getenv` into the
unified `Settings`. **Also add a `.dockerignore`** — there is none today, so every
build ships `db/`, `tmp/`, `exports/` and `frontend/node_modules` into the build
context. Side benefit: the container no longer starts from a frozen snapshot that
silently diverges from the local database and resets on rebuild.

**③ The `test/` root — add to `norecursedirs` for now.**
23 files, excluded from ruff but still collected by pytest, mixing
`Construction_*.py` scripts with `Test_*.py` modules (and the origin of the three
undecodable plan JSONs). Stop collecting them; archiving or migrating stays open as
a later cleanup.

**④ `azure-pipelines.yml` — delete.** Confirmed. It references a non-existent
Dockerfile path and triggers on a non-default branch; already indicated by
`P-DEAD-0`.

---

## Q-CC-15 — Do the five ownerless schema files belong to a shared contracts unit?

**Context:** `app/schemas/spar_plan.py`, `spar_insert.py`, `section_geometry.py`,
`flight_profile.py` and `WingAnalysisRequest.py` are each imported by handlers in
more than one module, so the import graph yields no single owner and the
traceability matrix scores them `n/a`. Their behaviour *is* documented in the
consuming modules' `contracts.md`, but no unit owns the file — which is exactly
why `SparPlanResult`'s real field names are still unknown (Q-CP-4).
**Spec affected:** [`_reversa_sdd/traceability/code-spec-matrix.md`]
**Question:** Should a shared contracts unit exist, or should each file be
assigned to its dominant consumer?
**Impact:** Five files are the only production code with no home unit.

**Answer:** **(a) Introduce a shared contracts unit that owns the cross-module
schema files.** _Answered by the maintainer, 2026-08-13._

A `shared-contracts` unit is added to the spec and owns the five files —
`app/schemas/spar_plan.py`, `spar_insert.py`, `section_geometry.py`,
`flight_profile.py`, `WingAnalysisRequest.py` — plus the **new computation-context
model introduced by `Q-CC-10`**, which is a sixth contract of exactly this kind.
The category is real and growing, which is the argument against assigning each file
to a "dominant" consumer.

**Why it matters beyond tidiness:** unowned means undocumented. This is precisely
why `SparPlanResult`'s real field names are still unknown (`Q-CP-4`) — one of the
few genuine re-implementation blockers in the catalogue. The new unit gives that
question a place to be answered.

**Also:** `WingAnalysisRequest.py` is the only one of the five that breaks the
`snake_case` file-naming convention; rename opportunistically.

**Effect on traceability:** the five `n/a` rows in
`traceability/code-spec-matrix.md` resolve, leaving no production file without a
home unit.

---

## Q-CC-16 — Two files have no importer anywhere: dead, or reached dynamically?

**Context:** `app/db/exceptions.py` and `app/services/example.py` are imported by
nothing in the tree.
**Spec affected:** [`_reversa_sdd/traceability/code-spec-matrix.md`]
**Question:** Dead code to delete, or reached in a way static analysis cannot see?
**Impact:** Trivial, but they are the last two unexplained production files.

**Answer:** _(derived — not a maintainer decision)_ **Delete both files.**

Follows from **P-DEAD-0**: the policy's own context names `Q-CC-16` among the items that "have no retention argument at all", and rule 3 makes deletion the default for anything that is neither a switched-off safety mechanism nor ticketed scaffolding. `app/db/exceptions.py` and `app/services/example.py` are removed and recorded in the spec as deleted; a one-off check for dynamic resolution (`importlib`, `getattr` on a module object) is a verification step before deleting, not a reason to keep them inert.

---

## Q-CC-17 — Verification request: does the frontend have a circular dependency?

**Context:** `.dependency-cruiser.cjs` sets `no-circular` to **error**, and no
cycle is recorded anywhere in `code-analysis.md`. An earlier note claimed one
exists; the static analysis could not reproduce it.
**Spec affected:** [`_reversa_sdd/frontend-workbench/requirements.md`],
[`_reversa_sdd/architecture.md`] §12
**Question:** Please run `cd frontend && npm run deps:check` and paste the output.
**Impact:** If a cycle exists it belongs in the debt register; if not, the claim
should be retired so it stops propagating.

**Answer:** _(resolved by code lookup — not a maintainer decision)_ **The cycle is real and reproducible: `ImportOpenVspButton.tsx → ImportProgressBar.tsx → ImportOpenVspButton.tsx`, reported by `npm run deps:check` as its one `no-circular` **error**, exit code 1.**

Current totals over 212 modules / 501 dependencies: **22** violations — 1 error (the cycle), 16 `no-lib-import-components` warnings on 8 `lib/` modules (`treeDnd.ts`, `sparSizingHelpers.ts`, `sparPlanHelpers.ts`, `planValidation.ts`, `planTreeUtils.ts`, `missionScale.ts`, `metricsAdapters.ts`, `geometryDiff.ts`), and 5 `no-orphans` info items (`SplitHandle.tsx`, `RadarChart.tsx`, `MarkerDetailBox.tsx`, `AlertBanner.tsx`, `AirfoilPreview.tsx`). `deps:check` is **not** wired into CI — a grep for it across `.github/workflows/` returns nothing — so the error has been sitting at exit code 1 with no gate to catch it. The claim belongs in the debt register, not retired.

**Verdict:** confirmed defect
Residual decision: whether to add `deps:check` to the frontend CI job, since nothing enforces it today.

_Full detail: [`wave3-lookups.md`](wave3-lookups.md) §B_


**Residual decision — ANSWERED by the maintainer, 2026-08-15: yes, add
`deps:check` to the frontend CI job.**

The cycle is confirmed real (`ImportOpenVspButton` ↔ `ImportProgressBar`) and
`npm run deps:check` detects it, but the CI frontend job runs only `lint`,
`tsc --noEmit` and `test:unit`, so nothing prevents the next one. Without the gate
the cycle is merely *documented*.

**Sequencing:** the existing cycle must be broken first, otherwise CI is red on the
first run. The `warn`-severity `lib/ → hooks/` violations (16 of them) should be
triaged at the same time — either the rule is right and the imports move, or the rule
is wrong and it is narrowed; leaving 16 standing warnings trains everyone to ignore
the tool.
---

# aeroplane-core

## Q-AC-1 — Is the shadowed `aeroplane.py` router module retained deliberately?

**Context:** `app/api/v2/endpoints/aeroplane.py` is shadowed by the package
`app/api/v2/endpoints/aeroplane/` — Python resolves
`from app.api.v2.endpoints import aeroplane` to the package's `__init__.py`
(verified with `importlib.util.find_spec`). The module is labelled "kept for
backward compatibility" but registers only 3 of the 24 sub-routers and is never
imported.
**Spec affected:** [`_reversa_sdd/aeroplane-core/requirements.md`]
**Question:** Intentionally retained, or leftover to delete?
**Impact:** It is currently the only file in the module marked 🔴 dead.

**Answer:** _(derived — not a maintainer decision)_ **Delete the shadowed `app/api/v2/endpoints/aeroplane.py` module.**

Follows from **P-DEAD-0**: it is unreachable by construction — the package `aeroplane/` shadows it, verified with `importlib.util.find_spec` — has no live ticket and is not a safety mechanism, so rule 3 ("anything else → delete") applies. The "kept for backward compatibility" label describes exactly the inert state the policy forbids, and it is misleading besides: the module registers only 3 of the 24 sub-routers, so it could not serve as a compatibility surface even if it were reachable.

---

## Q-AC-2 — Should `aeroplanes.name` be unique?

**Context:** It is not today, so duplicate aircraft names are legal. The
`IntegrityError → 409 "name existiert bereits"` handler would therefore be
misleading if it ever fired from a different constraint.
**Spec affected:** [`_reversa_sdd/aeroplane-core/aeroplane-crud/requirements.md`]
**Question:** Confirm that UUID-only identity is the intended contract.
**Impact:** One line in the contract, but it also settles whether the German
handler message is ever reachable for aeroplanes.

**Answer:** **CONFIRMED by the maintainer, 2026-08-15** (option a). _The derivation below stands; the maintainer additionally ordered removal of the unreachable handler._

**UUID-only identity is the intended contract, and the misleading `409 "name existiert bereits"` handler is removed from the aeroplane path** — a handler that can only ever fire from a *different* constraint reports the wrong cause, which is the diagnostic equivalent of the undeclared substitutions ADR 0020 forbids. Genuine integrity conflicts elsewhere surface through the single envelope (`Q-CC-3`), and the German string is translated per `Q-CC-5`.

_Original derivation:_ _(derived — not a maintainer decision)_ **No — `aeroplanes.name` must stay non-unique: UUID-only identity is the intended contract, and versioning now makes it structurally required.**

Follows from **ADR 0006**: a version is *"a real `aeroplanes` row with its own full subgraph"*, and `aeroplane_clone_service.py:187` copies `name=source.name`, so every snapshot and every branch deliberately produces a second aeroplane row carrying the same name — a unique constraint would make snapshotting fail with exactly the 409 this question asks about, breaking epic #901 at its root. The `IntegrityError → 409` handler is therefore unreachable for aeroplanes; it survives only for genuine integrity conflicts elsewhere, translated by **Q-CC-5** and carried in the single envelope of **Q-CC-3**.

---

## Q-AC-3 — Should the component tree defend against cycles at read time?

**Context:** `_build_tree` turns orphans into roots and `_roll_up_weights` would
recurse infinitely on a cycle. Only `move_node` guards writes, so a cycle
introduced out-of-band (direct SQL, an import, a future bulk endpoint) would hang
the read path.
**Spec affected:** [`_reversa_sdd/aeroplane-core/component-tree/requirements.md`],
[`_reversa_sdd/aeroplane-core/weight-rollup/design.md`]
**Question:** Should read-side depth limiting or cycle detection be added?
**Impact:** RF-13's cycle guard is currently the module's *only* structural
integrity check.

**Answer:** **Add read-side depth limiting, reported as a `DesignWarning`.**
_Answered by the maintainer, 2026-08-15._

`_build_tree` turns orphans into roots and `_roll_up_weights` recurses infinitely on
a cycle; only `move_node` guards writes, so a cycle arriving out-of-band (direct SQL,
an import, a future bulk endpoint) **hangs every read** of that aeroplane.

This weighs more after `Q-MB-1`: the component tree is now the **sole mass authority**,
so its read path is unavoidable for every sizing surface.

Depth limiting is chosen over full cycle detection: it is cheaper, catches the same
failure, and — reported as a `DesignWarning` rather than an exception — turns a hang
into a visible, diagnosable condition (`P-WARN-0`).

---

## Q-AC-4 — Are negative `scale_factor` / `quantity` values legal?

**Context:** Nothing in the own-weight resolution chain rejects them, and they
would **subtract** from the aircraft total.
**Spec affected:** [`_reversa_sdd/aeroplane-core/weight-rollup/requirements.md`]
**Question:** Reject at the schema, clamp, or is a negative quantity a deliberate
"credit" affordance?
**Impact:** Changes the weight ladder's acceptance criteria.

**Answer:** **Reject negative values at the schema.** _Answered by the maintainer,
2026-08-15._

A negative `scale_factor` or `quantity` is **not** a deliberate "credit" affordance.
Nothing in the own-weight resolution chain rejects them today and they would
**subtract** from the aircraft total, so the constraint is added where it belongs:
`quantity` and `scale_factor` are constrained non-negative in the Pydantic schema
(`quantity` strictly positive), producing a 422 rather than a silently wrong mass.

---

## Q-AC-5 — Is an empty `AirplaneConfiguration` export legal?

**Context:** An aeroplane with a `total_mass_kg` but no wings and no fuselages
exports successfully today. Separately, `AirplaneConfiguration.__init__`
evaluates `self.wings[0]` immediately, so an empty wing list raises `IndexError`
at construction on the `cad_designer` side.
**Spec affected:** [`_reversa_sdd/aeroplane-core/airplane-configuration-export/requirements.md`]
**Question:** Should the export require at least one lifting surface?
**Impact:** Decides whether the mass gate (RF-08) is the only precondition.

**Answer:** **ANSWERED by the maintainer, 2026-08-15** (option a) — **the export requires at least one lifting surface and is rejected with a clear message otherwise.**

Today an aeroplane with a `total_mass_kg` but no wings and no fuselages exports
**successfully**, producing a file the library it is written for cannot load:
`AirplaneConfiguration.__init__` evaluates `self.wings[0]` immediately, so an empty wing
list raises `IndexError` at construction on the `cad_designer` side.

**The export contract is "produces a loadable `AirplaneConfiguration`", not "produces
JSON".** An export that succeeds and yields an unloadable artefact is a false success —
the failure is merely deferred to whoever opens the file, where it appears as an
`IndexError` with no connection to the aircraft that caused it.

**The precondition is therefore two-part**, not one: the mass gate (RF-08) **and** at
least one lifting surface. The rejection is a `ValidationDomainError → 422` — the
submitted design is internally incomplete, and nothing in persisted state is in conflict,
so this is the 422 side of the discriminator recorded in `Q-FD-1`.

**Rejected — option (c), export with a `DesignWarning`.** ADR 0020 declares
*substitutions*, not *broken outputs*. Warning that a file is unusable while still
producing it leaves the user holding an artefact whose only correct use is to be thrown
away.

---

## Q-AC-6 — How should `AirplaneConfiguration` conversion failures be classified?

**Context:** Unresolvable airfoil files and inconsistent station lists are
user-fixable *data* problems, but they surface as a generic **500**,
indistinguishable from a server fault.
**Spec affected:** [`_reversa_sdd/aeroplane-core/airplane-configuration-export/contracts.md`]
**Question:** Should these become 422 with a remediation message, the way
`mass_cg_service` does for a missing wing?
**Impact:** The error contract for the only handover into the CAD stack.

**Answer:** _(derived — not a maintainer decision)_ **Classify user-fixable conversion failures as an explicit `ValidationDomainError` → 422 with a remediation message; only genuine server faults stay 500.**

Follows from **Q-CC-3**: it preserves the deliberate 422 as a *named type* precisely so the behaviour "applies uniformly, rather than surviving as a habit in two files", and its stated user-visible motivation is that the same class of user error must not yield a helpful 422 on two endpoints and a bare 500 everywhere else. Unresolvable airfoil references and inconsistent station lists are user-fixable data, so they raise `ValidationDomainError`; the envelope is `{"error": {code, message, details}}` either way.

---

## Q-AC-7 — Should a persistently failing mass sync be surfaced to the user?

**Context:** `_sync_aircraft_mass` catches bare `Exception` and only logs, by
design, so a failed sync never blocks tree CRUD (BR-A13). But the mass model can
then go stale indefinitely with no user-visible signal — which sits awkwardly
beside ADR 0012 ("design warnings, not silent fallbacks").
**Spec affected:** [`_reversa_sdd/aeroplane-core/component-tree/requirements.md`],
[`_reversa_sdd/mass-and-balance/component-tree-mass-sync/requirements.md`]
**Question:** Should repeated failures raise a design warning?
**Impact:** Also covers `weight_items_service._try_sync_assumptions`, which
catches a *narrower* set (`NotFoundError`, `SQLAlchemyError`) — so a `TypeError`
fails a weight-item write but not a tree write. Deliberate or oversight?

**Answer:** _(derived — not a maintainer decision)_ **Yes — a failed mass sync emits a `DesignWarning` instead of being swallowed, while still not blocking tree CRUD.**

Follows from **P-WARN-0**: a bare `except Exception:` with a log line only is the undeclared degradation the policy forbids; a stale mass model is `substituted_assumption`/`input_missing` at severity `warning` (the number is usable but no longer reflects the tree), escalating to `error` on repeated failure. BR-A13's non-blocking behaviour is unaffected — the rule is "declare it", not "fail the write". The narrower catch in `weight_items_service._try_sync_assumptions` becomes moot under **Q-MB-1**, which retires `weight_items` altogether.

---

## Q-AC-8 — Should `GET /component-tree/weight` carry a completeness indicator?

**Context:** The kilogram total alone cannot distinguish a fully specified
aircraft from one whose tree is mostly `invalid`. `weight_status` exists only on
the full tree read.
**Spec affected:** [`_reversa_sdd/aeroplane-core/weight-rollup/contracts.md`]
**Question:** Add a status/coverage field to the weight endpoint?
**Impact:** A consumer currently cannot tell a trustworthy total from a partial one.

**Answer:** _(derived — not a maintainer decision)_ **Yes — the weight endpoint must declare an incomplete tree, and it declares it through the shared `warnings` channel rather than a bespoke coverage field.**

Follows from **P-WARN-0** (with **Q-MB-1**): every response whose numbers were degraded carries `warnings: [DesignWarning]`, and a kilogram total rolled up over a tree that is largely `invalid` is precisely such a number (`input_missing`, with the covered/uncovered node counts in `context`). Q-MB-1 makes the tree the only mass producer, so this total now feeds every sizing surface — and the one-channel rule is what rules out inventing a second per-endpoint status shape.

---

## Q-AC-9 — Is `_to_json_compatible` permanent or transitional?

**Context:** It exists because the shared converter hub emits NumPy types. If the
hub's return contract were tightened it becomes dead code; if the hub gains a
NumPy-bearing container the stripper does not handle, serialisation silently
breaks again.
**Spec affected:** [`_reversa_sdd/aeroplane-core/airplane-configuration-export/design.md`]
**Question:** Tighten the hub, or keep the defensive stripper?
**Impact:** BR-A5 is currently specified as a permanent rule.

**Answer:** **ANSWERED by the maintainer, 2026-08-15** (option c) — **both: tighten the converter hub so it returns pure Python types, *and* keep `_to_json_compatible` — but as a throwing assertion, never a silent stripper.**

**Why both rather than either.** Tightening the hub alone (option a) is the ADR 0022 move
— one authority for "JSON-serialisable" — and it is necessary. But it is a *convention*,
enforced only by whoever writes the next converter, and the failure mode when it lapses
is the exact one this question describes: the hub grows a NumPy-bearing container the
stripper does not recognise, and serialisation breaks **silently**. Keeping the check
converts a convention into an invariant.

**What changes is the check's behaviour, and that is the substance of the decision.**
Today `_to_json_compatible` *repairs* what it finds — it is a fallback, and an undeclared
one, which is precisely what **ADR 0020** forbids: the hub emits something wrong, the
stripper quietly fixes it, and nobody learns that the hub is wrong. As an assertion it
inverts: encountering a non-JSON-native type is a **defect in the hub** and raises,
naming the offending field and type.

**This is not a second authority under ADR 0022.** The hub remains the sole *producer* of
serialisable output; the assertion produces nothing. It is a guard, in the same shape as
the `lazy="raise"` relationship decided in `Q-AF-7 ②` — the mechanism stays in place
specifically so that misuse fails loudly instead of working by accident.

**Consequence for BR-A5:** it stops being *"a defensive stripper runs on every export"*
and becomes *"the hub returns JSON-native types; an assertion enforces it."*

---

## Q-AC-10 — Is component-tree subtree deletion contractual or incidental?

**Context:** Deleting a node removes its subtree, but that follows from the
SQLAlchemy relationship cascade rather than from explicit service logic.
**Spec affected:** [`_reversa_sdd/aeroplane-core/component-tree/requirements.md`] (RF-12)
**Question:** Confirm it is intended, before callers rely on it.
**Impact:** One acceptance criterion moves from 🟡 to 🟢.

**Answer:** **ANSWERED by the maintainer, 2026-08-15** (option c) — **deleting a node that has children is rejected. The subtree cascade is not promoted to a contract; it is demoted to a database-level safety net that the service never relies on.**

**This is a behaviour change, not a confirmation.** Today the subtree disappears because of the SQLAlchemy relationship cascade — nothing in the service intends it. From now on `delete_component` raises when the node has children, and the caller removes them first.

**It matches the deletion philosophy already established elsewhere in this interview:** a referenced COTS component *"cannot be deleted, only changed"* (`Q-PT-7`), and `Q-FD-1` has just settled that a rejected operation conflicting with persisted state is a **409**. This is the same shape — the request is well-formed, existing state refuses it — so the rejection is a `ConflictError → 409` naming how many children block it.

**Consequences:**

- **The cascade stays in the DDL.** It is unreachable through the service once the guard is in place, so it costs nothing and protects against direct SQL. It is explicitly *not* an API behaviour: no acceptance criterion may describe subtree deletion as a feature.
- **The frontend needs an affordance**, because removing a deep assembly now takes one operation per node. `AeroplaneTree` shows the blocking child count in the error and offers to select the subtree, so the user performs the deletion deliberately, leaf-first. What it must **not** do is offer a "delete anyway" flag — that would reintroduce exactly the silent destructive behaviour this decision removes.
- **No `?cascade=true` escape hatch.** Considered and rejected for the same reason.

**RF-12 is rewritten**: previously *"deleting a node removes its subtree"*, now *"a node with children cannot be deleted"*.

---

# wing-design

## Q-WD-1 — Who should own the gh-772 mixing-name mapping (open bug #955)?

**Context:** The canonical control name is
`[{role}]{axis}_{wing_key}_{xsec_index}`. Three consumers still key on the raw
TED name from the DB: `trim_enrichment_service.build_deflection_limits_from_schema`,
`retrim_service._find_pitch_control_name`, and
`stability_service._find_trim_elevator` (a substring match on `"elevator"`, which
never matches `[ruddervator]pitch_…`). On any V-tail / elevon / flaperon aircraft
the lookup misses, authority is computed against a hard-coded **±25°**, and a
**phantom 0° surface** is injected under the DB name.
**Spec affected:** [`_reversa_sdd/wing-design/control-surface-mixing/requirements.md`],
[`_reversa_sdd/aero-analysis/requirements.md`] (BR-13),
[`_reversa_sdd/avl-integration/control-surface-naming/requirements.md`]
**Question:** Which layer should own the mapping — a name-normaliser exported by
`control_surface_mixing`, or deflection limits keyed by
`(role, surface_suffix)`? And should the mixing layer expose a **resolver that
trim/retrim/stability are required to call**, so the divergence becomes
impossible rather than merely fixed once?
**Impact:** The structural answer is what stops #955 recurring. Note the ±25°
collision: the topology layer *also* defaults `positive/negative_deflection_deg`
to 25°, so a report cannot distinguish "the real limit is 25°" from "the lookup
failed" — should the fallback use a distinguishable sentinel?

**Answer:** **(a) `control_surface_mixing` owns a resolver that trim, retrim and
stability are REQUIRED to call — and the silent ±25° fallback is removed.**
_Answered by the maintainer, 2026-08-13._

**Ownership.** The mixing layer generates the canonical names
(`axis_control_name` → `[{role}]{axis}_{wing_key}_{xsec_index}`), so it must also
own their resolution. It exports a resolver, and
`trim_enrichment_service.build_deflection_limits_from_schema`,
`retrim_service._find_pitch_control_name` and `stability_service._find_trim_elevator`
are converted to call it. Same single-authority principle applied to mass
(`Q-MB-1`) and `cd0` (`Q-AA-1`).

**Why mandatory rather than merely fixed:** patching the three call sites resolves
#955 today, but the next consumer that keys on the raw DB name reintroduces it. A
required resolver makes the divergence **structurally impossible**. Note in
particular `_find_trim_elevator`'s substring match on `"elevator"`, which can never
match `[ruddervator]pitch_…`.

**No silent fallback (per `P-WARN-0`).** When resolution fails today, three things
happen invisibly: authority is computed against a hard-coded **±25°**, a **phantom
0° surface** is injected under the DB name, and nothing is reported. All three are
removed. A failed resolution emits a `DesignWarning` with **`severity: error`** —
control authority is safety-relevant — and no fabricated surface is created.

**Resolves the ±25° collision.** The topology layer *also* defaults
`positive/negative_deflection_deg` to 25°, so today a report cannot distinguish "the
real limit is 25°" from "the lookup failed". The answer is not a sentinel value but
the warning channel: a genuine 25° limit carries no warning, a failed lookup carries
an `error`. The ambiguity disappears without inventing a magic number.

**Practical impact:** every V-tail, elevon and flaperon aircraft — i.e. a large part
of this maintainer's own designs — currently reports control authority computed
against the wrong limits.

---

## Q-WD-2 — Should the `units` block be able to express the millimetre spar exception?

**Context:** `WingUnitsSchema` / `WingModel.units` report `detail_length: "m"`
and the `SpareDetailSchema` field descriptions say "in meters", but
`wing_xsec_spares` stores all six dimensional fields in **millimetres** inside
the metre database (gh-402). The API still delivers metres, so the wire format is
consistent — but a client trusting `units` will be wrong about storage.
**Spec affected:** [`_reversa_sdd/wing-design/requirements.md`] (BR-2),
[`_reversa_sdd/domain.md`]
**Question:** Is `units` meant to describe only the wire format — and if so,
should the schema field descriptions be corrected, or should the block gain a
per-field storage-unit override?
**Impact:** This is the one place the system's own self-description contradicts
its storage.

**Answer:** _(derived — not a maintainer decision)_ **`units` describes the wire format only — correct the misleading `SpareDetailSchema` field descriptions, and do NOT add a per-field storage-unit override.**

Follows from **ADR 0019**: a storage-unit override would put "how this column happens to be persisted" into the public contract, which rule 4 forbids — a field existing only because of an internal representation, carrying no meaning for a client that is served metres either way. **Q-FD-2** already fixed storage as it is, so the millimetre exception on `wing_xsec_spares` (gh-402) belongs in `domain.md` and the module spec, not in the API; concretely, the `SpareDetailSchema` descriptions are reworded to state that they describe the payload, and `WingUnitsSchema` keeps `detail_length: "m"` as a true statement about the wire. Timing is not neutral — **Q-CC-11** bakes these descriptions into the generated TypeScript client.

---

## Q-WD-3 — Trailing-edge-device representation questions (bundle)

**Context:** Four related ambiguities in the TED/servo model:
- **`servo` is a union by convention.** `WingXSecTrailingEdgeDeviceModel.servo`
  returns a `WingXSecTedServoModel` when `servo_data` exists, else the integer
  `servo_index`; the schema type is `Servo | int`.
- **`Servo` schema required vs DB nullable.** Every `Servo` field is a required
  `NonNegativeFloat` while all `wing_xsec_ted_servos` columns are nullable, so a
  legacy row with a `NULL` dimension cannot be validated into the schema.
- **Default divergence.** `TrailingEdgeDevice` (topology) defaults
  `positive/negative_deflection_deg = 25`, `hinge_type = "top"`,
  `trailing_edge_offset_factor = 1.0`; the corresponding DB columns default to
  `NULL`.
- **`role` has no database-level constraint**, so an unknown role is silently
  treated as single-axis.

**Spec affected:** [`_reversa_sdd/wing-design/control-surface-mixing/requirements.md`],
[`_reversa_sdd/wing-design/cross-section-crud/contracts.md`]
**Question:** Which servo representation is canonical for new records (is
`servo_index` deprecated)? Is there a backfill for NULL servo dimensions, or is a
read failure intended? Which layer supplies the effective default during a CAD
build? And should `role` get a CHECK constraint or enum?
**Impact:** Four acceptance criteria are currently unwritable.

**Answer:** **ANSWERED by the maintainer, 2026-08-15** (option a) — all four as recommended.

**① `servo_index` is deprecated; `servo_data` is canonical for new records.** The union
`Servo | int` stays **readable** so existing rows resolve, but nothing new writes the bare
index. A union by convention is a contract a client cannot type against — it must branch
on the runtime shape to learn which it got.

**② A `NULL` servo dimension is rejected on read, not silently defaulted.** Every `Servo`
field is a required `NonNegativeFloat` while every `wing_xsec_ted_servos` column is
nullable, so a legacy row with a `NULL` dimension **cannot** be validated into the schema.
Failing loudly is correct: substituting a plausible number for a missing servo dimension
would put an invented value into a CAD build, which is exactly the undeclared substitution
**ADR 0020** forbids. The error names the row and the field so it can be filled in.

**③ Defaults have one authority: the topology classes.** `TrailingEdgeDevice` defines
`positive/negative_deflection_deg = 25`, `hinge_type = "top"`,
`trailing_edge_offset_factor = 1.0`; the DB columns default to `NULL`. Those are not two
opinions — `NULL` means *"not stated"*, and the effective value comes from the topology at
build time (**ADR 0022**). The DB must not acquire a second set of defaults, because they
would then diverge silently whenever one side is edited.

**④ `role` gets a CHECK constraint / enum.** Today an unknown role is **silently treated
as single-axis**, so a typo produces a wing that builds and flies differently from what
was asked, with no error anywhere. This is the same class as the `ga_runway` and
`mission_type` findings: an unconstrained string that quietly falls back.

Four acceptance criteria become writable.

---

## Q-WD-4 — Is the `role is None` skip in `_validate_mix_fields` a deliberate hole?

**Context:** A `None` role (a partial PATCH) skips the mixing-field validation
entirely, so a multi-step patch can leave a `flap` carrying a non-unity
`mix_gain_secondary` or `differential_ratio`.
**Spec affected:** [`_reversa_sdd/wing-design/control-surface-mixing/requirements.md`] (BR-12)
**Question:** Should changing `role` re-validate the existing mixing fields?
**Impact:** BR-12's gate is currently bypassable in two writes.

**Answer:** **Validate the resulting state, not the partial change.** _Answered by the
maintainer, 2026-08-15._

A `None` role (a partial PATCH) currently skips `_validate_mix_fields` entirely, so two
writes can leave a `flap` carrying a non-unity `mix_gain_secondary` or
`differential_ratio` — values that are physically meaningless for that role and exactly
what the single-write validation exists to prevent.

Required: **changing `role` re-validates the stored mixing fields, and changing a
mixing field validates it against the stored role.** The gate applies to the resulting
state. Otherwise any rule of this shape stays bypassable in two steps.

---

## Q-WD-5 — Is BR-6 (segment root chord is not independently settable) meant to be enforced?

**Context:** A segment's root chord *is* the previous segment's tip chord, but
nothing in the schema expresses it — a client write silently rewrites the
previous segment's tip chord. The copilot carries the rule as a free-text `note`.
**Spec affected:** [`_reversa_sdd/wing-design/requirements.md`] (BR-6),
[`_reversa_sdd/ai-copilot/copilot-tools/requirements.md`]
**Question:** Should the schema reject it, or is the free-text note the intended
level of protection?
**Impact:** Currently the only business rule in the module with no enforcement at
any layer.

**Answer:** _(expert consensus, endorsed by the maintainer 2026-08-14)_ **Enforce it — but in the Pydantic schema layer, where JSON-described wings arrive: a supplied root chord that contradicts the previous segment's tip chord must be rejected with a 422 naming that governing tip chord, or accepted with a `DesignWarning`, but never silently discarded.**

The distinction that decides this: **within** a segment, root → tip chords differ freely — that is taper, and nothing constrains it. **Between** segments the invariant holds *because construction always goes through* `add_segment`, which copies the previous segment's tip airfoil (airfoil, chord, dihedral, incidence) into the new root — `cad_designer/airplane/aircraft_topology/wing/WingConfiguration.py` ~line 271. Only the true wing root (segment 0) has an independently meaningful chord. **But the invariant is a property of the construction API, not of the data structure:** `WingConfiguration.from_json_dict` appends `WingSegment.from_json_dict(...)` objects **directly** (~lines 51–52), bypassing `add_segment`, so a directly-described (deserialised) structure can carry a discontinuity. The API path (`app/services/create_wing_configuration.py:226–236`) does go through `add_segment`, so a supplied root chord there is **silently discarded** — that is the actual `P-WARN-0` violation. The guard therefore belongs in the schema layer, not in the frozen `cad_designer` topology (ADR 0002).

Geometrically the invariant is what "lofted" means: the loft starts from the previous segment's **existing** tip wire (`cad_designer/cq_plugins/wing/wing_segment.py:19`), and a mismatch yields a non-manifold solid or a real spanwise step face. All three apparent counter-examples dissolve — plug-in/removable outer panels are a *structural* split at matching chord, a stub wing / LERX / glove is a kink the schema already expresses as a short segment with differing root and tip chord, and a genuine unfaired step is invisible to every solver in the stack (VLM, lifting line and AeroBuildup each rebuild a continuous camber surface from the xsecs), so allowing it would produce an analysis silently computed on a different wing. Tolerance: **exact equality after rounding to 1 µm** — a topological invariant, not a measurement, so there is no physical justification for a band. The copilot's free-text `note` is not enforcement and must not be counted as any; keep it (it improves first-try success) but back it with the schema guard.

**Authority:** Scholz/Sadraey (continuous chord distribution `c(y) = c_r[1 − (1 − λ)·y/(b/2)]` per panel; kink-vs-step in the double-trapezoidal wing); the loft geometry itself (`wing_segment.py:19`); AeroSandbox tooling (every solver builds its own continuous camber-surface representation); RC practice (plug-in wings) supplies the strongest apparent counter-example and reinforces the rule. Placement of the guard in the schema layer rather than by removing the field: maintainer ruling, 2026-08-14, under the ADR 0002 freeze.
**Confidence:** high

_Full reasoning: [`expert-consensus-aero.md`](expert-consensus-aero.md)_

---

## Q-WD-6 — Should a silently degraded spar-vector recompute be reported?

**Context:** `_recompute_spare_vectors` (`wing_service.py:854-873`) swallows
`ImportError` (aarch64 without CadQuery) and `FileNotFoundError` (missing airfoil
`.dat`) with a log line only, so a client cannot tell whether the spar vectors it
just read were recomputed or left stale.
**Spec affected:** [`_reversa_sdd/wing-design/requirements.md`] (BR-W4)
**Question:** Per ADR 0012, should this become a warning in the response body?
**Impact:** Same pattern as the turbulator optimiser, which *does* emit warnings.

**Answer:** _(derived — not a maintainer decision)_ **Yes — the swallowed `ImportError` / `FileNotFoundError` becomes a `DesignWarning` in the response body, so a client can tell recomputed spar vectors from stale ones.**

Follows from **P-WARN-0**: "swallowed `ImportError`/`FileNotFoundError`" appears verbatim in the policy's own list of violations. A missing CadQuery is `capability_unavailable`, a missing airfoil `.dat` is `input_missing`; both leave the stored vectors unrefreshed, which is severity `warning` (usable, confidence reduced) — the one thing it may not be is silent.

---

## Q-WD-7 — Historical data audits (bundle)

**Context:** Three "has this already happened?" questions that only you can
answer from the live database:
- **Pre-gh-402 metre rows.** The millimetre invariant on `wing_xsec_spares` is
  enforced only at the service boundary. A row with `spare_length < 1.0` is
  suspect, but no detection heuristic exists. Has this been audited?
- **Pre-gh-1053 spar-origin loss.** If solved spars written before
  `should_preserve_normal_spare` existed do not satisfy the predicate, their
  origins are being recomputed away on **every read today**.
- **Pre-gh-951 terminal dihedral.** `NULL` means "derive from geometry", which is
  correct for interior stations and *wrong* for a terminal rib that was rotated —
  and the value is genuinely unrecoverable.

**Spec affected:** [`_reversa_sdd/wing-design/requirements.md`] (BR-2, BR-W3, BR-7)
**Question:** Is a manual re-entry / audit pass expected, or is the current state
acceptable indefinitely?
**Impact:** Determines whether the spec needs migration tasks.

**Answer:** **All three audited against the live database on 2026-08-15 — no
remediation needed.** _Measured, at the maintainer's request, over `db/test.db`
(29 aircraft, 414 wing cross-sections, 47 spar rows)._

**① Pre-gh-402 metre rows in `wing_xsec_spares`: none.** All 47 rows have
`spare_support_dimension_width`, `spare_support_dimension_height`, `spare_length` and
`spare_start` **≥ 1.0**, so no row shows the sub-millimetre signature of metre-unit
contamination.

**② Pre-gh-1053 spar-origin loss: none.** Of 11 `normal`-mode spars, **0** lack an
explicit `spare_origin` or `spare_vector`, so none fail `should_preserve_normal_spare`
and none are having their origins recomputed away on read.

**③ Pre-gh-951 terminal dihedral: present but harmless.** 73 terminal ribs carry
`dihedral IS NULL` (381 of 414 ribs overall). However, **none of those 73 wings has a
non-zero dihedral stored anywhere**, so deriving the terminal value from geometry
yields exactly what persistence would have — nothing is unrecoverable.

**Verdict:** all three catalogued risks are theoretical for the current data. No audit
pass, no manual re-entry. The heuristics above are recorded so the check can be re-run
if data is imported from elsewhere.

---

## Q-WD-8 — Spar-sizing factor ownership (bundle) — **numerically load-bearing**

**Context:** Four questions about the structural pipeline whose answers change
the computed spar diameter:
- **`moment_fn` provenance.** Which service produces the bending-moment
  distribution, at which load case, and does it already apply `g_limit` / `j`?
  **A double application would be silent and would oversize every spar by 4.5×.**
- **`packing_factor` applied twice?** It scales `outer(y)` in the sizing formula
  (`spar_sizing.py:13`) *and* derives the containment band during station
  sampling.
- **Rod-equivalent OD.** Every station's `required_od` is solved as a **rod**
  regardless of the requested shape, so the band check is conservative for capped
  and rectangular spars. Intended, or should it use the requested shape's actual
  height?
- **`_MIN_REAR_X_C = 0.05` can defeat the hinge clearance.** When
  `hinge_x_c − 0.03 < 0.05` the floor wins and the computed rear spar sits
  **inside** the control surface, with no warning — the opposite of ADR 0012.

**Spec affected:** [`_reversa_sdd/wing-design/spar-sizing/requirements.md`],
[`_reversa_sdd/wing-design/spar-sizing/design.md`]
**Question:** Confirm each. These feed a structural safety output consumed
directly by the builder.
**Impact:** The highest-consequence numeric ambiguity in the corpus.

**Answer:** **Two of four concerns cleared; two confirmed defects, both to be
fixed: ①(a) implement the shapes properly, ②(a) wire the hinge guard and fix the
clamp order.** _Answered by the maintainer, 2026-08-13. Facts established by code
lookup — see [`wave2-lookups.md`](../wave2-lookups.md) §C for citations._

**✅ Cleared — `g_limit` / `j` are applied exactly ONCE.** The factor is applied at
`cad_designer/airplane/geometry/spar_solver.py:730`; the producer
(`app/services/spanwise_loads.py`) emits **un-factored** aerodynamic M(y), and the
second `g·j` in `app/services/spar_sizing.py:315` belongs to a disjoint code path.
There is **no ~4.5× oversizing**. *Action: state the un-factored input contract
explicitly in the spec so a re-implementation cannot get it wrong.*

**✅ Cleared — `packing_factor` is not applied twice.** Two different quantities in
two different paths: the containment band (`spar_solver.py:727`) versus the fixed
outer dimension in the #1008 path (`spar_sizing.py:323`). In the spar-plan path it
does not affect `required_od` at all, because `_solve_rod` ignores `outer_mm`.

### ① Rectangular and capped spars do not actually exist → **(a) implement them**

`spar_solver.py:733` always solves a **solid rod**, whatever shape was requested,
and `width` / `height` / `cap_width` are **never assigned anywhere**. A request for
`rectangular` or `capped` therefore returns a round solid rod: strength-adequate,
but heavier than necessary and **mislabelled** — exactly the silent substitution
`P-WARN-0` forbids.

**Maintainer's rationale — project intent, not previously recorded anywhere:**
these shapes are **not intended for 3D printing**. The plan is a future
**`WingCreator` that generates a classic wooden rib-and-spar construction**, with
the ribs **laser-cut from wood** using the laser-cutter attachment of the 3D
printer. Rectangular spars are wooden strips; capped spars are the classic
flange-and-web built-up wooden spar. Per-shape solving is therefore a
**prerequisite for a planned feature**, not a speculative nicety.

**Implications to carry into the spec:**
- Per-shape solving must assign the real dimensions (`width`, `height`,
  `cap_width`) instead of a rod-equivalent OD.
- The material library needs **wood** entries (different σ_allow and density than
  carbon tube); spar sizing is material-driven.
- The wooden-rib `WingCreator` is a **new** Creator — permitted under ADR 0002,
  which freezes the topology classes but explicitly allows new Creators.

### ② The gh-1059 hinge-clearance guard is dead → **(a) wire it and fix the order**

Two distinct defects:
- **Dead:** `control_surface_hinge_x_c` is passed by **no production caller**, so
  the guard never runs in the spar-plan pipeline.
- **Wrong order:** `return max(safe, _MIN_REAR_X_C)` (`spar_solver.py:221`) is
  applied *after* the hinge clamp, so with `_REAR_CLEARANCE_FRACTION = 0.03` and
  `_MIN_REAR_X_C = 0.05` it erodes the clearance for `hinge_x_c < 0.08` and places
  the rear spar **inside the control surface** for `hinge_x_c < 0.05`.

Both are fixed: the caller passes the hinge position, and the floor no longer
overrides the clearance (when the two conflict, that is an infeasibility to report
via `P-WARN-0`, not something to paper over). Leaving it inert was excluded by
`P-DEAD-0` in any case — and it is a **safety** guard: a rear spar inside the
control surface fouls the hinge line.

---

## Q-WD-9 — What does a duplicate control name return to the client?

**Context:** `assert_unique_control_names` raises before any AVL file is written,
but the exception *type* was not captured. A 422 (the user can rename) and a 500
(internal fault) imply very different UX. Same question for
`required_section_modulus`, which raises a bare `ValueError` on `σ_allow ≤ 0`
rather than a domain exception.
**Spec affected:** [`_reversa_sdd/wing-design/control-surface-mixing/contracts.md`],
[`_reversa_sdd/wing-design/spar-sizing/contracts.md`]
**Question:** Does a translation layer map these to 422, or do they surface as 500?
**Impact:** Two contract rows.

**Answer:** _(resolved by code lookup — not a maintainer decision)_ **They differ: a duplicate control name surfaces as an opaque **500** with its diagnostic message dropped, while `required_section_modulus` reaches the client as a **422** produced one layer up.**

Both raise a bare `ValueError`, which is outside the `ServiceException` hierarchy (`app/core/exceptions.py:11`) and therefore not translated by the global handler (`app/main.py:274-306`). `assert_unique_control_names` (`app/services/control_surface_mixing.py:149-164`) is called from `build_avl_geometry_file` (`app/services/avl_geometry_service.py:202-208`); the AVL-geometry routes catch only `ServiceException` (`app/api/v2/endpoints/aeroplane/avl_geometry.py:31-32`, `:64-65`), and the analysis call sites are mostly outside the surrounding `try` (`app/services/analysis_service.py:312`) — so every path yields a raw 500, and the message naming the duplicated control never reaches the body. There is no path on which it produces a 422; the user cannot tell "rename your control surface" from "the server is broken". `required_section_modulus`'s `ValueError` (`app/services/spar_sizing.py:78-88`) is unreachable in production because its only caller validates first with a real `ValidationError` → 422 (`app/services/analysis_service.py:2136-2150`), and `compute_spar_sizing` has exactly one caller, so there is no bypass.

**Verdict:** confirmed defect (`assert_unique_control_names`) + confirmed safe (`required_section_modulus`).
Residual decision: your 422-vs-500 call now applies only to the duplicate-name case, plus whether `required_section_modulus` should nevertheless become a domain exception so a future second caller cannot reintroduce the 500.

_Full detail: [`wave3-lookups.md`](wave3-lookups.md) §I_


**Residual decision — ANSWERED by the maintainer, 2026-08-15.**

**① A duplicate control-surface name returns 422, not 500.** Today
`assert_unique_control_names` raises a bare exception, which surfaces as a **500**
(confirmed defect). A duplicate name is **user-correctable input** — rename one of the
surfaces — so it is a `ValidationDomainError` per `Q-CC-3`. A 500 tells the user
something is broken when they can fix it themselves. The message must **name both
colliding surfaces**, otherwise the user cannot tell which to rename.

**② `required_section_modulus` gets a proper domain exception.** It currently yields
422 only *incidentally*, because the bare `ValueError` happens to be caught at the one
call site. A future second caller would get a 500 again. Converting it to an explicit
domain exception makes the status independent of who calls it.
---

## Q-WD-10 — Turbulator optimiser semantics (bundle)

**Context:** Six unresolved points on the gh-934 optimiser:
- **Is `xtr_opt` ever persisted** back into `wing_xsec_turbulators`? If adoption
  is manual (consistent with ADR 0007) the UI needs an explicit apply step; if it
  is automatic anywhere, the propose/adopt boundary is being crossed silently.
- **How is `symmetry_factor` chosen?** Documented as `2` "for a symmetric wing",
  but whether the code reads `wings.symmetric` or infers it from the section list
  was not captured. **A vertical stabiliser is exactly where this goes wrong, and
  a doubled `ΔCD0` is invisible in the output.**
- **`height_mm` and `form` do not enter the drag model** — the optimiser sweeps
  position only, while trip height and form are physically what determine whether
  transition is forced. Should the response carry that caveat, the way
  `airfoil-catalog` carries its explicit caveat block?
- **How does one `xtr_opt` per section map onto a per-segment
  `position_root` / `position_tip` pair?** The stored turbulator supports a
  tapered strip; the optimiser reports a single value per section.
- **Does an out-of-range operating `CL` produce a NaN or a silent clamp?**
  `_ALPHA_GRID` spans `[-4°, 14°]`; if it clamps, the reported optimum is for a
  different operating point than the one requested.
- **What does `POST /turbulator/optimize` return without AeroSandbox?** A 500, an
  empty result and a platform warning are all plausible — only the last is
  consistent with ADR 0012.

**Spec affected:** [`_reversa_sdd/wing-design/turbulator-optimizer/requirements.md`],
[`_reversa_sdd/wing-design/turbulator-optimizer/design.md`]
**Question:** Confirm each.
**Impact:** The turbulator slice is the least verifiable part of `wing-design`.

**Answer:** _(resolved by code lookup — not a maintainer decision)_ **Two of the six settled factually: `xtr_opt` is **never** persisted — the endpoint is compute-only and adoption stays manual — and `symmetry_factor` is `2.0 if main_wing.symmetric else 1.0`, **read** from the `wings.symmetric` column via the ASB converter, not inferred from the section list.**

`optimize_turbulator` (`app/api/v2/endpoints/aeroplane/turbulator_optimizer.py:184-199`) calls `_call_optimizer` then `_result_to_response` with no DB write in between, and the only writers of `position_root` / `position_tip` in `app/` are ordinary wing CRUD (`app/services/wing_service.py:1541`, `app/models/aeroplanemodel.py:401`) and the version clone (`app/services/aeroplane_clone_service.py:279-284`) — so ADR 0007's propose/adopt boundary is not crossed and the UI does need an explicit apply step. Stored positions are read in the other direction only, by the assumption pipeline's `cd0` adjustment (`app/services/assumption_compute_service.py:2236-2237`). `symmetry_factor` is set at `app/services/turbulator_optimizer_service.py:330-331`, with `wing_symmetric` read at both call sites from the **largest-planform-area** wing (`turbulator_optimizer.py:99-102`, `assumption_compute_service.py:144-148`), and ASB's `Wing.symmetric` comes straight from the DB column (`app/converters/model_schema_converters.py:796-806`). The anticipated vertical-stabiliser failure mode therefore does not occur, for two independent reasons: the flag is read rather than inferred, and the optimiser only ever runs on the largest-area surface.

**Verdict:** confirmed safe / as-specified on both.
Residual decision: whether Slice 3 (persisting the optimum back to `wing_xsec_turbulators`) is still wanted, together with the per-section → per-segment mapping and the three items `P-WARN-0` constrains, remains a product call.

_Full detail: [`wave3-lookups.md`](wave3-lookups.md) §J_


**Residual decision — ANSWERED by the maintainer, 2026-08-14/15, with expert
consensus on the height criterion.**

**① Slice 3 is wanted — the optimum flows back into `wing_xsec_turbulators`.**
Maintainer's rationale: the turbulator is a **manufacturable feature**, not merely an
analysis parameter — a `WingCreator` can **print it directly into the wing**. An
explicit "apply" step in the UI preserves the ADR 0007 propose/adopt boundary.

**② Mapping section → segment: store the position as a fraction of the segment's own
root and tip chord**, i.e. exactly the existing `position_root` / `position_tip` pair.
Where the computation ran in root-to-tip mode, the section values are **interpolated**
onto the segment's root and tip stations.

**③ Height — add ONE `height_mm` per turbulator (not a root/tip pair), sized at the
segment root.** _Expert consensus, `expert-consensus-turbulator.md`._

- **Criterion:** `Re_k = u_k·k/ν ≥ Re_k,crit` — **600** for 3D roughness (`dots`;
  Braslow & Knox, NACA TN 4363 — *external source, not in any project vault*),
  **≈300 (200–400)** for 2D elements (`zigzag`, `thread`).
- **Procedure:** at the **segment root** (largest chord ⇒ largest `k_min`) and at the
  **lowest** operating speed the trip must work at (≈1.1–1.3 × V_stall, **not**
  cruise): `δ = 5.0·√(νx/u_e)` (Blasius), then root-find
  `f'(5k/δ)·u_e·k/ν = Re_k,crit`; ×1.25 in an adverse pressure gradient. The computed
  value is used **directly** — see the manufacturing note below.
- **No spanwise pair.** `k_min ∝ c^(1/4)`, so even at taper 0.3 the requirement varies
  ≤26 % root→tip — **below print quantisation**. This overrules the earlier proposal
  for `height_root_mm` / `height_tip_mm`.
- **The project's `0.3 mm` default is subcritical almost everywhere** (`k_min` is
  0.25–0.85 mm across the envelope). **Recommended default: 0.5 mm.**
- **Sizing speed matters:** `Re_k ∝ V^1.5`, so a cruise-sized trip is 2.8× subcritical
  at half speed.

**Warning policy (per `P-WARN-0`) — graded, never blocking.** A genuine
theory-vs-practice disagreement was recorded: theory says 0.3 mm zigzag should not
work, RC practice says it does. Resolved by treating `Re_k ≥ Re_k,crit` as
**sufficient, not necessary**. Therefore: below `k_min` → `warning` (the forced
transition is not justified, so the computed polars are optimistic); far above
(`k/δ ≳ 0.8`, penalty `Δcd_trip ∝ k³`) → `notice`; **above Re ≈ 250 000** → `notice`
that the measured benefit has vanished (40 % at Re 60 k, 19 % at 100 k, 4 % at 200 k,
**0 % at 400 k**).

**④ `height_mm` and `form` do not enter the drag model — declared as a caveat.**
Confirmed factually: `xtr_upper` means "transition is forced here", is
mechanism-agnostic, is **blind to `k`**, and models **no trip form drag** (verified in
the Sharpe PhD thesis §7.2 and in the installed `neuralfoil/main.py:108,163-177`).
The response carries an explicit caveat block, as `airfoil-catalog` already does.

**Manufacturing note — CORRECTED 2026-08-15 by the maintainer.** An earlier draft of
this answer assumed the printed turbulator height is quantised by layer height /
nozzle width, and that assumption was carried into the expert brief. **It is wrong.**
The wing is printed **standing on its root rib**, so the spanwise axis lies along the
build (Z) direction and the turbulator height protrudes in the **layer plane (XY)**,
not in Z. Layer height therefore does not quantise it: as a contour deviation of the
lofted solid, the slicer simply follows the geometry, and **near-arbitrary heights are
achievable**. Consequence: `k_min` is adopted directly rather than rounded up, and the
"far above `k_min`" branch becomes a genuine design choice (unnecessary form drag)
rather than a manufacturing constraint.

**⑤ Optimiser objective.** Single-point optimisation is **fine for position**
(off-design penalty +0.0…+4.1 % at Re 100 k) but **not for height**, which must be
sized at the low-speed end as above.

---

## Q-WD-11 — Is a stored non-zero `deflection_deg` meant to persist into every trim?

**Context:** `deflection_deg` doubles as the primary-axis **baseline** deflection
in the gh-772 decomposition.
**Spec affected:** [`_reversa_sdd/wing-design/control-surface-mixing/requirements.md`] (BR-9)
**Question:** Should a stored commanded deflection persist into every subsequent
trim, or be reset?
**Impact:** Affects every trim result on an aircraft with a pre-set surface.

**Answer:** **Trim starts at zero; a stored `deflection_deg` is NOT a baseline.**
_Answered by the maintainer, 2026-08-15._

**Maintainer's rationale — this reverses the field's role:** `deflection_deg` is meant
to end up holding **the trim value the solver found**, so it can be handed to the pilot
who then dials that trim in physically. It is therefore an **output of trimming, not an
input to it**.

Consequence: trimming ignores any stored value and begins at zero; the result is
written back. The gh-772 decomposition must not treat the stored value as the primary
axis's baseline deflection (BR-9), or the aircraft would be trimmed relative to an
earlier answer and drift with each run.

---

# fuselage-design

## Q-FD-1 — Duplicate name: is 409 (fuselage) or 422 (wing) the intended contract?

**Context:** `create_fuselage` raises `ConflictError` → **409**
(`fuselage_service.py:80-84`); `create_wing` raises `ValidationError` → **422**
for the identical situation (`wing_service.py:285-300`). Two adjacent CRUD
families, one condition, two status codes. Both sides document their own
behaviour and name the divergence.
**Spec affected:** [`_reversa_sdd/fuselage-design/requirements.md`] (BR-F17, RF-03),
[`_reversa_sdd/wing-design/contracts.md`], [`_reversa_sdd/openapi/da3dalus-v2.yaml`]
**Question:** Which is correct?
**Impact:** Changing either is a client-visible break; the OpenAPI document
currently has to declare both.

**Answer:** **ANSWERED by the maintainer, 2026-08-15** (option a) — **409 everywhere; `create_wing` aligns to the fuselage's `ConflictError`.**

_This overrides a derived answer that had proposed the opposite (422, by analogy to `Q-WD-9 ①`). The maintainer was shown that analogy explicitly and chose 409._

**The rule:** a **create** whose name collides with an existing sibling is a **conflict with persisted state**, not an unreadable payload. The request is well-formed and would succeed against a different aeroplane; only the current contents of the database make it fail. That is what 409 means. `create_wing`'s `ValidationError → 422` becomes `ConflictError → 409`, and the OpenAPI document stops declaring both codes for one condition.

**Reconciliation with `Q-WD-9 ①`, which stays 422.** The two are not the same operation, and the discriminator is recorded here so the divergence is principled rather than historical:

| | operation | why |
|---|---|---|
| **409** | *creating* a resource whose name collides with an existing sibling | the payload is valid; existing state rejects it |
| **422** | *processing* a configuration and finding two control surfaces share a name | the submitted configuration is internally inconsistent — nothing external is in conflict |

A duplicate control-surface name is discovered while **building an AVL file from a design the user already owns**; there is no second party to conflict with. A duplicate wing name is discovered while **adding a row next to rows that already exist**. The first is bad input, the second is a state conflict.

**Both messages must name the colliding item** — that requirement from `Q-WD-9 ①` is independent of the status code and carries over unchanged.

**Cost:** client-visible break on `create_wing`, affordable because every consumer is in this repository (ADR 0024) — and it must land before TypeScript client generation (`Q-CC-11`).

---

## Q-FD-2 — What unit is an uploaded STEP assumed to be in?

**Context:** Verified during review: `slice_step_to_fuselage`
(`cad_designer/aerosandbox/slicing.py:856-865`) takes **no scale or unit
parameter**, and `app/services/fuselage_slice_service.py` performs no scaling.
The emitted `a` / `b` / `xyz` are the STEP's **native** coordinate values,
persisted as metres. That is safe on the OpenVSP path only because BR-OV13 forces
`STEPSettings.LenUnit = LEN_M`. On the user-upload route nothing constrains the
unit, and millimetres are both the normal CAD authoring convention and the
convention `cad_designer` itself uses (ADR 0001). A millimetre STEP yields a
fuselage **1000× too large**, silently — `volume_ratio` / `area_ratio` stay ≈1.0
because they are reconstruction-to-original ratios.

The same question applies to construction parts: columns are `volume_mm3` /
`area_mm2` / `bbox_*_mm`, so millimetres are assumed, and `_extract_geometry`
verifies nothing — a metre STEP records a volume 10⁹× too small.
**Spec affected:** [`_reversa_sdd/fuselage-design/step-slicing/design.md`] §F4
(reclassified 🟢 → 🟡 during review),
[`_reversa_sdd/construction-plans/construction-parts/requirements.md`]
**Question:** Should the slicer take an explicit source-unit parameter, detect
the unit from the STEP header, or is "metres only, undocumented" the intended
contract? Answer for both upload paths — they should agree.
**Impact:** The most reachable silent-1000× path in the system.

**Answer:** **(a) Unify the *mechanism* across both upload paths: header detection
+ explicit override + a plausibility check.** _Answered by the maintainer,
2026-08-13._

Three layers, because no single one is reliable on its own:

1. **Read the unit from the STEP header** — the `SI_UNIT` entries in the
   `GEOMETRIC_REPRESENTATION_CONTEXT` are standard and usually correct.
2. **Explicit override at upload**, pre-filled with the detected value. Necessary
   because header data is not trustworthy in practice: the project's own RV-7 test
   fixture was found during analysis to carry **contradictory** `SI_UNIT`
   declarations.
3. **Plausibility check on the resulting dimensions**, emitting a `DesignWarning`
   when the result is implausible. This is the most robust layer and needs no
   header at all: an RC fuselage is 0.3–3 m, so 1700 m or 1.7 mm is unambiguous.

**Unify the mechanism, not the assumed unit.** Storage stays as it is — fuselage
geometry in metres, `construction_parts` in millimetres (`volume_mm3`,
`bbox_*_mm`) — and conversion happens at import. Today the two upload paths assume
**opposite** units with no verification on either:

| Path | Assumption | Failure mode |
|---|---|---|
| Fuselage slicing | metres | a millimetre STEP yields a fuselage **1000× too large** |
| Construction parts | millimetres | a metre STEP records a volume **10⁹× too small** |

**Why this is invisible today:** `volume_ratio` and `area_ratio` compare the
reconstruction against the original, so a uniform scale error **cancels out** and
both stay ≈ 1.0. The existing quality metrics cannot detect it by construction —
which is why the plausibility check must be on absolute dimensions.

**Rejected:** (b) explicit parameter only — a mis-stated unit still propagates
silently; (c) "metres only, enforced" — impractical, since millimetres are both the
normal CAD authoring convention and the convention `cad_designer` itself uses
(ADR 0001).

---

## Q-FD-3 — Should the `a`/`b` ↔ ASB `width`/`height` mapping be asserted at runtime?

**Context:** `a` is the **Y half-axis** and maps to `FuselageXSec.width`; `b` is
the **Z half-axis** and maps to `height` (gh-706). Swapping them rotates the body
90°; treating them as diameters doubles it. Neither produces an error, and the
convention lives only in field descriptions.
**Spec affected:** [`_reversa_sdd/fuselage-design/requirements.md`] (BR-F1),
[`_reversa_sdd/fuselage-design/superellipse-xsecs/requirements.md`]
**Question:** Add a runtime assertion? And: do any existing `fuselage_xsecs` rows
hold full widths instead of half-axes (detectable only against the source STEP
bounding box where a `step_path` survives)?
**Impact:** A historical importer error here would be invisible today.

**Answer:** _(expert consensus, endorsed by the maintainer 2026-08-14)_ **Not a bare runtime assertion — collapse the two independent `2.0 * a` conversions into one `superellipse_to_asb_xsec(a, b, n)` seam so the convention holds by construction, then check against the STEP bounding box where a `step_path` survives.**

The three failure modes have very different signatures, and the one that matters most is invisible to every integral metric: a **swap `a ↔ b`** rotates the body 90° while leaving volume and wetted area near-unchanged (*exactly* unchanged for a body of revolution), so `volume_ratio`/`area_ratio` (Q-FD-4) cannot see it — yet AeroBuildup's fuselage model reads width and height separately (Jorgensen slender-body inviscid + crossflow-analogy viscous, separation keyed to local curvature), so a swap produces confidently wrong side force and `C_nβ`. The **factor-2** and **half-factor** errors *are* caught by the ratios (≈ 4.0 and ≈ 0.25 respectively). A bare assertion is the wrong instrument because it can only compare `a`/`b` against something, and the only meaningful something is the source geometry. Three measures, in priority order: **(1)** one conversion seam replacing the `2.0 * a` in `cad_designer/aerosandbox/slicing.py:1291-1300` and `app/converters/openvsp_fuselage_handler.py:215`; **(2)** at **import time only**, per xsec, `2a ≤ 1.02 · Y_extent(step)` and `2b ≤ 1.02 · Z_extent(step)` to catch the factor-2 error, plus `max_x(2a)/max_x(2b)` within **20 %** of `Y_extent/Z_extent` for the whole body to catch the swap on any non-circular fuselage (on a body of revolution the swap is both unobservable and harmless, so this raises no false positive); **(3)** where there is no source, an aspect-ratio plausibility band `2a/2b ∈ [0.3, 3.0]` — outside it, `severity="warning"`, **never an exception**, because a 0.5 kg foamie with a genuinely 4:1 flat fuselage exists and refusing to store it would be worse than the bug.

**On the historical audit: the check in (2) *is* the audit query.** Run it once over `fuselage_xsecs` rows that still have a `step_path`; a row whose `2a` exceeds the STEP Y-extent by ≈ 2× is a pre-fix full-width row. Rows with no surviving `step_path` cannot be checked and must be reported as `unverified` rather than pretended-clean — the same conclusion the wing-side audit reached for pre-gh-951 terminal dihedral.

**Authority:** AeroSandbox tooling (`FuselageXSec` takes full `width`/`height`; the fuselage buildup reads the two dimensions separately); ADR 0012 / `P-WARN-0` for `DesignWarning` over a hard raise; RC practice for the `[0.3, 3.0]` band.
**Confidence:** high on the failure-mode analysis and on the assertion being the wrong instrument; medium on the specific 1.02 / 20 % / [0.3, 3.0] numbers.

_Full reasoning: [`expert-consensus-aero.md`](expert-consensus-aero.md)_

---

## Q-FD-4 — What `volume_ratio` / `area_ratio` counts as an unacceptable fit?

**Context:** Both are reported with every slice result (BR-F11) but nothing
thresholds, flags or rejects a poor reconstruction, so a caller can store a badly
simplified body with no signal. Relatedly, the superellipse exponent bound
`n ∈ [0.5, 8.0]` is enforced silently by the optimiser — a body whose true
exponent lies outside is fitted **at** the bound with no indication, the opposite
of ADR 0012.
**Spec affected:** [`_reversa_sdd/fuselage-design/step-slicing/requirements.md`]
**Question:** Is there a threshold below which the fit should be rejected or
warned about? Should a bound-hitting `n` produce a warning?
**Impact:** Two acceptance criteria.

**Answer:** _(expert consensus, endorsed by the maintainer 2026-08-14)_ **Good `[0.95, 1.05]` → silent; degraded `[0.85, 0.95) ∪ (1.05, 1.15]` → `info`; poor `[0.70, 0.85) ∪ (1.15, 1.40]` → `warning`; reject outside `[0.70, 1.40]`, or `volume_ratio ≤ 0.05`, or non-finite — and yes, a bound-hitting `n` must warn.**

The bands are anchored on what the numbers are used for at this scale — fuselage parasite drag, not structural loads. Sadraey Eq. 7.5 gives `C_D0,f = C_f · f_LD · S_wet,f / S_ref` with `f_LD = 1 + 60/(L/D)³ + 0.0025·(L/D)`, so a **5 % `area_ratio` error is a 5 % error in fuselage `C_D0`**; the fuselage carries 15–30 % of a typical RC model's parasite drag, hence ~1 % of aircraft `C_D0` — comfortably inside the Reynolds-driven scatter (profile drag "nearly doubles" across the model Re band). A 10 % volume error at fixed length is a ~5 % diameter error, moving `f_LD` by ~4 % at a typical RC `L/D` ≈ 6–8. Two deliberate choices in the table: the **1.40 upper cut sits below 4.0**, so Q-FD-3's factor-2 bug is caught by this gate as well as by the source-anchored check; and the **≤ 0.05 / non-finite cuts** catch the degenerate-dimension case that already produced 15/15 NaN on the Stratos inside AeroBuildup's `log10` — that must fail loudly at slice time, not silently downstream. The ratios are asymmetric in meaning: `> 1` is worse than `< 1` by the same margin, because a reconstruction *bigger* than the source means the superellipse bulges outside the real skin (geometrically impossible for a fit, and a strong units/half-axis signal), while *smaller* is the expected direction for a simplification. Ship the symmetric bands first; tighten the upper edge to 1.02 and leave the lower at 0.90 once ratio statistics exist over a real corpus.

**State the limits in the response rather than letting a caller read the ratios as a fit-quality score.** A ratio near 1.0 is necessary, not sufficient: it cannot detect the `a ↔ b` swap (volume-neutral), local errors that cancel (a fat nose against a thin tail integrates to ≈ 1.00), surface smoothness (which is what actually drives drag), or the *position* of the volume (which drives CG and `C_m`). On the exponent: `np.clip(fit["n"], 0.5, 8.0)` at `slicing.py:1285` silently returns a fit sitting *at* the bound — the textbook silent-degradation shape and the exact opposite of ADR 0012. `n → 8.0` means a near-rectangular section, **very common on 3D-printed and foam-board RC fuselages**; `n → 0.5` means a strongly concave/star section, which for a real fuselage almost always means the optimiser diverged. Emit a per-station `DesignWarning(severity="info")` naming the station and the bound, count them, and **escalate to `severity="warning"` above 25 % of stations** — past that the superellipse family is the wrong model for the body and the user should be told rather than quietly handed a rounded box.

**Authority:** Sadraey Eq. 7.5 / fineness-ratio drag sensitivity (band calibration); AeroSandbox tooling (`volume()` / `area_wetted()`, and why a degenerate dimension goes NaN downstream); RC practice (near-rectangular printed fuselages) for the `n`-bound severity; ADR 0012 / `P-WARN-0` for the mandatory warning.
**Confidence:** medium-high — the failure-mode analysis and the reject cuts are solid; the 0.95 / 0.85 / 0.70 edges are engineering judgement calibrated on the drag sensitivity above.

_Full reasoning: [`expert-consensus-aero.md`](expert-consensus-aero.md)_

---

## Q-FD-5 — Should a 5–30 s CPU-bound slice become an asynchronous job?

**Context:** BR-F13 documents 5–30 s of CPU-bound work per slice. There is no
progress, cancellation or timeout surface — one upload occupies a worker for the
whole duration. Every other long CAD operation in the system is a task with a
status endpoint.
**Spec affected:** [`_reversa_sdd/fuselage-design/step-slicing/requirements.md`]
**Question:** Deliberate simplification, or should it join the task model?
**Impact:** Changes the endpoint's contract from 200-with-body to 202-with-status.

**Answer:** **ANSWERED by the maintainer, 2026-08-15** (option a) — **STEP slicing joins the task model: `202 Accepted` plus a status endpoint, like every other long CAD operation.**

**Consistency is the primary argument, and it is not cosmetic.** Every other operation of
this duration in the system is already a task with a status endpoint. A single synchronous
outlier means the client needs two interaction patterns for the same class of work, and
the one place a user has no progress indication is a 5–30 s wait during which the UI can
only appear frozen.

**The single-user argument (ADR 0024) was considered and does not carry.** It establishes
that nobody is *queued behind* the blocked worker — which disposes of the throughput
concern, and only that one. It says nothing about the three properties actually missing:
**progress**, **cancellation**, and a **timeout**. A single user staring at an
unresponsive upload is the case ADR 0024 describes, not an exception to it — and with one
worker, a slice that hangs takes the whole application with it.

**Contract change:** the endpoint returns `202` with a task id instead of `200` with the
result body; the slices are fetched from the task result. Client-visible, and affordable
for the usual reason — every consumer lives in this repository (ADR 0024) — and it must
land before TypeScript client generation (`Q-CC-11`).

**Carried over from option (b):** the task still needs a timeout and a readable failure.
Moving to the task model does not by itself bound the work, and a slice that never
finishes is now an eternally `RUNNING` task rather than an eternally open request — better,
but not resolved. The timeout is part of this change, not a follow-up.

---

## Q-FD-6 — Fuselage slicing details that were not read (bundle)

**Context:** Four small unknowns:
- **What does `slice_axis="auto"` actually do**, and what are the alternatives?
  The parameter is in the signature but its resolution logic was not read.
- **Does the pipeline guarantee ≥ 2 usable slices before returning?** A body
  yielding fewer would only fail later, on the caller's `PUT`, against
  `min_length=2`.
- **Is there a maximum cross-section count?** `min_length=2` is enforced; no
  upper bound was found.
- **Should a failing component-tree sync block a fuselage delete?** The lazy
  import here is for cycle-breaking only, with **no** `try/except`, unlike
  `aeroplane-core`'s explicitly best-effort `_sync_aircraft_mass`.

**Spec affected:** [`_reversa_sdd/fuselage-design/step-slicing/design.md`],
[`_reversa_sdd/fuselage-design/superellipse-xsecs/requirements.md`]
**Question:** Confirm each.
**Impact:** Four 🟡s become 🟢.

**Answer:** _(resolved by code lookup — not a maintainer decision)_ **Three of the four: `slice_axis="auto"` resolves to the longest bounding-box axis; ≥ 2 **usable** cross-sections are **not** guaranteed; and there are two upper bounds — 500 at the HTTP boundary, 4 096 internally on the shell path.**

`"auto"` calls `detect_longest_axis` (`cad_designer/aerosandbox/slicing.py:470-473`, `:892-904`), a pure bounding-box comparison — so a short, wide body (a flying-wing pod) is sliced across its span with no warning. The alternatives are `"x"` (no-op), `"y"` (rotate +90° about Z), `"z"` (rotate −90° about Y); anything else raises, and the endpoint pre-validates the four literals with a 422 (`app/api/v2/endpoints/fuselage_slice.py:44-48`), so that branch is defence-in-depth. The two clamps (`slicing.py:949-955` and `:498-500`) bound the **station count**, not the sections that survive: three separate gates drop stations (`:958-960`, `:987-993`, `:544-547`), nothing between the loop and the return asserts `len(xsec_dicts) >= 2`, and `slice_step_file` does not check either (`app/services/fuselage_slice_service.py:87-97`) — so a degenerate body returns HTTP 200 with 0 or 1 xsecs and only fails later on the caller's `PUT` against `min_length=2`. The CUSTOM OpenVSP handler enforces exactly this invariant (`app/converters/openvsp_custom_handler.py:98-106`), so the pattern exists in the codebase and is simply missing here. Bounds: `Form(ge=2, le=500)` on `number_of_slices` and `10 ≤ points_per_slice ≤ 200` (`fuselage_slice.py:25-30`), plus `min(…, 4096)` on the shell/adaptive path (`slicing.py:951`); the solid path has no 4 096 clamp, and nothing bounds the *stored* `x_secs` list.

**Verdict:** confirmed defect on the ≥ 2-usable-slices item; confirmed safe / as-specified on the axis resolution and the upper bounds.
Residual decision: the fourth bundle item — whether a failing component-tree sync should block a fuselage delete — was not part of this lookup and still needs you.

_Full detail: [`wave3-lookups.md`](wave3-lookups.md) §G_


**Residual decision — ANSWERED by the maintainer, 2026-08-15: best-effort, but the
failure is surfaced as a `DesignWarning`.**

A failing component-tree sync must **not block** deleting a fuselage. The primary
intent is the delete; a secondary bookkeeping step should not veto it. This also makes
the module consistent with `aeroplane-core`, whose `_sync_aircraft_mass` is explicitly
best-effort — today the two behave in opposite ways, because the fuselage path has
**no** `try/except` and a sync failure therefore propagates and fails the delete.

But it is **not** silently logged: a failed sync leaves an **orphaned group node** in
the component tree, so it emits a `DesignWarning` (`P-WARN-0`) naming the orphan. Best
effort about *blocking*, not about *reporting*.

The other three items of this bundle were settled by the code lookup (`slice_axis="auto"`
= longest bounding-box axis; **≥ 2 usable slices are NOT guaranteed** — confirmed
defect; two upper bounds on the cross-section count do exist).
---

## Q-FD-7 — Should `update_fuselage` preserve import artefacts?

**Context:** `update_fuselage` is a destructive replace, not a merge — the old
`FuselageModel` is removed from the collection and a brand-new one appended
(`fuselage_service.py:120-122`). Any `step_path` / `solid_step_path` absent from
the incoming payload is **lost**.
**Spec affected:** [`_reversa_sdd/fuselage-design/requirements.md`] (BR-F18)
**Question:** Should the update preserve import artefacts when the client omits
them?
**Impact:** Today an edit through the UI can silently orphan an imported STEP.

**Answer:** **Yes — preserve import artefacts when the client omits them.**
_Answered by the maintainer, 2026-08-15._

`update_fuselage` is a destructive replace rather than a merge: the old
`FuselageModel` is removed from the collection and a new one appended
(`fuselage_service.py:120-122`), so any `step_path` / `solid_step_path` missing from the
payload is **lost** and its file orphaned.

This is the **same defect class as issue #1094** (`ComponentEditDialog` hard-codes
`model_ref: null`, erasing the uploaded model on every edit): an update that silently
discards a field the client simply did not send. Recorded as such in the spec so both
are recognised as one pattern — *a partial update must not destroy what it does not
mention.*

---

## Q-FD-8 — Is `FuselageConfiguration.from_step_file` dead, and is a parametric CAD fuselage planned?

**Context:** `from_step_file` assigns
`analysis_specific_options = {dict(panel_resolution=24, panel_spacing="cosine")}`
— a **set containing a dict**, which raises `TypeError` because dicts are
unhashable (`FuselageConfiguration.py:123-125`). Strong evidence the path is
never executed. The class also carries a literal
`#TODO generate fuselage from XSecs`, so there is no way to build a CAD fuselage
from cross-sections at all.
**Spec affected:** [`_reversa_sdd/fuselage-design/requirements.md`] (BR-F22),
[`_reversa_sdd/cad-designer-topology/requirements.md`]
**Question:** Is the path dead? And is a parametric CAD fuselage planned, or is
STEP intended to remain the only CAD-side source permanently?
**Impact:** This is the stated reason both representations must coexist — it is
the load-bearing justification for the module's whole dual-representation design.

**Answer:** _(**partially** derived — the roadmap half is REOPENED as `Q-FD-8b`, below)_ **The `from_step_file` path is dead and is recorded as removed; STEP is not the only CAD-side source, because a fuselage lofted from the stored cross-sections is a required *fallback*.**

Follows from **Q-VI-4 ③**, which turns the class's own `#TODO generate fuselage from XSecs` into a requirement: when `solid_status != ok`, *"the Creators loft an approximate solid from the stored `fuselage_xsecs` superellipses"*, a body *"well-formed by construction, being a loft of simple closed curves"*. The roadmap half is therefore answered — both representations are load-bearing (STEP for precise imported geometry, superellipse x-secs for the buildable fallback and for drag/layout), and the xsec → CAD loft is scheduled work rather than an open question.

> **⚠ Second correction, 2026-08-15 — the parenthetical above understates the x-secs and
> must not be carried into the fuselage-design specs in that form.** `Q-FD-8b` established,
> by code measurement, that **parametric fuselage authoring is already implemented** in
> both frontend and backend. So the cross-sections are not "the fallback representation
> plus drag/layout" — they are a **first-class authoring surface**, and a user may design a
> fuselage from them with no STEP file involved. The dual representation is therefore two
> **peer** paths into the model, not a primary and a substitute. What is still missing is
> only the CAD side: generating a solid *from* those cross-sections. The `set`-of-`dict` assignment proves `from_step_file` has never executed, which is **P-DEAD-0 / ADR 0021** rule 3; because `FuselageConfiguration.py` sits inside the **ADR 0002** freeze, the removal is *stated in the spec* rather than executed, exactly as ADR 0021 prescribes for that directory.

> **⚠ Narrowed 2026-08-15.** The original derivation overstated its reach: it concluded
> from `Q-VI-4 ③` that "the roadmap half is answered". It is not. `Q-VI-4 ③` makes the
> loft a **required fallback for a defective STEP solid** — reached when
> `solid_status != ok`. That is not the same claim as a parametric fuselage being a
> **first-class design path**: designing a fuselage from cross-sections with no STEP
> file involved at all. The first is recovery, the second is authoring. Only the first
> is in the record.
>
> **What survives as derived:** `from_step_file` has provably never executed
> (`analysis_specific_options = {dict(...)}` — a set containing an unhashable dict),
> so P-DEAD-0 rule 3 applies; and the dual representation keeps its justification
> either way, because the loft fallback needs the x-secs.

## Q-FD-8b — Is *authoring* a fuselage from cross-sections (no STEP) planned?

**Reopened from `Q-FD-8`, 2026-08-15.** The fallback loft (`Q-VI-4 ③`) is settled. The
open question is whether a user may ever **create** a fuselage parametrically — enter
superellipse stations, get a CAD body — without importing or uploading a STEP file.

**Why it matters beyond one requirement:** it decides whether `fuselage_xsecs` is a
*derived, simplified view of an imported body* (today's role, per
`project_fuselage_step_vs_xsec_roles`) or an **authoring surface in its own right**. The
second reading makes the x-secs a source of truth and pulls validation, defaults and UX
toward them.

**Answer:** **ANSWERED by the maintainer, 2026-08-15** (option b) — **yes, and the premise of this question was wrong: parametric fuselage authoring is already implemented, in both frontend and backend. Imported fuselages can even be reworked.**

_The maintainer corrected this, and it was verified in code rather than taken on trust._

| layer | evidence |
|---|---|
| **Backend** | `create_fuselage` / `update_fuselage` (`fuselage_service.py:63, 103`) accept a full `FuselageSchema` — including `x_secs` — and rebuild the model via `FuselageModel.from_dict`. A fuselage can be created and overwritten from cross-section data alone. |
| **Frontend** | `PropertyForm.tsx` carries a `"fuselage"` mode (`:24`), selects a cross-section by index (`:529-532`) and edits it through `useFuselage(...).updateXSec` (`:575`). `useFuselage.ts` / `useFuselages.ts` exist. |

**So `fuselage_xsecs` is an authoring surface in its own right, not a derived view of an
imported body.** That is the opposite of what `Q-FD-8` inferred, and it changes where
validation, defaults and UX belong: they belong **on the cross-sections**, because a user
can start there with no STEP file in sight.

**The `#TODO generate fuselage from XSecs` is real, but it sits one layer down.** It is in
`cad_designer/.../FuselageConfiguration.py` and concerns **CAD geometry generation** from
the cross-sections — turning the superellipse stations into a solid. That capability does
not exist yet and is exactly the loft scheduled by `Q-VI-4 ③` as the fallback for a
defective STEP solid.

**The two must not be conflated again**, which is how the original error arose:

| | status |
|---|---|
| **authoring** fuselage cross-sections (app level) | ✅ **implemented**, FE + BE |
| **generating CAD geometry** from those cross-sections (`cad_designer`) | ❌ planned — the `Q-VI-4 ③` loft |

A user can therefore design a fuselage parametrically today and get a persisted,
analysable model (the x-secs feed drag and layout); what they cannot yet get is a CAD
solid for the Creators without a STEP file. That is one gap, not two, and closing it is
the loft.

---

# airfoil-catalog

## Q-AF-1 — Are all 1 665 bundled `.dat` files Selig, and should format sniffing be added?

**Context:** `_parse_dat_file` assumes Selig ordering and skips the first line as
a header. A Lednicer-format file's two-column count row would be mis-parsed as
coordinates rather than rejected. There is no format detection anywhere.
**Spec affected:** [`_reversa_sdd/airfoil-catalog/requirements.md`] (BR-C2)
**Question:** Are the bundled files all Selig, and should sniffing be added for
user uploads (`POST /airfoils/datfile`)?
**Impact:** A mis-parsed airfoil produces a plausible but wrong geometry, which
then propagates into polars, scoring and CAD.

**Answer:** _(resolved by code lookup — not a maintainer decision)_ **Yes — all 1 665 bundled `.dat` files are Selig: a scan replicating `_parse_dat_file` exactly found **0** Lednicer candidates.**

The scan (a throwaway script in the session scratchpad, not the repository) reproduced `app/services/airfoil_service.py:57-87` — skip line 0 as a header, accept any line whose first two whitespace tokens parse as floats — and flagged a Lednicer candidate when the first parsed pair has both values `> 1.0` (the point-count row). Results: 0 candidates, 0 files with `|y| > 1.0`, 0 files with fewer than 3 parsable coordinates, and 0 files where line 0 parses as a coordinate pair — so the unconditional `lines[1:]` header skip (`:73`) loses nothing on the bundled corpus. The 65 files with some `x > 1.0` are one extended-chord section (`e664ex.dat`, max_x 1.2) and 64 rounding-level overshoots (all ≤ 1.002).

**Verdict:** confirmed safe for the bundled corpus — format sniffing would change nothing today.
Residual decision: user uploads via `POST /airfoils/datfile` are not validated at all — `_save_airfoil_dat` (`app/api/v2/endpoints/airfoils.py:437-458`) writes the bytes without parsing them, so a Lednicer file is accepted and mis-parsed on first read — and whether to add sniffing on that upload path is still your call.

_Full detail: [`wave3-lookups.md`](wave3-lookups.md) §E_


**Residual decision — ANSWERED by the maintainer, 2026-08-14: (a) sniff the format
on upload and convert.**

The bundled corpus is clean (all 1 665 files are Selig), so this is purely about the
**user-upload path**, which today validates nothing: `_save_airfoil_dat`
(`app/api/v2/endpoints/airfoils.py:437-458`) writes the bytes without parsing them.

**Required:**
- **Detect the format at upload.** A Lednicer file opens with a point-count line
  (first numeric pair with both values > 1), then upper LE→TE followed by lower
  LE→TE. The Selig parser reads that count line as a coordinate and splits the
  contour at the x-minimum, producing an airfoil that **exists, looks plausible and
  is wrong** — every polar computed from it is silently garbage.
- **Convert Lednicer → Selig** (reverse the upper surface and concatenate) rather
  than rejecting: the UIUC database, the usual source, serves airfoils in **both**
  formats, so the confusion is routine rather than exotic.
- **Parse at upload, not at first read**, and reject an unparseable file with a
  clear message instead of letting it enter the library and fail later.

---

## Q-AF-2 — Is there a staleness marker for the low-Re backfill?

**Context:** Both the gh-834 reflex fix and the gh-825 windowed-confidence change
require a `--force` re-backfill, tracked only in code comments. Stored `family`
and `min_analysis_confidence` values from before either change are silently
wrong, and nothing can detect them. The provenance columns
(`neuralfoil_model_size`, `n_crit`) let the backfill skip *up-to-date* rows but do
not record the *semantics* version.
**Spec affected:** [`_reversa_sdd/airfoil-catalog/low-re-polar-backfill/requirements.md`]
**Question:** Should a semantics/version marker be added so stale rows are
detectable automatically?
**Impact:** Every scoring result rides on these two columns.

**Answer:** _(derived — not a maintainer decision)_ **Yes — add an explicit semantics-version marker beside the existing provenance columns, so rows produced under superseded semantics are detectable and their use is declared.**

Follows from **Q-CC-10** and **P-WARN-0**: Q-CC-10 settled this exact failure mode for the computation context — a `context_version` for shape/semantics drift plus a freshness marker, because a stale artefact is otherwise "indistinguishable from a fresh one" — and P-WARN-0 forbids serving silently-wrong stored values. `neuralfoil_model_size` and `n_crit` record *how* a row was computed but not *under which semantics* (gh-834 reflex fix, gh-825 windowed confidence), so a pre-change row must be detectable and must raise a `DesignWarning` when read.

---

## Q-AF-3 — What are the confidence *tier* boundaries used for ranking?

**Context:** BR-C25 says ranking sorts by `(confidence tier, −score)` so a
high-scoring low-confidence airfoil never outranks a trustworthy one.
`low_re_low_confidence_flag = 0.85` is the documented UI badge threshold — but
whether the ranking tier uses that same value, and how many tiers exist, is
unconfirmed.
**Spec affected:** [`_reversa_sdd/airfoil-catalog/suitability-search/requirements.md`]
**Question:** How many tiers, and at what boundaries?
**Impact:** **A re-implementation cannot reproduce the ranking order without
this.** It is the single most load-bearing unknown in the module.

**Answer:** _(derived — not a maintainer decision)_ **Two tiers, boundary `min_analysis_confidence >= 0.85` (inclusive), taken from the single setting `low_re_low_confidence_flag` — literally the same constant as the UI badge threshold.**

Follows from **the wave-2 code lookup** ([`wave2-lookups.md`](wave2-lookups.md) §A, a factual answer rather than a maintainer decision): `_conf_tier` (`app/services/suitability_service.py:623-625`) returns `0` or `1` only and is the primary sort key in all three ranking lenses (`:627-635`), so BR-C25 can be stated as two lens-independent tiers. A missing confidence is coerced to `0.0` upstream (`:534-536`) and lands deterministically in tier 1. Do not confuse it with `low_re_confidence_gate = 0.90`, which gates metric acceptance during the backfill and never reaches the sort.

---

## Q-AF-4 — Is `/airfoils/db/suitability` declared before `/airfoils/db/{name}`?

**Context:** If not, the literal `"suitability"` is captured as an airfoil name
and the suitability route is unreachable. The two routes were specified in
different slices, so nothing currently pins the ordering.
**Spec affected:** [`_reversa_sdd/airfoil-catalog/suitability-search/contracts.md`]
**Question:** Confirm the declaration order, and should a test pin it?
**Impact:** Same class of bug as gh-914 (`/aeroplanes/compare` vs
`/aeroplanes/{id}`), which the router order in `main.py` already guards against
elsewhere.

**Answer:** _(resolved by code lookup — not a maintainer decision)_ **Yes — `/airfoils/db/suitability` is declared at `app/api/v2/endpoints/airfoils.py:492`, well before `/airfoils/db/{name}` at `:698`, so FastAPI matches the literal first and the route is not shadowed.**

The full declaration order of all 12 routes in the module was checked and shows no other literal/parameterised collision (`492 db/suitability`, `682 db`, `698 db/{name}`, `715 import`, `746 {airfoil_name}/known`, `779 datfile`, …). The ordering is already pinned *behaviourally*, though not by an explicit assertion: `app/tests/test_airfoils_suitability_endpoint.py:114,119` assert a **422** for a missing required query parameter, which would instead be a **404** from `get_airfoil_db(name="suitability")` if the parameterised route won.

**Verdict:** confirmed safe
Residual decision: whether to add an explicit route-order assertion on top of that incidental behavioural coverage.

_Full detail: [`wave3-lookups.md`](wave3-lookups.md) §C_


**Residual decision — ANSWERED by the maintainer, 2026-08-14: (c) unify the two
route families and drop the `db/` segment — plus a new ADR forbidding this class of
leak in general.**

The route-order assertion was rejected as treating the symptom. The real defect is
that **the storage mechanism appears in the URL**: `/airfoils/db/…` (database-backed)
sits beside `/airfoils/…` (filesystem-backed `.dat` files), so a client has to know
which store an airfoil lives in. The `suitability` ↔ `{name}` collision is a
consequence: `/airfoils/db/suitability` and `/airfoils/db/{name}` are the same shape
to FastAPI and work **only** because `suitability` happens to be declared first
(route 1 of 12; `{name}` is route 3). Re-ordering them would make the app look up an
airfoil named `"suitability"` and return 404 — a change that reads as harmless in a
diff.

To be clear on the original sub-question: `suitability` is a `GET` using **query
parameters only, no body** — nothing is passed in a body that belongs in the path.
The problem is purely path shape. (Its 13 query parameters are at the upper edge of
comfortable for a GET, but idempotent and cacheable, so acceptable.)

**Origin — established from git history during the interview:**

| Date | Commit | Event |
|---|---|---|
| 2026-02-16 | `5dfe0037` | Filesystem airfoil registry (upload, download, NeuralFoil) — the original API |
| 2026-04-25 | `06a25ff4` (gh-335) | "store airfoils in DB, import from .dat files" — the DB store was added **alongside**, creating the parallel `/airfoils/db/*` family instead of migrating the existing routes |
| 2026-06-04 | `a9fa31ee` (gh-821) | The suitability search was filed under `db/` |

`db` is literally the marker for "the new store" — an additive migration that was
never completed.

**Required:** merge the two families into one coherent airfoil resource model with no
storage marker in the path, which removes the collision by construction (no ordering
test needed). **Timing is deliberate:** `Q-CC-11` introduces a *generated* TypeScript
client and `Q-CC-6` has just unified the route prefix — the shape must be right
before generation bakes it in.

**Generalisation:** see the new **ADR 0019 — Implementation details must not leak
into the public API**, created at the maintainer's request so this class of defect is
prevented rather than repeatedly discovered.

---

## Q-AF-5 — Polar and scoring edge cases that were not read (bundle)

**Context:** Six behaviours the analysis could not confirm from the source:
- **The null-metric policy.** Every polar metric column is nullable, implying a
  row is written even when no α point clears the 0.90 confidence gate — but the
  code path was not read. Is a null-metric row written, or is the airfoil skipped
  entirely at that Re?
- **An airfoil with no polar rows** — omitted from `results`, or returned with
  `null` scores?
- **Null propagation through Lens 2.** It multiplies Lens 1, so a `None` should
  propagate — confirm before relying on it.
- **`_level_flight_cl`'s call sites** were not read, so which `target_cl_*` values
  are derived from it versus supplied by the caller is unclear.
- **Duplicate-upload behaviour.** Does `POST /airfoils/datfile` with an existing
  stem replace, conflict with 409, or skip the way the directory import's
  case-insensitive dedup does?
- **The ASB-absent response shape for `/neuralfoil/analysis`.** The service
  returns `[]`; does the endpoint surface a 200 with an empty body, or a 5xx?
  (Only the former is consistent with ADR 0017.) Same question for
  `/geometry-stats` on an imported-but-unclassified airfoil: 404 or a null-filled
  body?

**Spec affected:** [`_reversa_sdd/airfoil-catalog/low-re-polar-backfill/requirements.md`],
[`_reversa_sdd/airfoil-catalog/suitability-search/contracts.md`],
[`_reversa_sdd/airfoil-catalog/neuralfoil-analysis/contracts.md`]
**Question:** Confirm each.
**Impact:** Six contract rows.

**Answer:** _(resolved by code lookup — not a maintainer decision)_ **All six read out of the source: (1) a row **is** written with every metric `NULL`; (2) an airfoil with no polar rows is returned with a fabricated `0.0`, not `null`; (3) the Lens-2 `None` does **not** propagate; (4) `_level_flight_cl` has exactly three call sites, all in the `aeroplane_id` block and all overridable; (5) duplicate upload is **409**, or 200 with `?overwrite=true`; (6) there is no ASB-absent path at all.**

(1) When no α clears the confidence gate, `_extract_metrics` returns its all-`None` template (`app/services/airfoil_low_re_service.py:582-603`), `compute_airfoil_low_re` appends the row unconditionally (`:519`) and the persistence layer upserts it without inspection (`app/core/background_jobs.py:396-410`) — but `min_analysis_confidence` is still a real number on such a row (`:552-553`). (2) The scoring loop iterates **geometry** rows (`app/services/suitability_service.py:444-447`) and coerces the `None` score to `0.0` (`:467-469`), so a geometry-only airfoil is ranked last in confidence tier 1 — while the `include=` path explicitly refuses to fabricate the very same item (`:660-668`); an airfoil with a polar row but no geometry row is omitted entirely. (3) `score_mission` is *written* to propagate `None` (`airfoil_low_re_service.py:894-906`), but its only production caller has already replaced it with `0.0` two lines earlier, so a no-polar airfoil gets `mission = 0.0` that reads like a scored result. (4) Cruise / best glide / min sink at `suitability_service.py:336-338`, `:346-348`, `:356-358`, all fed from `aeroplane.assumption_computation_context` and all overridden entirely by the explicit `target_cl_*` query parameters (`airfoils.py:523-546`). (5) `airfoils.py:437-458` raises `ConflictError` → 409, and `?overwrite=true` replaces the file and downgrades the declared 201 to **200** (`:800-802`); the collision test is `Path.exists()` (case-sensitive on Linux, not on macOS) and the upload writes only the `.dat`, no `airfoils` DB row. (6) `import aerosandbox as asb` at `airfoils.py:7` is unguarded and module-level, so on a platform without AeroSandbox the whole router fails to import and app startup fails — all 12 routes disappear; the `[]` the question refers to belongs to a different function, `compute_airfoil_low_re` (`airfoil_low_re_service.py:458-462`). And `/geometry-stats` on an imported-but-unclassified airfoil is a **404**, not a null-filled body, because it reads the filesystem via `_resolve_airfoil_file` (`airfoils.py:213-224`, `:882-884`).

**Verdict:** confirmed defect on (2), (3) and (6) — the last breaks ADR 0012's graceful degradation for the entire airfoil router; confirmed safe / as-specified on (1), (4) and (5).
Residual decision: for (2), whether the main sweep should adopt the `include` path's explicit "not fabricated" rule (omit the airfoil, or return `null` scores) instead of ranking a fabricated `0.0`.

_Full detail: [`wave3-lookups.md`](wave3-lookups.md) §D_


**Residual decision — ANSWERED by the maintainer, 2026-08-14: (a) `null`, not a
fabricated `0.0`, and grouped separately.**

Confirmed defect D.2: an airfoil with **no polar rows** is currently returned with a
**fabricated `0.0`** score. That is semantically the opposite of the truth — `0.0`
reads as "evaluated, and poor" (ranked last but legitimately), when the fact is
"could not be evaluated, data missing". The two call for opposite user actions:
discard the airfoil, versus run the low-Re backfill.

**Required:**
- Return `null` scores for airfoils without polar data, and place them in a
  **separate "not evaluated" group** rather than interleaving them in the ranking.
- Emit a `DesignWarning` naming **how many** candidates were skipped for missing
  polars — actionable information (run the backfill), not just an error.
- This adopts the rule the `include` path already applies explicitly ("not
  fabricated"); the main sweep was the outlier.

Rejected: omitting the airfoils entirely — the user would not learn which
candidates are missing from consideration.

---

## Q-AF-6 — Where does the batch backfill run from, and is it chunked?

**Context:** The sweep entry point has no HTTP route and `--force` is referenced
only in code comments. The grid is 1 665 airfoils × 13 Re × 116 α points.
`schedule_airfoil_low_re_compute` is untracked fire-and-forget and imports
`scripts.backfill_airfoil_low_re._compute_geometry_stats` from application code.
**Spec affected:** [`_reversa_sdd/airfoil-catalog/low-re-polar-backfill/design.md`],
[`_reversa_sdd/platform-core/background-jobs-invalidation/requirements.md`]
**Question:** Where is it run from, is it chunked or cancellable, and should the
backfill logic move out of `scripts/` into a service?
**Impact:** The module's most expensive operation has no documented operator
surface.

**Answer:** **ANSWERED by the maintainer, 2026-08-15** (option a; decided together with `Q-PC-5`) — **the backfill logic moves into a service, the `scripts/` entry point becomes a thin CLI wrapper, and the run is a tracked `Job`.**

**The dependency currently points the wrong way.** `background_jobs.py:362` imports
`scripts.backfill_airfoil_low_re._compute_geometry_stats` **from application code**, so the
application depends on a script — and on a private function of one. Inverting it is the
substance of the change: the service owns the computation, and `scripts/` becomes one of
its callers alongside the scheduler.

**Chunking and cancellation are *not* the priority the question assumed.** Measured, the
sweep takes roughly **2.4 minutes for ~1 622 airfoils**, not hours. The grid looks alarming
(1 665 × 13 Re × 116 α) but NeuralFoil evaluates it quickly. So a cancel button solves a
problem that lasts two minutes.

**What does matter is that it is the only untracked job family of three.**
`schedule_airfoil_low_re_compute` is fire-and-forget in a worker thread with **no `Job`
record**, so an operator cannot tell whether it is running, finished or died — and a
failure is invisible. Becoming a tracked `Job` gives it the same surface as its siblings
and closes that gap, which is the same *"a partially-completed operation must say so"*
reasoning as `P-WARN-0`.

**Operator surface:** the CLI remains the entry point; no HTTP route is added, because
this is a maintenance operation for a single-user desktop install (**ADR 0024**), not a
capability the API should expose. The `--force` flag becomes documented rather than
mentioned only in code comments.

_See also the note at `Q-PC-5`, which is the same decision viewed from `platform-core`._

---

## Q-AF-7 — Is renaming an airfoil forbidden by convention?

**Context:** `airfoil_geometry.airfoil_name` and
`airfoil_low_re_polar.airfoil_name` reference `airfoils.name` with only
`ON DELETE CASCADE` — no `ON UPDATE CASCADE`. Renaming would break the relation.
Relatedly, there is **no ORM relationship** from `AirfoilModel` to its children;
joins are done by name in the services, inferred as deliberate (it avoids loading
1 665 × 13 rows) but nowhere documented.
**Spec affected:** [`_reversa_sdd/airfoil-catalog/requirements.md`] (BR-C28, BR-C29)
**Question:** Confirm both — renaming forbidden, and the missing relationship
deliberate?
**Impact:** Two 🟡/🔴s become 🟢.

**Answer:** **ANSWERED by the maintainer, 2026-08-15** (option a) — **both confirmed: renaming an airfoil is forbidden, and the absent ORM relationship is deliberate. Both become documented contract rather than incidental behaviour.**

**① Renaming is forbidden.** `airfoil_geometry.airfoil_name` and `airfoil_low_re_polar.airfoil_name` reference `airfoils.name` with `ON DELETE CASCADE` and **no `ON UPDATE CASCADE`**, so a rename orphans the geometry and every low-Re polar row silently — the airfoil still resolves, its data does not. Adding `ON UPDATE CASCADE` was rejected: it would make renaming *work*, but the name is how an airfoil is referenced from wing cross-sections, imported `.dat` files, construction plans and the copilot's prompt tables, and a rename would have to propagate to all of them. The name is the airfoil's identity, not a label.

**Enforcement:** no rename route exists and none is added; the constraint is stated in the spec so a future editor does not read the missing route as an oversight.

**② The missing `relationship()` is deliberate — and gains a guard.** Joining by name in the services avoids ever lazily materialising 1 665 airfoils × 13 Reynolds numbers of polar rows behind an innocuous attribute access. The reason is now written down (`BR-C29`), because an undocumented *absence* is indistinguishable from a forgotten one — the next contributor's instinct is to "fix" it.

Where a relationship is genuinely wanted for readability, it is declared with **`lazy="raise"`**, so an accidental traversal fails loudly at development time instead of quietly loading twenty thousand rows in production. That was option (c) in isolation; here it is the shape any future relationship must take rather than a change made now.

**Both move from 🟡 to 🟢.**

---

## Q-AF-8 — Should `high_re` carry a degraded-confidence signal?

**Context:** The Re grid tops out at 750 k, so the `high_re` tag (fires at
`Re ≥ 500 k`) is knowingly approximate — the contract says so — but it is exposed
as a plain boolean with no signal of its own.
**Spec affected:** [`_reversa_sdd/airfoil-catalog/suitability-search/requirements.md`] (BR-C27)
**Question:** Should the tag carry its own caveat, the way `tip_re_flag` does?
**Impact:** Minor, but it is the one place the module asserts more than the data
supports.

**Answer:** _(derived — not a maintainer decision)_ **Yes — `high_re` must declare that it is extrapolated beyond the 750 k grid, and it declares it through the one `DesignWarning` channel rather than a second bespoke caveat field.**

Follows from **P-WARN-0**: the policy forbids *undeclared* approximation and mandates one shared channel, explicitly because each subsystem inventing its own warning shape is the defect being fixed. A boolean that fires at `Re ≥ 500 k` on a grid that stops at 750 k asserts more than the data supports, so it carries `notice` · `substituted_assumption` with the Re regime in `context` — and `tip_re_flag`'s existing ad-hoc caveat moves onto the same channel rather than being copied.

---

## Q-AF-9 — Should the interactive analysis response echo its model size?

**Context:** BR-C12 deliberately keeps two model sizes: the backfill uses
`"xxxlarge"`, the interactive endpoint `"large"`, with a docstring saying
**"do NOT collapse"**. But a `"large"` sweep and an `"xxxlarge"` stored polar can
disagree, and nothing in the response explains why.
**Spec affected:** [`_reversa_sdd/airfoil-catalog/neuralfoil-analysis/contracts.md`]
**Question:** Should the response echo the model size?
**Impact:** A user comparing the two surfaces currently has no explanation for a
discrepancy.

**Answer:** _(derived — not a maintainer decision)_ **Yes — the response must state which NeuralFoil model produced it.**

Follows from **P-WARN-0**: keeping `"large"` for interactive latency while the stored polar is `"xxxlarge"` is a legitimate, deliberate substitution — and the rule is "no *undeclared* fallbacks". Echoing the model size (the same provenance the backfill already persists as `neuralfoil_model_size`) is what makes an otherwise unexplained discrepancy explicable to a user comparing the two surfaces; BR-C12's "do NOT collapse" is untouched.

---

# cad-generation

## Q-CG-1 — 3MF export is broken and a test pins the bug: fix the mapping, or drop the format?

**Context:** Verified during review. `map_exporter_type`
(`cad_service.py:196`) returns `"ExportTo3MFCreator"`; the real class is
`ExportTo3mfCreator` (`.../ExportTo3mfCreator.py:10`). The `$TYPE` decoder uses
`getattr`, so every 3MF export raises `AttributeError` in the worker and the task
ends `FAILURE`. `app/tests/test_cad_service_extended.py:130` asserts the **wrong**
string, so the suite is green and stays green through a partial fix.
`construction_plan_service.py:559` already uses the correct spelling.

Same rule: `ExporterUrlType.AMF = "amf"` exists with **no** mapping entry, so
every AMF request 422s.
**Spec affected:** [`_reversa_sdd/cad-generation/requirements.md`] (BR-CG5, RF-07),
[`_reversa_sdd/construction-plans/plan-execution/tasks.md`] (T-PE-13)
**Question:** Fix the mapping **and** the test, or remove 3MF and AMF from the
enum? The enum is the public contract, so either is a client-visible change.
**Impact:** Two of five advertised export formats do not work.

**Answer:** **(a) Fix 3MF properly; remove AMF.** _Answered by the maintainer,
2026-08-13._

**3MF — two independent defects, both must be fixed** (verified during the
interview; the casing fix alone is NOT sufficient):
1. `map_exporter_type` (`cad_service.py:196`) returns `"ExportTo3MFCreator"`; the
   real class is `ExportTo3mfCreator`. The `$TYPE` decoder uses `getattr`, so every
   3MF export raises `AttributeError` in the worker and the task ends `FAILURE`.
2. `ExportTo3mfCreator.__init__` declares `shapes_to_export: list[ShapeId]` with
   **no default**, unlike every sibling (`ExportToStlCreator` has
   `= None`), and `build_wing_blueprint` never sets the key. Since the decoder omits
   absent keys, fixing only the casing would trade the `AttributeError` for a
   `TypeError: missing 1 required positional argument`. The class body itself
   already handles `shapes_to_export is not None`, so the missing default is clearly
   an oversight.
3. **Correct the test.** `test_cad_service_extended.py:130` asserts the wrong
   string, keeping the suite green through a partial fix. This is not a weakening of
   a test under the project's "fix the code, not the tests" rule — the test encodes
   a defect.

**Why 3MF is worth keeping:** it is the most valuable export format for this
maintainer's 3D-printing workflow — it carries **units**, colours and metadata,
unlike STL, which is unitless (the same ambiguity dealt with in `Q-FD-2`).

**AMF — remove.** `ExporterUrlType.AMF = "amf"` exists with no mapping entry, so
every request 422s; it was never implemented, and the format has been superseded by
3MF across the ecosystem. Deleted per `P-DEAD-0` ("anything else → delete").

**Note:** the enum is the public contract, so removing AMF is a client-visible
change — acceptable per `Q-CC-1` (no external consumers).

---

## Q-CG-2 — Should exports be written into a per-task directory?

**Context:** The worker zips *everything* in the shared `./tmp/exports` into
`./tmp/{aeroplane_id}.zip` and then `os.unlink`s *every* file in it
(`cad_service.py:368-377`). `check_task_available` serialises only per aeroplane
while the pool runs four workers, so two concurrent exports for **different**
aircraft capture each other's files and delete them. Construction plans already
solved this with per-execution directories under `ARTIFACTS_BASE_DIR`.
**Spec affected:** [`_reversa_sdd/cad-generation/requirements.md`] (BR-CG6),
[`_reversa_sdd/cad-generation/wing-export-task/design.md`]
**Question:** Adopt the per-execution directory model for exports too?
**Impact:** Data loss under concurrency, today.

**Answer:** _(derived — not a maintainer decision)_ **Yes — exports move to a per-execution directory, the model construction plans already use.**

Follows from **Q-CC-8**, which carves this out by name: "this does NOT resolve `Q-CG-2`. The CAD export race is between the four workers *inside* the pool of a single process, all writing to the same `./tmp/exports` directory. It remains a real defect and must be fixed independently (per-task directory), regardless of this answer." Single-worker deployment removes the multi-process framing but not this data loss, so the per-execution directory pattern under `ARTIFACTS_BASE_DIR` is adopted for exports too.

---

## Q-CG-3 — Is the viewer relying on per-part bounds, or is camera-fit silently wrong?

**Context:** Verified during review. The worker writes
`shapes["bb"] = combined_bb(shapes).to_dict()`, which `ocp_tessellate` returns as
`{xmin, xmax, ymin, ymax, zmin, zmax}`; `_expand_bounding_box`
(`cad.py:91-95`) returns early unless the dict carries `"min"` **and** `"max"`.
So `GET /aeroplanes/{id}/tessellation` always answers
`bb = {"min":[0,0,0],"max":[0,0,0]}`.
**Spec affected:** [`_reversa_sdd/cad-generation/requirements.md`] (BR-CG16, RF-18),
[`_reversa_sdd/frontend-workbench/cad-viewer-integration/requirements.md`]
**Question:** Is the viewer computing its own bounds from the parts, or is
camera-fit wrong for multi-wing scenes? Which key set should win?
**Impact:** Determines whether this is a cosmetic camera issue or a visible bug.

**Answer:** **(b) Remove `bb` from the response and delete `_expand_bounding_box`.**
_Answered by the maintainer, 2026-08-13._

**First, the reassurance: this is cosmetic, not a visible bug.** Verified in the
frontend — `CadViewer.tsx:60` adds every part with `{ skipBounds: true }` and then
`CadViewer.tsx:140-142` calls `viewer.updateBounds()` ("Recompute bounds once after
all parts are added"). The viewer computes its own bounds from the geometry, so
camera-fit is correct, including for multi-wing scenes.

**But the contract defect is real.** `GET /aeroplanes/{id}/tessellation` always
answers `bb = {"min":[0,0,0],"max":[0,0,0]}`: the worker writes
`combined_bb(...)` in `{xmin, xmax, ymin, …}` form, while `_expand_bounding_box`
(`cad.py:91-95`) returns early unless the dict carries `"min"` and `"max"` — which
it never does. The function therefore **never does anything**.

**Decision:** `bb` is removed from the response and `_expand_bounding_box` is
deleted, following the delete-by-default rule of `P-DEAD-0`. The viewer
demonstrably does not need it, and shipping a field that is always zero is worse
than shipping no field.

**Considered and rejected:** (a) fixing the key mapping so `bb` is correct — cheap,
and a valid bounding box would be useful to non-viewer consumers (e.g. an MCP agent
asking how large an aircraft is without downloading all geometry). Rejected in
favour of the policy default; it can be reintroduced deliberately if such a
consumer actually appears.

---

## Q-CG-4 — Is GH #202 still the plan for background re-tessellation?

**Context:** `trigger_background_tessellation` is fully implemented — 2 s
debounce, timer and future cancellation, stale-hash discard — and **nothing calls
it**. `tessellation_hooks.on_wing_changed` ends in a TODO referencing GH #202, so
a stale cache entry stays stale until someone POSTs the endpoint again.
**Spec affected:** [`_reversa_sdd/cad-generation/wing-tessellation/requirements.md`] (BR-CG12, RF-15)
**Question:** Is #202 still the plan, and what supplies the wing schema pickle at
hook time?
**Impact:** RF-15 is currently specified as "implemented but unreachable".

**Answer:** _(resolved by code lookup — not a maintainer decision)_ **Both blockers named in the TODO are already solved in the same repo — the pickle is four lines that already exist and the session factory is already used in the same module — so the wiring is roughly six lines plus one decision; the only genuinely open item is `geometry_hash`.**

`trigger_background_tessellation` (`app/services/tessellation_service.py:240-247`) needs `aeroplane_id` and `wing_name` (both are the hook's own parameters, `app/services/tessellation_hooks.py:19-20`), a `wing_schema_pickle` — a pure function of `(db, aeroplane_id, wing_name)` already written at `app/api/v2/endpoints/cad.py:161-170` — and a `db_session_factory`, for which `tessellation_service` already imports and uses `SessionLocal` in its own done-callback (`:204-215`). The open item is `geometry_hash`: `compute_geometry_hash` exists (`app/services/tessellation_cache_service.py:21-28`) but has **zero** callers and takes a `dict`, while what is available at hook time is an ASB wing schema object — so somebody has to define the canonical dict form. Consequence today: every cached wing entry is stored with the literal hash `"manual"` (`tessellation_service.py:220`), so the background path's stale-hash discard has nothing meaningful to compare against. One subtlety not in the TODO: the hook runs *inside* the request transaction (ten call sites in `app/api/v2/endpoints/aeroplane/wings.py`) while a worker would read through a new session, so pickling at hook time — as the TODO proposes — is the ordering-safe choice rather than passing ids.

**Verdict:** confirmed safe — the wiring is small, not hard; the TODO's stated reasons no longer hold.
Residual decision: whether #202 is wanted at all remains your `P-DEAD-0` wire-or-delete call, and if it is wired, the canonical dict form feeding `compute_geometry_hash` has to be defined.

_Full detail: [`wave3-lookups.md`](wave3-lookups.md) §M_


**Residual decision — ANSWERED by the maintainer, 2026-08-14: DELETE — and the
whole wing-tessellation subsystem with it, not just GH #202.**

The question's premise collapsed under investigation. **The single-wing 3D preview
path is legacy in its entirety**, superseded by (a) the Plotly outline preview
(`WingOutlineViewer`) in the wing editor and (b) the shapes delivered during
construction-plan execution. The maintainer confirms the replacement is deliberate:
the only remaining use case would be displaying an STL, for which simpler solutions
exist.

**Evidence gathered during the interview:**

| Component | Lines | Consumers |
|---|---|---|
| `frontend/hooks/useTessellation.ts` | 205 | **none** |
| `frontend/hooks/usePreviewState.ts` | 207 | **none** |
| `frontend/components/workbench/ViewerPanel.tsx` | — | **none** (`<ViewerPanel` is rendered nowhere) |

`<CadViewer` is rendered in exactly two places: `ViewerPanel.tsx` (itself unused) and
`construction-plans/ExecutionResultDialog.tsx`, which takes its parts from the plan
execution — `const parts = isStreaming ? streamedParts : nonStreamParts;`
(`ExecutionResultDialog.tsx:123`) — **not** from the tessellation endpoints. Note
also the recurring duplication pattern: two near-identical hooks (205 and 207 lines)
for the same job, neither reachable.

**To be removed:**
- **Frontend:** `useTessellation.ts`, `usePreviewState.ts`, `ViewerPanel.tsx`.
- **Backend:** `tessellation_service.py`, `tessellation_hooks.py`,
  `tessellation_cache_service.py`, the `tessellation_cache` table and its migration,
  `POST /aeroplanes/{id}/wings/{name}/tessellation`,
  `GET /aeroplanes/{id}/tessellation`, and the ~10 `on_wing_changed` call sites in
  `app/api/v2/endpoints/aeroplane/wings.py`.

**Explicitly NOT removed** — these are separate and stay live:
- `construction_plan_service._tessellate_shapes` and the `ocp_tessellate` usage that
  feeds `ExecutionResultDialog` (the live path).
- The CAD **export** task (`cad_service`) and its zip download — a different
  subsystem. In particular `Q-CG-2` (the shared `./tmp/exports` race) remains a real
  defect to fix.

**Questions rendered moot by this deletion:** `Q-CG-5` (fuselage tessellation +
cache unique constraint), `Q-FW-5` (bounding the tessellation cache), the `"manual"`
geometry-hash placeholder, the tessellation cache race and its missing timeout, and
the already-decided `Q-CG-3` (`bb` removal) — which concerned this same dead
endpoint.

---

## Q-CG-5 — Are fuselage tessellation and the cache unique constraint planned?

**Context:** Two related gaps: `tessellation_cache.component_type` models
`"fuselage"` and the scene assembler colours it `#888888`, but **no producer
exists** and `start_wing_export_task` passes `fuselages=None` with the comment
"not yet routed through the REST path". Separately, the cache key
`(aeroplane_id, component_type, component_name)` is treated as unique by
`get_cached(...).first()` but the DDL creates only the FK and two indexes — **no
unique constraint** — so two concurrent inserts can produce duplicate rows.
**Spec affected:** [`_reversa_sdd/cad-generation/wing-tessellation/requirements.md`] (BR-CG13, BR-CG14, RF-24)
**Question:** Is fuselage tessellation planned, or should the modelled component
type be removed? And should the unique constraint be added, or is duplication
tolerated?
**Impact:** RF-24 is currently `Won't (today)` with a modelled-but-unreachable type.

**Answer:** _derived — not a maintainer decision (follows from `Q-CG-4` + ADR 0021)._

**Both halves are moot: the subsystem they belong to is deleted.** `Q-CG-4` retires the
whole wing-tessellation path — the `tessellation_cache` table, both endpoints and the
three backend services. There is therefore no cache to add a unique constraint to, and
no producer to write for the modelled `"fuselage"` component type; the modelled-but-
unreachable type disappears with the table.

**RF-24 is withdrawn rather than answered.** The live 3D path is construction-plan
execution, which tessellates through `construction_plan_service._tessellate_shapes` and
does not use this cache. If fuselage geometry is ever shown in the viewer it arrives the
same way — as an executed plan artefact — so it needs no cache row and no component-type
enum.

_Guard for the re-implementation:_ should any future cache reintroduce a
`(aeroplane_id, component_type, component_name)` key that a `.first()` treats as unique,
the unique constraint is part of the DDL from the start. Relying on `.first()` to
paper over duplicate rows is exactly the undeclared substitution ADR 0020 forbids.

---

## Q-CG-6 — Is `_template_runs` appearing in plan listings a bug?

**Context:** `_resolve_execution_dir` deliberately skips the `_template_runs`
prefix when scanning per-aeroplane directories (`artifact_service.py:282-283`),
but `list_executions` does not (l.123-142) — so a template run can surface in a
plan listing with `aeroplane_id == "_template_runs"`.
**Spec affected:** [`_reversa_sdd/cad-generation/artifact-serving/requirements.md`] (BR-CG20)
**Question:** Bug or intentional?
**Impact:** One acceptance criterion.

**Answer:** _derived — not a maintainer decision (an internal inconsistency, i.e. a bug)._

**It is a bug.** `_resolve_execution_dir` deliberately skips the `_template_runs` prefix
when scanning per-aeroplane directories (`artifact_service.py:282-283`); `list_executions`
scans the same tree and does not (l.123-142). One code path treats the prefix as a
reserved namespace and the other treats it as an aeroplane id — they cannot both be right,
and the one carrying the explicit skip is the one that states an intent.

The symptom is a listing row with `aeroplane_id == "_template_runs"`, i.e. a synthetic
directory name surfacing as a domain identifier. That is also an **ADR 0019** instance in
miniature: a storage-layout detail (how template runs are laid out on disk) leaking into
a value a client reads.

**Fix:** `list_executions` applies the same reserved-prefix skip, and the prefix is
defined once as a module constant rather than spelled twice. The acceptance criterion
becomes "a template run never appears in a plan listing".

---

# cad-designer-topology

> ⚠ This module is **frozen** (ADR 0002). These questions are about what a
> *re-implementation* should do, and about whether any carve-out is warranted —
> not about editing the current files.

## Q-CT-1 — What should happen to the three undecodable plan JSONs?

**Context:** Nine removed Creator classes (`FullWingLoftShapeCreator`,
`FullFuselageLoftShapeCreator`, `WingRibCageCreator`, `ReinforcementPipesCreator`,
`WingOffsetCreator`, `MirrorShapeCreator`, `EngineMountPanelShapeCreator`, and
the three `CPACS*` creators) — 9 of 32 `$TYPE` names — are still referenced by
`wings.root.json`, `fuselage.root.json` and `full_wing.json` under
`components/constructions/`. `GeneralJSONDecoder` resolves `$TYPE` with `getattr`,
so all three raise `AttributeError`. Latent, not live: nothing under `app/` reads
that directory. The other five plan JSONs resolve cleanly. They were authored by
the third test root `test/`.
**Spec affected:** [`_reversa_sdd/cad-designer-topology/requirements.md`] (BR-CT28)
**Question:** Historical artefacts to delete, or plans that should be migrated?
And who owns them, given `app/` never reads the directory?
**Impact:** Ownership is currently unresolved between two modules.

**Answer:** _(derived — not a maintainer decision)_ **Delete the three undecodable plan JSONs (`wings.root.json`, `fuselage.root.json`, `full_wing.json`) and record them in the spec as removed.**

Follows from **P-DEAD-0**: nine of their `$TYPE` names refer to Creator classes that no longer exist, so they cannot be decoded — let alone migrated — and no live ticket claims them, which puts them squarely in rule 3 ("anything else → delete"). Ownership resolves with them, since nothing under `app/` reads `components/constructions/`. Retaining them as a historical reference is only available under rule 2, i.e. with a live ticket plus an explicit marker — not as the current inert state.

---

## Q-CT-2 — Does the frozen layer's `gp_D*` singleton mutation warrant a carve-out?

**Context:** `ComponentInformation.get_z_axis` does `z = gp_DZ`, which **aliases
the module global**, and `gp_Dir.Rotate` mutates in place — so `gp_DX` / `gp_DY` /
`gp_DZ` are permanently rotated after the first call. `get_middle_point` also
builds `gp_Vec(trans_x + length/2, trans_y − width/2, trans_z − length/2)`, where
the z term uses `length/2` and `height/2` reads as intended. Rotation units are
never stated while `gp_Ax1` rotation takes **radians** and `rot_*` are unlabelled
floats.
**Spec affected:** [`_reversa_sdd/cad-designer-topology/requirements.md`] (BR-CT29)
**Question:** Document-only per ADR 0002, or is a carve-out warranted — these
classes feed the servo and engine creators, so the corruption is reachable from a
real build?
**Impact:** ADR 0002's boundary; this is the strongest candidate for an exception
after the `Turbulator` precedent.

**Answer:** **Carve-out granted — but narrowly: fix the aliasing only. The other two
findings are documented, not changed.** _Answered by the maintainer, 2026-08-15._

**The defect.** `ComponentInformation.get_z_axis` does `z = gp_DZ`, which **aliases the
module global** rather than copying it, and `gp_Dir.Rotate` mutates **in place**. After
the first call, `gp_DX` / `gp_DY` / `gp_DZ` are **permanently rotated for the whole
process**. These classes feed the servo and engine creators, so the corruption is
reachable from a real build — and it contaminates everything built afterwards: a servo
placed after a motor comes out skewed.

**The exception, precisely scoped:** `z = gp_Dir(gp_DZ)` instead of `z = gp_DZ` — copy
instead of alias. It is the minimal change that removes the corruption and alters **no**
behaviour except the faulty one. This follows the `Turbulator` precedent as the second
permitted exception to ADR 0002.

**Documented only, deliberately not changed:**
- `get_middle_point` uses `length/2` in the z term where `height/2` reads as intended.
- Rotation units are never stated, while `gp_Ax1` rotation takes **radians** and `rot_*`
  are unlabelled floats.

Both are recorded in the spec rather than corrected, because changing either would
**move existing geometry** — a silent change to already-built models. They are flagged
for a deliberate migration if ever addressed.

---

## Q-CT-3 — Is `AirplaneConfiguration._main_wing_index = 0` a dead path or a second ASB entry point?

**Context:** It is the same "first wing is the main wing" assumption that made
every coefficient ≈8× wrong for a tail-first import (gh-788). The app converter
was fixed to pick the largest-planform wing
(`model_schema_converters.py:761-817`); this copy was not. It is currently a dead
second ASB path — the app builds an `AirplaneConfiguration` purely as an export
payload (`aeroplane_service.py:288`) and uses `aeroplane_schema_to_asb_airplane`
for all aerodynamics — so any future caller would silently inherit the bug.
**Spec affected:** [`_reversa_sdd/cad-designer-topology/requirements.md`] (BR-CT30)
**Question:** Dead legacy path to delete, or a second entry point that needs the
same fix?
**Impact:** A latent 8× error waiting for its first caller.

**Answer:** _(derived — not a maintainer decision)_ **Dead legacy path: the second ASB entry point goes rather than being fixed a second time — a re-implementation carries exactly one "which wing is the main wing" rule.**

Follows from **P-DEAD-0** plus the single-authority rulings in **Q-AA-1**, **Q-WD-1** and **Q-MB-1**: leaving a latent 8× coefficient error waiting for its first caller is the false-protection case the policy forbids, and every comparable question in this catalogue was settled by keeping *one* producer — here `aeroplane_schema_to_asb_airplane`, already corrected to the largest-planform wing under gh-788 — rather than duplicating the fix into a second copy that must then be kept in step. Because the file sits inside the ADR 0002 freeze, the spec states the removal; editing the frozen file itself still depends on the carve-out asked for in `Q-CT-2`.

---

## Q-CT-4 — Is `euler_xyz` consumed anywhere the intrinsic/extrinsic convention matters?

**Context:** `CoordinateSystem` passes `'XYZ'` but the implementation lowercases
it before calling `Rotation.from_matrix(R).as_euler(order.lower(), …)`. In SciPy
upper-case means **intrinsic** and lower-case **extrinsic**, so the stored
`euler_xyz` is always the extrinsic decomposition regardless of the requested
order. `from_json_dict` also **recomputes** `euler_xyz` rather than reading the
serialised value, and `InvalidRotationOrderException` is declared and never
raised.
**Spec affected:** [`_reversa_sdd/cad-designer-topology/wingconfiguration-coordinate-system/requirements.md`] (BR-CT22)
**Question:** Is `euler_xyz` consumed anywhere the convention matters?
**Impact:** If it is display-only, this is cosmetic; if any geometry reads it, it
is a silent frame error.

**Answer:** _(resolved by code lookup — not a maintainer decision)_ **No — `euler_xyz` is display/serialisation-only and is not even read back on deserialisation, so the intrinsic/extrinsic convention is unobservable.**

It is computed once in the constructor (`cad_designer/airplane/aircraft_topology/wing/CoordinateSystem.py:52-53`), emitted in `__getstate__` (`:55-63`), and **discarded on the way back in**: `from_json_dict` rebuilds from the three direction vectors and the origin and lets the constructor recompute the angles (`:112-117`). A repo-wide grep across `app/`, `cad_designer/` and `frontend/` returns exactly three production lines — all inside `CoordinateSystem` itself — plus 17 lines in `cad_designer/tests/test_coordinate_system.py`; there is no consumer in `app/`, none in the frontend, none in any converter. Geometry consumes the direction vectors only, including the one place a `CoordinateSystem` is built from real CAD geometry (`cad_designer/airplane/aircraft_topology/wing/Airfoil.py:52`). The spec can state `euler_xyz` as a derived, informational field; the class is frozen topology per `cad_designer/CLAUDE.md` regardless.

**Verdict:** confirmed safe

_Full detail: [`wave3-lookups.md`](wave3-lookups.md) §F_

---

## Q-CT-5 — Dead topology code: templates for future work, or delete? (bundle)

**Context:** Four items, all confirmed dead:
- `AbstractConstructionStep.construct` (11 lines) has **no implementers**.
- `create_XYZ_ted_sketch` (`ted_sketch_creators.py:22`) is defined but absent
  from the dispatch dict (`{"middle","top","top_simple"}`).
- `cq_plugins/scaleXyz/__init__.py` registers `cq.Workplane.scaleXyz` but
  `cq_plugins/__init__.py` never imports it, so the plugin is **never
  installed** — and its implementation has a typo'd parameter `y_sacle`.
- The plugin directory is misspelled `offest3D` and ships a stale
  `.ipynb_checkpoints/` copy.

Related: `round_inside` and `round_outside` hinge types are persisted and
selectable but have **no `ted_sketch_creators` entry**, so a wing using one
cannot build.
**Spec affected:** [`_reversa_sdd/cad-designer-topology/requirements.md`] (BR-CT31),
[`_reversa_sdd/architecture.md`] TD-24
**Question:** Templates for future work, or dead code? And should the hinge-type
literal be narrowed to the three that build?
**Impact:** The hinge-type one is user-facing — a selectable value that cannot
build.

**Answer:** **ANSWERED by the maintainer, 2026-08-15** — **the hinge-type literal keeps all five values; `round_inside` / `round_outside` are *declared but not yet implemented*, and the implementation will follow. This is not damage to a beta-test user.**

**The important correction is the category.** This question bundled the two round hinge types with four items of genuinely dead code, and they are not the same kind of thing:

| | category | disposition |
|---|---|---|
| `AbstractConstructionStep.construct` (no implementers) | complete but unreachable | **ADR 0021** — deleted by default |
| `create_XYZ_ted_sketch` (defined, absent from dispatch) | complete but unreachable | ADR 0021 |
| `cq_plugins/scaleXyz` (never imported; typo'd `y_sacle`) | complete but unreachable | ADR 0021 |
| `offest3D/` misspelling + committed `.ipynb_checkpoints/` | cosmetic debt | tidy when touched |
| **`round_inside` / `round_outside`** | **declared but incomplete** | **stays — planned work** |

ADR 0021 governs code that is *finished and unreachable*. A hinge type with no creator yet is the opposite: a **declared intent whose implementation is outstanding**. Deleting it would delete a roadmap item, and narrowing the literal would have to be undone. `HingeType` remains
`Literal["middle", "top", "top_simple", "round_inside", "round_outside"]` in all four
declarations (`app/schemas/aeroplaneschema.py:23`, `app/schemas/wing.py:103`,
`cad_designer/.../TrailingEdgeDevice.py:10`).

**The four dead items are recorded for removal, not removed.** They sit inside the
`cad_designer/` freeze (**ADR 0002**), so ADR 0021's disposition is *stated in the spec*
and executed only if that directory is ever re-implemented — the same treatment
`Q-FD-8` gives `from_step_file`.

**One derived guard, which does not touch the decision.** The dispatch is a bare dict
lookup — `ted_sketch_creators[ted.hinge_type]` (`ted_sketch_creators.py:187`, called from
`VaseModeWingCreator.py:662`) — so selecting a round hinge today raises
`KeyError: 'round_inside'` and surfaces as an **opaque 500**. The maintainer's
"no harm during beta" judgement is about the *missing feature*, not about the *error
shape*, and an unreadable stack trace is what **ADR 0020** exists to prevent. The lookup
gains an explicit miss branch naming the hinge type and stating that it is not yet
implemented (`NotImplementedError` → 501, or a `DesignWarning` at plan-validation time so
the user learns before the build runs, which is the better place). This is a defect fix,
not a scope change.

---

# construction-plans

## Q-CP-1 — Should plan execution move into the CAD process pool, or is ADR 0005 wrong?

**Context:** `cad_service`'s module docstring records the root cause verbatim:
OCCT is not thread-safe, and the same `.intersect().clean()` call that takes
~100 ms on the main thread **hangs indefinitely** in a worker thread. That is why
every CAD build goes through a spawned `ProcessPoolExecutor` (ADR 0005). Yet
`execute_plan` (step 7) calls `root_node.create_shape()` **on the FastAPI request
thread**, and `execute_plan_streaming` runs it on a `threading.Thread` — both
driving the same CadQuery/OCCT stack.
**Spec affected:** [`_reversa_sdd/construction-plans/requirements.md`] (BR-CP11),
[`_reversa_sdd/construction-plans/plan-execution/design.md`],
[`_reversa_sdd/adrs/0005-…md`]
**Question:** Either the process isolation is unnecessary or plan execution is
exposed to the documented hang. Which?
**Impact:** **A re-implementation must not silently pick one.** Compounding it:
streaming arms `set_display_callback` and
`os.environ["DISPLAY_CONSTRUCTION_STEP"]` — both process-global, no lock, no
per-execution context — so two concurrent streams cross-deliver shape events and
can clobber each other's display gate. Is concurrency out of scope, or does this
need per-execution context?

**Answer:** **(a) Route plan execution through the same CAD process pool.**
_Answered by the maintainer, 2026-08-13._

ADR 0005 stands; the code is what diverges. `cad_service`'s own docstring records
the reason verbatim — OCCT is not thread-safe, and the same `.intersect().clean()`
call that takes ~100 ms on the main thread **hangs indefinitely** in a worker
thread — yet `execute_plan` runs `root_node.create_shape()` on the FastAPI request
thread and `execute_plan_streaming` on a `threading.Thread`, both driving that same
stack.

**Secondary benefit:** the process-global state in the streaming path resolves by
construction. Today `set_display_callback` and
`os.environ["DISPLAY_CONSTRUCTION_STEP"]` are set process-wide with no lock and no
per-execution context, so two concurrent streams cross-deliver shape events and can
clobber each other's display gate. With one process per execution the problem
disappears rather than needing its own locking design. Note that `Q-CC-8`'s
single-worker rule does **not** help here: it prevents multi-*process* deployment,
not two concurrent requests inside the one process.

**Implementation cost, stated honestly:** streaming shape events must be returned
over IPC (a queue) instead of an in-process callback. That is the real work in this
change.

**Rejected:** (b) narrowing ADR 0005 to specific operations after empirically
showing plan execution is thread-safe — thread-safety cannot credibly be
established by the absence of observed failures, and a hang that only manifests on
particular geometry may simply not have been hit yet; (c) documenting the
divergence as accepted risk.

---

## Q-CP-2 — Where should `servo_information` / `engine_information` / `component_information` come from?

**Context:** The decode call injects `wing_config`, `printer_settings`,
`servo_information={}`, `engine_information=None`, `component_information=None`
(`construction_plan_service.py:670-678`) — **three of five slots hard-coded
empty**, at both execution call sites. Consequently `ServoImporterCreator`,
`ComponentImporterCreator` and `EngineMountShapeCreator` can never receive real
data through the REST path.
**Spec affected:** [`_reversa_sdd/construction-plans/requirements.md`] (BR-CP9),
[`_reversa_sdd/construction-plans/plan-execution/design.md`]
**Question:** Where is this data meant to come from — the component tree, the
COTS library, or the request body?
**Impact:** Three of 29 Creators are unreachable; the spec currently records this
as `Won't (today)`.

**Answer:** **ANSWERED by the maintainer, 2026-08-15** (option a) — **from the component tree and the COTS library. This is not yet implemented, and the gap is historical rather than a design choice.**

**The maintainer's stated intent, recorded because it reframes the finding:** *"Klarer
Plan ist, dass alle Informationen aus dem Komponentenbaum am Ende auch in den Creators
genutzt werden. Das ist historisch bedingt, da die Creator-Strecke viel älter ist als das
Frontend. Das Frontend hilft dem Product Owner, genau solche Lücken zu füllen und auch
weiterzuentwickeln."*

**This changes how the three hard-coded slots should be read.** `servo_information={}`,
`engine_information=None` and `component_information=None`
(`construction_plan_service.py:670-678`, both call sites) are not a decision to withhold
data and not an oversight — they are the **unfinished end of a migration**. The Creator
layer predates the component tree and the frontend by a wide margin; it was written when
there was no structured source for this data, so the slots were left empty and the
callers passed literals. The component tree now *is* that source.

**The target state:** the component tree supplies instances and placement, the COTS
library supplies part specifications, and `ServoImporterCreator`,
`ComponentImporterCreator` and `EngineMountShapeCreator` receive real data through the
REST path. This is consistent with two decisions already in the record — the component
tree is the **sole mass authority** (`Q-MB-1`) and referenced COTS parts are corrected
rather than versioned (`Q-PT-7`) — so routing Creator inputs anywhere else would create a
second source for parts the tree already owns (**ADR 0022**).

**Rejected — option (b), from the request body.** It would make the caller the authority
for what is mounted on an aircraft the tree already describes: a second producer, and one
that cannot be kept consistent with the tree.

**Spec consequence.** BR-CP9 stops reading `Won't (today)` and becomes **planned, not
yet implemented**, with the three Creators marked *unreachable pending the component-tree
wiring*. That distinction matters for `P-DEAD-0`: these Creators are **not** dead code
under ADR 0021 — like the round hinge types in `Q-CT-5`, they are declared capability
awaiting its data source, and deleting them would delete the target of the migration.

**A general observation worth carrying into the review of any `cad_designer` finding:**
where the Creator layer looks like it is ignoring modern application state, the default
reading is *"older layer, migration incomplete"* rather than *"deliberately excluded"*.
The frontend's role here is diagnostic — it surfaces exactly these gaps to the product
owner.

---

## Q-CP-3 — Should a partially converted aircraft be reported?

**Context:** A per-wing `wing_model_to_wing_config` failure logs a warning and
**removes that wing from the map** (l.650-654); the plan then executes against a
partial aircraft and `ExecutionResult` says nothing about it. This sits directly
against ADR 0012 ("design warnings instead of silent fallbacks").
**Spec affected:** [`_reversa_sdd/construction-plans/requirements.md`] (BR-CP6),
[`_reversa_sdd/construction-plans/plan-execution/requirements.md`]
**Question:** Should partial conversion become a warning in the response?
**Impact:** A builder can currently receive a manufacturable file for an
incomplete aircraft with no signal.

**Answer:** _(derived — not a maintainer decision)_ **Yes — a dropped wing becomes a `DesignWarning` on `ExecutionResult`, at severity `error`.**

Follows from **P-WARN-0**: "per-wing conversion drops" is named in the policy's own list of violations. The `error` band ("number not physically meaningful; do not build on it") is the right one here rather than `warning`, because the artefact handed to a builder is not the aircraft that was requested — a manufacturable file for an incomplete airframe is worse than a failed execution.

---

## Q-CP-4 — What are `SparPlanResult`'s actual field names?

**Context:** Only `front_no_spar_from_y` and `rear_no_spar_from_y` are confirmed
by name (from the gh-1076 test mocks); the remaining fields were inferred from
behaviour. `app/schemas/spar_plan.py` has no home unit (Q-CC-15), which is why
this was never pinned down.
**Spec affected:** [`_reversa_sdd/construction-plans/spar-plan/contracts.md`]
**Question:** Please paste the schema, or confirm the field list.
**Impact:** **The response shape cannot be reproduced exactly from the spec
alone** — this is the module's one hard blocker for re-implementation.

**Answer:** _(derived — not a maintainer decision)_ **The backend model is `SparPlanResponse` (there is no `SparPlanResult` in the backend) with 9 fields: `front_pieces`, `rear_pieces`, `front_joint`, `rear_joint`, `reinforcement`, `feasible`, `infeasibility_reason`, `front_no_spar_from_y`, `rear_no_spar_from_y`.**

Follows from **the wave-2 code lookup** ([`wave2-lookups.md`](wave2-lookups.md) §B, a factual answer rather than a maintainer decision): full typed tables are given there for `SparPlanResponse` (9 fields, `app/schemas/spar_plan.py:266`), the nested `SparPieceOut` (18 fields, `:178`) and `SparPlanRequest` (13 fields, `:56`). `SparPlanResult` is the *frontend* TypeScript interface (`frontend/hooks/useSparPlan.ts:67`), field-for-field identical — the spec was citing the client-side name for a server-side contract, and should be corrected. All response lengths are metres; `utilisation` is deliberately unclamped (`> 1` means no round tube strong enough fits); `width`/`height`/`cap_width` are declared but never assigned today (see `Q-WD-8` ①). Ownership of the file belongs to the shared contracts unit created in **Q-CC-15**.

---

## Q-CP-5 — Should the spar plan itself be persisted?

**Context:** There is no `spar_plans` table: the result is derived, returned and
projected onto `wing_xsec_spares`. A committed spar therefore carries geometry
but **no provenance** — not the sizing parameters, not the moment distribution,
not a plan id — and a re-solve silently supersedes the previous answer with
nothing to diff against.
**Spec affected:** [`_reversa_sdd/construction-plans/spar-plan/requirements.md`]
**Question:** Should the plan be persisted? Related: should it round to **stock
tube sizes**? It emits computed diameters while a builder buys tube in discrete
sizes, and nothing reports the plan against a stock list.
**Impact:** Structural provenance for a safety-relevant output.

**Answer:** _(resolved by code lookup — not a maintainer decision)_ **The stock-rounding half is already answered: stock snapping runs on 100 % of production paths, so only the *persistence* half is still open.**

`compute_spar_plan_object` calls `apply_stock_snap_to_plan` whenever `db is not None` (`app/services/spar_plan_service.py:573-585`), and `db` is a **required positional parameter with no default**, so no caller can omit it accidentally; both production callers pass the request-scoped session (`compute_spar_plan` at `:600`, `spar_insert_service.py:460`), and the single HTTP entry point injects `Depends(get_db)` (`app/api/v2/endpoints/aeroanalysis.py:520,535`). `db=None` appears nowhere in `app/` outside the explanatory comment — it is a test-only affordance. This also closes the loop on `wave2-lookups.md` §C.3: the intermediate under-strength tube (`Di = 0.6·Da`, ~15 % below the required `W`) is always repaired before leaving the service, because the snapper re-derives `erf_W = outer_d³/10` and accepts only stock with `W_stock ≥ erf_W` (`spar_plan_service.py:208-218`, `:158-162`) — but that guarantee lives in the snapper, not the solver, so a re-implementation that omits snapping would ship the under-strength tube.

**Verdict:** confirmed safe on the stock-size half.
Residual decision: whether the plan itself — sizing parameters, moment distribution, plan id — should be persisted so a committed spar carries provenance and a re-solve can be diffed; that half still needs you.

_Full detail: [`wave3-lookups.md`](wave3-lookups.md) §Q_


**Residual decision — ANSWERED by the maintainer, 2026-08-14: (a) persist the plan.**

A `spar_plans` table is introduced, capturing the **inputs** (material, safety factor
`j`, packing factor, shape, moment and torsion samples or a reference to their
source), the **resulting pieces**, and the **aeroplane version** the plan was solved
against. `wing_xsec_spares` rows carry a `spar_plan_id`.

**Rationale — this is a structural, safety-relevant output.** These wings are built
and flown. Today a committed spar carries geometry but **no provenance**: the
question "which load case was this spar sized for?" has no answer, not even for the
maintainer months later. Persisting the plan also makes a re-solve **diffable**
instead of a silent supersede, and composes with the auto-snapshot
`spar_insert_service` already performs (gh-1058).

Rejected: (b) inputs only — re-solving against changed geometry yields a different
answer, so the provenance would only be half trustworthy.

**⚠️ Spec-critical note that must accompany this (from the code lookup):** the
solver's intermediate tube is **under-strength** — `Di = 0.6·Da`, roughly 15 % below
the required section modulus. It is repaired **only by the stock snapper**, which
accepts stock solely when `W_stock ≥ erf_W` (`spar_plan_service.py:208-218`,
`:158-162`). That guarantee therefore lives **in the snapper, not in the solver**: a
re-implementation that omits stock snapping would ship an under-strength spar. The
spec must state the snapper as load-bearing, not as a convenience.

---

## Q-CP-6 — What counts as a "destructive" spar edit?

**Context:** The gh-1058 auto-snapshot fires for a segment split and a spare
`REPLACE`, but that list is **hard-coded** rather than derived from a property of
the edit. A future destructive edit type would silently miss the guard.
Separately, `_inboard_collinear`'s `tol_mm = 5.0` is a bare constant, not derived
from section thickness or tube diameter, so its meaning changes with aircraft
size.
**Spec affected:** [`_reversa_sdd/construction-plans/spar-plan/requirements.md`] (BR-SP7)
**Question:** Should the guard default to snapshotting *unless* the edit is
proven safe? And is the 5 mm collinearity tolerance appropriate at all scales?
**Impact:** The snapshot is the only recovery point before a destructive spar
commit.

**Answer:** **Invert the burden of proof: snapshot by default. And make the 5 mm
collinearity tolerance relative.** _Answered by the maintainer, 2026-08-15._

**Snapshot guard.** The gh-1058 auto-snapshot currently fires from a **hard-coded**
list (segment split, spare `REPLACE`) rather than from a property of the edit, so a
future destructive edit type misses the guard silently. Reversed: a snapshot is taken
**unless the edit is marked as provably non-destructive**. A forgotten new type then
costs at most a redundant snapshot instead of a missing recovery point.

This definition is shared with `Q-MC-1`, which applies the same auto-snapshot rule to
destructive MCP writes — one definition, two consumers (ADR 0022).

**Collinearity tolerance.** `_inboard_collinear`'s `tol_mm = 5.0` is a bare constant,
not derived from section thickness or tube diameter, so its meaning changes with
aircraft size — 5 mm means something different on a 1.5 m model than on a 4 m sailplane.
Per ADR 0023 it becomes **relative** (a fraction of the spar diameter or the local
section thickness) and carries its rationale.

---

## Q-CP-7 — Should `_migrate_tree_json` become a one-off data migration?

**Context:** It rewrites a root whose `$TYPE` is `ConstructionStepNode` into
`ConstructionRootNode`, drops the `creator` key, calls `flag_modified` and
flushes — **on every read of every plan**, inside `get_plan`. There is no audit
trail, no version marker and no way to tell a migrated row from an originally
correct one.
**Spec affected:** [`_reversa_sdd/construction-plans/requirements.md`] (BR-CP3, RF-07)
**Question:** Is the migration still needed, and should it become a one-off
Alembic data migration?
**Impact:** Currently every read is a write.

**Answer:** **Convert it to a one-off Alembic data migration.** _Answered by the
maintainer, 2026-08-15._

`_migrate_tree_json` currently rewrites a root whose `$TYPE` is
`ConstructionStepNode`, drops the `creator` key, calls `flag_modified` and flushes —
**on every read of every plan**, inside `get_plan`. There is no audit trail, no version
marker, and no way to distinguish a migrated row from an originally correct one.

Two reasons to move it:
- **A GET that writes is a side effect nobody expects**, and combined with `get_db()`'s
  commit-on-success it is genuinely persisted, not merely staged.
- After a one-off migration the read path becomes a pure read, and the rewrite is
  recorded once with a revision id instead of happening invisibly forever.

---

## Q-CP-8 — Is template → plan provenance wanted?

**Context:** `instantiate_template` and `to_template` are both deep copies with
**no version chain and no back-link** — after instantiation the two rows evolve
completely independently.
**Spec affected:** [`_reversa_sdd/construction-plans/plan-template-lifecycle/requirements.md`] (BR-69)
**Question:** Is lineage wanted (it would mirror the aeroplane versioning model)?
**Impact:** Currently specified as `Won't` — a design change, not a
re-implementation detail.

**Answer:** **ANSWERED by the maintainer, 2026-08-15** (option a) — **template → plan provenance is wanted: instantiation records a back-link to the template it came from.**

Today `instantiate_template` and `to_template` are both **deep copies with no version chain
and no back-link**, so the two rows evolve independently from the moment of instantiation
and nothing records that they were ever related.

**This mirrors the aeroplane versioning model**, which is the argument for it: a plan
derived from a template is the same kind of relationship as a design derived from a
snapshot. Once the link exists, two questions become answerable that cannot be answered
today — *which plans came from this template?* and *what has this plan diverged into since
it was instantiated?*

**Deliberately a back-link, not a live dependency.** The instantiated plan stays a full
copy and keeps evolving on its own; editing the template must not reach into plans already
derived from it. The link records history, it does not create coupling — the same
distinction `Q-VS-5` drew when rejecting shared file references between branches.

---

## Q-CP-9 — Construction-part storage and lifecycle (bundle)

**Context:** Five related decisions:
- **Should `construction_parts.aeroplane_id` become a real FK?** It is a plain
  indexed `String`, so deleting an aeroplane orphans both rows and files with
  nothing to find them by. `component_tree.aeroplane_id` has the same shape — the
  answer should be consistent across both (see Q-CC-7).
- **Why do part files live outside `ARTIFACTS_BASE_DIR`?** `STORAGE_ROOT` is the
  CWD-relative `tmp/construction_parts/`, so parts miss the `_ensure_within_base`
  traversal guard and symlink rejection that every artefact path gets (BR-68).
- **Is `material_component_id` meant to accept any component or only a
  `material`?** The FK to `components.id` is untyped; only the frontend filters
  the dropdown, so an API client can link a part to a motor.
- **Should a part referenced by `component_tree.construction_part_id` be
  undeletable?** The `locked` flag is user-driven and advisory, not referential.
- **Null geometry carries no reason.** An STL upload, an absent CAD kernel, a
  failed individual measurement and a genuinely degenerate solid all produce the
  same all-null response. Should the response say which?

Also: the STL-from-STEP regeneration serves a `tempfile.mkstemp` file and
**never removes it** — who cleans these up?
**Spec affected:** [`_reversa_sdd/construction-plans/construction-parts/requirements.md`]
**Question:** Confirm each.
**Impact:** Six contract/DDL decisions.

**Answer:** **All five decided.** _Answered by the maintainer, 2026-08-15._

**① `construction_parts.aeroplane_id` becomes a real FK** — already settled by
`Q-CC-7`, which migrates exactly these three soft `String` references (with
`component_tree` handled consistently).

**② Part files move under `ARTIFACTS_BASE_DIR`** and are read and written through the
same containment helper as every other artefact.

*Primary reason — an operational bug, not a security one:*
`STORAGE_ROOT = Path("tmp") / "construction_parts"` is **CWD-relative**, and the
resulting `file_path` is stored relative too, while `ARTIFACTS_BASE_DIR` is absolute
and `.resolve()`d by a validator. Running the backend from a worktree, another
directory or Docker with a different `WORKDIR` therefore either writes parts to a
second location or **fails to find existing ones — silently**. Same class as the
relative `./db/test.db` that already requires a symlink in worktrees.

*Secondary — defence in depth, honestly scoped:* part files miss `_ensure_within_base`
and the symlink rejection every artefact path gets. This is **not** the #1093 hole:
the filename is server-generated (`{part_id}_{uuid4().hex[:8]}{suffix}`, integer id,
whitelisted suffix) and `file_path` is not writable through `ConstructionPartUpdate`,
so there is no traversal primitive. The point is that parts are safe *by accident of
how filenames happen to be built*, not by construction — the guard is what would hold
if a future feature accepted a user-supplied name or path.

A small data migration is needed for existing `file_path` values.

**③ `material_component_id` is typed to materials only.** The FK to `components.id` is
untyped and only the frontend filters the dropdown, so an API client can currently link
a part to a motor. The constraint belongs in the contract, not in a dropdown
(ADR 0019 / ADR 0022).

**④ A referenced part cannot be deleted, only modified.** While
`component_tree.construction_part_id` references it, deletion is refused. The `locked`
flag stays what it is — user-driven and advisory — and is **not** the referential
guard. Consistent with the component deletion guard chosen in `Q-PT-13`.

**⑤ Null geometry carries its reason** (`P-WARN-0`): an STL upload, an absent CAD
kernel, a failed individual measurement and a genuinely degenerate solid must be
distinguishable, not collapse into the same silent `NULL`.

---

# openvsp-import

## Q-VI-1 — Wiring the `SS_CONTROL` post-pass changes what an import produces: go ahead?

**Context:** Verified during review. The gh-644 post-pass is dead **twice over**:
`openvsp_ss_control.register()` has exactly one caller in the repository
(`app/tests/test_openvsp_ss_control.py:24`) and is absent from
`_ensure_handlers_loaded`; and even if it ran, `_persist_aeroplane` writes wings
through `AsbWingGeometryWriteSchema` (`extra="forbid"`) whose
`WingXSecGeometryWriteSchema` has **no `trailing_edge_device` field at all**.
Fixing only the registration changes nothing.
**Spec affected:** [`_reversa_sdd/openvsp-import/requirements.md`] (BR-OV16, RF-29),
[`_reversa_sdd/openvsp-import/geom-handlers/requirements.md`]
**Question:** Every aircraft imported so far arrived with **no** control
surfaces. Turning this on will start creating TEDs with role `OTHER`. Does
anything downstream — trim, operating points, the copilot — currently assume
their absence?
**Impact:** The spec records RF-29 as `Could` on the grounds that "the user can
re-tag control surfaces in the UI afterwards, which was always the intent".
Confirm that reading.

**Answer:** **(a) Wire it fully — registration AND the write path.** _Answered by
the maintainer, 2026-08-13._ The spec's RF-29 reading is **confirmed**: the user
re-tags roles in the UI afterwards; that was always the intent.

**Both blockers must be fixed — this is not a one-line change:**
1. Register the post-pass in `_ensure_handlers_loaded` (today
   `openvsp_ss_control.register()` has exactly one caller in the repository — its
   own test file).
2. Extend the import write path so trailing-edge devices can persist:
   `WingXSecGeometryWriteSchema` has **no `trailing_edge_device` field**, and
   `AsbWingGeometryWriteSchema` is `extra="forbid"`. Fixing only the registration
   changes nothing observable.

**Scope check — consistent with ADR 0018.** That ADR excludes propulsion, inertia,
the `CSGroup` mixing matrix, VSPAERO validation and LE devices. The **SS_CONTROL
sub-surfaces themselves were in scope** — gh-644 was built for them. Role inference
remains out of scope, so imported surfaces carry `role = OTHER`.

**Behaviour after the change:** an import yields control-surface geometry and hinge
lines (tedious to re-enter by hand), which the user then tags with real roles.
Until tagged, an `OTHER` surface is not found by the pitch resolver from `Q-WD-1` —
but thanks to that decision the user now gets a visible `DesignWarning` instead of a
silent ±25° fallback. A `DesignWarning` noting "imported control surfaces need role
tagging" should be emitted on import.

**Also required by `P-DEAD-0`:** leaving a finished mechanism inert is not an
available option — it had to be wired or deleted.

---

## Q-VI-2 — `validate_geometry`: wire it, or delete it?

**Context:** The gh-647 span / area / MAC / fuselage-length cross-check against
VSP's own `TotalSpan`, `TotalProjectedArea`, `TotalChord` and `Length` at
`DEFAULT_REL_TOL = 0.01` is complete and tested, and referenced only from
`app/tests/test_openvsp_validation.py`. Its own module docstring shows the
intended wiring (`result.warnings.extend(mismatches)`), which does not exist in
`import_vsp3`.
**Spec affected:** [`_reversa_sdd/openvsp-import/requirements.md`] (BR-OV17, RF-30)
**Question:** Wire it in, or was it deliberately parked?
**Impact:** Shipping it inert a second time is worse than not having it. It adds
confidence, not capability — which is why it is `Could`, not `Must`.

**Answer:** **Wire it in.** _Answered by the maintainer, 2026-08-15._

The gh-647 cross-check (span / area / MAC / fuselage length against VSP's own
`TotalSpan`, `TotalProjectedArea`, `TotalChord`, `Length` at
`DEFAULT_REL_TOL = 0.01`) is complete and tested but referenced only from
`app/tests/test_openvsp_validation.py`. Its own module docstring shows the intended
wiring (`result.warnings.extend(mismatches)`), which never existed in `import_vsp3`.

**Why now, when it was parked before:** it catches precisely the failure class this
interview kept finding — imported geometry that *looks* plausible and is wrong
(camber loss `Q-VI-8`, silently dropped control surfaces `Q-VI-1`, unit errors
`Q-FD-2`). A 1 % cross-check against the source would have reported all three. And the
likely reason it was parked in 2026-04 is now gone: there was no channel to report a
mismatch into. `P-WARN-0` provides one — mismatches become `DesignWarning`s rather
than needing a new mechanism.

Required by `P-DEAD-0` in any case: leaving a finished confidence mechanism inert was
not an available option.

---

## Q-VI-3 — Should a feet-unit model without a fuselage be detectable?

**Context:** `_detect_source_scale_to_meters` measures the unit by exporting the
largest-X-span **fuselage** to a metric STEP and comparing spans. A wing-only
model — a flying wing, a core RC/UAV case — has no fuselage, so the function
returns `None`, **no conversion is applied and no `UNITS` warning is emitted**.
The importer's own acceptance criterion records it: *"🔴 A feet-unit flying wing
therefore imports 3.28× too large, silently."* Relatedly,
`LEN_UNIT_TO_METERS` maps `LEN_UNITLESS → 1.0`, silently treating a unitless
legacy file as metres.
**Spec affected:** [`_reversa_sdd/openvsp-import/requirements.md`] (BR-76, RF-17),
[`_reversa_sdd/openvsp-import/vsp3-import-pipeline/requirements.md`]
**Question:** Is there a wing-based fallback, or should the UI force an explicit
unit choice when detection is impossible? Should a unitless file warn?
**Impact:** The one remaining silent-3.28× path after gh-808.

**Answer:** _(derived — not a maintainer decision)_ **No silent scale: unit resolution follows the `Q-FD-2` mechanism — detection, an explicit override pre-filled with the detected value, and a plausibility check on the resulting dimensions — and `LEN_UNITLESS` never imports silently as metres.**

Follows from **Q-FD-2** and **P-WARN-0**: Q-FD-2 settled that no single layer of unit resolution is trustworthy on its own and that the *mechanism* must be the same across import paths; a wing-only model, where `_detect_source_scale_to_meters` returns `None` because there is no fuselage to measure, is exactly the case the plausibility layer exists for (an RC airframe is 0.3–3 m, so a 3.28× error is unambiguous). Whether a wing-based measurement is added as a further convenience layer is an implementation choice; what is settled is that "no conversion applied, no warning emitted" is not an available behaviour, and that `LEN_UNITLESS → 1.0` must emit a `DesignWarning`.

---

## Q-VI-4 — Bug #814: which body should the CAD download serve?

**Context:** The sewn solid STEP is malformed at sharp fuselage fillets (the Romo
nose-body fillet). The x-section path already routes around it — gh-812's
`_select_xsec_slice_source` prefers the **surface** STEP — but the CAD
construction/download path still consumes `solid_step_path`. Fixing the sewing
and changing the download contract are different products, and the code does not
indicate which was intended.
**Spec affected:** [`_reversa_sdd/openvsp-import/step-export-and-sewing/requirements.md`] (BR-77)
**Question:** What is the fallback when a user downloads a corrupt solid?
**Impact:** The solid is the input to battery-bay cuts, servo-mount unions and
carbon-tube bores.

**Answer:** **Detect the unusable solid, record the state, and fall back to a solid
lofted from the superellipse cross-sections.** _Answered by the maintainer, 2026-08-15._

**Premise corrected by the maintainer:** the solid is required **by the Creator
classes**, not for export to an external CAD tool. Handing the user a surface set to
heal themselves is therefore not a fallback — the consumer is the code.

**Three stages:**

**① Detection at sewing time.** Beyond today's `BRepCheck_Analyzer.IsValid()` — which
the malformed Romo nose-fillet solid **passes**, because it is topologically valid and
geometrically wrong — add:
- `BOPAlgo_ArgumentAnalyzer` with self-intersection checking (verified available in the
  installed OCP). It answers the question that actually matters — *is this shape fit for
  boolean operations?* — rather than *is its topology well-formed?*
- A **volume plausibility comparison against the surface STEP**. Unlike the scale
  ratios in `Q-FD-2`, this comparison does **not** cancel, because it compares two
  different representations of the same body.

**② Persist the outcome.** The fuselage carries `solid_status ∈ {ok, unusable, absent}`.
Today a failed sewing is indistinguishable from never having been attempted (both leave
`solid_step_path = NULL`), so the Creators cannot decide whether to fall back.

**③ Fallback.** When `solid_status != ok`, the Creators loft an approximate solid from
the stored `fuselage_xsecs` superellipses. That body is **well-formed by construction**,
being a loft of simple closed curves.

**Warning policy:** a `DesignWarning` with `severity: notice` — this is a *legitimate
substitution*, not a defect (the same reasoning as the sewing-tolerance retry and the
low-Re `e = 0.8` fallback). But it must be visible: internal cut-outs were then made
against an **approximated** fuselage rather than the exact imported geometry, which can
matter for a battery bay with little clearance.

---

## Q-VI-5 — Should the loose-tolerance sewing retry be disclosed?

**Context:** `BRepBuilderAPI_Sewing` runs at `_SEW_TOLERANCE_TIGHT = 0.001`
(1 mm) and, if no shells come out, retries at `_SEW_TOLERANCE_LOOSE = 0.005`
(5 mm — the documented ceiling before the nose cap would stitch itself to the
tail). A body sewn at 5 mm may have merged features that are genuinely 5 mm
apart, giving it materially lower geometric confidence — yet **nothing records
which tolerance succeeded**. Per ADR 0012 this looks like it should be a warning.
There is also no sewing success metric and no reason string stored when
`solid_step_path` is NULL, so how often sewing fails is unmeasurable.
**Spec affected:** [`_reversa_sdd/openvsp-import/step-export-and-sewing/requirements.md`] (BR-OV14)
**Question:** Should the tolerance used be recorded and surfaced?
**Impact:** Directly related to #814 — a loose-tolerance sew is the likeliest
producer of a malformed solid.

**Answer:** _(derived — not a maintainer decision)_ **Yes — record which tolerance succeeded and surface it: a 5 mm sew is `notice` · `geometry_healed`.**

Follows from **P-WARN-0**, whose worked classification table contains this exact case: "Sewing tolerance 1 mm → 5 mm | `notice` · `geometry_healed` | Standard CAD healing; user should still know healing occurred." The tolerance used is persisted with the artefact so that #814's malformed solids can be correlated with loose sews, and a failed sew stores a reason string instead of leaving a bare `NULL` `solid_step_path` — the policy forbids the current state where sewing quality is unmeasurable.

---

## Q-VI-6 — Should the export-unit ↔ unit-detection dependency be asserted at runtime?

**Context:** BR-76's measured unit detection is valid **only** because BR-OV13
forces `STEPSettings.LenUnit = LEN_M` on every export. Neither module states the
dependency, and nothing asserts it. Separately, `scale_geom_step` and the
persisted schema are scaled by two different code paths, and nothing afterwards
asserts that the stored STEP and the persisted fuselage x-sections still agree.
**Spec affected:** [`_reversa_sdd/openvsp-import/step-export-and-sewing/requirements.md`],
[`_reversa_sdd/openvsp-import/vsp3-import-pipeline/design.md`]
**Question:** Should both be asserted at runtime rather than relied upon?
**Impact:** BR-OV11 already says "getting this order wrong silently mismatches
the schema and the STEP artefact" — this is the missing guard for that.

**Answer:** _(derived — not a maintainer decision)_ **Not a bare runtime assertion — both invariants are now checked against the source geometry by mechanisms already decided elsewhere.**

Follows from **Q-VI-2**, whose stated reason for wiring `validate_geometry` names this failure class outright: *"A 1 % cross-check against the source would have reported all three"*, the three being camber loss, dropped control surfaces and **unit errors (`Q-FD-2`)** — so a wrong export unit, or a schema that has drifted from the STEP it was scaled beside, surfaces as a `DesignWarning` instead of resting on BR-OV13 silently holding. **Q-FD-3** settles the second half in the same idiom — *"Not a bare runtime assertion"*, check `2a ≤ 1.02·Y_extent(step)` and the body aspect ratio against the STEP bounding box wherever a `step_path` survives — which is precisely the stored-STEP ↔ persisted-x-sections agreement BR-OV11 was missing, and **Q-FD-2 / ADR 0001**'s plausibility layer catches an implausible absolute size where no source survives. BR-OV13's `LEN_M` stays a documented precondition; it is simply no longer the only thing standing between an import and a silent scale error.

---

## Q-VI-7 — Should handler registration failures be reported?

**Context:** Each of the four handler imports in `_ensure_handlers_loaded` sits
in its own `try: … except ImportError: pass`, so a broken handler module degrades
into "every geom of that type is unsupported" with **no diagnostic at all**.
**Spec affected:** [`_reversa_sdd/openvsp-import/requirements.md`] (BR-OV19)
**Question:** Should a failed registration be logged or raised?
**Impact:** This failure mode is indistinguishable from a genuinely unsupported
geom type.

**Answer:** _(derived — not a maintainer decision)_ **Yes — a failed handler registration is reported; `except ImportError: pass` goes.**

Follows from **P-WARN-0**: "swallowed `ImportError`" is named in the policy's own list of violations, and the present behaviour is indistinguishable from a genuinely unsupported geom type. The import result carries a `DesignWarning` (`capability_unavailable`) naming the handler that failed to load, at severity `error`, because every geom of that type is then skipped without the user being able to know why.

---

## Q-VI-8 — Where is camber lost (#791), and is #792 acceptable?

**Context:** Two open benchmark findings from `scripts/vspaero_benchmark/`:
**#791** — the importer loses airfoil camber: a `C_L0` offset of ≈0.43 on the
DG-101G but only 0.07 on the Titan Falcon, so it is geometry-specific. The
responsible branch was not identified in the analysed code.
**#792** — x-section augmentation makes the ASB VLM intractable: 215 s per solve
on a 31-xsec Cessna.
**Spec affected:** [`_reversa_sdd/openvsp-import/geom-handlers/requirements.md`],
[`_reversa_sdd/architecture.md`] §12
**Question:** Is #791 blocking any user-visible accuracy claim, and is #792
acceptable given AeroBuildup is the default solver?
**Impact:** #791 in particular would make every imported aircraft's lift curve
wrong at α = 0.

**Answer:** _(expert consensus, endorsed by the maintainer 2026-08-14)_ **#791: ship — the loss is a pure `C_L0`/`C_m0` offset that provably leaves `C_Lα`, the aerodynamic centre, `dC_m/dα`, the neutral point and the static margin untouched, and the importer's true share is `ΔC_L0 ≈ 0.10–0.17`, not 0.43. #792: accept as a perf item — scale panel count, do not chase VLM fidelity.**

Thin-airfoil theory decides the triage. `α_L0 = −(1/π)∫₀^π (dz/dx)(cos θ₀ − 1) dθ₀`, `c_l = 2π(α − α_L0)`, and `c_m,c/4 = (π/4)(A₂ − A₁)` (Anderson Eq. 4.64) depend only on camber-line shape, not on α — so `c_lα` is 2π regardless of camber and **only `α_L0` (hence `C_L(α=0)`) and `C_m0` move**. Evaluating those integrals on the DG-101G's own stored sections in `dg101g.vsp3` gives FX 61-184: `α_L0 = −6.05°`, `c_l0 = 0.664`, `c_m,c/4 = −0.165`; FX 60-126: `α_L0 = −4.68°`, `c_l0 = 0.513`, `c_m,c/4 = −0.127` — so the wing's true inviscid `C_L0` lands in **0.48–0.63**, against ASB VLM's 0.44 and VSPAERO's 0.87. **VSPAERO overshoots by more than the importer undershoots**, so the ticket's framing of VSPAERO as truth is wrong and the 0.43 attribution is over-stated by roughly 2.5×. Retitle from "camber loss" to "zero-lift-angle (`α_L0`) fidelity on import". Add a ~1 ms runtime check that recomputes `α_L0` from the written `.dat` and compares against the source: **|Δα_L0| ≤ 0.5°** silent, **0.5–1.0°** `severity="info"`, **> 1.0°** `severity="warning"` naming the section. Fix the separate latent bug regardless — `openvsp_wing_handler.py:916` hard-codes the root section's `twist=0.0` and `:1033-1036` applies the geom XForm rotation only to `xs.xyz_le`, so a model setting incidence via `Y_Rotation` (the standard OpenVSP idiom) arrives at 0° incidence with the identical fingerprint and will be misdiagnosed as camber loss. Scope the accuracy claim meanwhile: the UI may not present imported `C_L0`, cruise α or required incidence as verified.

**#792 is expected, not anomalous.** `asb.VortexLatticeMethod` defaults to 10 × 10 **per wing section**, so 31 xsecs → 30 sections → 3 000 panels on the main wing alone; the AIC build is O(N²) and the solve O(N³). Keep **AeroBuildup the default** — it is vectorised over operating points (a 15-α sweep is one call) and it is the only solver in the stack that produces a profile-drag polar at all, which is precisely what `(L/D)max`, `CD0`, best-glide and sink rate need. Scale resolution so **panel count**, not section count, is the knob: `spanwise_resolution = max(1, round(120 / n_sections))` with `chordwise_resolution = 8` (≈ 1 000 panels → 2–4 s/solve, a ~50–100× improvement), plus `run_symmetric_if_possible=True` for another ~2×. Offer VLM only for span efficiency and control derivatives, never as the polar engine.

**Authority:** Anderson §4.8–4.9 (thin-airfoil theory; Eq. 4.64 — note the vault page's `c_m,c/4 = −π(A₁/2)` rendering does not reproduce measured data and Eq. 4.64 was used); Sadraey (`i_w = α_{C_li}`, so a 1.5° `α_L0` error corrupts a design decision); AeroSandbox tooling (VLM resolution semantics and the AeroBuildup vectorisation); Lennon (pitching moment "little affected by Rn"; profile drag nearly doubles at model Re).
**Confidence:** high on the physics, the `C_L0`/`C_m0`-only conclusion, the numeric re-attribution and the VLM cost model; medium on root-cause attribution — mechanism (b) is confirmed present in code and confirmed *not* the DG-101G's cause, while the Selig re-export off the lofted surface is inferred from the parm set without running OpenVSP.
Disagreement: RC practice would tolerate the `C_L0` offset (a builder absorbs 1.5° of trim error with elevator on the first flight); Scholz does not, because incidence is *set* from the airfoil's ideal-lift angle. Resolved in favour of Scholz per the authority hierarchy — fix it — while both agree on shipping meanwhile.

_Full reasoning: [`expert-consensus-aero.md`](expert-consensus-aero.md)_

---

## Q-VI-9 — Handler details that were not read (bundle)

**Context:** Three small unknowns:
- **Is `_read_section_parm`'s one-index fallback intentional inheritance or a bug
  workaround?** It tries `XSec_{i}`, then `XSec_{i-1}`, then returns `0.0` — and
  `0.0` is a legal value for several of these parms, so a missing parm is
  indistinguishable from a deliberate default.
- **Should `_u_to_segment_index` clamp or report?** A sub-surface running past the
  tip currently resolves silently to the last segment
  (`clamp(int(u·n_sec)+1, 1, n_sec)`).
- **The CUSTOM handler was read at summary level only.** Its parm coverage and
  degradation behaviour are unconfirmed, so that slice cannot be re-implemented
  from the spec alone.

**Spec affected:** [`_reversa_sdd/openvsp-import/geom-handlers/requirements.md`]
**Question:** Confirm each.
**Impact:** The CUSTOM one is the only genuine re-implementation blocker of the
three.

**Answer:** _(resolved by code lookup — not a maintainer decision)_ **The CUSTOM handler is now fully documented — 5 API calls, geometry from 12 u-stations × 32 w-points of `CompPnt01` reduced to Y/Z bounding-box half-axes with a hard-coded `n=2.0`, and a four-branch degradation table — so that re-implementation blocker is cleared.**

It touches only `GetNumMainSurfs` / `GetNumXSecSurfs` (capability probes, `app/converters/openvsp_custom_handler.py:59-60`), `CompPnt01` (`openvsp_fuselage_handler.py:350`, the sole geometry source), `Sym_Planar_Flag` (`:287`) and the geom XForm — which it reads and then deliberately discards (`openvsp_custom_handler.py:113-132`). No script-private `Design.*` parm, no XSec shape/skinning parm, no scale, colour or sub-surface is read; the module docstring states why (`:5-9`). Fidelity consequences a re-implementation must reproduce or consciously reject: `a`/`b` are bounding-box half-widths (a square-ish fuselage gains area), `cx` is the arithmetic mean of the sampled x while `cy`/`cz` are bbox midpoints (`openvsp_fuselage_handler.py:354-356`), and `CompPnt01(gid, 0, u, w)` hard-codes main-surface index 0 although the probe only requires `>= 1`, so a multi-surface Custom Geom silently loses every surface but the first. Degradation has four branches: probe failure → `info` + `mark_lossy` + skip (`:59-73`); `len(xsecs) < 2` → `warning` + `mark_lossy` + skip (`:98-106`); non-zero geom rotation → `info`, XForm not applied (`:114-126`, translation is discarded with no warning at all); and a mid-body `CompPnt01` failure → `warning` then **`break`** (`:79-91`), which imports a silently truncated fuselage and does **not** mark it lossy. Symmetry is XZ-only and its warnings are emitted with `component_type="FUSELAGE"` (`openvsp_fuselage_handler.py:287-304`), so a CUSTOM geom's symmetry warning is mis-attributed in the warning stream.

**Verdict:** confirmed defect — the mid-body `CompPnt01` failure path truncates the body without marking it lossy; the rest of the coverage and degradation contract is confirmed as-is.
Residual decision: the other two bundle items — `_read_section_parm`'s one-index fallback intent and whether `_u_to_segment_index` should clamp or report — were not part of this lookup and still need you.

_Full detail: [`wave3-lookups.md`](wave3-lookups.md) §H_


**Residual decision — ANSWERED by the maintainer, 2026-08-15.** (The CUSTOM-handler
item was cleared by the code lookup — see `wave3-lookups.md` §H.)

**① `_read_section_parm` must stop returning `0.0` for "not found".** It tries
`XSec_{i}`, then `XSec_{i-1}`, then returns `0.0` — and **`0.0` is a legal value for
several of these parms**, so "missing" and "deliberately zero" are indistinguishable.
Three states are reported instead:
- found at `XSec_{i}` → the value, no warning;
- inherited from `XSec_{i-1}` → the value plus a `DesignWarning`
  (`substituted_assumption`, `notice`);
- not found → **`None`, never `0.0`**, plus `severity: error`.

Whether the `i-1` fallback itself is retained depends on whether it reflects genuine
OpenVSP inheritance semantics or was a workaround — to be checked against the OpenVSP
API. The silent `0.0` goes either way.

**② `_u_to_segment_index` reports instead of clamping silently.** A sub-surface
extending past the tip currently resolves to the last segment via
`clamp(int(u·n_sec)+1, 1, n_sec)` with no signal. The imported geometry then differs
from the source, which is exactly what must be visible (`P-WARN-0`).
---

## Q-VI-10 — Is epic #638 (B5 / B6) still the intended direction?

**Context:** Deferred by the spec as `Won't (this iteration)`: B5 —
`XS_GENERAL_FUSE` / `XS_FILE_FUSE` / `XS_EDIT_CURVE` polyline sampling; B6 — a
STEP fallback for CUSTOM / CONFORMAL / NGON_MESH geoms.
**Spec affected:** [`_reversa_sdd/openvsp-import/requirements.md`] (MoSCoW)
**Question:** Still the intended direction?
**Impact:** Confirms the module's scope boundary alongside ADR 0018.

**Answer:** **ANSWERED by the maintainer, 2026-08-15** (option a) — **epic #638's B5 and B6 stay out of scope; the boundary is confirmed as the spec records it.**

- **B5** — polyline sampling for `XS_GENERAL_FUSE` / `XS_FILE_FUSE` / `XS_EDIT_CURVE`
- **B6** — a STEP fallback for `CUSTOM` / `CONFORMAL` / `NGON_MESH` geometries

Both remain `Won't (this iteration)`.

**Consistent with the importer's stated purpose** and with **ADR 0018**: the OpenVSP path
exists as *RC-scaling inspiration* — geometry and mass are what must come across, and that
is satisfied by the cross-section types already supported. The unsupported types are
either rare in the source material or lead into full-scale-preliminary territory the
importer deliberately does not enter.

**The scope boundary is stated positively in the spec**, not left as a list of omissions,
so a reader can tell that the limits were chosen rather than merely not yet reached.

---

# aero-analysis

## Q-AA-1 — `_auto_populate_cd0` writes total CD into the `cd0` assumption: delete, or rewrite?

**Context:** `stability_service._auto_populate_cd0` (`:257-281`) writes
`result.CD` — the **total** CD at the operating point — into the `cd0` design
assumption with `calculated_source="stability_analysis"`, whenever an AeroBuildup
stability summary is requested. That is exactly the quantity gh-924 / ADR 0004
removed from the authoritative path: `recompute_assumptions` writes the
**parasite** CD0 (`CD_total − CL²/(π·AR·e)`). The two run on different triggers,
so the stored `cd0` flips between a parasite and a total value between
recomputes.
**Spec affected:** [`_reversa_sdd/aero-analysis/requirements.md`] (BR-AA17),
[`_reversa_sdd/aero-analysis/aero-context-single-source/requirements.md`],
[`_reversa_sdd/adrs/0004-…md`]
**Question:** Delete it outright, or rewrite it to publish the parasite split via
`_parasite_cd0`? Deleting changes behaviour for anyone currently relying on the
stability path to seed `cd0`.
**Impact:** On a cambered wing (CL(α=0) ≈ 0.55 on a glider) the total-CD value
collapses `(L/D)max` from ~24 to ~17 — a plausible-looking number, not an error —
and nine consumers read it.

**Answer:** **(a) Delete `_auto_populate_cd0`.** _Answered by the maintainer,
2026-08-13._

After removal the `cd0` design assumption has **exactly one producer**
(`recompute_assumptions`, writing the parasite split
`CD_total − CL²/(π·AR·e)`), restoring ADR 0004 ("one aero truth per aircraft").
The stored value can no longer flip between a parasite and a total quantity
depending on which trigger fired last.

**On the one loss — cold-start seeding:** an aeroplane that has never been
recomputed no longer gets `cd0` incidentally seeded by the stability path. Under
`P-WARN-0` this is now an **improvement, not a regression**: instead of silently
storing a wrong value, a missing `cd0` raises a `DesignWarning`
(`input_missing`) telling the user to run a recompute. A visible "not computed
yet" beats an invisible "computed for a different aircraft".

**Rejected:** (b) rewriting it to publish the parasite split — it would keep
*two* producers of the same quantity, which must then agree on `e` and `AR` or
diverge again, only more quietly; this is precisely the pattern ADR 0004 exists
to prevent. (c) keeping it with a divergence warning — leaves the value
ambiguous.

---

## Q-AA-2 — Should `min_static_margin` / `max_static_margin` be real assumptions?

**Context:** `stability_service._get_margin_bounds` (`:225-254`) queries
`design_assumptions` for both names, but neither appears in `VALID_PARAMETERS` /
`PARAMETER_DEFAULTS`, so `seed_defaults` never creates the rows and the lookup
always returns empty. The 5 % / 25 % CG-range bounds are therefore **effectively
hard-coded while appearing configurable**.
**Spec affected:** [`_reversa_sdd/aero-analysis/stability-derivatives/requirements.md`] (BR-AA16)
**Question:** Add them to the catalogue, or drop the query and promote the numbers
to named constants?
**Impact:** A user editing what looks like a configurable bound would see no effect.

**Answer:** _(derived — not a maintainer decision)_ **Drop the dead lookup and promote the 5 % / 25 % bounds to named constants the spec states; making them configurable later is a new feature with its own ticket.**

Follows from **P-DEAD-0**: `_get_margin_bounds` queries two parameter names that `seed_defaults` never creates, so the query can only ever return empty — inert code whose only effect is to make a hard-coded bound *look* configurable, which is the false-impression case the policy calls decisive. It is not a switched-off safety mechanism and carries no live ticket, so rule 3 applies: delete the query, keep the numbers, and record them as fixed constants rather than as assumptions a user can edit without effect.

---

## Q-AA-3 — Should a missing `mass` assumption suppress the speed polar instead of defaulting to 1.0 kg?

**Context:** `_build_speed_polar` (`analysis_service.py:617-623`) catches
`NotFoundError`, logs a warning and continues with `base_mass = 1.0`. The chart
then renders physically meaningless speeds with no user-visible signal.
**Spec affected:** [`_reversa_sdd/aero-analysis/requirements.md`] (BR-AA23),
[`_reversa_sdd/adrs/0012-…md`]
**Question:** Suppress the polar, or emit a design warning alongside it?
**Impact:** ADR 0012's own rule — "null is an honest no value, never a fabricated
fallback" — argues against the current behaviour.

**Answer:** _(derived — not a maintainer decision)_ **Both: the 1.0 kg fallback is removed so no polar is rendered from a placeholder mass, and the response carries a `DesignWarning` (`input_missing`, severity `error`).**

Follows from **P-WARN-0** and **Q-CC-10**: the worked table classifies "`mass = 1.0 kg` because the context key was missing" as `error` · `input_missing` — "a placeholder unrelated to the aircraft — a defect, not engineering" — and Q-CC-10 removes the RC-typical defaults outright, naming `mass 1.0 kg` among them. With no mass there is no physically meaningful speed axis, so ADR 0012's "null is an honest no value, never a fabricated fallback" applies to the chart itself, not merely to the fields on it.

---

## Q-AA-4 — Are the duplicated geometry listeners deliberate?

**Context:** `stability_events.py` and `avl_geometry_events.py` both attach
`after_insert/update/delete` on `WingModel`, `WingXSecModel` and `FuselageModel`,
and both call `mark_ops_dirty` and publish `GeometryChanged`. Every geometry write
therefore fires the event bus **twice**.
**Spec affected:** [`_reversa_sdd/aero-analysis/retrim-invalidation/design.md`],
[`_reversa_sdd/avl-integration/requirements.md`]
**Question:** Deliberate (each module owns its own dirty flag), or should the
shared parts be factored out?
**Impact:** Doubles the invalidation fan-out on every geometry edit.

**Answer:** _(derived — not a maintainer decision)_ **Not deliberate — factor the shared listener out so a geometry write publishes `GeometryChanged` exactly once, with `aero-analysis` and `avl-integration` subscribing.**

Follows from **ADR 0022** as the maintainer applied it in **Q-AA-5**'s residual decision: a second path performing the same invalidation work *"is an instance of the single-authority rule (ADR 0022)"*. The "each module owns its own dirty flag" reading does not survive inspection — `stability_events.py` and `avl_geometry_events.py` call the **same** `mark_ops_dirty` and publish the **same** `GeometryChanged` event on the same three models, so this is one path written twice, not two concerns. It also gets worse under Q-AA-5: once the marking moves into the handlers, two publishers per DB event mark and schedule twice, leaving the 2 s debounce as the only thing hiding it.

---

## Q-AA-5 — Should `mark_ops_dirty` move into the event handlers?

**Context:** It is called by **seven publishers by hand**, immediately before
`event_bus.publish(...)`, while the handlers only schedule jobs — yet the
handlers' log lines read *"OPs marked DIRTY"*. A new geometry-mutating path that
publishes but forgets to mark leaves stale operating points with no warning, and
the misleading log is actively harmful during an incident.
**Spec affected:** [`_reversa_sdd/platform-core/requirements.md`] (BR-82),
[`_reversa_sdd/aero-analysis/retrim-invalidation/design.md`],
[`_reversa_sdd/traceability/spec-impact-matrix.md`] (CS-6)
**Question:** Is the manual pairing deliberate (ordering guarantees?) or
historical — and should the handler own the marking so a new publisher cannot
forget it?
**Impact:** CS-6 in the impact matrix; the fan-out is only correct by convention.

**Answer:** _(resolved by code lookup — not a maintainer decision)_ **The pairing is historical, not an ordering guarantee — no ordering guarantee depends on `mark_ops_dirty` preceding `publish`, and swapping the two lines would change nothing observable.**

Three facts establish it. The handlers never read operating-point status; they only schedule (`app/services/invalidation_service.py:39-48`) — and the misleading `"OPs marked DIRTY"` log line sits right there at `:42`, announcing something the handler does not do. `EventBus.publish` is synchronous (`app/core/events.py:36-42`), but `schedule_retrim` only creates an asyncio task whose coroutine begins with a 2-second sleep (`app/core/background_jobs.py:101-133`, `debounce_seconds = 2.0`). And the consumer reads through a different, later session — `retrim_dirty_ops` opens its own `SessionLocal()` (`app/services/retrim_service.py:59`) — so it sees only what the request transaction committed, while `mark_ops_dirty` issues a bulk `UPDATE` on the caller's session (`invalidation_service.py:26-36`) that `get_db()` commits at request end. The real constraint is "both must happen before the request commits", which both orderings satisfy. The seven manual publishers are enumerated in the lookup.

**Verdict:** confirmed safe to move — moving the marking into the handlers is a pure refactor with no behavioural risk, and it would also make the log line true.
Residual decision: whether to actually do it is still yours; only the factual objection ("maybe the ordering matters") is closed.

_Full detail: [`wave3-lookups.md`](wave3-lookups.md) §K_


**Residual decision — ANSWERED by the maintainer, 2026-08-15: yes, move it —
low priority.**

Confirmed safe: no ordering guarantee depends on `mark_ops_dirty` preceding
`event_bus.publish(...)`. The move removes a duplicated path — today
`mass_cg_service` calls `mark_ops_dirty` **directly** *and* publishes an
`AssumptionChanged` event whose handler does the same thing — so it is an instance of
the single-authority rule (ADR 0022). Pure tidying: no behaviour changes, hence low
priority.
---

## Q-AA-6 — Operating-point lifecycle decisions (bundle)

**Context:** Four related state-machine questions:
- **Should OP `warnings` be cleared on a successful retrim?** Today they
  accumulate on the row (`STALE_NO_POLAR`, `FLAP_DEFLECTION_CLIPPED`,
  `STALL_IN_TURN`, …) and nothing removes them, so a point that was once stale
  reads as permanently suspect.
- **`DIRTY` is absorbing when no pitch control exists.** `retrim_dirty_ops` logs a
  warning and leaves every OP `DIRTY` forever. Should the aircraft be marked "not
  trimmable" once, so the UI can explain it rather than showing a permanently
  pending state?
- **`get_cached_stability` relies on alphabetical status ordering**
  (`status ASC` puts `CURRENT` before `DIRTY`). Should this become an explicit
  rank before a third status is added?
- **`operating_points.aircraft_id` has no `ondelete`**, unlike
  `stability_results` / `design_assumptions` which cascade. Are orphaned operating
  points cleaned up elsewhere?

**Spec affected:** [`_reversa_sdd/aero-analysis/retrim-invalidation/requirements.md`],
[`_reversa_sdd/state-machines.md`] §1
**Question:** Confirm each.
**Impact:** Four state-machine rows.

**Answer:** _(resolved by code lookup — not a maintainer decision)_ **On the fourth item: orphaned operating points are cleaned up **nowhere**, and the working database already holds **22** of them (13 % of the table).**

`operating_points.aircraft_id` is a plain FK with no `ondelete` (`app/models/analysismodels.py:20-25`, and the introducing migration `1f3b9c42e3aa_extend_operating_points_for_generation.py` likewise). There is no ORM relationship to cascade through — `AeroplaneModel` declares eleven relationships but no `operating_points` (`app/models/aeroplanemodel.py:719-768`), and `OperatingPointModel` declares none back. `delete_aeroplane` simply calls `db.delete(aeroplane)` (`app/services/aeroplane_service.py:177-189`), and SQLite never enforces the constraint anyway: the connect hook sets `journal_mode`, `synchronous` and `busy_timeout` but not `foreign_keys` (`app/db/session.py:38-52`). The only bulk delete of operating points (`app/services/operating_point_generator_service.py:1033-1039`) runs when a *new* set is generated for a still-existing aircraft, and the per-row deletes are explicit user actions. A read-only query against `db/test.db` returned 22 orphans out of 165 rows.

**Verdict:** confirmed defect
Residual decision: `ondelete="CASCADE"` on the column versus a `relationship(..., cascade="all, delete-orphan")` on `AeroplaneModel` (the latter would also make the clone-coverage test see the table) — either way a one-off data migration is needed to clear the existing 22, and the bundle's other three items (clearing `warnings` after a successful retrim, the absorbing `DIRTY` state, the alphabetical status ordering) still need you.

_Full detail: [`wave3-lookups.md`](wave3-lookups.md) §L_


**Residual decision — ANSWERED by the maintainer, 2026-08-14. All four confirmed;
item ④ resolved as (a).**

**① Clear OP `warnings` on a successful retrim — yes.** Today they accumulate on the
row (`STALE_NO_POLAR`, `FLAP_DEFLECTION_CLIPPED`, `STALL_IN_TURN`, …) and nothing
removes them, so a point that was once stale reads as permanently suspect. Warnings
describe the **current** computation: a new result replaces them. Accumulation
produces exactly the alert fatigue `P-WARN-0` is designed to avoid.

**② `DIRTY` must stop being absorbing.** When no pitch control exists,
`retrim_dirty_ops` logs and leaves every operating point `DIRTY` **forever**, which
the UI renders as a permanently pending state. Mark the condition **once, explicitly**
("not trimmable") so the UI can explain it. Consistent with the
`CONTROL_AUTHORITY_LIMIT` status introduced by `Q-MS-5` and the error-severity
warning from the `Q-WD-1` resolver.

**③ Replace the alphabetical status ordering with an explicit rank — and do it
now.** `get_cached_stability` relies on `status ASC` happening to put `CURRENT`
before `DIRTY`. `Q-MS-5` introduces a third status, `CONTROL_AUTHORITY_LIMIT`, which
sorts **before** `CURRENT` alphabetically and would silently change which row is
treated as authoritative. This is no longer a latent trap but an imminent one.

**④ Orphaned operating points → (a) an ORM `relationship(..., cascade="all,
delete-orphan")` on `AeroplaneModel`,** rather than only `ondelete="CASCADE"` on the
column. Both fix the orphans, but only the relationship makes the table **visible to
the clone-coverage test**, closing the same versioning blind spot addressed in
`Q-CC-7` — double duty for the same change. A one-off data migration clears the
**22 existing orphans**.

---

## Q-AA-7 — Are the German polar-rejection hints developer-facing only?

**Context:** `PolarRejection.hint` strings ("Zu wenig Punkte im linearen
Polar-Fenster …", "Polare zeigt mit steigendem Auftrieb fallenden Widerstand …")
are surfaced to the UI whenever `category == "design"` — and the frontend is
English-only.
**Spec affected:** [`_reversa_sdd/aero-analysis/aero-context-single-source/requirements.md`]
**Question:** Translate, or are these developer-facing only? (See also Q-CC-5.)
**Impact:** The gh-956 design-warning mechanism is the *point* of surfacing them
to the user.

**Answer:** _(derived — not a maintainer decision)_ **Translate them — they are the most user-facing German strings in the system, not developer-facing.**

Follows from **Q-CC-5**, which names them explicitly: "`PolarRejection.hint` strings surfaced whenever `category == \"design\"` — these are **deliberately user-facing** (gh-956), so they matter most." Domain terms are translated by meaning rather than transliterated, consistent with the project's English-only UI rule.

---

## Q-AA-8 — Dead code in `assumption_compute_service`: remove, or keep?

**Context:** `_load_cg_agg` (l.1739) has no callers — the pipeline uses
`loading_scenario_service.compute_cg_agg_for_aeroplane`. `_extract_scalar`
(l.1316) is imported only by tests. Separately,
`polar_re_table_top_band_fallback` is computed **twice** — once inside
`build_re_table` (returned only implicitly via `fallback_used`) and once in
`recompute_assumptions` by re-scanning the table.
**Spec affected:** [`_reversa_sdd/aero-analysis/aero-context-single-source/design.md`]
**Question:** Remove, or keep as documented fallbacks? Should `build_re_table`
return the flag directly?
**Impact:** Three small clean-ups in the system's most important pipeline.

**Answer:** _(derived — not a maintainer decision)_ **Remove `_load_cg_agg` and `_extract_scalar`, and have `build_re_table` return the top-band fallback flag directly so it has exactly one producer.**

Follows from **P-DEAD-0** and the single-producer rulings in **Q-AA-1**/**Q-MB-1**: a helper with no callers and a helper imported only by its own tests are rule 3's "anything else → delete" (a test-only helper tests nothing the system uses). And computing `polar_re_table_top_band_fallback` twice — once inside `build_re_table`, once by re-scanning the table in `recompute_assumptions` — is the same two-producers-of-one-quantity pattern ADR 0004 and Q-AA-1 exist to eliminate, in the one pipeline nine consumers read.

---

## Q-AA-9 — Is `recompute_assumptions`'s single ~750-line form deliberate?

**Context:** It performs 12 distinct stages with per-stage error policies in one
function. The spec documents each stage, but the linear form is unusual for
something with nine downstream consumers.
**Spec affected:** [`_reversa_sdd/aero-analysis/aero-context-single-source/design.md`]
**Question:** Is a decomposition planned, or is the linear form deliberate for
traceability?
**Impact:** Guides whether the spec prescribes the same shape.

**Answer:** **ANSWERED by the maintainer, 2026-08-15** (option a) — **decompose: one function per stage, with the orchestration on the outside.**

`recompute_assumptions` currently performs **twelve distinct stages with per-stage error
policies in a single ~750-line function**, feeding nine downstream consumers.

**The error policies are the strongest argument for splitting.** Twelve different failure
behaviours in one body means the policy for any given stage can only be understood by
reading the whole function, and a change to one stage's handling sits textually adjacent to
eleven others it must not affect. Extracted, each stage's policy is stated once, next to
the thing it governs — which is also what makes them individually testable, currently
impossible without driving all twelve.

**The linear form's real virtue is preserved, not lost.** Stage order matters here, and
that was the case for leaving it alone. An outer orchestrator makes the sequence *more*
visible, not less: twelve named calls in order is a clearer statement of the pipeline than
twelve inlined blocks separated by comments.

**Spec consequence:** the specification prescribes the decomposed shape, with the stage
list as the orchestration contract. This matters because the spec documents each stage
already — the code should have the same structure the description does.

---

# avl-integration

## Q-AV-1 — Is there an AVL output flag that should replace the inferred convergence?

**Context:** `trim_with_avl` declares `converged = ("CL" in raw)` — a partially
converged AVL run that still printed coefficients is reported as **converged**.
**Spec affected:** [`_reversa_sdd/avl-integration/requirements.md`] (BR-AV19, RF-34)
**Question:** Is there a genuine flag in AVL's output that should be parsed
instead?
**Impact:** RF-34 is the module's only `Must (open)` — a partial run currently
reports success.

**Answer:** _(resolved by code lookup — not a maintainer decision)_ **Yes — AVL prints the literal `Trim convergence failed` on stdout; and the current inference is not merely weak but **inert**, because a non-converged run writes no stability file at all, so `converged = ("CL" in raw)` is unreachable-false.**

The marker is written by the Newton loop's failure branch (`Avl/src/aoper.f:1298-1319`), whose criterion is the maximum update over α, β, the three normalised rates and every control deflection below `EPS = 2e-5` rad (`:935-936`); on failure `LSOL = .FALSE.` gates every output command, so the `ST` command this wrapper uses prints the second marker `* Execute flow calculation first!` and writes nothing (`:594-611`). The runner therefore raises `FileNotFoundError` (`app/services/avl_runner.py:347-356`), which `app/services/avl_trim_service.py:125-132` maps to `InternalError` → **HTTP 500** telling the user to "check avl_command and input geometry" for what is actually a user-fixable ill-posed variable/constraint system — and the `if not trimmed.converged` warning at `:136-141` is dead code. Both markers are on stdout, which the runner already captures and uses only for strip forces and the error hint (`avl_runner.py:333`), so no new plumbing is needed: parse them, return convergence as a first-class field, and map a non-converged trim to a **422** with the AVL message. RF-34 should be respecified as "parse the stdout markers", not "strengthen the inference". One latent hazard: with a reused `working_directory` (`avl_runner.py:102,109,305-312`) a stale `output.txt` would be parsed as the current result and the flag would return `True` for a failed run — no production code passes it today.

**Verdict:** confirmed defect — and the fix is available.

_Full detail: [`wave3-lookups.md`](wave3-lookups.md) §R_

---

## Q-AV-2 — Is the wing-only AVL model an accepted limitation?

**Context:** `AvlBody` / `BFIL` is implemented in the emitter and **nothing
constructs one**, so every AVL run is wing-only. Fuselage contributions to `Cnb`
and drag are absent from AVL results while AeroBuildup does model them — so the
two solvers disagree by construction on directional stability.
**Spec affected:** [`_reversa_sdd/avl-integration/requirements.md`],
[`_reversa_sdd/traceability/spec-impact-matrix.md`] (the `FD → AV` ◐ cell)
**Question:** Accepted limitation, or a gap?
**Impact:** A user comparing the two solvers has no explanation for the
divergence.

**Answer:** **ANSWERED by the maintainer, 2026-08-15** (options a + b) — **the wing-only AVL model is an accepted and correct limitation. `AvlBody` / `BFIL` is never constructed; AeroSandbox is the sole authority for `Cnb`. Separately, the missing centre-section carry-through is recorded as a defect.**

_Verified by the domain experts against the **AVL 3.40 Fortran source**, not only the user primer._

**① Why AVL's `BODY` is not the answer — three findings from the source.**

- **The body never participates in the solve.** Source and doublet strengths are *prescribed from the onset flow* (`src/asetup.f:418-423`) and feed the wing lattice one-way; the body never responds to wing-induced flow. Nothing is gained over a closed-form calculation from the volume distribution.
- **An AVL body has essentially zero drag by construction.** The force is purely normal to the local axis, so for an axis-aligned body `UN(1) ≡ 0` and `CDBDY = 0` at α = 0 (`src/aero.f:1346-1365`). No skin friction, no form drag, no base drag.
- **Drela flags it as unvalidated.** *"the experience with this model is relatively limited… If a fuselage is expected to have little influence on the aerodynamic loads, it's simplest to just leave it out"* (`avl_doc.txt:110-118`), and the version notes add *"It's not yet clear how useful this modeling capability will be."* The path also carries bug history — one fixed force-summation defect, and a still-visible commented `BUG 5 Dec 10` at `src/aero.f:1409`.

**② AeroSandbox already implements a strict superset.** `AeroBuildup.fuselage_aerodynamics` uses the **same** slender-body theory (Drela, *Flight Vehicle Aerodynamics* Eq. 6.77/6.78) and adds **Jorgensen cross-flow**, **skin friction with form factor** and **base drag** — the three things AVL's body lacks entirely. Non-degenerate fuselages are already in the ASB airplane (`app/converters/model_schema_converters.py:824`), with degenerate ones skipped deliberately (gh-790). **Building `BODY` would create a second producer of `Cnb` — ADR 0022 — while adding no physics.**

**③ The physics, and why the two solvers must not be reconciled.** The fuselage's yaw contribution is the **Munk moment**: a potential-flow couple proportional to body **volume**, containing no circulation anywhere. A vortex-lattice solution space is spanned entirely by vorticity, so the term has no basis function to live in — this is a *structural* absence, not a resolution problem, and refining the lattice cannot recover it. The omission is **one-signed**: AVL's `Cnb` is always too optimistic, never conservative.

At RC/UAV scale the fuselage is **13–27 %** of the `Cnb` magnitude (central ≈18 %), so omitting it overestimates `Cnb` by **18–57 %**. It **cannot flip the sign** — that would need a fuselage volume ~2.7× a solid cylinder of the maximum width. **Exception:** below `V_v ≈ 0.008` (flying wing with vestigial fins) the sign genuinely can flip, and there the correction is not optional.

**Contract consequence:** AVL computes *"`Cnb` of the lifting surfaces"*, ASB computes *"`Cnb` of surfaces + body"*. These are **not two estimates of one number** and must never be averaged, blended or reconciled. ASB is the authority (**ADR 0022**); the *gap between them* is a useful diagnostic ≈ the fuselage term. It becomes a defect in exactly two cases: presenting AVL's number unqualified as "directional stability", or **silently falling back** to AVL when ASB is unavailable — which requires a `DesignWarning`, severity **defect**, because the substitute is wrong in a known direction (**ADR 0020**).

**④ Rejected — the primer's own alternative.** `avl_doc.txt:528-530` suggests modelling the fuselage as crossed `SURFACE` blocks with `NOWAKE` from its side and top profiles. **The aerodynamics authority overrules the tool primer here:** a lifting-surface substitute produces a real side *force with a centre of pressure* where the truth is *zero force plus a couple*. Matching `Cnb` that way is calibration, not physics, and it fails to track with fineness ratio because the true term scales with **volume** and the substitute with **area**.

**⑤ The defect this question uncovered (option b).** The primer makes it a hard requirement, not advice: when the fuselage is omitted, *"the two wings should be connected by a fictitious wing portion which spans the omitted fuselage"* (`avl_doc.txt:117-118`). Without it, `CL` is under-predicted, `Sref` bookkeeping is wrong, and the artificial gap in the spanload corrupts `CDi` **and** the reported `e = (CL²+CY²)/(π·A·CDi)`. **Action taken — measured 2026-08-15, and the result reframes the defect.**
`_build_surface` sets `yduplicate=0.0` for symmetric wings (`avl_geometry_service.py:162`)
and builds the surface directly from its cross-sections. Where the root sits on the
centreline, mirror and original meet there and no gap exists.

Measured over the live database — **74 of 82 wing roots sit on `y = 0`; 8 do not**:

| surface | `y_root` | chord | reading |
|---|---|---|---|
| `Verts-Full` ×2 | 1.529 m | 0.255 m | deliberately off-centre |
| `Struts` ×2 | 0.533 m | 0.130 m | deliberately off-centre |
| `Strut_MainGear` ×2 | 1.419 / 0.244 m | 0.183 / 0.031 m | deliberately off-centre |
| **`Wing` ×2** | **−0.205 m** | **4.0 m** | **surface crosses the centreline** |

For struts and vertical surfaces the offset is structural, `YDUPLICATE` is correct, and a
carry-through would be **wrong** — the primer's case does not apply. So the missing
carry-through is *not* the defect this codebase has.

**The real defect is the opposite one.** A **negative** root `y` means the surface crosses
the centreline, so mirroring makes it **overlap itself** — here by 0.41 m. That is not a
missing centre section but a **doubled** one, and it silently inflates `Sref`, corrupts
`CDi` and therefore falsifies the reported `e = (CL²+CY²)/(π·A·CDi)`, with no warning
anywhere.

**The invariant AVL geometry generation needs is therefore `y_root ≥ 0` for any surface
carrying `YDUPLICATE`** — asserted at build time, emitting a `DesignWarning` of severity
**defect** (ADR 0020) naming the surface and the overlap width. The primer's
carry-through rule stays recorded as the *other* half of the same invariant, applying only
when a genuine gap exists.

_Both affected rows have 4 m chord, i.e. they come from an imported full-scale model rather
than an RC design — consistent with the OpenVSP import scope, and a reminder that imported
geometry reaches the AVL path unvalidated._

---

## Q-AV-3 — Was the replay-artefact wiring lost, or is it staged?

**Context:** `avl_artefact_service` implements the full gh-529 semantics —
`compute_geometry_hash` (deliberately excluding coordinates), `build_artefact`,
`verify_avl_replay` returning `AvlReplayMismatch` — and **no production path
persists or checks an artefact**. The spec is explicit that a non-`None` result
must be treated as a hard failure, because replaying against drifted geometry
produces silently mis-mapped surfaces.
**Spec affected:** [`_reversa_sdd/avl-integration/requirements.md`] (BR-AV20, RF-30)
**Question:** Was the wiring lost, or is it staged for a future replay feature?
**Impact:** A complete safety mechanism sitting unused.

**Answer:** **ANSWERED by the maintainer, 2026-08-15, together with `Q-AV-4` — see there for the full decision.** In short: **the wiring was neither lost nor staged — it is withdrawn.** AVL prints the surface name in every output block, so the index map is parsed per run instead of cached, and the geometry-hash artefact (`build_avl_artefact`, `verify_avl_replay`, `compute_geometry_hash`, `AvlReplayMismatch`) is deleted as complete-but-unreachable (ADR 0021). `get_control_surface_index_map` is **live** and stays; `build_yduplicate_sign_map` is held pending the mirrored-sign defect investigation.

_Original deferral note:_

**The question was mis-framed and is reframed here.** "Replay" is not a planned future
feature: the module docstring states an `AvlArtefact` captures the **surface-index
map**, run state and a geometry hash "so downstream tools (**spar-load sizing**, AVL
re-runs at a converged trim point) can validate that the underlying airplane geometry
hasn't drifted out from under them". AVL returns results by **surface index**, not by
name, so any reuse of an AVL result after a geometry change can silently attribute
strip forces to the wrong surface — and those forces reach the spar sizing through
`/spanwise_loads_with_sizing`.

**The reuse path already exists**, so the drift scenario is not hypothetical:
`avl_geometry_files` persists generated `.avl` files with an `is_dirty` flag. Whether
that flag is maintained correctly is exactly what **`Q-AV-4`** asks. The two are front
and back of one question — *when may a stored `.avl` be reused?* — and deciding one
without the other would settle half a mechanism.

> **⚠ CORRECTION, 2026-08-15 — this paragraph previously said the index mapping was
> "called only from tests, so as unwired as the artefact itself." That was wrong, and
> the truth cuts the other way.** Re-measured directly:
>
> | symbol | production callers | status |
> |---|---|---|
> | `get_control_surface_index_map` | `avl_trim_service.py:134` (inside `trim_with_avl`), `avl_strip_forces.py:216` (`build_indirect_constraint_commands`) | **live** |
> | `build_yduplicate_sign_map` | only from within `avl_artefact_service` | unreached |
> | `build_avl_artefact` | none | unreached |
> | `verify_avl_replay` | none | unreached |
>
> **The index mapping is already load-bearing.** Every AVL trim maps control-surface
> names to AVL indices today, so index correctness is not a hypothetical that arrives
> with a future replay feature — it is relied upon on the live trim path, *without* the
> artefact's hash check guarding it. That makes `Q-AV-3` more urgent, not less.
>
> **A second finding falls out of the same measurement:** `build_yduplicate_sign_map`
> exists to give strip forces the correct sign across a `YDUPLICATE` mirror, and it is
> reachable **only** through the unreached artefact service. So the live strip-force
> path takes the index map but **not** the sign map. Whether that is correct — or whether
> mirrored-surface strip forces are being summed with a wrong sign into spar loads —
> is a defect question in its own right and is carried into the expert consultation.

The original premise of this question is otherwise confirmed: **no production path
persists or verifies an artefact.**

**`Q-AV-4` is lifted out of the deferred Tier 2 set for this reason** and decided
together with this question.

---

## Q-AV-4 — Should a successful regenerate clear `avl_geometry_files.is_dirty`?

**Context:** `is_dirty` is set by the geometry listeners and cleared **only** by
a user `PUT` or an explicit `POST …/regenerate`. After any geometry edit the
stored user-edited file is therefore bypassed permanently until the user
intervenes.
**Spec affected:** [`_reversa_sdd/avl-integration/requirements.md`] (BR-AV22, RF-32)
**Question:** Intended (force an explicit re-save), or should a
regenerate-and-compare clear it automatically?
**Impact:** The user-editable geometry escape hatch silently stops taking effect.

**Answer:** **ANSWERED by the maintainer, 2026-08-15** (option a, decided together with `Q-AV-3`) — **the index map is never cached: it is parsed from AVL's output on every run. The geometry-hash artefact is not wired up; it is withdrawn. A successful regenerate clears `is_dirty` automatically.**

**The question's premise was wrong, and correcting it dissolves the problem.** `Q-AV-3` was built on *"AVL returns results by surface index, not by name."* Verified against the source: **AVL prints the surface name alongside the index in every output block.** `STITLE(N)` is the trailing field of each `FN` line (`src/aoutput.f:168-174`, format `I2,1X,F9.3,8F8.4,3X,A`), appears in `FS` (`:290-323`) and has its own line in the machine-readable `STRP` block (`src/aoutmrf.f:273-278`). **The index → name mapping is recoverable from every single result file.** A caller never needed to persist one.

**Decision: parse, don't cache.** A map that is never stored cannot go stale, and the entire class of drift bugs disappears by construction rather than by a check. This is the same argumentative shape as ADR 0019's airfoil merge — remove the possibility, don't guard it.

**Why a hash could not have been trusted anyway.** Had the artefact been wired, `compute_geometry_hash` covers wing order, xsec order and control-surface name/symmetric/hinge_point. Two edits leave that hash **intact while invalidating the index map**:

| edit | surface indices | strip numbering | hash sees it? |
|---|---|---|---|
| **`YDUPLICATE` toggled** | image inserted right after its parent → **every later index shifts ±1** (`src/amake.f:718`) | shifts | ❌ **no** |
| **`NSPAN` changed** | unchanged | `NJ(N)` changes → every later `JFRST` shifts → global strip index **renumbers silently** | ❌ **no** |
| control surface added | unchanged | unchanged | — but the **control** map breaks: `d(t)` components are keyed by declaration order (`avl_doc.txt:2309-2310`) |
| section coordinates only | unchanged | unchanged | (deliberately excluded) |
| `NCHORD` only | unchanged | unchanged (affects `FE` elements, not `FS` strips) | — |

A sufficient hash would have needed name, file position, `Nchord`, `Cspace`, `Nspan`, `Sspace`, every per-section `Nspan`/`Sspace`, the `YDUPLICATE` flag **and** the control-name list in declaration order. Parsing two fields from the output is cheaper and cannot drift.

**`is_dirty` now clears on a successful regenerate.** The escape hatch was silently failing: `is_dirty` is set by the geometry listeners (`avl_geometry_events.py:26`) and cleared only by a user `PUT` or an explicit `POST …/regenerate` (`avl_geometry_service.py:327, 349`), while `get_user_avl_content` returns `None` whenever the flag is set (`:354-365`). So after **any** geometry edit the user-edited file was bypassed **permanently** until the user intervened — the feature stopped taking effect without saying so, which is exactly the undeclared behaviour **ADR 0020** forbids.

**Disposition of the artefact service (`P-DEAD-0` / ADR 0021):** `build_avl_artefact` and `verify_avl_replay` have **no production callers** — measured 2026-08-15 — and under this decision they never will. They are complete-but-unreachable and are **deleted**, together with `AvlReplayMismatch` and `compute_geometry_hash`.

**Not deleted: `get_control_surface_index_map`.** It is **live** on the trim path (`avl_trim_service.py:134`) and in `build_indirect_constraint_commands` (`avl_strip_forces.py:216`). **`build_yduplicate_sign_map` — RESOLVED, delete it** (**RESOLVED 2026-08-15 — the premise was wrong, and the disposition flips to *delete*.**)

**RESOLVED 2026-08-15 — the premise was wrong, and the disposition flips to *delete*.**

`build_yduplicate_sign_map` has nothing to do with strip forces. Its own docstring states
what it maps: control-surface **names → `SgnDup`**, the sign factor on the **CONTROL card**
of the `.avl` file — an *input* to AVL, not a correction applied to *output* strip forces.

This matches the AVL 3.40 source exactly: **no per-surface sign must be applied to
forces.** AVL consumes `IMAGS` internally wherever it matters — strip `cm_LE` direction
(`src/aero.f:919-923`), the surface hinge/LE moment reference (`:1063-1071`), root/tip
identification in the `VM` shear-bending output (`src/getvm.f:88`) — so `CLsurf`/`CDsurf`
and strip `cl`/`cd`/`cm` arrive **already in the aircraft frame with correct sign**. The
only genuine per-surface flip is on **input**: the image's hinge axis has its Y component
reversed, which is precisely what `SgnDup` encodes (+1 elevator, −1 aileron).

**And `SgnDup` is already emitted from the right authority.** `app/avl/geometry.py:83`
writes it onto every `CONTROL` line, fed from `avl_geometry_service.py:138` ←
`axis.sgn_dup` ← **`control_surface_mixing.py:45`**, where the field carries its own
warning: `# +1 symmetric, -1 antisymmetric (NEVER a differential magnitude)`. The mixing
layer — the same layer `Q-WD-1` makes the owner of canonical control names — sets it
explicitly at three sites.

**Disposition: `build_yduplicate_sign_map` is a second producer of a quantity the mixing
layer already owns, reachable only through the deleted artefact service. Delete it with
the rest** (ADR 0022 — one authority; ADR 0021 — complete but unreachable). Nothing is
held pending investigation.

*The original R1 wording — "the live strip-force path takes the index map but not the
sign map, so mirrored forces may be summed with a wrong sign into spar loads" — was a
misreading. Recorded rather than deleted, because the reasoning that produced it was
sound and only the object was wrong.*

_Original framing:_ **it was the open item** — its only reference is from the unreached artefact service, so the live strip-force path takes the index map but **not** the sign map. Whether mirrored-surface forces are therefore summed with a wrong sign into spar loads is carried forward as a separate defect investigation; it must be resolved **before** deleting the function.

**Two operational notes for the implementation.** Prefer the **`MRF`** machine-readable output (`src/aoper.f:103, 693-698`) — it is `ES23.15`, whereas the text `FN` format is `F8.4` and quantises small RC-scale coefficients; `MRF` is absent from the primer. And **parse the axis-orientation line**: `LSA` flips the sign of `Cl` and `Cn` on output via `DIR = ∓1` (`src/aoutput.f:1669-1675`), and it is printed at the head of every `FN`/`FS`/`FB` block. Per-surface force signs need **no** correction — AVL applies `IMAGS` internally.

---

## Q-AV-5 — Should a CDCL surface/wing count mismatch be a hard error?

**Context:** `inject_cdcl` walks surfaces and sections **in parallel index
order**; a count mismatch only logs a warning and truncates the loop, leaving
later sections with zero CDCL — i.e. **no viscous drag** on those sections.
**Spec affected:** [`_reversa_sdd/avl-integration/requirements.md`] (BR-AV10)
**Question:** Should a mismatch raise instead?
**Impact:** Silently incomplete viscous modelling is exactly the failure class
ADR 0012 targets.

**Answer:** _(derived — not a maintainer decision)_ **No silent truncation: a surface/section count mismatch emits a `DesignWarning` (`result_truncated`, severity `error`) and the run must not be presented as a valid viscous result.**

Follows from **P-WARN-0**: "`inject_cdcl`'s truncating loop" is named in the policy's own list of violations, and `result_truncated` is one of its six mandated categories. Sections left with zero CDCL carry no viscous drag at all, which places the outcome in the `error` band ("do not build on it"); raising instead is compatible with the policy — continuing silently is not.

---

## Q-AV-6 — Is a user's `.avl` edit expected to be ignored for single-wing runs?

**Context:** `analyze_airplane`, `trim_with_avl` and the full-airplane
strip-force path honour a user-edited stored `.avl`; `analyze_wing` and the
single-wing strip-force path **never** consult it — they prune the airplane to
one wing and always build fresh.
**Spec affected:** [`_reversa_sdd/avl-integration/requirements.md`] (BR-AV23)
**Question:** Deliberate, given the pruning, or an inconsistency?
**Impact:** A user who hand-tuned their `.avl` gets it applied on some routes and
not others, with no indication.

**Answer:** _(expert consensus, endorsed by the maintainer 2026-08-14)_ **It is an inconsistency, not a defensible design — but the fix is a merge, not a swap: lift the matching `SURFACE` block verbatim and always regenerate the header from the pruned wing.**

The AVL 3.40 primer splits the file exactly along the line that decides this. **Global header, before any `SURFACE` block** (`avl_doc.txt:243-289`): `Mach`, symmetry, **`Sref Cref Bref`**, **`Xref Yref Zref`**, `CDp` — and the primer is explicit that *"Sref and Bref are assumed to correspond to the total geometry"* (`:289`) and that *"if doing trim calculations, XYZref must be the CG location"* (`:272-274`). **Per-`SURFACE`/`SECTION`** (`:305-940`): `Nchord Cspace Nspan Sspace`, `COMPONENT`, `YDUPLICATE`, `SCALE`, `TRANSLATE`, `ANGLE/AINC`, `NOWAKE`, `NOALBE`, `NOLOAD`, **`CDCL`**, `CLAF`, `CONTROL`, `NACA`/`AIRFOIL`/`AFILE`, `DESIGN`. So a hand-edited full-airplane file genuinely **cannot** be reused for a single-wing run by deleting surfaces — the coefficients would still be normalised against whole-aircraft `Sref/Cref/Bref` and moments taken about the aircraft CG, producing numbers that look like wing coefficients and are not (the same `P-WARN-0` failure shape as the VSPAERO benchmark's "`s_ref` from the first wing → 8× wrong coefficients"). **But that argument only justifies rewriting the header**, not discarding the per-surface edits, which are precisely the edits AVL's own primer instructs the user to make: *"Spacing should be bunched at dihedral and chord breaks, control surface ends, and especially at wing tips"* (`:1100-1108`), refinement in both directions (rule 4, `:1121-1130`), adequate `Nchord` to resolve the hinge-line kink (rule 3, `:1110-1119`).

Concretely, for `analyze_wing` and the single-wing strip-force path: **(1)** parse the stored user `.avl` and lift out the `SURFACE` block matching `wing_name` verbatim — spacing, `CDCL`, `CLAF`, `CONTROL`, section airfoil references, `ANGLE`, `YDUPLICATE`; **(2)** always regenerate the header from the pruned wing (`Sref/Cref/Bref` from that wing alone, `Xref/Yref/Zref` from the request's `xyz_ref`), never inheriting the aircraft header; **(3)** if the named wing has no matching `SURFACE` block, fall back to the generated file and emit a `DesignWarning` (`input_ignored`) naming what was dropped; **(4)** report `avl_source: "user_surface+generated_header" | "generated"` either way — today the user cannot tell, and that silence, not the pruning, is the actual complaint. **Acceptable minimum** if (1)–(2) is judged too much work: **(3) and (4) alone**. Silence is the one option not acceptable under ADR 0012. At RC scale `CDCL` is the edit most likely to have been made and the one whose loss hurts most — AVL is inviscid and Reynolds-blind except through hand-entered `CDCL` (`:547-580`, `:909-940`), so at Re 50 k–500 k it is the difference between a drag number and no drag number; **preserving `CDCL` outranks preserving the spacing parms**.

**Authority:** `avl-advisor` (AVL 3.40 primer `avl_doc.txt:243-289`, `:272-274`, `:289`, `:1100-1130`, `:547-580`) — sole authority on the file format, unambiguous in both directions.
**Confidence:** high. Note that this project's standing preference for AeroSandbox over AVL caps the item's priority — it affects a secondary analysis route.

_Full reasoning: [`expert-consensus-aero.md`](expert-consensus-aero.md)_

---

## Q-AV-7 — Should a missing AVL binary be reported as a service-level error?

**Context:** `_resolve_default_avl_command` falls back through the `avl_binary`
wheel's `avl_path()` → `shutil.which("avl")` → the bare string `"avl"`. When the
wheel is absent and `avl` is not on `PATH`, the failure surfaces only as a
`FileNotFoundError` from `Popen`, deep inside a run.
**Spec affected:** [`_reversa_sdd/avl-integration/avl-run-and-parse/requirements.md`] (BR-AV11)
**Question:** Should the missing binary be detected and reported as a clean
capability error, the way CadQuery and AeroSandbox are (ADR 0017)?
**Impact:** AVL is the one heavy dependency with no capability probe.

**Answer:** _(derived — not a maintainer decision)_ **Yes — probe for the AVL binary and report its absence as a clean capability error, the way CadQuery and AeroSandbox are handled.**

Follows from **P-WARN-0** (with ADR 0017): `capability_unavailable` is one of the six mandated categories, and the present chain — `avl_path()` → `shutil.which("avl")` → the bare string `"avl"` — is an undeclared fallback whose only symptom is a `FileNotFoundError` from `Popen` deep inside a run. The capability is resolved and declared up front instead, so AVL stops being the one heavy dependency without a probe.

---

## Q-AV-8 — Was file-based `.mass` / `.run` input deliberately dropped?

**Context:** No `.mass` or `.run` files are ever produced. Mass properties reach
AVL through the `OPER → m` keystroke submenu (`mn`, `v`, `d`, `g 9.81`) and run
cases through keystrokes.
**Spec affected:** [`_reversa_sdd/avl-integration/requirements.md`] (MoSCoW `Won't`)
**Question:** Deliberately dropped, or a gap for eigenmode / dynamic analysis?
**Impact:** Confirms the module's scope boundary.

**Answer:** **ANSWERED by the maintainer, 2026-08-15** (option b) — **`.mass` / `.run` stay out for now. The two dynamic results that matter at this scale are shipped instead, both of which are free. File-based input is deferred behind a real precondition: a per-component mass model with positions.**

**What is actually lost without the files: exactly one capability — eigenmodes.** And that is the one thing AVL does that AeroSandbox does not. ASB's `get_modes` computes **decoupled analytic approximations** from `Ixx`, `Iyy`, `Izz` only — no `Ixz`, no full A/B matrix, no apparent mass — and its own test fixture concedes the limit (`"spiral": -0.0573, # Too small, get_modes says -0.17`, a ~3× error). AVL's `MODE` solves the full 12-state system including `Ixz` cross-coupling. **Products of inertia `Ixy`/`Iyz`/`Izx` are reachable *only* through a `.mass` or `.run` file — no keystroke exists** (`src/amass.f:343-345`).

**But three of the five modes are non-issues at 0.5–15 kg, and now we can say so with numbers** (3 kg reference airframe):

| mode | value | requirement | margin |
|---|---|---|---|
| Roll subsidence | `T_R` = 0.07 s | ≤ 1.0 s | **×14** |
| Dutch roll | ω = 5.0 rad/s, ζ = 0.115 | ζ ≥ 0.08, ω ≥ 0.4 | **×1.4 – ×12** |
| Short period | ω = 7.4 rad/s | — | **above human pilot bandwidth** (~2–3 rad/s) |

Dutch roll is a transport problem *because* it is a transport problem: its three causes are a large fin, a long fuselage (high `Izz`) and wing sweep. A 3 kg RC aircraft has none of them.

**The spiral is the exception, and it is the reason for this decision.** All mode times shrink with √λ, but the requirements are written in **absolute seconds** — so a *minimum*-time requirement like the spiral's `T₂ ≥ 20 s` gets **harder** as the aircraft shrinks, while every maximum-time and minimum-frequency requirement gets easier. This matches field experience exactly: an RC model left in a bank tightens up in seconds.

**And its criterion costs nothing.** `|C_lβ·C_nr|` vs `|C_lr·C_nβ|` is **inertia-free** — all four derivatives fall out of a VLM run already performed. Result for the reference airframe: neutral spiral needs **~6–7° dihedral**. RC trainers are built with 5–10°; that is this equation, not tradition.

**Two independent sources converge on the spiral**, which is why it is worth shipping: Scholz via the derivative product, and RC practice via Lennon's **Spiral Stability Margin** — the CG-to-CLA distance as a fraction of the fin moment arm, using the whole-aircraft side-view centroid (22 % super stable / 25 % good / 28 % neutral / 30 % mild / ≥33 % very unstable). Both are geometry-and-derivative only. **Implement both and let them cross-check; a disagreement between them is itself a usable signal.**

**Ship now (no new user input required):**
- **Spiral:** stability sign plus the margin ratio, presented as a design warning with a dihedral recommendation — *"spiral divergent; increase dihedral to ≥7° for neutral"* — not as a bare number.
- **Phugoid:** `ω = √2·g/U₁`, `ζ ≈ 1/(√2·L/D)`, flagged as the Lanchester approximation. Both inputs already exist in the cruise operating point. Warn when `ζ < 0.04` — which fires for clean high-L/D soaring UAVs and stays silent for draggy sport models. Correct in both cases.

**Deferred behind a genuine precondition (the substance of option b):** short period, roll subsidence and dutch roll are computed **only** when a per-component mass model with positions exists and the inertia tensor is built from it. **If the mass model is a single lumped mass, refuse rather than guess** — a factor-2 error in `I_yy` is a 41 % error in both ω and ζ, wider than the entire specification band, and substituting a guessed inertia to keep a feature alive is precisely the undeclared fallback **ADR 0020** forbids. Per **ADR 0021** the code is not shipped inert either: the precondition *is* the feature gate.

**Three traps recorded for whenever `MODE` is wired.**
1. **Without a `.mass` file, `g` and `rho` default to `1.0`** — not 9.81 / 1.225 (`avl_doc.txt:1264-1266`). Eigenvalues then emerge in a nonsense unit system **with no warning**. Assert on `g` and `rho`; AVL already guards `V`, mass and the diagonal inertias (`src/amode.f:844-875`).
2. **AVL adds apparent air mass and inertia itself** (`src/amode.f:889-897`). At 0.5–2 kg the entrained air is a non-negligible fraction of airframe mass, so the supplied `Ixx/Iyy/Izz` must **not** pre-include it — doing so double-counts. This is an RC-scale trap with no transport-scale analogue.
3. **`Ixy` sign convention differs between the two file formats.** `.mass` takes raw products `∫xy dm`; AVL stores the **negated** tensor elements (`src/amass.f:294`), and `.run` carries the already-negated values. Anything generating `.run` directly must use the run-file convention.

> **⚠ Follow-up, 2026-08-15 — this decision was made on an incomplete premise and should
> be re-weighed.** The "three of five modes are non-issues" conclusion describes the
> **free-decay** response to a single gust. The maintainer, an FPV pilot, reports from
> experience that dutch roll is genuinely objectionable in flight — and on **flying wings**
> permanently so, as a configuration defect rather than a gust response. Both are correct:
> in gusty low-altitude air the mode is **continuously re-excited** and never settles, so ζ
> governs *sustained amplitude* rather than decay time, and the mode acts as a narrow-band
> resonant filter on the turbulence spectrum.
>
> A second point cuts against the "above pilot bandwidth" argument used for the short
> period: a flying wing's dutch roll sits at **ω ≈ 2.4 rad/s, inside** the ~2–3 rad/s human
> crossover, so the pilot *can* couple with it — *"sonst reagiert man mit dem Knüppel gegen
> und verschlimmert die Situation"*. That is a **frequency** problem, not a damping one,
> and it is why MIL-F-8785C specifies ζ, ζ·ω and ω separately.
>
> **Actionable today, no new data:** `|Clb/Cnb|` is a dutch-roll coupling indicator and
> both derivatives are already computed and stored (`stability_service.py:325-326`;
> 13 rows in the live DB, spanning 0.59 for a Cessna 172N to **negative `Cnb`** — outright
> directional instability — on two stored designs). See
> [`dutch-roll-visualisation/README.md`](dutch-roll-visualisation/README.md) for the full
> proposal, the measured spread and the staged plan. **`Q-AV-8`'s option (b) may deserve
> re-weighing:** AVL `MODE`'s eigenvector *is* the roll/yaw ratio and phase, so the
> justification for `.mass`/`.run` becomes "show the designer how the aircraft will
> behave", not "tune an autopilot".

**Never report a handling-qualities Level 1/2/3 verdict at this scale** without stating that those criteria assume a human pilot in the loop on aircraft ≥ 6000 kg — the short-period and dutch-roll modes here sit **above** human pilot bandwidth, so the thresholds are close to vacuous for a human RC pilot even where they are met (**ADR 0023**). For a UAV with an autopilot the conclusion inverts, and that is the trigger for revisiting option (c).

---

# mission-and-sizing

## Q-MS-1 — `power_to_weight` is W/kg in the catalogue and T/W-shaped in seven presets: which is canonical?

**Context:**

| Source | Value | Unit |
|---|---|---|
| assumption catalogue | default `220.0` | **W/kg** |
| `motor_glider`, `flying_wing` | `100.0` | W/kg (pinned by the gh-580/gh-582 tests) |
| the other seven presets | `0.0`–`1.4` | dimensionless, **T/W-shaped** |

Selecting `trainer` therefore declares a **0.5 W/kg** aircraft. Both the matching
chart's power-loading constraint and the `is_glider` test (`P/W ≤ 0`) consume the
value.
**Spec affected:** [`_reversa_sdd/mission-and-sizing/mission-objectives-presets/requirements.md`],
[`_reversa_sdd/mission-and-sizing/design-assumptions/requirements.md`]
**Question:** Which unit is canonical, and who backfills the seven wrong presets?
**Impact:** Seven of nine shipped presets currently seed a physically absurd
value into a sizing input.

**Answer:** **(a) W/kg is canonical; the seven T/W-shaped presets are re-authored.**
_Answered by the maintainer, 2026-08-13._

**Evidence for W/kg:** the assumption catalogue default (`220.0`), the two presets
pinned by the gh-580/gh-582 tests (`motor_glider`, `flying_wing` at `100.0`), and
the RC convention itself — power loading in the RC world is expressed in W/kg
(or W/lb). The seven outliers use T/W, the full-scale/jet convention.

**This is NOT a mechanical conversion.** T/W (a thrust ratio) and W/kg (specific
power) are not inter-convertible without propeller efficiency and airspeed. The
seven presets must be **re-authored with domain-sensible values**, not multiplied by
a factor.

**Consumers affected:** the matching chart's power-loading constraint and the
`is_glider` test (`P/W ≤ 0`). Selecting `trainer` today declares a **0.5 W/kg**
aircraft — a real trainer is roughly 100–150 W/kg — so the resulting matching chart
is meaningless.

**Follow-up:** replacement W/kg values per mission type are being derived from the
RC design references for the maintainer to sanity-check before they are seeded.
A data migration is required for existing rows.

---

## Q-MS-2 — Which landing-distance model should the UI trust?

**Context:** Two coexist with no cross-check: Roskam §3.4 on
`GET /field-lengths`, and the gh-477 energy balance published on the computation
context as `landing_field_length_m`. Related: two `t_static_N` sources — gh-548
migrated it into `mission_objectives` (read by the field-length endpoint) while
the design assumption of the same name still exists and is still read by the
matching chart. They can disagree silently.
**Spec affected:** [`_reversa_sdd/mission-and-sizing/requirements.md`],
[`_reversa_sdd/mission-and-sizing/design-assumptions/requirements.md`]
**Question:** Which is authoritative in each case?
**Impact:** Two user-facing numbers with two producers each.

**Answer:** _(expert consensus, endorsed by the maintainer 2026-08-14)_ **The gh-477 energy balance is the authoritative landing distance at RC/UAV scale, and `mission_objectives.t_static_N` wins over the same-named design assumption.**

`field_length_service._compute_s_ldg_ground` (`app/services/field_length_service.py:233`) uses `K_LDG = 0.5847 · (μ_brake_hard/μ_brake)` multiplied by `_K_LDG_50FT = 2.73`, a constant its own docstring calibrates against a *Cessna 172N POH* (`:75-82`); `assumption_compute_service._compute_landing_field_length` (`:1797`) instead computes `s = 1.5 · (15 m + V_TD²/(2·g·μ_eff))` with `V_TD = 1.15·V_S0` and a per-surface `μ_eff`. Every element of the Roskam chain — the 50 ft obstacle, the 1.3 V_S approach, the CS-OPS 0.6/0.7 operator factor and Roskam's braked ground roll — is a **certification artefact with no counterpart at 0.5–15 kg**, where essentially no airframe has wheel brakes and many belly-land on grass. The decisive number: `K_LDG = 0.5847` is derived in the code from `μ_brake = 0.4`, a *braking* coefficient, while Sadraey Table 4.15 gives **rolling** friction of 0.03–0.05 (dry concrete), 0.05–0.1 (grass) and 0.1–0.3 (soft ground) — so an unbraked model decelerates at roughly a quarter of the assumed rate and Roskam's landing roll is structurally optimistic by ~4× before the 2.73 obstacle factor partly masks it. Worked example (1.5 kg trainer, S = 0.30 m², CL_max,ldg = 1.8): Roskam gives `s_ldg_50ft ≈ 35.5 m`, the energy balance on short grass gives **52.5 m — 48 % apart for the same aircraft, both labelled "landing distance"**.

Therefore: publish `landing_field_length_m` as *the* landing distance; keep Roskam §3.4 only for `ga_runway` mode (where its calibration is valid) or delete it, and have `GET /field-lengths` delegate its landing branch to the energy balance so one producer feeds both surfaces. The takeoff side is unaffected — Roskam's `_C_TO = 1.21` is a ground-roll energy constant, not a braking one. **Fix the touchdown-speed inconsistency while merging:** Roskam's path uses `V_TD = 1.3·V_S` and the energy balance `1.15·V_S0`; both are defensible at their own point in the trajectory (1.3 V_S is the *approach* speed at the 50 ft gate, 1.15 V_S0 the *touchdown* speed after flare) but they differ by (1.3/1.15)² = **1.28× in energy** — keep `V_TD = 1.15·V_S0` for the ground roll and `V_app = 1.3·V_S0` for the air phase, never one for both. On `t_static_N`, two arguments agree: gh-548 migrated it to `mission_objectives`, so the assumption row is the residue; and static thrust is a **propulsion/mission input** — measured, or produced by the powertrain model the app already owns — not a design assumption with an estimate/calculated duality. On the matching chart T/W is an *output* (the design point) and the aircraft's actual T/W is only the "Ist" marker, which must read the same `t_static_N` the field-length endpoint reads. Change `matching_chart.py:83` to read the mission objective and delete the `t_static_N` design-assumption row.

**Authority:** Sadraey Table 4.15 (rolling friction) and Eq. 4.31 (the stall-speed constraint he recommends for non-Part-25 aircraft); Scholz *05_PreliminarySizing* §5.1 / CS 25.125 / CS-OPS 1.515 for what the Roskam chain actually is; Scholz §5.8 (matching chart) for T/W as an output.
**Confidence:** high — the 48 % worked example is reproducible and the `μ_brake = 0.4` provenance is in the code's own docstring.
Disagreement: none between the authorities — Scholz/Sadraey and RC practice both point away from the certified-transport method at this scale; the conflict is between the code's two implementations.

_Full reasoning: [`expert-consensus-sizing.md`](expert-consensus-sizing.md)_

---

## Q-MS-3 — What is `LANDING_SURFACE_MU` calibrated against?

**Context:** Documented as coming from *"operational RC / UAV practice (Raymer
ch. 17 / Roskam P.7 territory)"*, explicitly **not** from a cited source. It is
the single largest lever on the landing answer, and it drives a user-facing
"field sufficient" verdict. The same applies to `_wcl_constraint`, which admits
in-code that Lennon's lb/ft^4.5 → SI mapping is *"a numerical stand-in awaiting
calibration"* and accepts a `g` parameter it never uses.
**Spec affected:** [`_reversa_sdd/mission-and-sizing/requirements.md`]
**Question:** Should these be validated against Raymer / Roskam before they drive
a verdict, and what is the intended calibration source for the WCL conversion?
**Impact:** Two numbers presented to the user as authoritative.

**Answer:** _(expert consensus, endorsed by the maintainer 2026-08-14)_ **`LANDING_SURFACE_MU` is a mean deceleration expressed in g, not a tyre friction coefficient — rename it and keep four of six values; the WCL conversion is wrong three separate ways and must become `W/S_max = (WCL[oz/ft³] · 9.818)^(2/3) · W^(1/3)`.**

**Part A — the friction table is defensible but mislabelled.** Sadraey Table 4.15 gives rolling friction of 0.03–0.05 (dry concrete), 0.04–0.07 (turf), 0.05–0.1 (grass), 0.1–0.3 (soft ground), so the code's `grass_short = 0.15` looks 1.5–3× too high and `belly_grass = 0.40` above any tyre-rolling value at all. What resolves it: `s = V_TD²/(2·g·μ_eff)` is constant-deceleration kinematics, so **`μ_eff` is `a/g`, not a friction coefficient**. The real balance is `m·a = D + μ_roll·(W − L)`, and aerodynamic drag plus residual wing lift are both first-order at RC scale and appear nowhere in the code — so `μ_eff = μ_roll + Δ_aero` with `Δ_aero ≈ 0.05–0.10` for a model rolling out with the wing still at high α. Read that way the existing numbers survive: `hard_paved` **0.10** (raised from 0.07 = 0.04 rolling + 0.06 aero), new `hard_paved_braked` **0.40**, `grass_short` **0.15** ✔, `grass_long` **0.22** ✔, `soft_soil` **0.30** ✔, `belly_grass` **0.40** ✔, `net_recovery` special-cased to `s_ground = 0` ✔. **Rename `LANDING_SURFACE_MU` → `LANDING_DECEL_COEFF`** (or document it as `a/g`): the present name invites a future reader to "correct" 0.15 down to Sadraey's 0.09 and silently make every landing 60 % longer. Raising `hard_paved` also matters because 0.07 makes paved the *longest* rollout of any surface — physically correct once brakes are absent, but so counter-intuitive it reads as a bug, so explain it in the UI and give the braked variant as the lever the user expects. Replace the fixed `_LANDING_FLARE_M = 15.0` — simultaneously too long for a 0.5 kg foamie at 6 m/s and too short for a 15 kg UAV at 20 m/s — with a scaling air distance **`s_air = h_obstacle · (L/D)_approach`**, `h_obstacle = 3 m` user-settable, `(L/D)_app` typically 5–8 (for the 1.5 kg trainer: 3 × 6 = 18 m, same order as today but now scaling). Keep the 1.5 safety factor and keep it user-visible.

**Part B — the WCL constant is genuinely wrong, three ways.** (1) `W/S^1.5` with W in oz and S in ft² has units **oz/ft³**, not `lb/ft^4.5`; no exponent arrangement produces ft^4.5. (2) `47.88` is the **lb/ft² → N/m² pressure** factor, the wrong dimension entirely; the correct factors are **1 oz/ft³ = 9.818 N/m³** (force form) or **1.0012 kg/m³** (mass form). (3) The derivation ignores weight and invents an AR dependence: from `WCL = W/S^1.5` and `S = W/(W/S)` it follows exactly that `W/S_max = WCL_SI^(2/3) · W^(1/3)` — **AR does not appear**, and the missing term is the aircraft *weight*, which is the entire point of a cube loading. Today's code returns **70.8 N/m² for trainer at AR = 7 for every aircraft regardless of mass** (while its docstring claims ~120 N/m², so the comment does not match the code either); the corrected formula gives 48.6 N/m² at 1.5 kg and 72.7 N/m² at 5 kg — i.e. the current constant is accidentally calibrated for a ~5 kg model and is ~46 % too permissive for a small one. Drop the unused `g` and the `ar` argument. Bands: glider/slope **6**, trainer **9** (raised from 6), sport/motor-glider **12** ✔, STOL/bush/scale warbird **15**, wing-racer/acro-3D **none**. The trainer raise is required: at 1.5 kg the corrected 9 oz/ft³ gives 48.6 N/m² = **49.6 g/dm²**, dead centre of the independent RC trainer band of 40–55 g/dm², whereas 6 oz/ft³ is the *glider* bound and would declare every real RC trainer infeasible. **Attribution correction:** the code credits WCL to Lennon, who covers wing loading in oz/ft² but not wing cube loading — WCL in oz/ft³ is Francis Reynolds' metric from the RC magazine literature and must be labelled as hobbyist material.

**Authority:** Sadraey Table 4.15 / *16_Sadraey* §4.3.4 (rolling friction); constant-deceleration kinematics and the glide-path relation `s_air = h/tan γ` for the flare; pure dimensional analysis for the WCL defects; RC practice (rcplanedesigner wing-loading bands; Francis Reynolds for WCL itself) for the oz/ft³ bounds.
**Confidence:** high for the WCL fix (dimensional analysis, verifiable without new data); medium for the friction table — the reinterpretation is sound and the values survive it, but no measured RC rollout exists to pin `Δ_aero = 0.06`.
Disagreement: WCL has no academic counterpart — Scholz/Sadraey have no cube-loading concept at all. That is a scope boundary, not a conflict: WCL is legitimate only as an RC-specific additive constraint (trainer and sport only, as `_PROFILE_CONSTRAINT_MAP` already scopes it) and must never be applied to a UAV profile.

_Full reasoning: [`expert-consensus-sizing.md`](expert-consensus-sizing.md)_

---

## Q-MS-4 — Is the `DEFAULT_E_OSWALD = 0.8` design warning implemented?

**Context:** The matching chart module documents that consumers *"should surface
a design warning rather than silently using this"* (gh-956), and the fallback is
reached whenever the context has no Oswald factor.
**Spec affected:** [`_reversa_sdd/mission-and-sizing/requirements.md`]
**Question:** Is that warning implemented at the endpoint or in the frontend, or
still open?
**Impact:** The same `0.8` fallback that ADR 0012 and gh-956 were written to
eliminate.

**Answer:** _(derived — not a maintainer decision)_ **The warning is mandatory, and its severity is already specified: `notice` when `0.8` substitutes for a non-converging low-Re fit, `warning`/`error` when it would mask `k ≤ 0` or an unphysical `e`.**

Follows from **P-WARN-0**, whose worked table classifies this exact fallback in two separate rows and makes the channel mandatory on every response whose numbers were degraded — so the requirement no longer depends on whether gh-956's intent was ever wired. Whether the warning exists today at the endpoint or only in the frontend is a verification step against the code, not a decision for the maintainer; `DEFAULT_E_OSWALD` may remain as a value, but never as a silent one.

---

## Q-MS-5 — Should `_grid_search_trim` search a deflection grid?

**Context:** `best_controls` is reset to `{}` on every improvement and returned
empty, so when the Opti stage fails the fallback trims by α/β/V alone and the
elevator stays at 0°. A target that needs a different deflection is unreachable
and is reported `NOT_TRIMMED` rather than "not reachable with the available
authority". The `Opti` failure log is also DEBUG-level, so a systematically
failing stage 1 — and the ~4× slower grid path it implies — is invisible in
production.
**Spec affected:** [`_reversa_sdd/mission-and-sizing/operating-point-sweep/requirements.md`]
**Question:** Should the fallback search a coarse deflection grid, or should the
point get its own status?
**Impact:** Silently mislabels an authority limitation as a solver failure.

**Answer:** _(expert consensus, endorsed by the maintainer 2026-08-14)_ **No deflection grid — the defect is rank deficiency, not resolution: restore the second degree of freedom with a two-point secant on δE, and give the point its own `CONTROL_AUTHORITY_LIMIT` status. Both.**

Longitudinal trim is Sadraey's 2 × 2 **linear** system (Eq. 12.86, closed-form Cramer solution at Eq. 12.90) in the two unknowns α and δE. It is not a search problem. Grid-searching α while holding δE = 0 solves a different, **over-constrained** problem: one free variable against `C_m ≈ 0` *and* `C_L ≈ C_L,target`. For any aircraft with `C_m0 ≠ 0` — i.e. any cambered wing; the FX 61-184 computed in Q-VI-8 has `c_m,c/4 = −0.165` — those two conditions are met at *different* α, so the score floor is bounded away from zero and the point is labelled `NOT_TRIMMED` **no matter how fine the α grid gets**. AVL confirms the shape of the correct answer: you do not search for elevator deflection, you constrain it (`D1 PM 0`) inside the same linear system (`avl_doc.txt:1534-1538`), and AVL ships no trim grid because none is needed; convergence failure there means the variable/constraint system is ill-posed (`:1553-1555`), which is exactly what the current fallback is.

**(a) Two-point secant on δE — preferred.** For each α already on the grid, evaluate at δE = 0 and at a probe `δ_probe = 5°`, then `δE* = −C_m(0)·δ_probe / (C_m(δ_probe) − C_m(0))`, clipped to the authority limit. Because `C_m` is **linear in δE** below hinge-line separation this is **exact in one step**, at exactly **2×** the current evaluation count versus ~7–11× for any grid worth having; add one refinement pass if `|C_m(δE*)|` still exceeds tolerance, which it will only for a stalled tail. **(b) If a grid is mandated anyway: δE ∈ [−25°, +25°] in 2.5° steps (21 values)** — the bound is Sadraey's ("maximum deflection ≤ 25° to avoid flow separation on the horizontal tail"; "if the required δ_E exceeds about 30°, the elevator must be enlarged or the tail arm extended"), so do not extend past ±25°: beyond that the *aircraft* is deficient, not the solver. 2.5° is the coarsest step whose residual sits below the pitch resolution an RC model is actually trimmed to (transmitter trim steps ≈ 0.5–1° of surface at a typical 4:1 horn/servo ratio). **(c) Three statuses, not two:** `TRIMMED` when `|C_m| ≤ 0.01` **and** `|C_L − C_L,target| ≤ 0.02` with `|δE| ≤ 25°`; **`CONTROL_AUTHORITY_LIMIT` (new)** when a solution exists but needs `|δE| > 25°` or hits the α limit — **carry the required δE in the payload** so the user sees how far short they are, because this is a design finding (enlarge the elevator, lengthen the tail arm) and under ADR 0012 it belongs in the response body, not a log line; `NOT_TRIMMED` only for numerical failure. **(d) Fix the tolerance:** with a typical RC tail volume `V_H ≈ 0.5` and `C_mδE ≈ −0.01/deg`, `ΔC_m = 0.01` is **1° of elevator** — the resolution a pilot trims at — whereas the current `best_score < 0.35` on a mixed-unit sum is ~35° equivalent, i.e. effectively no criterion at all. **(e) Raise the Opti-failure log from DEBUG to WARNING and count it**: a systematically failing stage 1 means every point silently pays the ~4× grid cost, and `max_runtime = 0.35 s` is a very tight budget for an IPOPT solve that rebuilds AeroBuildup each iteration — measure the failure rate before tuning it. RC-scale caveat: hinge-line separation tightens at Re 50 k–150 k, so ±20° is the honest RC authority bound — keep ±25° as the solver bound and flag anything above 20°. Known bias to record: AeroBuildup does not propagate main-wing downwash onto the tail, so tail effectiveness is somewhat over-estimated and the solved δE will be slightly small in magnitude.

**Authority:** Sadraey Eq. 12.86 / 12.90 (the 2 × 2 linear trim system) and the elevator-design principles (≤ 25° tail-separation limit, the 30° "enlarge the elevator" rule); `avl-advisor` (`avl_doc.txt:1534-1538`, `:1553-1555`) for trim as a constrained solve; AeroSandbox tooling for the downwash bias.
**Confidence:** high on the rank-deficiency diagnosis and on the secant step being exact; medium on the specific 2.5° / 0.01 / 5° numbers — defensible engineering choices calibrated as shown, not derived constants.
Disagreement: none. RC practice frames elevator authority as a *surface ratio* decision (trainer 25–30 %, sport 35–40 %, aerobatic 40–70 % of tail area) and offers no throw limits, so it neither supports nor contradicts the ±25° bound; AVL and Scholz agree that trim is a constrained solve.

_Full reasoning: [`expert-consensus-aero.md`](expert-consensus-aero.md)_

---

## Q-MS-6 — Should the OP store its trimmed CL so V-n markers land correctly?

**Context:** `_load_operating_point_markers` comments that "without stored CL, we
cannot derive actual load factor", so `turn_20/40/60` operating points plot on the
**1-g line** of the V-n diagram — exactly where they are not. The function even
accepts `mass_kg` and `wing_area_m2` for the calculation that was never written,
and the generator already knows `n_target` per target.
**Spec affected:** [`_reversa_sdd/mission-and-sizing/flight-envelope/requirements.md`]
**Question:** Should the OP store its trimmed CL (or `n_target`) so the marker is
placed correctly?
**Impact:** The V-n diagram currently shows turn points in the wrong place.

**Answer:** _(expert consensus, endorsed by the maintainer 2026-08-14)_ **Yes — persist both `n_target` and `cl_trimmed`; in a steady coordinated turn `n = 1/cos φ` exactly, so plotting `turn_60` at n = 1.0 is a factor-of-two error in the plotted quantity, not an approximation.**

`flight_envelope_service._load_operating_point_markers` (`:589`) sets `n = 1.0` for **every** operating point with the comment "Without stored CL, we cannot derive actual load factor", and accepts `mass_kg` and `wing_area_m2` that it then uses for nothing — while `operating_point_generator_service._build_target_definitions` (`:497`) **already computes** `n_target = round(1.0/cos(radians(bank)), 4)` and discards it after trimming. From force balance alone, `L·cos φ = W ⇒ n ≡ L/W = 1/cos φ`, so `turn_20 → n = 1.064`, `turn_40 → n = 1.305`, **`turn_60 → n = 2.000`**; independently `n = q·S·C_L/W` from the definition of the lift coefficient, so a stored trimmed `C_L` recovers `n` exactly and the two routes must agree to within the trim solver's residual. The turn markers exist for exactly one purpose — showing how close a manoeuvre gets to the g-limit — and placing them on the 1-g line deletes that purpose. Sadraey's `n_max` for a remote-controlled model is **1.5–2**, so a 60° turn at n = 2.0 sits **at or above** the load factor assigned to the entire model-aircraft class: precisely the finding the diagram should surface and currently cannot.

Persist both, because they answer different questions: **`n_target`** (the commanded load factor) is exact for the marker, already computed, and costs one column; **`cl_trimmed`** (the CL the solver converged on) lets `n` be re-derived at a different mass or density without re-running the sweep — which is what makes the marker survive a mass edit — and is the only way to detect that the trim solution disagrees with the commanded `n`, i.e. that the point did not actually achieve the turn. Marker placement rule: `n = q·S·C_L,trim/(m·g)` when `cl_trimmed` is present and the point is `TRIMMED`; otherwise fall back to `n_target`; otherwise 1.0 **with the marker flagged as unverified**, never silently. **This will expose a second, real defect — that is a feature.** The generator sets turn velocity to `max(cruise, 1.3·V_S)` (`:494`), but the stall boundary at load factor `n` is `V_stall(n) = V_S·√n`, so a 60° turn requires `V ≥ 1.414·V_S`; at `1.3·V_S` the `turn_60` point lies **inside the stall boundary** — a stalled turn, today hidden on the 1-g line where 1.3·V_S looks perfectly safe. Either raise the turn velocity to `max(cruise, 1.05·V_S·√n_target)` or let the marker land outside and rely on the existing `STALL_IN_TURN` warning — but that warning must then be emitted as a **bare token**, not the formatted sentence noted in Q-MS-12, so a consumer can match it.

**Authority:** force balance for the steady level turn (`n = 1/cos φ`) and Anderson §6.7.2 (`L = q·S·C_L`) for the equivalent `n = q·S·C_L/W`; Sadraey §10.4.1 (`n_max` = 1.5–2 for RC models) for the consequence.
**Confidence:** high — both relations are exact for the steady level turn, and the generator already holds the value.

_Full reasoning: [`expert-consensus-sizing.md`](expert-consensus-sizing.md)_

---

## Q-MS-7 — What is the intended marker → KPI mapping?

**Context:** `derive_performance_kpis` looks up markers labelled `best_ld`,
`min_sink` and `max_turn`, but `VnMarker.label` is the **operating point's name**
and the generator emits `max_range`, `loiter_endurance`, `turn_60`, … So the
`"trimmed"` KPI confidence tier is unreachable through the standard flow. A
marker's *status* is also not checked before the `"trimmed"` label is applied, so
a point named `best_ld` in state `NOT_TRIMMED` would be reported as trimmed.
**Spec affected:** [`_reversa_sdd/mission-and-sizing/flight-envelope/requirements.md`]
**Question:** A role field on the marker, or matching the context's `v_md_mps` /
`v_min_sink_mps` to the nearest point?
**Impact:** A whole confidence tier is dead.

**Answer:** _(expert consensus, endorsed by the maintainer 2026-08-14)_ **Add an explicit `role` field set by the generator — `best_ld` ← `max_range`, `min_sink` ← `loiter_endurance`, `max_turn` ← `turn_60` — and gate the `"trimmed"` tier on `status == TRIMMED` **and** being within 5 % of the polar's `v_md_mps`/`v_min_sink_mps`; nearest-match must be rejected.**

The mapping is decided by propeller physics, not by convention. For a propeller aircraft — which every airframe in scope is — **maximum range occurs at minimum drag**, i.e. maximum L/D, i.e. at `V_md`, so `best_ld` ← `max_range`; **maximum endurance occurs at minimum power required**, i.e. maximum `C_L^1.5/C_D`, i.e. at minimum sink speed ≈ `0.76·V_md`, so `min_sink` ← `loiter_endurance`; and `max_turn` ← `turn_60`, the highest-bank point generated. The prop-vs-jet distinction is why this is not arbitrary: for a jet the range point would sit at `V_md·3^0.25`. The project already uses the prop convention consistently — `mission_kpi_service` defines the `target_climb_energy` axis as `C_L^1.5/C_D`.

**Renaming alone would be the wrong fix.** The generator's speeds for those two points are heuristics, not polar solutions: `max_range` is `max(1.25·V_S, 0.95·cruise)` and `loiter_endurance` is `max(1.15·V_S, 0.80·cruise)` (`:448-461`). Mapping by name would promote a heuristic speed to confidence `"trimmed"` — strictly worse than the current dead tier, because a heuristic would then wear the highest-confidence badge in the system, while the polar-derived `v_md_mps`/`v_min_sink_mps` in the context are the better numbers today (which is why tier 2, `"computed"`, exists). **Nearest-match is also wrong**: matching the context's `v_md_mps` to the nearest operating point is unstable — two adjacent points can swap roles when a speed shifts by 0.1 m/s — and it would still stamp "trimmed" on a point that is merely *near* `V_md`. Three changes, all required together: **(1)** add `role ∈ {best_ld, min_sink, max_turn, cruise, takeoff, approach, stall_clean, stall_flaps, vx, vy, v_max, dutch_roll, none}`, set by the generator; the KPI derivation keys off `role`, never off `name`, so names stay free-form and user-editable while roles are the contract. **(2)** Gate the `"trimmed"` tier on **two** conditions — `marker.status == TRIMMED` **and** velocity within **5 %** of the polar's `v_md_mps`/`v_min_sink_mps`, otherwise fall through to the polar value at confidence `"computed"`. The 5 % band is deliberate: L/D is a smooth maximum and stays within ~1 % of its peak over roughly ±10 % of `V_md`, so a 5 % speed tolerance costs well under 1 % in the reported KPI while excluding a merely-neighbouring point. Condition (a) alone is already a bug fix — the missing status check at `:419` would mislabel a `NOT_TRIMMED` point as trimmed regardless of how the mapping is done. **(3)** Better still, make the generator honest: seed `max_range` at the context's `v_md_mps` and `loiter_endurance` at `v_min_sink_mps` whenever a polar exists, falling back to the `1.25·V_S`/`1.15·V_S` heuristics only at cold start — then condition (b) is satisfied by construction, the tier becomes genuinely reachable, and the reported KPI is a real trimmed value rather than a polar estimate.

**Authority:** Scholz/Sadraey plus propeller-aircraft performance physics (prop range at `V_md`, prop endurance at minimum power / minimum sink); the project's own `mission_kpi_service` convention.
**Confidence:** high on the role mapping; medium on the exact 5 % tolerance — the flatness argument supports anything in 3–10 %, and 5 % is the recommendation, not a derived optimum.

_Full reasoning: [`expert-consensus-sizing.md`](expert-consensus-sizing.md)_

---

## Q-MS-8 — Flight-envelope inconsistencies (bundle)

**Context:** Five related items:
- **Two `V_max` fallbacks for one number.** `flight_envelope_service._get_v_max`
  returns a bare `28.0`; the OP generator uses
  `max(1.35·V_cruise, V_cruise + 8)`. `V_dive`, `max_speed` and `dive_speed` all
  ride on it.
- **`ρ` is a fixed sea-level `1.225` in `compute_vn_curve`**, so the flight
  profile's `altitude_m` — which shapes every operating point — never reaches the
  envelope.
- **An absent gust envelope is completely silent.** When `b_ref` or `CL_α` is
  missing, `gust_lines_*` are empty with no warning and no log line, and
  `_get_b_ref`'s bare `except` has already discarded the reason.
- **`assumptions_snapshot` records only `{mass, cl_max, g_limit}`** and does not
  identify the **context** version, although `cl_alpha_per_rad`, `v_md_mps` and
  `v_min_sink_mps` shape the gust lines and two KPIs. A row can be silently stale
  with respect to half its inputs.
- **Cold-start conditions are reported as 500s.** A wingless aircraft raises
  `InternalError`; a non-positive `cl_max` raises a `ValueError` the endpoint
  reports as *"Unexpected error"*. The sibling matching-chart and field-length
  endpoints answer **422 with a remediation sentence** for the same class of
  condition.

**Spec affected:** [`_reversa_sdd/mission-and-sizing/flight-envelope/requirements.md`]
**Question:** Confirm each.
**Impact:** The last one is user-facing: the same mistake gets a helpful message
on one endpoint and "Unexpected error" on another.

**Answer:** _(expert consensus, endorsed by the maintainer 2026-08-14)_ **Four are confirmed defects and one is not: `ρ = 1.225` is CORRECT because a V-n diagram is an EAS chart — the real bug there is plotting TAS markers on it.**

**8.1 — one `V_max`, and a bare constant is not it.** `_get_v_max` (`:577`) returns a hard-coded **`28.0`** — a 3 kg sport model's top speed asserted for a 0.5 kg slow-flyer and a 15 kg UAV alike — while the generator (`:399`) uses `max(1.35·V_cruise, V_cruise + 8)`. The app already computes the physically right quantity: `assumption_compute_service._max_level_speed` (`:1863`) solves `P_avail·η_prop = D(V)·V`. Precedence: (1) the user's declared `goals.max_level_speed_mps`; (2) **`V_H` from the context's computed power balance**; (3) `1.35·V_cruise` **with the envelope flagged `V_MAX_ESTIMATED`**; (4) never a bare constant. Define the speed chain once and cite it: **`V_C = 0.9·V_H`** [CS-VLA 335(a)] and **`V_D = 1.4·V_C`** [CS-23/FAR-23 §23.335(b) normal/utility minimum]. Note this changes the *base*, not the factor — today's `v_dive = 1.4·v_max` uses `V_H` where the regulation uses `V_C` — and fix the internal `v_c = v_dive/1.4` in `_build_gust_lines` (`:189`), which currently makes `V_C ≡ V_H` and anchors the gust-velocity taper at the wrong speed. Surface the caveat that at RC scale nothing enforces `V_D`: a model in a vertical dive routinely exceeds it, so `V_D` is a *design reference*, not a limit the airframe imposes.

**8.2 — the fixed ρ is correct; the bug is elsewhere.** A V-n diagram is conventionally drawn in **equivalent airspeed**, and in EAS `ρ_SL` is the only density that may appear: `V_E` is *defined* by `½ρ_alt·V_TAS² = ½ρ_SL·V_E²`, so both the manoeuvre boundary `n = ½ρ_SL·V_E²·S·C_Lmax/W` and the Pratt-Walker gust increment are altitude-independent in EAS. Keeping `1.225` is what makes the diagram a single, altitude-free chart. **The actual defect is mixed airspeeds**: the operating points are trimmed *at altitude*, so their velocities are TAS, and they are then plotted on an EAS diagram. Label the axis "EAS" (it is currently unlabelled as to airspeed type, which is how this survived) and convert marker velocities with `V_E = V_TAS·√(ρ_alt/ρ_0)` — 500 m → 2.4 % low, 1000 m → 4.8 %, 2000 m → 9.4 %. Small but silent, and it compounds with the load-factor error from Q-MS-6.

**8.3 — a silent gust envelope is the *most* important warning in the module, not the least.** Scholz gives gust sensitivity as `n_α = dn/dα = ½·ρ·v²·C_Lα/(W/S)` — **inversely proportional to wing loading** — so at 40–60 N/m² an RC model is ~10× more gust-sensitive than a light GA aircraft at ~600 N/m², and the gust envelope is frequently the **structurally sizing** case at this scale. The module already knows this regime is marginal (it emits `GustValidityWarning` when `μ_g < 3`). Requirements: emit a structured warning naming the **specific** missing input (`GUST_ENVELOPE_UNAVAILABLE: b_ref` / `: cl_alpha`), never an empty array; replace `_get_b_ref`'s bare `except Exception: return None` (`:632`) with a logged, typed failure that preserves the reason; and when the existing Helmbold fallback supplies `C_Lα`, mark the gust lines reduced-confidence, since Helmbold is a lifting-line approximation, not the aircraft's actual `C_Lα`.

**8.4 — the snapshot is insufficient.** It must identify **every input that shapes the stored output**: `mass_kg`, `cl_max`, `g_limit`, `s_ref_m2`, `b_ref_m`, `cl_alpha_per_rad` (and whether it was Helmbold-derived), `rho`/`altitude_m`, `v_h_mps` **and its provenance** (declared / computed / estimated), `v_c_mps`, `v_d_mps`, `v_md_mps`, `v_min_sink_mps`, `gust_u_vc/vd` — plus a **context hash**. `mission_kpi_service._hash_context` (`:392`) already implements exactly this (stable SHA-256 over the sorted context); reuse it rather than writing a second one. Storing the hash makes staleness a one-line check and automatically covers context keys added later.

**8.5 — 422 with a remediation sentence.** A wingless aircraft and a non-positive `cl_max` are **user-state** conditions, not server faults. The sibling endpoints already do this (`field_length_service.py:457-463` is the model to copy); two endpoints treating the same mistake differently is the user-facing defect. Recommended messages: no wings → *"No wing defined — add a wing before computing the flight envelope."*; `cl_max ≤ 0` → *"CL_max is not available. Run the aerodynamic analysis to compute the polar, or set cl_max in Design Assumptions."*

**Authority:** CS-VLA 335(a) and CS-23/FAR-23 §23.335(b) for the speed chain; Anderson (definition of equivalent airspeed via the pitot relation) for 8.2; Scholz *07_WingDesign* §7.3 (`n_α ∝ 1/(W/S)`) for 8.3; internal consistency with the sibling endpoints for 8.5.
**Confidence:** high on 8.2, 8.3, 8.5 (physics and consistency, both decidable); medium on 8.1's exact `V_C`/`V_D` factors — the CS-VLA/CS-23 numbers are borrowed by analogy for uncertificated models, and the honest position is that `V_D` at RC scale is set by pilot discipline, not by structure.
Disagreement: none between authorities. Item 8.2 is the one place the code turns out to be right for a reason the code does not state — worth capturing in the requirements so it is not "fixed" later.

_Full reasoning: [`expert-consensus-sizing.md`](expert-consensus-sizing.md)_

---

## Q-MS-9 — Design-assumption semantics (bundle)

**Context:** Six related decisions:
- **Which effective-value resolver is canonical?**
  `design_assumptions_service.get_effective_assumption` (int-keyed) falls back to
  `PARAMETER_DEFAULTS` and returns `None`;
  `mass_cg_service.get_effective_assumption_value` (UUID-keyed) **raises**
  `NotFoundError`. `flight_envelope_service` uses the second and re-implements the
  first's fallback with a `try/except`. Consolidating changes that module's
  missing-row behaviour — is that intended?
- **A zero calculated value hides the divergence entirely.**
  `compute_divergence_pct` returns `None` when `calculated == 0` — exactly the
  case for `t_static_N` on a glider and for the `power_to_weight` a sailplane
  preset writes. Is "no divergence" the right answer there?
- **`update_calculated_value` can write onto a design choice.** Only the *switch*
  is guarded, so a design-choice parameter can display a `calculated_value` and a
  divergence it can never activate.
- **A no-op `switch_source` still fans out** — it publishes `AssumptionChanged`
  and schedules a recompute even when the requested source is already current.
- **Nothing records a suppressed fan-out.** An estimate edit under an active
  `CALCULATED` is intentionally silent *including in the logs*, so "why did my
  change do nothing?" has no server-side trace.
- **`0.0` is a "not set" sentinel** for `battery_capacity_wh`,
  `motor_continuous_power_w` and `t_static_N`, indistinguishable from a deliberate
  zero.

**Spec affected:** [`_reversa_sdd/mission-and-sizing/design-assumptions/requirements.md`]
**Question:** Confirm each.
**Impact:** The assumption machine is read by every sizing surface.

**Answer:** **One resolver — the raising one — plus a `DesignWarning`. The behaviour
change in `flight_envelope_service` is accepted.** _Answered by the maintainer,
2026-08-15._

Two resolvers exist for the same question: `design_assumptions_service.get_effective_assumption`
(int-keyed) falls back to `PARAMETER_DEFAULTS` and returns `None`;
`mass_cg_service.get_effective_assumption_value` (UUID-keyed) **raises**
`NotFoundError`. `flight_envelope_service` uses the second and re-implements the
first's fallback with a `try/except`.

The raising variant wins (ADR 0022). A silent `PARAMETER_DEFAULTS` substitution is
exactly what `P-WARN-0` forbids — it is the same shape as the RC-typical context
defaults removed in `Q-CC-10`.

**Accepted consequence, explicitly confirmed:** `flight_envelope_service`'s behaviour on
a missing row changes from *silent default* to *visible error*. That is the intended
direction — an envelope computed from an invented assumption is worse than one that
refuses.

---

## Q-MS-10 — Should a mission-preset change fan out?

**Context:** `_apply_preset_estimates` bypasses `update_assumption` and sets
`estimate_value` directly on the ORM rows, so five estimates can change **without
an `AssumptionChanged` event and without dirtying operating points** — even when
those estimates are the effective values. It also silently no-ops on an unknown
`mission_type`, and its docstring defers rejection to the KPI service, which also
does not reject (it falls back to the `trainer` preset). A typo produces no error,
no warning and no change anywhere.
**Spec affected:** [`_reversa_sdd/mission-and-sizing/mission-objectives-presets/requirements.md`]
**Question:** Should a mission change fan out — and if so, does the resulting
recompute/retrim storm need a batch mode? Should `mission_type` get an FK to
`mission_presets.id`?
**Impact:** Changing the mission is the single largest assumption edit a user can
make, and it currently propagates to nothing.

**Answer:** _(**partially** derived — the fan-out decision itself is REOPENED as `Q-MS-10b`, below)_ **No batch mode is needed, `_apply_preset_estimates`' bypass of `update_assumption` is a hole, and an unknown `mission_type` must fail visibly instead of silently no-opping.**

Follows from **ADR 0022 corollary 5** and **Q-MS-14**: the mission preset is *"the single author of mission-shaped defaults"* — cruise speed, g-limit, CL_max, power-to-weight and static margin — so a preset change moves effective values that every sizing surface reads, and `_apply_preset_estimates` writing `estimate_value` straight onto the ORM rows is a bypass of the very invalidation contract that keeps those surfaces honest; a context left undirtied is the stale-vs-fresh blind spot **Q-CC-10** was answered to close. The storm is already solved: **Q-PC-4** replaced dropping with coalescing (*"record 're-run needed' and run **once** on completion"*), which together with the existing 2 s debounce collapses five estimate changes into one recompute and one retrim — a separate batch mode would be a second answer to a decided problem. The silent no-op on an unknown `mission_type`, and the KPI service's silent fallback to the `trainer` preset, are undeclared substitutions forbidden by **P-WARN-0**; the enforcement point is a real reference constraint rather than an unvalidated string, the shape **Q-CC-7** and **Q-CC-9** establish for exactly this defect.

> **⚠ Narrowed 2026-08-15.** The original derivation answered *whether* a mission change
> should fan out. That is not derivable — it is a preference, and the record points the
> other way as plausibly as toward automatic propagation: **ADR 0007** establishes
> propose/adopt as this system's idiom for changes with wide blast radius, and an
> explicit *"apply this mission"* step is a defensible design rather than an oversight.
>
> **What survives as derived:**
> - **No batch mode.** `Q-PC-4` replaced dropping with coalescing, which with the 2 s
>   debounce collapses five estimate changes into one recompute and one retrim. The
>   storm the question worried about is already solved.
> - **The write path is wrong regardless of the fan-out decision.**
>   `_apply_preset_estimates` setting `estimate_value` directly on ORM rows bypasses the
>   invalidation contract. Even under an explicit-apply design the write goes through
>   `update_assumption` — the difference is *when* it is called, not whether.
> - **Silent failure is forbidden.** An unknown `mission_type` no-opping, and the KPI
>   service falling back to the `trainer` preset, are undeclared substitutions
>   (**P-WARN-0** / ADR 0020). A typo currently produces no error, no warning and no
>   change anywhere.

## Q-MS-10b — Should changing the mission propagate automatically, or be applied explicitly?

**Reopened from `Q-MS-10`, 2026-08-15.** Changing the mission is the single largest
assumption edit available: it moves cruise speed, g-limit, CL_max, power-to-weight and
static margin at once, and today it propagates to **nothing**.

**Routed through the domain experts before it reaches the maintainer** — the question is
partly an engineering one (does a mission change invalidate a trimmed operating point in
practice, or only shift targets the user is still free to ignore?).

**Answer:** **ANSWERED by the maintainer, 2026-08-15** (option a) — **tiered invalidation, driven by a fingerprint of the trim-equation arguments rather than a hand-maintained mapping.**

**The discriminator is one mechanically checkable question: is the changed quantity an argument of the trim system?** (Sadraey Eq. 12.86.) Its arguments are `{C_L1, C_Lo, C_Lα, C_LδE, C_mo, C_mα, C_mδE, T·z_T, q}`. Everything in that list is an **input**; everything outside it is an **acceptance criterion**. That single rule replaces the per-field judgement the question was asking for.

| tier | preset item | why |
|---|---|---|
| 🔴 **invalidating** | **cruise speed** | enters `C_L1 = 2W/(ρV²S)` directly. At Re 5e4–5e5 it also moves `C_D0` by **10–35 %** through laminar-bubble behaviour — so at RC scale a speed change invalidates a stored result **more** severely than the same change would for a transport, not less |
| 🔴 | **static margin — if the preset writes `x_cg`** | `C_mα = C_Lα(x_cg − x_np)` is a row of the trim matrix. Under this project's *"CG is a top-down design target from stability"* philosophy the preset almost certainly does write it, so this is Tier 1 here |
| 🔴 | **power-to-weight — for thrust-pinned points only** | in level cruise `T` is pinned by `T = D` and P/W only answers *"is that much thrust available?"*. At full power (climb, go-around, sustained turn) `T` is an input |
| 🟡 **boundary-moving** | **`CL_max`** | never appears in the trim system — a cruise trim runs at `C_L ≈ 0.3–0.6`. It invalidates **only points whose defining condition is expressed relative to `V_S`** (approach, 1.3·V_S, stall margin). Absolute-speed points survive |
| 🟢 **re-targeting** | **`n_max`** | structural sizing and the V-n envelope only. Invalidates **nothing** while mass is a manual estimate — but **migrates to Tier 1 the moment mass becomes derived from it**, so the spec must state which regime it is in rather than leave it implicit |

**Mechanism — two requirements, because a hand-written mapping would rot on the sixth preset field:**

1. **Store each operating point's *defining condition*, not only its results** — what was pinned: an absolute `V`, a multiple of `V_S`, a load factor, or full thrust. Invalidation then becomes a pure function of *"did a pinned input change?"*
2. **Store a fingerprint of the trim-system arguments actually used.** **Tier 1 ⟺ fingerprint changed.** Mechanically checkable, no runtime judgement, and future-proof.

**Never silently discard.** A `DesignWarning` (ADR 0020) with severity `stale` for Tiers 2–3 and `invalid` for Tier 1. Results computed under a superseded mission are **re-tagged, not deleted** — the numbers are not *wrong*, they are a valid operating point for a **different condition**, and the RC design literature is explicit that the previous state is the artefact the whole method is built on: *"Change too many things at once, and the airplane stops teaching."*

**`CL_max` must not be a mission-preset field at all.** It is a property of the airfoil that was fitted, so a preset value would be a **second producer of a user-visible number** (ADR 0022) — and the two are not even the same kind of number: a VLM cannot produce `CL_max` at all, being linear and inviscid, so only AeroBuildup/NeuralFoil can approximate it. Mission chooses the **airfoil**; `CL_max` follows.

**Carried over from the narrowing of `Q-MS-10`, all still binding:** no batch mode is needed (`Q-PC-4` coalescing plus the 2 s debounce already collapse five estimate changes into one recompute and one retrim); `_apply_preset_estimates` must route through `update_assumption` under either design; and an unknown `mission_type` silently no-opping — plus the KPI service falling back to the `trainer` preset — are undeclared substitutions forbidden by `P-WARN-0`.

---

## Q-MS-11 — Are the `wing_loading` axis ranges unit-consistent?

**Context:** The presets use a 10–120 band while the "Ist" axis computes
`m·g/S_ref` in **N/m²** and `target_wing_loading_n_m2` defaults to `412`. One of
the two is in the wrong unit; the code says nothing. Relatedly, a degenerate
`axis_range` (`hi <= lo`) scores `0.0`, not `None` — the one place an unknown is
rendered as a bad result.
**Spec affected:** [`_reversa_sdd/mission-and-sizing/mission-objectives-presets/requirements.md`]
**Question:** Which band is in the intended unit?
**Impact:** Every mission KPI score on the wing-loading axis.

**Answer:** _(expert consensus, endorsed by the maintainer 2026-08-14)_ **The unit is N/m² and the 10–120 band is correct — but `412` is a full-scale value that leaked in, and the default must become 55 N/m².**

The reason nobody caught the ambiguity is a numerical coincidence: **1 g/dm² = 0.981 N/m²**, so the RC-practice band of 10–120 g/dm² is 9.8–117.7 N/m² — **the same band in both units to within 2 %**. The band is right either way, and `mission_kpi_service._kpi_wing_loading` (`:262`) returning `mass_kg · 9.81 / s_ref` fixes the unit as N/m². No change there. **`412` is not a unit error either** — 412 N/m² = **420 g/dm²**, roughly **4× above the RC "danger zone"** (~95–110 g/dm²) and in light-GA/ultralight territory. Set `_default_objective`'s `target_wing_loading_n_m2` to **55 N/m² (≈ 56 g/dm²)**, the mid of the trainer band, matching that same default's declared `mission_type="trainer"`.

**This is more than cosmetic, because `412` currently inverts the trainer's mission intent.** `_normalise_score` (`:56`) scores *higher* wing loading as *better*; with the trainer band 20–80 and a target of 412 the Soll score clips to **1.0** — maximum loading — while the trainer preset's declared `target_polygon["wing_loading"]` is **0.3**. The white Soll line and the orange Ist polygon are meant to be directly comparable (gh-767), and today the trainer's target wing-loading vertex is pinned at the wrong end of the axis. Two supporting changes: **show g/dm² as a secondary label** — RC modellers read g/dm², not N/m², so keep N/m² as the stored and computed unit and render `"55 N/m² (56 g/dm²)"`, which removes the ambiguity permanently; and **a degenerate `axis_range` (`hi ≤ lo`) must yield `None`, not `0.0`** — that is a *configuration* fault, not a bad aircraft, and returning `0.0` renders a config error as a maximally-bad score on the radar, the one place in the system where an unknown is drawn as a failure. Return the `provenance="missing"` shape `_missing()` already produces, with a warning naming the offending axis — the same principle as the `DEFAULT_E_OSWALD` ruling in Q-MS-4.

**Authority:** the code's own formula `m·g/S_ref` fixes the unit; RC practice supplies the band (rcplanedesigner's mission chart plots 10–120 g/dm²: slowflyer ~10–45, trainer ~40–75, sport ~45–100, acrobatic ~50–95, danger zone above ~95–110; Lennon's oz/ft² figures convert to gliders <30–45 N/m², sport 45–60, pattern 69–78). Scholz/Sadraey supply the *method* — the matching chart's W/S axis and the constraint that it must not start at zero, which the code's `_WS_MIN = 10.0` already respects.
**Confidence:** high — the unit is fixed by the code's own formula and the RC band is corroborated by two independent RC sources that agree after conversion.
Disagreement: Sadraey's suggested plotting range (5–100 lb/ft² = 239–4788 N/m²) and the RC band differ by two orders of magnitude, but this is scale, not conflict — his range is for transports, his *method* transfers unchanged, and where a concrete RC number is needed Scholz is silent, so RC practice supplies it legitimately.

_Full reasoning: [`expert-consensus-sizing.md`](expert-consensus-sizing.md)_

---

## Q-MS-12 — Operating-point sweep semantics (bundle)

**Context:** Six items:
- **`replace_existing` is aircraft-wide, not set-scoped** — it deletes every
  `operating_pointsets` and `operating_points` row of the aircraft, including
  manually created points. Scope it, or rename the flag?
- **A capability-gated target is invisible on the SSE stream.** The streaming path
  filters `supported` **before** emitting `targets`, so a gated target appears in
  neither `targets` nor `skip`; `skip` carries only `{"name": …}` with no reason.
  A client cannot distinguish "your aircraft has no rudder" from "this target
  failed to solve".
- **`profile.goals.target_turn_n` and `loiter_s` are validated but never read** —
  the banks are hard-coded at 20/40/60° and the loiter point is a speed, not a
  duration. A user who sets `target_turn_n = 3.0` sees no effect.
- **`has_pitch_control` is detected but never required by any target**, so an
  aircraft with no pitch surface generates all fifteen and trims with an empty
  control set.
- **`STALL_IN_TURN` is a formatted sentence with embedded numbers**, while every
  other `warnings[]` entry is a bare token — a consumer matching on equality
  misses it.
- **None of the six trim-objective weights (50, 3, 15, 2, 2, 0.001) is named or
  justified** in the code, and the reference-speed `provenance`
  (`polar` / `cold_start`) is not persisted, only its consequence
  (`STALE_NO_POLAR`).

**Spec affected:** [`_reversa_sdd/mission-and-sizing/operating-point-sweep/requirements.md`]
**Question:** Confirm each. The trim weights in particular cannot be reproduced
from the spec without provenance.
**Impact:** The sweep generates fifteen points that feed the whole analysis tab.

**Answer:** _(expert consensus, endorsed by the maintainer 2026-08-14)_ **Store the trimmed `C_L` and the solved deflections on the operating point (they are constitutive, and this also fixes Q-MS-6's V-n markers); derive the turn banks from `target_turn_n` via `φ = arccos(1/n)`; require `has_pitch_control`; make `STALL_IN_TURN` a bare token; re-express the six weights as three tolerances; persist the reference-speed provenance.**

**What defines an operating point** is the complete set of arguments that make the aerodynamic problem well-posed — in AeroSandbox terms `OperatingPoint(velocity, alpha, beta, p, q, r, atmosphere)` plus the configuration state (control deflections, flap setting) plus the mass and CG the moments are referenced against (`xyz_ref`). The code's target dictionaries carry the right *input* list; what is missing from the **stored** point is the outcome-defining pair — the trimmed `C_L` and the deflections that achieved it. Without `C_L` the point cannot be replayed and cannot be placed on a V-n diagram, which is Q-MS-6's bug with the same root cause. **`target_turn_n` and the hard-coded banks are the same quantity**: `n = 1/cos φ ⇔ φ = arccos(1/n)`, and the code already encodes the forward direction correctly (`n_target = round(1/cos(radians(bank)), 4)`, applied in `C_L,target = n·m·g/(q·S)`) — but with banks frozen at 20/40/60° the hardest turn evaluated is **n = 2.0**, so a user who set `target_turn_n = 3.0` is asking for a **70.5° bank** and gets a sweep whose worst case is **33 % below their stated requirement, with no warning**. Keep 20° as a low anchor, add `φ(n_target)` and the midpoint. **`has_pitch_control` detected but never required is physically indefensible**: an aircraft with no pitch surface has one free variable (α) against two conditions (`L = W`, `C_m = 0`), so it is trimmable at exactly the single `C_L` where `C_m(α)` crosses zero, if at all — generating fifteen "trimmed" points for it produces fifteen results that are really `CONTROL_AUTHORITY_LIMIT` (Q-MS-5). Require it for every target that is not itself a stall probe; a flying wing with elevons passes through the `[pitch]` role, so this excludes no configuration RC users actually build.

**`STALL_IN_TURN`'s physics is right and only its representation is wrong** — it correctly evaluates the required `C_L` at the turn's own velocity (`:1153-1154`) — but it is a formatted sentence while every sibling warning is a bare token, so equality-matching consumers miss it: emit the bare token and put `{bank_deg, n, cl_required, cl_max}` in a structured field. **The six weights (50, 3, 15, 2, 2, 0.001) are not arbitrary but are unreproducible from the spec.** The standard defensible construction is inverse-square-of-tolerance weighting, `w_i = 1/tol_i²`: `tol_Cm = 0.01` → 10 000 → normalised **50** (shipped 50); `tol_CL = 0.02` → 2 500 → **12.5** (shipped 15); `tol_CY = 0.03` → 1 111 → **5.6** (shipped 3). All three land within a factor of ~2 — so re-express them as the three tolerances plus a documented `1e-3` control-effort **regulariser** whose only job is to select the minimum-deflection solution when several surfaces make the trim under-determined (relative to a 50-weighted `C_m²` it biases trim by well under 0.1°, which is correct regulariser behaviour). That makes them reproducible from the spec and makes Q-MS-5's trim criterion fall out of the same three numbers. **Persist the reference-speed provenance (`polar` / `cold_start`), not only its consequence** (`STALE_NO_POLAR`): the difference is a stall speed from a *computed* `C_Lmax` versus an *assumed* one, and at RC Reynolds numbers that assumption is the single largest error source in the sweep (`C_Lmax` varies by **−54 %** across the model Re band) — ten of the fifteen target velocities are multiples of `vs_clean`/`vs_to`/`vs_ldg`, so it propagates into almost every point. Finally, **label the result set as a mission point-set, never a polar**: it varies velocity and configuration together across its 15 targets, which is correct for a set of design points but means the results must never be plotted as a curve. (Held constant and correctly so: mass, CG, altitude, atmosphere.)

**Two items are contract decisions, flagged not ruled on:** `replace_existing` being aircraft-wide rather than set-scoped — it deletes manually created points, so scope it or rename it, either is defensible; and the SSE stream filtering `supported` before emitting `targets`, so a capability-gated target appears in neither `targets` nor `skip` while `skip` carries no reason — a real information loss that should carry the capability string `_validate_target_capability` already returns (`:568-583`), but the API shape is a product call.

**Authority:** Scholz/Sadraey for the operating-point definition and the load-factor relation; AeroSandbox tooling for the exact argument list that makes the problem well-posed; Lennon / RC practice for the Re sensitivity of `C_Lmax` that raises the priority of the provenance item.
**Confidence:** high on the operating-point definition, the `n ↔ φ` identity and `has_pitch_control`; medium on the weight re-derivation — a defensible reconstruction that matches the shipped numbers, not a recovery of the original author's stated intent.

_Full reasoning: [`expert-consensus-aero.md`](expert-consensus-aero.md)_

---

## Q-MS-13 — Loading-scenario and profile constraints (bundle)

**Context:** Four items:
- **`is_default` on `loading_scenarios` is unconstrained** — two default scenarios
  produce a non-deterministic `cg_agg_m`.
- **`component_uuid` in scenario overrides is unvalidated**, so an override naming
  a deleted component is indistinguishable from a no-op.
- **`ga_runway` is reachable in `matching_chart_service` but is not a member of
  the `AircraftMode` literal**, so the endpoint cannot select it.
- **The bank ↔ `target_turn_n` consistency validator exists only on
  `RCFlightProfileCreate`**, so a PATCH can leave a profile self-inconsistent.
  `ComputeEnvelopeRequest.force_recompute` is likewise dead surface — the
  flight-envelope POST takes no body.

**Spec affected:** [`_reversa_sdd/mission-and-sizing/requirements.md`],
[`_reversa_sdd/mission-and-sizing/flight-envelope/contracts.md`]
**Question:** Confirm each.
**Impact:** Four small contract decisions.

**Answer:** **ANSWERED by the maintainer, 2026-08-15** (option a for the bank/load-factor pair; the remaining three bundle items resolved alongside).

**① Bank ↔ load factor: `n` becomes derived, not stored.**
```
n = cos γ / cos φ          (steady turn at flight-path angle γ; γ = 0 ⇒ n = 1/cos φ)
```
Storing both `max_bank_deg` and `target_turn_n` makes the record carry **two producers of one physical number** — exactly what **ADR 0022** forbids — and the create-only validator was the worst of both worlds: it blocks a legitimate record on create and permits an inconsistent one on PATCH. Either the invariant holds always or it is not an invariant.

**Bank is primary; `n` is derived, with `γ` defaulting to 0.** The climb-angle term is not academic at RC/UAV scale, where climbing turns at γ = 20–40° are routine: at γ = 30° assuming `1/cos φ` is **13 %** high, at 45° **41 %**.

**An explicit override remains possible, with a stated reason and a `DesignWarning`** (ADR 0020), because three legitimate states break the relation entirely: a **slipping or skidding turn** (fin and fuselage carry part of the lateral force, and none of {φ, n, ψ̇} then determines the other two); a **spiral**, which is not a steady state at all; and **knife-edge at φ = 90°**, where the formula returns ∞ while the truth is `n_wing ≈ 0` — the aircraft is held up by fuselage side force and rudder. **An aerobatic mission must be able to express knife-edge**, which is precisely why this is a warning and not an enforced constraint.

**② `is_default` on `loading_scenarios` gains a uniqueness constraint.** Two defaults produce a non-deterministic `cg_agg_m` — a user-visible number whose value depends on row order. Partial unique index on `(aeroplane_id) WHERE is_default`.

**③ `component_uuid` in scenario overrides — validated, and now cheap.** Since referenced components **cannot be deleted, only changed** (`Q-PT-7`, and `Q-AC-10` extends the same principle to tree nodes), a dangling override can no longer arise through normal use. Validation becomes an invariant check rather than a data-repair path: an override naming an unknown component is rejected at write time instead of being indistinguishable from a no-op.

**④ `ga_runway` is deleted, not exposed.** It is reachable in `matching_chart_service` but absent from the `AircraftMode` literal (`app/schemas/matching_chart.py:9`), so no endpoint can select it. It is also **full-scale single-engine GA, Cessna-172 class, FAR-23.65** — outside the 0.5–15 kg scope entirely, and **ADR 0023** forbids carrying a constant set that is standard in transport-category literature but unvalidated at this scale. Complete and unreachable ⇒ **ADR 0021** deletes it. Adding it to the literal would be adding a mode nobody in scope can use.

**⑤ `ComputeEnvelopeRequest.force_recompute` is dead surface** — the flight-envelope POST takes no body. Deleted under ADR 0021.

---

## Q-MS-14 — Which of the three `target_static_margin` defaults is authoritative?

**Context:** `0.12` (the seeded assumption), `0.10` (an inline default in the
SM-suggestion endpoint), and whatever the active mission preset wrote.
Separately, `_default_profile()` duplicates goal defaults that also exist in
`mission_preset_seed` and `PARAMETER_DEFAULTS` — three independent default sets
that can drift (e.g. cruise 18 m/s appears in both the default profile and the
mission-objective default).
**Spec affected:** [`_reversa_sdd/mission-and-sizing/design-assumptions/requirements.md`],
[`_reversa_sdd/mission-and-sizing/mission-objectives-presets/requirements.md`]
**Question:** Which is canonical in each case?
**Impact:** Static margin is the central design target of ADR 0011.

**Answer:** _(expert consensus, endorsed by the maintainer 2026-08-14)_ **The seeded default is `0.10`, not `0.12`; precedence is user edit > active mission preset > seeded default; and the presets are already right except `acro_3d = 0.0`, which must become `0.03`.**

`0.12` (`app/schemas/design_assumption.py:75`) matches **no source in any of the three vaults**. `0.10` is Lennon's sport value, the average of rcplanedesigner's trainer band, and the top of Scholz's "typical stability margin requirement: 5–10 % MAC". Change `PARAMETER_DEFAULTS["target_static_margin"]` to **0.10** and **delete the inline `0.10` in `sm_suggestions.py:74`**, reading the resolver instead so there is one place to change. The precedence chain is already the implemented behaviour — the preset writing `estimate_value` on mission change (gh-549) is the correct mechanism and the seeded default is only the cold-start value before any mission is chosen — it just needs to become the *documented contract*, with the inline fallback removed so nothing bypasses it. Yes, the target must differ per mission: trainer **0.15** ✔, stol_bush **0.15** ✔, sport **0.10** ✔, sailplane **0.10** ✔, motor_glider **0.10** ✔, slope_soarer **0.08** ✔, flying_wing **0.075** ✔, wing_racer **0.05** ✔ (Lennon's stated *minimum*), and `_SM_TAILLESS_TARGET = 0.075` is correct — exactly the mid of Lennon's tailless 5–10 % band.

**`acro_3d = 0.0` must become `0.03`.** A target of exactly zero means "put the CG on the neutral point" — by Sadraey Eq. 11.17 that is `C_mα = 0`, neutral static stability, and by his §11.4 statement it lies *inside* the dynamically-unstable band, since **"a conventional aircraft becomes dynamically longitudinally unstable when the cg lies within roughly 2–3 % MAC of the neutral point"**. Two effects make it worse at RC scale, both pushing the *real* SM below the computed one: a VLM `x_np` is **power-off and fuselage-free**, the fuselage's Munk moment shifts the real NP forward, and the power-on NP is several % MAC forward of the power-off NP on a model whose slipstream covers a large fraction of the tail. **A computed SM of 0.03 can therefore be a real SM near zero, so a 0.0 target is a design tool instructing the user to build an unflyable aeroplane.** 0.03 is the top of rcplanedesigner's acrobatic band and the edge of Sadraey's instability band — the lowest number defensible as a *default*. Add a hard classification floor matching ADR 0011's SM ladder: **error below SM = 0.02, warning below SM = 0.03**, both anchored to Sadraey's 2–3 % MAC statement, which is now the citation ADR 0011 corollary 4 is missing for its `<0.02 error` threshold. On the wider duplicate-defaults problem: the **mission preset is the design-intent layer and must be the single author of mission-shaped defaults**; `PARAMETER_DEFAULTS` should carry only values with no mission dependence (ρ, g), while cruise speed, g-limit, CL_max, power-to-weight and static margin all belong to the preset alone.

**Authority:** Sadraey Eq. 11.18 / 11.22 (`SM = (x_np − x_cg)/C̄`, `x_cg < x_np` as a hard constraint) and §11.4 (2–3 % MAC dynamic-instability band); Scholz *10_BoxWingSystematic* §4.2 ("typical 5–10 % MAC"); Lennon Ch. 6 (NP 35 % / CG 25 % MAC ⇒ SM 10 %, minimum 5 %) and Ch. 23 (tailless 5–10 %); rcplanedesigner's per-mission table for the RC bands.
**Confidence:** high on the ordering and on rejecting 0.0 and 0.12; medium on the exact acro value (0.03 vs 0.05) — Sadraey's 2–3 % figure is for *conventional* aircraft, and a small high-thrust 3D model is not that.
Disagreement: genuine. rcplanedesigner gives Sport avg 4 % and **Acrobatic avg 1.5 %** with an acrobatic *minimum* of zero, which sits inside Sadraey's instability band. Resolved in favour of Scholz/Sadraey per the authority hierarchy — acro at 0.03 rather than 0.015, sport at Lennon's 0.10 rather than 0.04. The reconciliation is real, not diplomatic: a 1 m aerobatic model flown line-of-sight has time constants short enough for a skilled pilot to hand-fly a marginally unstable airframe, but a **default** in a tool that also serves UAVs and first-time builders cannot assume that pilot. Expose 0.015 as a documented expert override; never ship it as the default.

_Full reasoning: [`expert-consensus-sizing.md`](expert-consensus-sizing.md)_

---

# mass-and-balance

## Q-MB-1 — Two mass producers write one column: which one wins?

**Context:** `weight_items` and the component tree both write
`design_assumptions["mass"].calculated_value`, with **no arbitration**. An
aircraft populated in both ends up with whichever source was touched last;
`calculated_source` records the winner and nothing warns that the other estimate
was discarded. Replaying the same edits in a different order therefore yields a
different aircraft mass. Compounded by the absence of a `component_id` on
`weight_items`: the same battery entered in both places is two unrelated rows and
is **double-counted** with nothing to detect it.
**Spec affected:** [`_reversa_sdd/mass-and-balance/requirements.md`] (BR-MB4),
[`_reversa_sdd/mass-and-balance/component-tree-mass-sync/requirements.md`]
**Question:** Is one intended to be authoritative (and the other read-only),
should the two be summed / reconciled, or should `weight_items` become a view
over the tree and be retired?
**Impact:** Mass drives retrim, `V_stall`, the matching chart, the solution space
and endurance — every sizing surface reads it.

**Answer:** **(a) The component tree is authoritative; `weight_items` becomes a
read-only view and is retired.** _Answered by the maintainer, 2026-08-13._

**Maintainer's domain reasoning (decisive):** components with mass are normally
added to the aircraft *through the component tree*. A point mass is therefore just
a **"fake component without dimensions" (L×B×H = 0,0,0)** — and both kinds need a
position in the aircraft anyway. Point masses can be represented in the tree
whenever they are needed, so `weight_items` has no distinct role to justify.

### Provenance — established from git history during the interview

This duplication is **historical drift from agentic development**, not a design:

| Date | Commit | Table |
|---|---|---|
| 2026-04-12 | `63aedee9` — "add **6 backend resources** for Construction Workbench MVP" | `weight_items` |
| 2026-04-14 | `7596e981` — "component tree — hierarchical assembly structure", `Closes gh#34` | `component_tree` |

`weight_items` came from a **bulk scaffold commit implementing six unrelated
resources at once**, explicitly to fill gaps the *UI wireframes referenced but that
were missing*. Its "ticket" identifiers (`ect`, `tz4`, `hm7`, `1bq`, `yu9`, `50t`)
are pencil.dev wireframe element IDs, not GitHub issues. Two days later
`component_tree` arrived as a properly ticketed, designed feature with 13 tests.
**Neither commit references the other**, and nobody reconciled them afterwards.

So: **`weight_items` is the accident; `component_tree` is the design.**

**Wider pattern worth recording in the spec:** the same 2026-04-12 bulk commit also
produced `1bq` — "Design Versioning … `/aeroplanes/{id}/design-versions`" — which is
almost certainly the source of the **five dead `design-versions` routes** in
`Q-VS-3`, later superseded by the real versioning model (epic #901). Wireframe-driven
bulk scaffolds are a recurring generator of ownerless surfaces that a properly
designed feature later supersedes.

### Required

1. **Single producer.** Only the component tree writes
   `design_assumptions["mass"].calculated_value`. The race in which *the same edits
   in a different order yield a different aircraft mass* disappears.
2. **Point masses in the tree.** No schema change needed: a node with
   `weight_override_g`, or a `cots` node referencing a `components` row with mass and
   zero bounding box, expresses a point mass today.
3. **CG must read the tree.** Today `mass_cg_service` reads **only** `WeightItemModel`
   (`:200`, `:230`), even though the tree carries `pos_x/y/z`. This answers `Q-MB-4`:
   yes — and ultimately the tree becomes the *only* CG source.
4. **Unit conversion in the migration.** `weight_items.x_m/y_m/z_m` are **metres**;
   `component_tree.pos_x/y/z` are **millimetres** (per the schema descriptions). The
   migration must apply ×1000 — the mm/m boundary of ADR 0001.
5. **Migration path.** Existing `weight_items` rows become tree nodes (position
   converted, `category` preserved or mapped); `weight_items` is then a read-only
   view, and removed once nothing depends on it.
6. **Double-counting resolved.** The missing `component_id` on `weight_items` — which
   made the same battery entered in both places two unrelated, double-counted rows —
   is moot once the tree is the only writer, since tree nodes already carry
   `component_id`.

**Rejected:** (b) `weight_items` authoritative — discards the richer model;
(c) sum both with a dedup key — no longer needed once point masses live in the tree;
(d) warn on divergence — leaves the number order-dependent.

---

## Q-MB-2 — Is `compute_recommended_cg` the intended home of the top-down CG rule?

**Context:** The project's central rule `x_np − SM·MAC` (ADR 0011) is implemented
and unit-tested in `mass_cg_service.py:36` and has **no production caller** —
production re-derives it in `loading_scenario_service.compute_stability_envelope`
and in `assumption_compute_service`. `RecommendedCGRequest` /
`RecommendedCGResponse` are declared (`app/schemas/mass_cg.py:8-23`) and returned
by no endpoint.
**Spec affected:** [`_reversa_sdd/mass-and-balance/requirements.md`] (RF-18),
[`_reversa_sdd/mass-and-balance/cg-mass-computation/requirements.md`]
**Question:** Which of the three is canonical, and should the other two delegate?
Was a `/recommended_cg` route planned and dropped, or superseded by the
stability-envelope endpoint?
**Impact:** ADR 0011's central rule is implemented three times.

**Answer:** _(expert consensus, endorsed by the maintainer 2026-08-14)_ **The formula is exactly Sadraey Eq. 11.18 rearranged and needs no change — make `mass_cg_service.compute_recommended_cg` the single implementation and have the other two delegate; do not add a `/recommended_cg` route, it is superseded by the stability-envelope endpoint.**

`SM = (x_np − x_cg)/C̄ ⇒ x_cg = x_np − SM·C̄` is Sadraey §11.6.2, and the *direction* of the design loop ADR 0011 asserts is also his: *"one of the explicit objectives of aircraft configuration design is to achieve the best possible cg location… the ideal cg becomes a **target** for weight distribution. Components are then placed to drive the actual cg toward the ideal"* (§11.3.3). **ADR 0011 is not a house opinion — it is textbook methodology, and the ADR can cite it.** RC practice states the identical procedure as a build workflow: Lennon's "balancing act" places a fulcrum at the design CG and moves components until the beam balances (design CG first, components second), with the worked instance `NP = 35 % MAC`, `CG = 25 % MAC`, `SM = 10 %` — the same equation. `mass_cg_service.compute_recommended_cg` (`app/services/mass_cg_service.py:36`) should be canonical: it is the only one of the three that is a pure function of exactly the three inputs the rule needs, the only one already unit-tested, and it lives in the module whose name matches its subject. Three implementations of one two-term formula is three places for a sign or unit error. Delete `RecommendedCGRequest`/`RecommendedCGResponse` (`app/schemas/mass_cg.py:8-23`) rather than wiring a route to satisfy them: the stability-envelope endpoint returns the same number *plus* the aft/forward limits and the classification, which is strictly more useful and is what the UI needs.

**Four caveats at this scale, all real, none invalidating the formula.** (1) **Units:** `x_np` and `MAC` must be in the same frame and unit, and the codebase carries an mm/m dualism (WingConfig mm, DB/ASB m) — whichever module owns the rule must take metres and say so in the signature. (2) **Which `x_np`:** a VLM neutral point is power-off and (depending on the model) fuselage-free; both corrections move the real NP **forward**, so the *achieved* SM is **smaller** than the computed one — the error is in the unsafe direction. **Extend the signature to carry the caveat, not just the number:** return the NP provenance (power-on/power-off, fuselage-included yes/no) alongside `x_cg`, so it reaches the user instead of living in a comment, and read Q-MS-14's warning bands as applying to a computed SM that is optimistic by a few % MAC. (3) **It is a target, not a limit:** `x_np − SM_target·MAC` is the design CG; the **aft limit** is `x_np − SM_min·MAC` and the **forward limit** comes from elevator authority, not from this formula — ADR 0011 corollary 3 already says this, it just must not be conflated in the implementation. (4) **Tailless:** for a flying wing NP ≈ wing AC so the formula is unchanged, but the SM band tightens to 5–10 % and CG sensitivity is much higher — conventional aircraft tolerate CG shifts of several percent MAC, tailless aircraft do not.

**Authority:** Sadraey Eq. 11.18 (§11.6.2) for the formula and §11.3.3 for the design-loop direction; Sadraey's Munk fuselage shift ΔX_fus and Lennon Ch. 6 (power-on NP forward of power-off) for caveat 2; Lennon Ch. 23 for the tailless band.
**Confidence:** high on the formula and the delegation; medium on the magnitude of the NP correction in caveat 2 — quantifying the fuselage/slipstream shift for RC-scale bodies would need a fuselage-inclusive panel run or flight data.
Disagreement: none — Scholz/Sadraey, Lennon and the ADR agree on both the formula and the design-loop direction.

_Full reasoning: [`expert-consensus-sizing.md`](expert-consensus-sizing.md)_

---

## Q-MS-13b — `turn_60` is generated inside the stall boundary, and contradicts the RC load-factor band

**Raised 2026-08-15** during the expert consultation for `Q-MS-13`; **ANSWERED by the
maintainer the same day** (option a — fix both).

**Context.** Two independent findings that meet on the same operating point. A 60° level
coordinated turn requires **n = 2.0**, and therefore:

- **Stall speed rises by √n = 1.414.** The generator sets turn velocity to
  `max(cruise, 1.3·V_S)` (`operating_point_generator_service.py:494`). At `1.3·V_S` the
  `turn_60` point lies **inside the stall boundary** — a stalled turn. On a 2 kg / 15 m/s
  reference airframe the margin in the turn is **1.077·V_S**, against a universal ≥1.3·V_S
  approach convention.
- **Sadraey Table 10.9 gives remote-controlled models `n_max = 1.5–2`.** A steady `turn_60`
  therefore sits **at or above the top of the RC design band in steady flight**, with zero
  margin for gust or elevator input. A `turn_60` paired with a trainer `n_max` is an
  internally contradictory preset.

**Answer:** **Both are defects and both are fixed** (option a).

**① Turn velocity becomes `max(cruise, 1.05·V_S·√n_target)`.** The maintainer's reason is
the decisive one and is recorded verbatim: *"es soll ja ein fliegbarer OP sein"* — **an
operating point that lies inside the stall boundary is not an operating point.** It is not
a marker placed slightly wrong; it describes a state the aircraft cannot occupy. The `1.05`
keeps a small margin above the boundary rather than sitting on it.

**② Preset cross-validation: `turn_60` ⇒ `n_max ≥ 2.0`.** Cross-field validation of a
preset is a prerequisite to validating anything downstream of it — a preset that
contradicts itself makes every derived verdict meaningless. Recommended practical floor is
`n_max ≥ 2.5` so a gust or a control input does not immediately exceed the envelope.

**③ Related, already recorded at `Q-MS-12`:** `flight_envelope_service._load_operating_point_markers`
(`:600-616`) hardcodes `n = 1.0` for **every** V-n marker, with the comment *"Operating
points represent level flight conditions (n=1.0). Without stored CL, we cannot derive
actual load factor."* Both halves are false — turn points are not level flight, and
`n_target` was already computed by the generator and then discarded. Fixing ① without ②
and ③ would leave the corrected point still plotted on the 1-g line, where `1.3·V_S` looks
perfectly safe.

> **Maintainer's forward note, recorded because it scopes future work rather than this
> question:** *"Auf die OPs muss ich später nochmal genauer schauen, ob sie das bringen,
> was ich haben möchte. Nämlich Aussagen über die Flugeigenschaften des Flugzeugs."*
>
> The generated operating-point set is to be reviewed against the question *does it yield
> statements about the aircraft's flying qualities?* — not merely *does each point trim?*
> Part of the answer already exists in the record from the `Q-AV-8` consultation: at
> 0.5–15 kg the **spiral** is the one dynamic mode that matters, its criterion is
> inertia-free, and the **phugoid** needs only `U₁` and `L/D` — both already available.
> Roll subsidence, dutch roll and short period are non-issues at this scale by margins of
> 1.4× to 14×. A flying-qualities review should therefore start from those two, not from
> the trim status of individual points. **Not a question for this interview.**

---

## Q-MB-3 — Is lateral/vertical CG out of scope?

**Context:** `aggregate_weight_items` computes `cg_x`, `cg_y` and `cg_z`; all
three are serialised on `WeightSummary` and `CGComparisonResponse`; only `cg_x`
reaches `assumption_computation_context.cg_agg_m`. Nothing downstream reads
`cg_y` / `cg_z`.
**Spec affected:** [`_reversa_sdd/mass-and-balance/requirements.md`],
[`_reversa_sdd/mass-and-balance/cg-mass-computation/design.md`]
**Question:** Out of scope, or is a lateral-balance check planned?
**Impact:** Two computed and published fields that no consumer uses.

**Answer:** **ANSWERED by the maintainer, 2026-08-15** (option a) — **both are consumed, but for different reasons and with different consumers: `cg_y` feeds an aileron-trim check, `cg_z` feeds the thrust-line pitch check and nothing else.**

_Expert consensus: Sadraey §11.3.2/§11.3.3 + §12.5.4, with RC-scale numbers computed for a 2 kg / 1.5 m reference airframe._

**① Lateral — `cg_y` earns its keep.**
```
δ_A,trim  =  C_L · y_cg / (b · C_lδA)
```
The trim demand is **independent of dynamic pressure** and scales with `C_L`, so it is worst **slow**, not at cruise — structurally the same shape as Sadraey's rule that longitudinal trim is critical at low speed. Evaluate it at the **approach** condition, never at cruise.

Scale, on the reference airframe: **19 mm (2.5 % of semi-span) ⇒ ~1° of standing aileron**; 37 mm ⇒ 3.1°. A 250 g camera 100 mm off-centre lands exactly there. Build asymmetry — one panel 10 g heavy at a 300 mm mean arm — gives **0.08°**, i.e. noise. **The tool must therefore distinguish deliberate asymmetric payload from build scatter, or it will cry wolf.**

Bands (share of Sadraey's ±20° `δ_Amax` design budget): **≤1° silent · 1–3° warn (domain practice) · >3° defect.** Where aileron geometry is unknown, fall back on `|y_cg|/b` ≤0.005 / 0.005–0.015 / >0.015 with a conservative `C_lδA = 0.25`.

Sadraey treats the **lateral cg range as a first-class design quantity** alongside longitudinal and vertical (§11.3.2), with the ideal at *"the position at which the aircraft requires no aileron deflection to hold lateral trim"* (§11.3.3). This is not an invented consumer.

_Honest bound:_ the pure-aileron figure is an **upper bound** — real free flight settles on a mix of small aileron and small sideslip, because `C_lβ` also supplies rolling moment. Order of magnitude and design conclusion are unaffected.

**② Vertical — `cg_z` is consumed for exactly one reason: the thrust-line arm.**

Sadraey Eq. 12.85 puts `z_T` **inside** the pitch-trim system, and `∂z_T/∂z_cg = 1` exactly, so `cg_z` is a first-class argument of the trim solution:
```
Δδ_E  =  T · z_T / (q·S·C̄ · |C_mδE|)
```
On the reference airframe a **30 mm** offset costs **0.54° at cruise but 6.7° at full power / low speed** — a third of the elevator budget — **and it reverses on throttle chop**. That is the classic *"pitches up when I open the throttle"*, and it is a `cg_z` effect. Per millimetre, `cg_z` is **2.7× more potent than `cg_y`**, on the axis with less margin.

Bands: **≤2° silent · 2–5° warn · >5° defect**, evaluated at **full power, low speed**. For the reference airframe that is `|z_T| ≤ 9 mm` green — thrust-line alignment is genuinely a millimetre-level concern at 2 kg.

⚠️ **Declared limitation (ADR 0020).** `z_T` is only *one* power-on pitch effect at this scale; slipstream over the tail, P-factor and torque are comparable or larger and are **not** CG-derivable. The check must say it models the thrust-line term only, rather than implying it explains the whole throttle-pitch coupling.

**③ Explicitly rejected, with reasons — because both rejected routes are widely believed.**

- **`cg_z` → `C_lβ`: no.** The only real channel is the fin's side force acting on the arm `(z_fin − z_cg)`, worth **≈0.17° of equivalent dihedral per 30 mm**. To buy 1° you would need **176 mm** of vertical CG travel on a 1.5 m model — the fuselage is ~100 mm deep, so it is structurally unreachable. Meanwhile the effect people attribute to it — high-wing vs low-wing, worth ~3.5° of dihedral equivalent — comes from **wing-fuselage crossflow interference**, geometry the tool already has. Feeding `cg_z` into `C_lβ` would capture 0.17° while the geometry carries 3.5°.
- **Pendulum stability: does not exist.** A free-flying aircraft rotates about its **own CG**, and weight acts at the CG, so its moment about the CG is identically zero. Neither Sadraey nor Scholz has such a derivative; the physics authority rejects it outright. What hobbyists call pendulum stability is the keel effect — which *is* the `C_yβ·z` channel above, already quantified as negligible. **The dihedral tables built on that folk explanation remain correct; only the explanation is wrong. Do not use the mechanism correction to discard the tables.**
- **`cg_z` → `I_xx` roll authority:** Sadraey's own §11.3.3 z-axis criterion, but moving a 500 g battery 40 mm changes `I_xx` by <1 %. Not worth a consumer.

**④ Landing gear — conditional, and not implemented now.** `α_tb = atan(x_mg/h_cg) ≥ α_TO + 5°` (§9.6.1) is a **live** constraint at RC proportions (18.4° vs 15° required — only 3.4° margin), while overturn `φ_ot ≥ 25°` (§9.5.3) is satisfied 2–3× over and is not binding. Both are pure geometry and transfer to RC scale unchanged. **Gated on landing-gear geometry existing in the model**; until it does, this consumer does not exist and `z_T` is `cg_z`'s only justification.

---

## Q-MB-4 — Should the CG comparison include the component tree?

**Context:** Only `weight_items` carry positions, so an aircraft built entirely
in the component tree has a known mass and a **`null` aggregate CG** — and the
response gives no reason why. `within_tolerance` is reported as *absent*, never
*false*, which is correct but indistinguishable from "no items".
**Spec affected:** [`_reversa_sdd/mass-and-balance/cg-mass-computation/requirements.md`] (BR-MB7)
**Question:** Should tree nodes carry positions, or should the response explain
why the comparison is absent?
**Impact:** ADR 0011's feedback signal is unavailable for tree-built aircraft.

**Answer:** _(derived — not a maintainer decision)_ **Yes — the CG comparison reads the component tree, and the tree ultimately becomes the only CG source.**

Follows from **Q-MB-1**, which answers this question by name: "**CG must read the tree.** Today `mass_cg_service` reads **only** `WeightItemModel` (`:200`, `:230`), even though the tree carries `pos_x/y/z`. This answers `Q-MB-4`: yes — and ultimately the tree becomes the *only* CG source." The mm ↔ m conversion from Q-MB-1 §4 applies to these positions as well, and a `null` aggregate CG then means "no positioned nodes", which the response states rather than leaving unexplained.

---

## Q-MB-5 — Should `PUT` on a weight item be a `PATCH`?

**Context:** `update_weight_item` uses `model_dump()` **without**
`exclude_unset`, so it is a full replacement: an omitted `x_m` silently resets a
position to `0.0`. This is a plausible source of "my battery moved" reports.
**Spec affected:** [`_reversa_sdd/mass-and-balance/weight-items/requirements.md`] (RF-05)
**Question:** Should it be a PATCH?
**Impact:** Silent data loss on a partial update.

**Answer:** _(derived — not a maintainer decision)_ **Moot — `weight_items` is retired, so there is no `PUT` left to convert to a `PATCH`.**

Follows from **Q-MB-1**: `weight_items` becomes a read-only view and is removed once nothing depends on it, so RF-05's full-replacement update disappears with the resource. The underlying defect — `model_dump()` without `exclude_unset` silently resetting an omitted position to `0.0`, a plausible source of "my battery moved" reports — is worth re-checking on the component-tree node update path during the migration, but that is a new finding rather than an answer to this question.

---

## Q-MB-6 — What is the sign convention of `delta_x`?

**Context:** `delta_x = cg_x_design − cg_x_components`, so a **positive** delta
means the design CG is *aft* of the components. Nothing in the code says so, and
a UI can invert it silently.
**Spec affected:** [`_reversa_sdd/mass-and-balance/cg-mass-computation/contracts.md`]
**Question:** Confirm the convention so it can be stated in the contract.
**Impact:** A sign error here inverts the user's corrective action.

**Answer:** _(expert consensus, endorsed by the maintainer 2026-08-14)_ **Confirmed — keep the arithmetic `cg_design − cg_agg` with *x positive aft from the aircraft datum*, but rename the field to `required_cg_shift_x_m` ("positive = move mass aft") and ship a categorical `cg_verdict ∈ {NOSE_HEAVY, TAIL_HEAVY, ON_TARGET}` that the UI drives off instead of the sign.**

Neither authority publishes a signed delta. Sadraey publishes **non-dimensional positions** — `h = (x_cg − x_LE_MAC)/C̄`, with `h_for` and `h_aft` (Eqs. 11.11–11.13) — and expresses the corrective action **categorically**: when the cg cannot be brought into range by weight distribution, **ballast** is added at a named location; his forward-vs-aft consequence table (forward: more stable, less controllable, more nose-wheel load, more elevator to rotate; aft: the reverse) shows the meaningful output is *which side you are on*, not a raw number. RC practice is identical and even more explicit: Lennon's balancing-act procedure produces exactly two verdicts and a named action for each — **"Tail-heavy: move power, nosewheel and possibly fuselage servos forward… Nose-heavy: best solution is to move the wing forward"**. No modeller reasons about a signed `Δx`; they reason about nose-heavy vs tail-heavy.

Five changes to what is published (`mass_cg_service.py:238` keeps computing the same value): **(1)** state the axis convention explicitly in the contract — *x is positive aft, measured from the aircraft datum* — because everything else is undefined without it. **(2)** Rename `delta_x` → **`required_cg_shift_x_m`**, defined as *"the distance the aggregate (component) CG must move to reach the design CG; positive = move mass aft"*, so a frontend cannot get it backwards from the field name alone. **(3)** Ship the verdict token alongside it and make the UI drive off the token, not the sign — this is the actual defence against inversion: `NOSE_HEAVY ⇔ required_cg_shift_x_m > +tol` (components are forward of the design CG, so move mass **aft**), `TAIL_HEAVY ⇔ < −tol`, `ON_TARGET` otherwise. A sign error in the frontend then produces a visible *contradiction* between token and number instead of a silently inverted instruction. **(4)** Report the shift in **% MAC** as well as metres: `Δx/MAC` is the number both authorities actually use, it is scale-free, and at RC scale a 10 mm shift is ~3 % MAC on a 300 mm chord but ~1 % on a 1 m chord — the metre value alone does not tell the user whether it matters. **(5)** Make the tolerance relative: `CG_TOLERANCE_M = 0.01 m` is a fixed absolute, and on a 300 mm MAC that is **3.3 % MAC** — large enough to be felt in pitch. Use **1 % MAC, floored at 5 mm** for buildability.

**Authority:** Sadraey Eqs. 11.11–11.13 (non-dimensional cg positions) and the forward/aft consequence table; Lennon Ch. 6 ("balancing act", the two named verdicts).
**Confidence:** high — this is a contract/ergonomics ruling and both authorities converge on it independently: publish the side, not just the signed scalar.

_Full reasoning: [`expert-consensus-sizing.md`](expert-consensus-sizing.md)_

---

## Q-MB-7 — `GET /total_mass_kg` vs the `mass` design assumption: which is authoritative?

**Context:** Two different masses with no reconciliation. `total_mass_kg` gates
the `AirplaneConfiguration` export; the `mass` assumption drives every sizing
surface. A consumer reading only one has no way to know the other exists.
**Spec affected:** [`_reversa_sdd/mass-and-balance/requirements.md`],
[`_reversa_sdd/aeroplane-core/requirements.md`] (RF-05/RF-06)
**Question:** Which is authoritative, and should one derive from the other?
**Impact:** Two "the aircraft's mass" endpoints that can disagree.

**Answer:** **The `mass` design assumption is authoritative; `total_mass_kg` becomes a
derived view of it.** _Answered by the maintainer, 2026-08-15._

**The maintainer's actual workflow is exactly ADR 0010's duality:** total mass is
*estimated* first (at the start of design there are no components yet), and that
estimate is then *improved* by the sum of the component tree. The `mass` assumption
already models precisely this — `estimate_value`, `calculated_value` (fed by the
component tree per `Q-MB-1`), and which one is in effect, with automatic switching.
`aeroplanes.total_mass_kg` is a bare float carrying none of that: the same number, with
no way to tell whether it holds the estimate or the tree sum.

**Concretely:**

| Today | After |
|---|---|
| `POST /total_mass_kg` writes the column | writes the assumption's **estimate** side |
| `GET /total_mass_kg` reads the column | returns the **effective** value (calculated if present, else estimate) |
| The `AirplaneConfiguration` export gate checks the column | checks the assumption |
| The number carries no provenance | provenance is available |

**Why this is not cosmetic.** Set `total_mass_kg = 3.2 kg` early; later the tree fills
up and `Q-MB-1` writes `calculated_value = 3.6 kg` into the assumption. From then on
the matching chart, `V_stall`, the solution space and endurance use **3.6 kg** while
the export gate still sees **3.2 kg** — and nothing reports the divergence, because the
tree sync never touches the column. Two numbers with the same name, free to drift.

Instance of ADR 0022 (one authority per user-facing quantity).

---

## Q-MB-8 — Should `GRAVITY` and `RHO` live in one physical-constants module?

**Context:** `GRAVITY = 9.81` in `mass_cg_service` vs `G = 9.80665` in
`endurance_service`, `powertrain_performance` and
`powertrain_solution_space_service`. 0.007 % — numerically irrelevant — but there
is no single constant. `RHO = 1.225` is likewise duplicated and "kept in sync by
comment".
**Spec affected:** [`_reversa_sdd/mass-and-balance/requirements.md`] (BR-MB9),
[`_reversa_sdd/domain.md`]
**Question:** Centralise in `app/core`?
**Impact:** Cosmetic today, but the comment-based sync is fragile.

**Answer:** _(derived — not a maintainer decision)_ **Yes — one physical-constants module, one value per constant; `g` and `ρ` stop existing in four copies kept in sync by comment.**

Follows from **Q-CC-4**, which settled the identical pattern: three coexisting version strings collapse to a single source "so release, `/health` and OpenAPI cannot disagree", and the three `os.getenv` escapees are folded in. `GRAVITY = 9.81` versus `G = 9.80665` is numerically irrelevant (0.007 %) but structurally the same defect, and centralising gives the still-open atmosphere question (`Q-PT-9`) exactly one place to be resolved.

---

## Q-MB-9 — Should `list_weight_items` call the shared aggregation helper?

**Context:** The same aggregation is implemented twice — rounded to 6 dp in
`weight_items_service.list_weight_items`, unrounded in
`mass_cg_service.aggregate_weight_items`. They agree today and nothing tests that
they still do. Two "empty" conventions also coexist inside one module:
`list_weight_items` reports `total_mass_kg = 0` with `null` CGs for an empty
inventory, while `get_aircraft_total_weight_kg` reports `null` for an empty tree —
and both feed the same `mass` assumption.
**Spec affected:** [`_reversa_sdd/mass-and-balance/weight-items/design.md`] (BR-MB14)
**Question:** Consolidate onto the shared helper, and pick one empty convention?
**Impact:** A divergence here would be invisible until the numbers drifted.

**Answer:** _(derived — not a maintainer decision)_ **Both resolve with the retirement: the duplicated aggregation disappears together with `weight_items`, and the surviving empty convention is `null`, not `0`.**

Follows from **Q-MB-1** and **P-WARN-0**/ADR 0012: once only the component tree produces mass, `weight_items_service.list_weight_items`'s 6-dp copy of `mass_cg_service.aggregate_weight_items` has nothing left to aggregate, so the untested "they agree today" risk is removed rather than tested. Of the two coexisting empty conventions, the tree's (`null` for an empty tree) is the one consistent with "null is an honest no value, never a fabricated fallback" — a `0 kg` aircraft is a fabricated number.

---

## Q-MB-10 — Should `weight_items.category` be constrained at the database?

**Context:** `WEIGHT_CATEGORIES = electronics | battery | structural | payload |
other` is enforced by Pydantic only; the DB column is a plain `String` with no
CHECK. Also: 409 is declared on all five weight-item routes and is unreachable —
no service path raises `ConflictError`. And there is no `name` uniqueness and no
user-facing ordering field; items come back in insertion order.
**Spec affected:** [`_reversa_sdd/mass-and-balance/weight-items/contracts.md`] (BR-MB15)
**Question:** Push the constraint to the DB? Remove the unreachable 409?
**Impact:** Three contract rows.

**Answer:** _(derived — not a maintainer decision)_ **No CHECK constraint — the table is being retired; the unreachable 409 is removed, and the closed-set question moves to the component tree.**

Follows from **Q-MB-1**, **Q-CC-9** and **P-DEAD-0**: Q-CC-9 deliberately left `weight_items.category` out of the constrained set pending "is it genuinely closed", and Q-MB-1 removes the table altogether, so paying for a migration on it would be wasted — the categories are preserved or mapped onto tree nodes, where Q-CC-9's CHECK on `component_tree.node_type` is the relevant enforcement point. The 409 declared on all five routes is unreachable dead surface (P-DEAD-0 rule 3), and the per-module error mapping that produced it is deleted by Q-CC-3 in any case; insertion ordering has no consumer once the resource is gone.

---

## Q-MB-11 — Is `print_resolution_mm` a node field or a material spec?

**Context:** `component_tree_service.py:454` reads it from the **material's**
`specs` with a `0.4` default, and `component_type_service.py:347` declares it on
the seeded `material` type. But the `aeroplane-core` contract lists it among the
tree-node payload fields. One of the two is wrong, and the code is the code.
**Spec affected:** [`_reversa_sdd/aeroplane-core/component-tree/contracts.md`],
[`_reversa_sdd/mass-and-balance/design.md`]
**Question:** Confirm it is a material spec so the `aeroplane-core` contract can
be corrected.
**Impact:** One contradicted field between two module specs.

**Answer:** _(resolved by code lookup — not a maintainer decision)_ **A material spec, not a component-tree node field — the `aeroplane-core` contract is the one that is wrong.**

`print_resolution_mm` is declared as a field of the `3d_print_material` **component-type schema** (`app/services/component_type_service.py:335-353`: unit mm, range 0.05–2.0, default 0.4) and read off the linked material component's `specs` (`app/services/component_tree_service.py:446-456`); it appears nowhere in `app/models/`. The only node-level field in that calculation is `print_type`, which *is* a real column (`app/models/component_tree.py:60`), and the resolution enters the weight only for `print_type == "surface"` nodes, as `weight_g = area_mm2 × resolution_mm × density_kg_m3 / 1e6 × scale_factor` — volume-printed nodes ignore it entirely. Minor cleanup available: the `0.4` default is hand-maintained in two places (`component_type_service.py:352` and `component_tree_service.py:454`).

**Verdict:** confirmed safe

_Full detail: [`wave3-lookups.md`](wave3-lookups.md) §O_

---

# powertrain

## Q-PT-1 — What is the intended ESC selection criterion?

**Context:** `_find_matching_esc` returns the **first** ESC in unordered query
order (`db.query(...).all()` has no `ORDER BY`) — not the lightest, cheapest or
smallest that fits. The recommendation is therefore arbitrary and can change
between runs. Related: a candidate with `esc_id = null` is returned unflagged, so
the UI cannot distinguish "no ESC needed" from "no ESC fits".
**Spec affected:** [`_reversa_sdd/powertrain/powertrain-sizing/requirements.md`]
**Question:** Lightest? Cheapest? Smallest sufficient current headroom?
**Impact:** A user-facing recommendation that is currently non-deterministic.

**Answer:** _(expert consensus, endorsed by the maintainer 2026-08-14)_ **Replace the first-match rule with an all-of gate on **peak** current at sag voltage — `continuous ≥ 1.4 × I_design` — plus a deterministic sort (mass → current → id); cruise current is the wrong load case by construction.**

`powertrain_sizing_service.py:104-113` returns the **first** ESC in unordered query order whose `continuous_current_a` ≥ `min_current_a`, and the call site (`:259`) passes **`cruise_current_a`** — the battery current in level cruise at *nominal* pack voltage — with no burst, cell-count or BEC check. Sadraey treats propulsion-component selection as constraint satisfaction over the **whole flight envelope**: the sizing case is the most demanding segment (take-off/climb), where shaft power and hence current peak. The physics agrees independently — an ESC is a thermal device (loss ≈ I²·R_ds(on) + switching loss), its failure mode is junction temperature, and thermal time constants for a 30–100 g ESC are tens of seconds, far longer than a full-throttle climb. Define `I_design` as the largest **sustained** battery current in the mission evaluated at **sag voltage (3.5 V/cell)**, not nominal; where the sizing path has no throttle sweep, use the motor as the limiter: `I_design = max(I_peak_computed, motor.max_current_a)`.

**Gates, all of which must pass, in this order.** (1) `esc.continuous_current_a ≥ 1.4 × I_design` — **1.2 is the absolute floor** for a well-cooled uncowled installation, 1.4 is the default (matching the `esc_margin` already defaulted in `powertrain_solution_space.py:59-63`, which also closes half of Q-PT-8), exposed as a user-editable assumption. (2) `esc.max_current_a ≥ I_design_burst` with `I_design_burst = motor.max_current_a`; if `max_current_a` is NULL, treat burst as **equal to continuous** — never assume the catalogue-typical 1.3×. (3) `esc.cells_lipo_min ≤ S ≤ esc.cells_lipo_max`, **two-sided**, plus `S × 4.2 V ≤ esc.max_voltage_v` where that field exists — RC-Network specifies the maximum voltage as the *unloaded* terminal voltage, so the check uses **4.2 V/cell, not 3.7 V nominal**. (4) A **BEC gate conditional on the design declaring servo power from the ESC**: `bec_current_a ≥ 0.3 A × n_servos` continuous plus the required BEC voltage; an OPTO ESC (`bec_current_a` NULL) is admissible **only** when a separate receiver supply is declared. **This gate must run before the sort** — otherwise the mass sort picks the OPTO. Then **sort survivors by `mass_g` ascending → `continuous_current_a` ascending → `id` ascending**; cheapest is not selectable (there is no price column). The shipped 19-ESC catalogue makes all three traps concrete: burst/continuous ratios run **1.18–1.50**, so burst headroom is not free; `Antares 85A OPTO` is **10 g lighter** (47 g vs 57 g) than the identically-rated SBEC, so a naive "pick the lightest" selects an ESC that cannot power the receiver; and `AVICON PRO 65A HV` has `cells_lipo_min = 6`, so a one-sided "≤ max" check hands a 3S design an ESC that will not run. ESC mass scales tightly with rating (6 A → 6 g … 100 A → 80 g), so "lightest" and "smallest sufficient" almost always coincide — which is exactly why the tie-break must be written down rather than left to query order. Finally, **`esc_id = null` must carry a reason** (`no_esc_required` vs `no_esc_fits`, naming the binding gate): the UI cannot tell the two apart today, and that is a contract defect, not a cosmetic one.

**Authority:** Sadraey ch. 8 (propulsion-component selection over the flight envelope) decides the **load case**; RC-Network Wiki *Motorsteller* / *BEC* supplies the **margins and the gate structure** (continuous rating as "the most important specification"; continuous and burst as separate gates; maximum *unloaded* voltage; BEC current "critical for selecting an appropriately-sized controller"); the shipped D-Power catalogue supplies the counter-examples.
**Confidence:** high — load case and gate structure are decided by first principles and confirmed by the catalogue; only the 1.4 multiplier is a convention rather than a derivation.
Disagreement: none on substance. The only tension is the margin value — RC practice has no single number (vendors quote 1.2–2.0) while the repo's own solution space already committed to 1.4. Scholz decides the load case, RC practice supplies the margin, and the repo's existing 1.4 breaks the tie in favour of internal consistency.

_Full reasoning: [`expert-consensus-powertrain.md`](expert-consensus-powertrain.md)_

---

## Q-PT-2 — Should propeller mass enter the sizing total?

**Context:** `size_powertrain` sums airframe + motor + battery only, although
`propeller_polars.weight_g` now carries real masses (gh-1000/1017). Related: a
`NULL` `mass_g` on a motor or battery **silently drops that mass term** from
`total_mass` rather than rejecting the combination.
**Spec affected:** [`_reversa_sdd/powertrain/powertrain-sizing/requirements.md`]
**Question:** Should the chosen propeller's mass be included, and should a NULL
mass reject the candidate?
**Impact:** The sizing total is the input to wing loading and stall speed.

**Answer:** _(expert consensus, endorsed by the maintainer 2026-08-14)_ **Yes — add the selected propeller's `weight_g` to `total_mass` as a fourth line item (1–3 % of AUM, and always one-signed on stall speed); a NULL `mass_g` must raise an error-severity `DesignWarning` and exclude the candidate, never contribute zero.**

Sadraey is unambiguous on the principle: Eq. (10.9) defines the installed engine weight as the engine plus all installation hardware "**and propeller(s) for prop-driven aircraft**", and the propulsion group mass is a first-class term in the empty-weight buildup that feeds W/S and the cg calculation. **But the equation does not transfer to this scale** — applying `W_E_ins = K_E·(N_E·W_E)^0.9` with `K_E = 3` (SI) to an 80 g RC outrunner (W_E = 0.785 N) yields `3 × 0.785^0.9 = 2.41 N ≈ 246 g`, i.e. **3.1× the bare motor mass**, because `K_E` is dimensional and calibrated on GA-size engines. Take the principle, reject the formula. Measured medians from the shipped 454-propeller APC dataset: 4–6 in **4.2 g**, 6–8 in **9.9 g**, 8–10 in **21.2 g**, 10–12 in **29.5 g**, 12–14 in **44.3 g**, 14–17 in **70.3 g**, 17–30 in **133.1 g**. Effect on the quantities `total_mass` feeds: 0.8 kg park flyer with an 8×4 → 21 g = **2.6 %** of AUM → +2.6 % wing loading, +1.3 % stall speed; 1.5 kg sport / 10×5 → 30 g = 2.0 % → +1.0 % stall; 3 kg e-glider / 12×6 → 44 g = 1.5 %; 5 kg UAV / 16×8 → 70 g = 1.4 %. Since `V_stall ∝ √m`, the stall-speed error is exactly half the mass error. Small — but **one-signed**: omitting it always under-predicts mass, wing loading and stall speed, and a systematic optimistic bias in a stall speed shown to a hobbyist is the wrong direction to be wrong in.

Do **not** apply Sadraey's installation factor; instead expose an optional `prop_installation_mass_g` assumption (spinner + adapter), **default 0**, and document that `weight_g` is the **bare blade** — spinner, adapter and bolts are extra and are not in the dataset. Inventing a scaled-down `K_E` would be a fabricated number. On NULL masses: `powertrain_sizing_service.py:212-213` uses `(motor.mass_g or 0) / 1000.0`, so a missing mass **silently contributes zero**. Replace it with an explicit policy — emit an **`error`-severity `DesignWarning`** naming the component and field (the warning policy already exists, reuse it) and **exclude the candidate from the ranked list**, returning it in an `excluded` array with the reason. Dropping it silently and returning a confident flight time computed from a wrong mass is worse than returning nothing. Note the dependency this creates: sizing currently selects motor + battery + ESC but not a propeller, so either **(a)** select a propeller in the same pass — which Q-PT-3 needs anyway — or **(b)** accept a user-supplied `prop_mass_kg` and warn when it is absent. **(a) is preferred**; the two questions share the same fix.

**Authority:** Sadraey Eq. (10.9) / §10 (propeller mass belongs to the propulsion group) for the principle, with the scale argument rejecting the formula; the shipped APC dataset for the masses; `V_stall ∝ √m` for the propagation.
**Confidence:** high — inclusion is decided by the lead authority and the magnitudes are measured from the shipped data; only the spinner/adapter allowance is left open, deliberately.
Disagreement: none. Scholz and RC practice agree; they differ only on whether an installation factor applies, and the scale argument settles that against the factor.

_Full reasoning: [`expert-consensus-powertrain.md`](expert-consensus-powertrain.md)_

---

## Q-PT-3 — Should the solution-space KV now use the APC polar database?

**Context:** `_PHASE1_PROP_DIAMETER_M` fixes the propeller diameter at 0.30 m,
documented as a Phase-1 approximation awaiting #615 — **which has since
shipped**, with 454 real propellers one table away.
**Spec affected:** [`_reversa_sdd/powertrain/powertrain-sizing/design.md`]
**Question:** Should the KV estimate now be derived from the polar database?
**Impact:** A documented placeholder whose blocker is resolved.

**Answer:** _(expert consensus, endorsed by the maintainer 2026-08-14)_ **Yes — the blocker is resolved and the fixed `_PHASE1_PROP_DIAMETER_M = 0.30` placeholder is wrong by up to 2× at the small end of the target range; size the diameter from the power requirement and take the advance ratio from the selected propeller's own polar.**

`powertrain_solution_space_service.py:157-159` sets `prop_d = 0.30` for every aircraft, then `rpm_target = (v_top/(prop_d·prop_pd))·60` and `kv_approx = rpm_target/(v_nom·0.85)`. Setting `n = V/(D·P/D)` asserts **J = P/D** at top speed — and measured across all 454 shipped APC propellers, `J` at maximum efficiency ÷ (pitch/diameter) has median **0.951** (p10 0.900, p90 1.035), so **the pitch model is only ~5 % off** (APC's geometric pitch is defined near 75 % radius, which is why it lands close to the effective pitch); zero thrust sits at `J ≈ 1.238 × P/D`, comfortably clear. **The error is entirely in the fixed diameter.** Since `J = V/(nD)`, holding D at 0.30 m scales RPM and hence Kv by `0.30/(0.95·D_true)`: a 6 in prop → **−108 %** (true Kv ≈ 2.1× the estimate), 8 in → −56 %, 10 in → −24 %, 12 in → −4 % (the placeholder's design point), 16 in → +28 %. Sadraey confirms the shape of the fix from the academic side — Eq. (8.13) makes diameter an *output* of the power and speed requirement, `D_P = K_np·√(2·P·η_P·AR_P/(ρ·V_av²·C_LP·V_C))` — and his worked method matches propeller to engine via a gearbox ratio (Eq. 8.14); direct-drive electric has no gearbox, so **Kv *is* the gear ratio**, which is the correct conceptual mapping.

Correct chain, all quantities already available: **(1)** size the diameter from the power requirement — either Sadraey Eq. (8.13) or, better since the data is one table away, select the propeller from `propeller_polars` whose polar delivers the required thrust at the design speed within the disk-loading and tip-speed limits. **(2)** Take the operating advance ratio from *that* propeller's polar — `J` at the maximum `Pe` row nearest the design RPM band — falling back to **`J = 0.95 × (pitch/diameter)`**, a measured relation rather than a guess. **(3)** `n = V_design/(J·D)`, then check `V_tip = √((π·D·n)² + V²) ≤ **150 m/s**` and reject or re-select if violated. **(4)** `Kv = n_rpm/(V_nom × 0.85)` — keep `load_rpm_factor = 0.85`, which is exactly ROXXY's "≈ 85 % of no-load RPM under realistic model-flight loading" and is confirmed correct. **(5)** Use the selected propeller's **`Pe` at that `J`** as `eta_prop` instead of the constant `DEFAULT_ETA_PROP = 0.65` (`endurance_service.py:53`) — 0.65 equals the **p10** of the measured APC maximum efficiencies, i.e. the worst propeller's best point, while the median is **0.786**, squarely inside Sadraey's η_P = 0.75–0.85 band — and its **`weight_g`** for Q-PT-2. Report the selected propeller (name, D, P, mass) alongside the Kv so the recommendation is inspectable, drop the "Phase 1 / approximate" caveat from the schema description once the polar path is live, and keep the fixed-diameter formula only as a documented fallback for an empty polar table. `prop_pd = 0.65` is well placed for trainer/scale (RC practice by mission: 3D ≈ 0.5, scale ≈ 0.6–0.7, glider/e-sailplane ≈ 0.7–0.9).

**Authority:** Sadraey Eq. (8.13) (diameter from power), Eq. (8.14) (propeller–engine matching) and the tip-speed table (**150 m/s for a plastic prop on an RC model aircraft** — the single most directly applicable academic number in the corpus for this tool); ROXXY *Motoren-Fibel* for `no-load RPM = Kv × V` and the 85 % load factor; the shipped 454-propeller APC dataset for the 0.951 / 1.238 / 0.786 measurements.
**Confidence:** high — the ratios are measured across the full shipped dataset with tight spread, and the diameter-error table follows algebraically.
Disagreement: mild, on the tip-speed ceiling — Sadraey says **150 m/s** for RC plastic props while ROXXY practice says Ma ≈ 0.4–0.6 (**130–200 m/s**). Resolved in favour of Scholz per the authority hierarchy: cap at **150 m/s** (≈ Ma 0.44), which sits inside the RC band anyway, and use the RC upper end only as a "you are past the recommended limit" warning threshold, never as the gate.

_Full reasoning: [`expert-consensus-powertrain.md`](expert-consensus-powertrain.md)_

---

## Q-PT-4 — Which spec-key spelling is canonical?

**Context:** Three vocabularies for the same physical quantities. C-rate is
`c_rate` (`BatterySpec`) vs `c_rating` / `discharge_c` (`_catalog_battery_match`);
ESC current is `continuous_current_a` / `max_continuous_a` / `max_current_a`
depending on the reader. **A battery imported under one spelling is invisible to
the other consumer.**
**Spec affected:** [`_reversa_sdd/powertrain/cots-powertrain-components/requirements.md`]
**Question:** Which key is canonical, and should the importers normalise?
**Impact:** Silently invisible catalogue entries.

**Answer:** **The Pydantic spec-model spellings are canonical; the importers
normalise.** _Answered by the maintainer, 2026-08-15._

Canonical: `c_rate` (not `c_rating` / `discharge_c`), `continuous_current_a` (not
`max_continuous_a` / `max_current_a`). Importers normalise incoming keys to these, and
an **unrecognised spec key is reported, not silently swallowed** (`P-WARN-0`).

Motivation: today a battery imported under one spelling is **invisible** to the other
consumer — it simply never appears in the selection, with no error. Direct instance of
ADR 0022.

---

## Q-PT-5 — Is the `component_types` schema a complete contract or a minimum?

**Context:** `validate_specs` never rejects unknown `specs` keys — the seed
writes `variant`, which is not in the `propeller` schema. And
`prop_component_seed` **bypasses `validate_specs` entirely**, writing
`ComponentModel` rows directly, so a polar with a NULL `diameter_in` / `pitch_in`
produces a component that violates the seeded schema (both `required`) and 422s
on the first API `PUT`.
**Spec affected:** [`_reversa_sdd/powertrain/cots-powertrain-components/requirements.md`],
[`_reversa_sdd/powertrain/propeller-polars/requirements.md`]
**Question:** Should the seed validate, or should the schema mark those fields
optional? Is the schema meant to be a complete contract or a minimum?
**Impact:** Seeded components that the API then rejects.

**Answer:** **A complete contract — the schema is binding for every writer,
including the seeds.** _Answered by the maintainer, 2026-08-15._

`component_types.schema` is the contract, not a minimum. Consequences:

- **`validate_specs` rejects unknown keys.** The seed currently writes `variant`,
  which the `propeller` schema does not declare — either the key is added to the
  schema or it stops being written.
- **`prop_component_seed` must validate like every other writer.** It currently
  bypasses `validate_specs` entirely and writes `ComponentModel` rows directly, which
  is how a polar with NULL `diameter_in` / `pitch_in` produces a component that
  violates the seeded schema (both `required`) and then **422s on the first API
  `PUT`** — a row the system created and subsequently refuses.
- A propeller polar that cannot satisfy the schema must therefore **not be turned into
  a component**; the skip is counted and reported rather than producing an
  unusable row.

Accepted cost: a new spec key becomes a schema change. That is the point of choosing
"contract" over "minimum".

---

## Q-PT-6 — Is a winding-resistance data source planned for QPROP?

**Context:** `rm_ohm` is absent from the D-Power catalog, so **every seeded motor
falls back to the fixed-RPM approximation** whose own docstring calls it a
simplification. The physically better QPROP model is dormant for the entire
shipped catalogue.
**Spec affected:** [`_reversa_sdd/powertrain/performance-model/requirements.md`]
**Question:** Is a data source planned, or should `Rm` be estimated from `Kv` and
no-load current?
**Impact:** Every production performance curve comes from the approximation.

**Answer:** _(expert consensus, endorsed by the maintainer 2026-08-14)_ **Rm is NOT a prerequisite: the simpler fixed-RPM model stays the default, the QPROP-fidelity path is offered only for motors that actually have Rm, and the response declares which model fidelity was used. Rm must be sourced opportunistically where a manufacturer publishes it — and never synthesised from Kv and i₀.**

**The maintainer has no test rig and cannot buy 41 motors, and two facts were verified during the interview.** D-Power publishes **no** winding resistance: the raw `data/cots/dpower.json` motor specs are only `kv_rpm_per_volt`, `io_no_load_a`, `continuous_current_a`, `max_current_a`, `cells_lipo_min/max`, `shaft_diameter_mm`, `static_thrust_g`, `art_no`. And the D-Power manual PDFs (`components/cots-assets/dpower/manuals/V3_AL-Manual_print_A5_Max.pdf`) contain a **specification table with one row per motor**, not a multi-point bench table — a single "ca. 300 g" thrust figure at unstated voltage with a recommended prop range — so **a voltage-balance fit is impossible from this source.** The PDF route is therefore recorded as **investigated and closed.** Add `rm_ohm` to the importer's spec vocabulary and populate it **opportunistically** where a manufacturer publishes internal resistance (Hacker, Scorpion, T-Motor, AXi commonly list `Ri` in mΩ); **partial coverage is accepted and made visible**. Per `P-WARN-0` the response must **declare which model fidelity was used** — fixed-RPM approximation vs QPROP three-parameter — rather than advertising a missing refinement in a free-text note (`powertrain_performance.py:795`).

**Rm still matters, and it matters where the sizing constraints bind** — which is why the QPROP path is worth offering when the data exists. Copper loss is `I²R`: on 3S (11.1 V), an Rm of 0.05 Ω costs 1.3 W = 2 % at 5 A but 20 W = **9 %** at 20 A; 0.10 Ω costs 2.5 W = 5 % at 5 A and 40 W = **18 %** at 20 A. So an Rm uncertainty of ±0.05 Ω moves motor efficiency by ~9 points at 20 A — i.e. exactly at climb and full throttle. (For comparison, the i₀ term the catalogue *does* carry is `i₀·V ≈ 0.7 A × 11 V ≈ 7.7 W`, ~6 % of a 122 W input — having i₀ without R gives you the model's smaller term only.) **The consensus's method hierarchy is retained as documentation of *how* Rm should be obtained if a source ever provides it:** (1) vendor-published `Ri` — a data-coverage task, not a modelling task; (2) a **Coates voltage-balance fit** `U_dd·δ_t = R·I_a + k_E·ω` solved as two-parameter linear least squares where a vendor publishes ≥ 2 operating points of (voltage, current, RPM), stored as `rm_source = "fitted"`, with samples weighted by `I_a²` because unmodelled ESC switching and eddy losses degrade the fit at light load; (3) **locked-rotor measurement** per Drela `motor1` §2 (milliohmmeter, or hold the shaft and sweep terminal voltage with `R = v/i` averaged over shaft positions) for motors the user physically owns, should the tool ever grow a "measure my motor" input. **(4) Never estimate Rm from Kv and i₀.** The three parameters are independent and there is no derivation from the other two; the physically motivated scaling `R ∝ 1/(Kv²·m_motor)` (turns N: `Kv ∝ 1/N`, `R ∝ N²`) is real but needs a per-frame-family calibration constant the repo does not have, and a single anchor point cannot establish it.

**Two clarifications that change what "Rm" means in this code.** The parameter QPROP wants for an ESC-driven system is the **circuit** resistance (winding + ESC + cable), not the motor-only datasheet value: the Coates validation on a Hacker A40-12S V2 gives 0.031 Ω (motor spec) vs **0.0587 Ω fitted** (R² = 0.9971), a ~90 % difference that dwarfs the modelling gain of switching from fixed-RPM to QPROP. Name the field's meaning explicitly, and where the value came from a motor datasheet either add the ESC/cable term or document that the model runs optimistic. Second, datasheet R is **cold**: under a full-throttle climb the winding runs 50–80 K hotter and copper's temperature coefficient (~0.0039 /K) raises R by **20–30 %** — either accept the optimism and document it, or apply a hot-resistance correction as an explicit, user-visible assumption.

**Authority:** Drela `motor1` §1.1 (the three-parameter model `V = i·R + Ω/Kv`, `Q_m = (i − i₀)/K_Q`; i₀ typically 0.5–2 A for small RC motors, consistent with the 0.4–0.7 A in the shipped catalogue) and §2 (measurement protocol, hot-vs-cold resistance); Coates 2019 §II.D / §V.A (voltage-balance system ID, Hacker A40-12S validation). Sadraey is silent — electric motor internals are below the granularity of conceptual aircraft design, which pushes the decision down the hierarchy to the tool/practice layers. **The ruling that Rm is not a prerequisite, that coverage is opportunistic and partial, and that the PDF route is closed: maintainer decision, 2026-08-14, on verified data-availability grounds.**
**Confidence:** high on the method and the ranking; the coverage question is settled by the maintainer's verification rather than left open.
Disagreement: none between the sources. The only tension is internal to RC practice — Drela's protocol yields the **motor** resistance while Coates' fit yields the **circuit** resistance, and the code has one field. Since the code models a full electric drivetrain the circuit interpretation is correct, but it must be labelled, because the two differ by ~2× in the one validated case available.

_Full reasoning: [`expert-consensus-powertrain.md`](expert-consensus-powertrain.md)_

---

## Q-PT-7 — Should the whole COTS library be versioned?

**Context:** `components`, `component_types` and the polar tables are shared
across aircraft and deliberately excluded from cloning, so editing a component's
`mass_g` **retroactively changes the mass of every historical snapshot** that
references it.
**Spec affected:** [`_reversa_sdd/powertrain/requirements.md`],
[`_reversa_sdd/versioning/aeroplane-clone-subgraph/requirements.md`]
**Question:** Intended, or should component data be versioned too?
**Impact:** Breaks the immutability promise of `versioning` from the outside.

**Answer:** **No — the COTS library is NOT versioned. Corrections propagate to
historical snapshots, and that is intended.** _Answered by the maintainer, 2026-08-15._

**Maintainer's rationale:** COTS values may simply have been **entered incorrectly**.
A correction *should* affect older models too — the old snapshot was already wrong, it
just did not know it.

**The distinction this establishes, and which belongs in the spec:** *design data is
versioned; reference data is corrected.* A snapshot preserves **the maintainer's design
decisions**, not **facts about a motor**. `components`, `component_types` and the polar
tables are shared reference data, deliberately excluded from cloning, and stay that
way.

**Consequence, recorded so nobody later "fixes" it as a bug:** the immutability
guarantee of ADR 0006 / `Q-VS-1` covers the *design subgraph*, **not** the values of
referenced reference data. A snapshot's computed mass is therefore not
bit-reproducible across a COTS correction — two snapshots compared months apart both
shift if a component's `mass_g` was corrected in between. This is accepted: the
alternative would keep an old design running on a known-wrong mass.

---

## Q-PT-8 — Should the two sizing paths share their RC defaults?

**Context:** `e 0.75 / AR 7.0 / S_ref 0.25` in the solution space versus
`e 0.8 / AR 8.0 / S_ref 0.5` in the catalog sweep — so the same context-less
aircraft is sized differently by two endpoints of the same module. Related: a
**stale** computation context is indistinguishable from a fresh one, because the
fallback warnings fire only when a value is *missing*.
**Spec affected:** [`_reversa_sdd/powertrain/powertrain-sizing/requirements.md`]
**Question:** Unify the defaults, and should staleness be detectable?
**Impact:** Two answers to one sizing question.

**Answer:** _(derived — not a maintainer decision)_ **Both: there are no RC-typical defaults left to unify, and staleness becomes detectable through the freshness marker.**

Follows from **Q-CC-10**, which names this question: the RC defaults (`cd0 0.03`, `e 0.8`, `AR 8.0`, `S 0.5 m²`, `mass 1.0 kg`) are removed and a missing key emits an `error`-severity `DesignWarning`, so the two divergent default sets — `e 0.75 / AR 7.0 / S_ref 0.25` in the solution space and `e 0.8 / AR 8.0 / S_ref 0.5` in the catalog sweep — both disappear rather than being reconciled at some agreed value. The freshness marker (`computed_at` plus a hash of the inputs the context was derived from) is introduced there explicitly because "this is `Q-PT-8`".

---

## Q-PT-9 — Should the powertrain use the ISA atmosphere?

**Context:** `_air_density = 1.225·exp(−h/8500)` is duplicated in
`powertrain_performance` and `powertrain_sizing_service`, while the whole aero
stack uses `asb.Atmosphere` (the ISA model).
**Spec affected:** [`_reversa_sdd/powertrain/performance-model/requirements.md`]
**Question:** Should the powertrain use ISA for consistency above a few hundred
metres?
**Impact:** Two atmosphere models in one aircraft's calculation.

**Answer:** _(expert consensus, endorsed by the maintainer 2026-08-14)_ **Yes to ISA — one shared helper wrapping `asb.Atmosphere` with a closed-form ISA fallback, deleting all three duplicate density paths — but only if `temperature_deviation` and `density_altitude()` ship with it: a hot day is worth 350–1000 m of density altitude, 3–6× the model error being fixed.**

The exponential (isothermal, scale height 8500 m) in `powertrain_performance.py:346-348`, its duplicate in `powertrain_sizing_service`, and the hard-coded `RHO_DEFAULT = 1.225` in the solution space (`:65`) are three places running two models. Against ISA barometric the exponential is **−0.43 %** at 200 m, **−1.05 %** at 500 m, **−2.03 %** at 1000 m, −3.81 % at 2000 m, −5.33 % at 3000 m. Now the term the code ignores entirely — **temperature**: at sea level, ISA +10 K (25 °C) gives ρ = 1.1839, −3.4 %, a density altitude of **354 m**; ISA +15 K → −4.9 %, **526 m**; ISA +20 K → −6.5 %, **694 m**; ISA +30 K (45 °C) → −9.4 %, **1020 m**. **A warm summer afternoon at sea level is worth more density altitude than the entire 0–1000 m geometric band** — the tool is currently precise about the small term and silent about the large one. There is also no academic endorsement of an exponential approximation at any scale: Scholz/Sadraey write the matching chart, field length, ceiling and Breguet against the ISA throughout, with σ = ρ/ρ₀ as the standard carrier of altitude effects.

Four changes: **(1)** delete both copies of the exponential and the third hard-coded `RHO_DEFAULT` — two atmosphere models in one aircraft's calculation is a defect regardless of the size of the discrepancy, and it will surface as an unexplainable few-percent mismatch between the aero page and the powertrain page for the same aircraft. **(2)** Introduce one shared helper, e.g. `app/services/atmosphere.py`, exposing `density(altitude_m, temperature_deviation_k=0.0)`, implemented as `asb.Atmosphere(altitude=h, temperature_deviation=dT).density()` when AeroSandbox imports, with a **closed-form ISA barometric fallback** `ρ = 1.225·(1 − 2.25577e-5·h)^4.2559` corrected for ΔT via the ideal gas law when it does not — four lines, no new dependency, and it honours the `linux/aarch64` platform guard that excludes `aerosandbox` by pyproject environment marker, so the powertrain module must not acquire a hard `import aerosandbox`. **(3)** Expose `temperature_deviation_k` as a design assumption, default 0 — this is the change that actually improves answers at RC scale. **(4)** Report `atmo.density_altitude()` in the powertrain response: it is the number an RC/UAV pilot can act on, and it makes the temperature assumption visible rather than buried. **Is ISA overkill? No** — it costs nothing (already a dependency, already computed elsewhere) and removes a duplicate model. But it is also **not where the accuracy is**: shipping ISA without the temperature knob would be precision theatre. Ship both or the change is not worth making.

**Authority:** Scholz/Sadraey (ISA throughout the sizing and performance methods; σ = ρ/ρ₀); the error magnitudes computed from ISA vs the exponential and from the ideal gas law; `aerosandbox-expert` verified against the **installed AeroSandbox 4.2.9** — `Atmosphere(altitude, method: 'differentiable'|'isa', temperature_deviation)` exposing `.density()`, `.temperature()`, `.speed_of_sound()`, `.dynamic_viscosity()`, `.density_altitude()`, measured ρ(0) = 1.22500, ρ(200) = 1.20149, ρ(500) = 1.16685, ρ(1000) = 1.11077.
**Confidence:** high — the error magnitudes are computed and the AeroSandbox API was verified against the installed version rather than assumed.
Disagreement: none. Scholz, physics and the tool all point the same way; RC practice is silent on the model and loud on density altitude, which is exactly the emphasis this ruling adopts.

_Full reasoning: [`expert-consensus-powertrain.md`](expert-consensus-powertrain.md)_

---

## Q-PT-10 — Is windmilling drag deliberately out of scope?

**Context:** `Ct` is clamped at 0, so a power-off or descent point reports **zero
propeller drag**.
**Spec affected:** [`_reversa_sdd/powertrain/performance-model/requirements.md`]
**Question:** Acceptable for the RC/UAV mission set, or needed for glide-ratio
work?
**Impact:** Glide performance on a powered aircraft is currently optimistic.

**Answer:** _(expert consensus, endorsed by the maintainer 2026-08-14)_ **Not deliberately out of scope — it is a genuine gap, and a windmilling propeller costs **20–45 % of the glide ratio** on a typical RC e-glider. But do not fix it by unclamping `Ct`: keep `max(Ct, 0)` in the thrust path and add a `prop_state` drag increment on the aircraft polar.**

Sadraey lists **folding propellers** as one of the five propeller families, defined by their purpose — *"used on motor gliders to reduce drag in engine-off flight"* — so the lead authority recognises power-off propeller drag as a **first-order design driver**, significant enough that an entire propeller family exists to eliminate it. A drag budget reporting it as exactly zero contradicts the reason the hardware exists. Drela's QPROP formulation, which `powertrain_performance.py` implements, treats the windmill branch as a first-class regime (*"for a windmill with negative thrust and torque: v_a and v_t are negative"*), so negative `Ct` past the zero-thrust advance ratio is the physics, not numerical noise. Magnitude bounds: a **freewheeling** propeller has a hard theoretical ceiling from actuator-disk theory — maximum extractable windmill power is `P_max = (8/27)·ρ·V³·πR²` at induction factor a = 1/3, where `T = (4/9)·ρ·A·V²`, i.e. **`C_D,disk = 8/9 ≈ 0.89`** — with a fine-pitch RC prop at low torque realistically at **0.05–0.2**; a **stopped** propeller is bluff-body drag on the blade planform (Anderson: C_D ≈ 2.0 flat plate normal, 1.2 cylinder), referenced to **blade** area (~0.0065 m² for a 2-blade 12 in prop), not disk area; **folded/feathered** is effectively zero — the one case the current clamp accidentally models correctly. Worked example, 3 kg electric glider, S = 0.6 m², V = 12 m/s, clean L/D = 20, 12 in prop (disk area 0.073 m² = 12 % of wing area), clean drag 1.47 N: folded → L/D **20.0**; freewheeling at `C_D,disk` 0.05 → 0.32 N (22 % of clean drag) → **16.4**; at 0.10 → 0.64 N (44 %) → **13.9**; at 0.20 → 1.29 N (88 %) → **10.7**; stopped broadside at C_D 1.2 on blade area → 0.69 N (47 %) → 13.6; theoretical ceiling 8/9 → 5.72 N → 4.1. That is the difference between a 20:1 and a 14:1 sailplane.

Five parts to the fix. **(1) Keep `max(Ct, 0)`** at `powertrain_performance.py:328-332`: the APC polars' negative tail is sparse and low-precision, and the powered performance curve does not need it — removing the clamp would let low-quality extrapolated data leak into thrust numbers. **(2) Add an explicit propeller-state drag increment on the aircraft drag polar**, in the shape of Sadraey's ΔC_D,gear term: `ΔC_D0,prop = k_prop · (A_disk/S_ref)` with a `prop_state` enum — `running` → 0 (the thrust model already covers it), `folded`/`feathered` → **0.00–0.01**, `stopped_braked` → **0.02–0.05** (blades edge-on or behind the fuselage), `windmilling` → **0.05–0.20, default 0.10**. Hard physical ceiling `k_prop ≤ 8/9` — reject any user override above it. The ranges are **physics-derived brackets, not measurements**, and must be labelled as such in the UI, with the value user-overridable. **(3) Default `prop_state` by propeller type**: a folding propeller in the catalogue → `folded`; a fixed propeller on a design with a glide/L-D requirement → `windmilling`; otherwise `stopped_braked`. **(4) Scope it to the glide/power-off analyses** — cruise, climb and top-speed points are unaffected because the propeller is producing thrust there; this is a drag-budget and glide-ratio feature, not a performance-curve feature. **(5) Make it a design lever, not just a correction:** the single most valuable output is the comparison above — *"a folding prop buys you +6 points of L/D on this airframe"* — which is a real design decision the tool can now support, and it is the payoff that justifies the work.

**Authority:** Sadraey §8.7 (folding propellers as a named family defined by this drag; the additive `C_D,P = C_D,0 + ΔC_D,flap + ΔC_D,slat + ΔC_D,gear` decomposition with ΔC_D,gear = 0.015 as the shape precedent); Drela QPROP §1.1 and §5.3 (windmill sign convention; `P_max = (8/27)ρV³πR²` at a = 1/3); Anderson (bluff-body C_D ≈ 2.0 flat plate normal, 1.2 cylinder); RC-Network Wiki *Luftschraube* / *Motorsteller* for the three-state operational taxonomy (folding props on sailplane engines; ESC motor braking exists specifically so "undesired motor spin-down is prevented" with folding props).
**Confidence:** high that windmilling drag belongs in the drag budget for glider/motor-glider work and that the clamp should stay in the thrust path; medium on the specific `k_prop` values — they are bracketed by actuator-disk theory and bluff-body data, but no measured RC propeller drag data exists in any consulted source. Treat them as defaults to be calibrated, and say so in the UI.
Disagreement: Scholz vs the current code — Sadraey defines a whole propeller family by the need to eliminate this drag while the code reports it as zero; resolved in favour of Scholz. RC practice supplies the taxonomy but no numbers, and physics supplies the bounds; that is a coverage gap, not a contradiction, which is why the coefficients are given as ranges with a derived ceiling rather than as point values.

_Full reasoning: [`expert-consensus-powertrain.md`](expert-consensus-powertrain.md)_

---

## Q-PT-11 — Should the performance endpoint keep requiring an aeroplane it never reads?

**Context:** The docstring calls the UUID *"anchoring the request to a valid
design context"*, but no aeroplane data enters the computation — so a 404 there
is pure ceremony and the same computation is unreachable without an aircraft.
Related: a wrong component **type** reports 404, not 422 — passing a battery id as
`motor_component_id` reads as "the id does not exist" when the id exists and is
the wrong kind of part. The helpers `_resolve_motor` / `_resolve_battery` /
`_load_polar_rows` also raise `HTTPException` directly, bypassing the domain layer
and making those failures untestable at the service level.
**Spec affected:** [`_reversa_sdd/powertrain/performance-model/contracts.md`]
**Question:** Is aircraft-level state expected to enter the computation later
(altitude, mission), or should the route move out of the aeroplane namespace?
**Impact:** Three contract rows.

**Answer:** **ANSWERED by the maintainer, 2026-08-15** (option b) — **the route stays in the aeroplane namespace: aircraft-level state (altitude, mission) is expected to enter the computation. The anchor is declared intent, not ceremony.**

**Why this is not a leak under ADR 0019.** The concern was that the UUID is pure ceremony — a 404 that guards nothing. It is not: the powertrain performance model is *meant* to be evaluated in the aircraft's operating context, and altitude alone changes air density and therefore thrust and endurance materially at UAV altitudes. A route that computed motor performance context-free would be the wrong contract, and moving it to `/powertrain/performance` would have to be undone.

**And the intent is already load-bearing, not aspirational.** `Q-PT-9` makes
`temperature_deviation_k` a **design assumption**, and `design_assumptions` carries an
`aeroplane_id` column (`app/models/aeroplanemodel.py:848-857`) — it is per-aeroplane by
construction. `Q-PT-9` further names `powertrain_performance.py:346-348` as one of the
density code paths it deletes, and that path is on **this** endpoint
(`app/api/v2/endpoints/aeroplane/powertrain_performance.py:187`). Computing density
correctly therefore *requires* the aeroplane the route already takes. `Q-PT-3` (prop
diameter from design speed) and `Q-PT-1` (`I_design` from the most demanding mission
segment) pull the same way. The anchor stops being ceremony as soon as `Q-PT-9` lands.

**The remaining intent must still be recorded, not assumed.** Today no aeroplane data enters the computation, so the spec states plainly: *the aeroplane anchor is reserved for atmospheric and mission state not yet wired.* An unexplained inert parameter is indistinguishable from a forgotten one — this is the same reasoning that made `Q-AF-7 ②` document an absence.

---

**Two sub-findings, derived and independent of the option chosen:**

**① A wrong component *type* must return 422, not 404.** Passing a battery id as `motor_component_id` currently reports 404 — *"the id does not exist"* — when the id exists perfectly well and is the wrong kind of part. The client cannot distinguish a typo from a mis-wired form, and the message actively misleads. This is a `ValidationDomainError → 422` naming both the expected and the actual component type. Note this does **not** conflict with `Q-FD-1`: nothing in persisted state is in conflict here; the payload itself is wrong.

**② `_resolve_motor` / `_resolve_battery` / `_load_polar_rows` stop raising `HTTPException`.** Raising transport-layer exceptions from the service bypasses the domain layer, which means (a) the single error envelope of `Q-CC-3` is circumvented, and (b) these failures are untestable at the service level — the test has to construct a request context to observe a domain condition. They raise domain exceptions and let the global handler translate, like every other service.

Both are recorded as defects against `powertrain/performance-model/contracts.md`.
---

## Q-PT-12 — Propeller-polar data integrity (bundle)

**Context:** Five items:
- **Skipped records are counted but not enumerated**, so a reimport that silently
  misses a corrected dataset leaves no auditable trace, and short/malformed rows
  are skipped without a per-file counter — a systematically broken source file
  looks like a smaller propeller rather than an error.
- **The snapshot is the only integrity boundary.** A hand-edited
  `apc_props.json.gz` imports without complaint; nothing checksums it.
- **`_records_equal` uses `source_version` as a freshness proxy**, and the
  docstring admits an APC data correction without a version bump is silently
  skipped. Should a content hash replace it?
- **`inertia_kg_m2` has no plausibility guard** although `weight_g` has one
  (`MIN_PLAUSIBLE_WEIGHT_G`) — both come from the same PE0 parse.
- **`Torque_Nm` / `Thrust_N` are stored and never used.** Their presence invites a
  future consumer to read exactly the low-precision column the physics
  deliberately avoids.

**Spec affected:** [`_reversa_sdd/powertrain/propeller-polars/requirements.md`]
**Question:** Confirm each.
**Impact:** 454 propellers with no import audit trail.

**Answer:** _(expert consensus, endorsed by the maintainer 2026-08-14)_ **Yes to a two-tier inertia guard — absolute `1e-7 … 1e-2 kg·m²` plus dimensionless `0.010 ≤ I/(m·D²) ≤ 0.10` — and yes to a content hash for the freshness decision, keeping `source_version` for provenance; checksum the snapshot too.**

**(a) The inertia guard writes itself from physics.** For any rigid body `I = m·r_g²`, so `k = I/(m·D²) = (r_g/D)²` has an **exact ceiling**: the radius of gyration cannot exceed the tip radius, `r_g ≤ R = D/2`, hence `0 < k ≤ 0.25` (k = 0.25 ⟺ all mass at the blade tips). That is a hard bound, not a heuristic. Across the 453 shipped APC propellers carrying both mass and inertia the measured `k` runs min **0.0204**, p1 0.0246, p5 0.0257, **median 0.0404**, p95 0.0578, max **0.0676** — i.e. `r_g/D ∈ [0.14, 0.26]`, or `r_g` between 0.29 R and 0.52 R, exactly what a tapered blade with a solid hub gives, and remarkably tight across a 5× diameter range (fitted scaling `I ≈ 0.0317·D^4.58`, residual p1–p99 0.40×–2.39×). **Tier 1 — absolute sanity, always applicable:** `1e-7 ≤ inertia_kg_m2 ≤ 1e-2 kg·m²`. The 5–20 in band spans 1e-6…3e-3 observed, so this gives about a decade of headroom either side while still catching the classic PE0-parse failures — a value read in g·cm² (off by 1e-7), oz·in² (~1.8e-5) or lb·ft² (~0.042) all land outside the window. **Tier 2 — dimensionless consistency, when mass and diameter are both known:** reject outside `0.010 ≤ I/(m·D²) ≤ 0.10`, warn outside `0.018 … 0.075`. The reject band is ~2× wider than the observed range on both sides and still well inside the hard 0.25 bound; Tier 2 is the stronger test because it catches an inertia internally inconsistent with its own mass and diameter even when both are individually plausible. **Failure policy — match the existing `weight_g` behaviour exactly** (`prop_polar_enrich.py:29,88-100`): log with the propeller name and offending value, **drop the field** (leave `inertia_kg_m2` NULL) rather than importing a wrong number, and count it in a per-file skip tally. Do not reject the whole record — the polar samples are still good. **Also add the missing symmetric mass check:** `MIN_PLAUSIBLE_WEIGHT_G = 1.0` has no upper bound; the largest shipped propeller is 133 g median in the 17–30 in band, so a `MAX_PLAUSIBLE_WEIGHT_G` of ~2000 g would catch a kg/g inversion at negligible risk. The asymmetry looks like an oversight rather than a decision.

**(b) Content hash and `source_version` answer different questions; neither substitutes for the other.** `source_version` is a **claim by the publisher** about provenance — the right thing to display ("APC data, PER3 rev X"), to record in an audit trail, and to reason about when deciding whether a dataset is *supported* — but it is **not evidence about the bytes**. A content hash is a **fact about the bytes**, and it is the only thing that can correctly answer "did this record change?", which is precisely what `_records_equal` (`prop_polar_import.py:68-79`) is asking; the docstring already documents the failure mode (an APC correction without a version bump is silently skipped) and a hash closes it by construction. Concretely: store a `content_hash` per propeller record — SHA-256 over the canonical serialisation of the fields that matter (sample rows plus the enriched `weight_g`/`inertia_kg_m2`/geometry) with stable key ordering and fixed float formatting so it reproduces across Python versions; have `_records_equal` decide on the **hash**, with `source_version` becoming a stored, displayed attribute updated whenever the record is, never a gate; store a **snapshot-level hash** of `apc_props.json.gz` committed alongside the snapshot and verified at import, since today a hand-edited archive imports without complaint and nothing checksums it — three lines; and keep `force` as the manual override, which the hash makes needed far less often. Hashing 454 records × ~50 sample rows is milliseconds, so there is no performance argument for the version proxy.

**On the remaining three bullets.** **Skipped records counted but not enumerated** — confirmed defect: emit a structured per-file report (`file`, `skip_reason`, `record_id`) and add the missing **per-file counter for short/malformed rows**, so a systematically broken source file reads as an error rather than as a smaller propeller. This is the same failure class as the NULL-mass issue in Q-PT-2: silence where a warning belongs. **`Torque_Nm` / `Thrust_N` stored and never used** — confirmed hazard: they are the low-precision columns the Ct/Cp physics deliberately avoids, and their presence invites a future consumer to read exactly the wrong thing. Either drop them or rename with an explicit `_raw_lowprec` suffix and document that the dimensional path is `T = Ct·ρ·n²·D⁴`. A comment in the model is not enough — **the column name is the API.**

**Authority:** physics (`r_g ≤ R` ⇒ `k ≤ 0.25`); the shipped 453-propeller APC dataset for the empirical band; ordinary data-integrity engineering plus the failure mode the code's own docstring already documents. No academic/practice axis applies to this question.
**Confidence:** high — both the physical bound and the empirical band are derived from the actual shipped dataset.
Disagreement: none.

_Full reasoning: [`expert-consensus-powertrain.md`](expert-consensus-powertrain.md)_

---

## Q-PT-13 — COTS component lifecycle (bundle)

**Context:** Four items:
- **Immutability is silent.** A `PUT /component-types/{id}` changing `name` or
  `deletable` returns **200 with the change dropped**, rather than 422.
- **Deleting a *component* is unguarded.** `component_tree.component_id`,
  `component_tree.material_id` and `wing_xsec_ted_servos.component_id` all
  reference it; the deletion guard exists only for **types**.
- **The seeded `deletable=False` guard fires before the reference-count guard**,
  so a type that is both seeded and referenced reports only the seed reason.
- **`_VALID_COMPONENT_TYPES` (`cots_import.py:26-40`) duplicates
  `DEFAULT_SEED_TYPES` (`component_type_service.py:331`)** — two hand-maintained
  copies of the same 12-name taxonomy. Should the importer read the registry from
  the DB?
- **Model-upload path handling was not audited.** `.claude/rules/security.md`
  requires an explicit `Path.resolve()` containment check; this analysis did not
  verify one exists. **Please confirm.**

**Spec affected:** [`_reversa_sdd/powertrain/cots-powertrain-components/requirements.md`]
**Question:** Confirm each — especially the last, which is a security check.
**Impact:** The upload-path one is the only unverified security control in the
corpus.

**Answer:** _(resolved by code lookup — not a maintainer decision)_ **The `Path.resolve()` containment check is absent everywhere in `app/api/v2/endpoints/components.py`; the model **upload** path is nevertheless safe by construction, but the model **download** path is an unauthenticated arbitrary-file-read.**

The write half (`POST /components/{id}/model`, `components.py:186-199`) never uses the client filename to build the destination: the basename is `{component_id}_{uuid4().hex[:8]}` — an `Annotated[int, Path(...)]` parameter plus a server-generated uuid — and only the whitelisted suffix (`.step`/`.stp`/`.stl`) is taken from the upload, so there is no traversal primitive even without the prescribed check. The read half (`GET /components/{id}/model`, `components.py:236-249`) hands `FilePath(comp.model_ref)` straight to `FileResponse` with `path.is_file()` as the only gate, while `model_ref` is a free-form client-writable field on `ComponentWrite` (`app/schemas/component.py:9,22`) persisted verbatim by a blind `setattr` loop (`app/services/component_service.py:113-114`), and nothing authenticates the API (`app/main.py:233-234`): `PUT /components/1 {"model_ref":"/etc/passwd"}` followed by `GET /components/1/model` returns the file. The prescribed check *is* implemented in five other places (e.g. `app/api/v2/endpoints/cad.py:62-74`, `app/services/fuselage_slice_service.py:62`), which makes the omission look like an oversight rather than a considered decision. Found on the same path: `ComponentEditDialog.tsx:173-183` hard-codes `model_ref: null` in its `PUT` body, so editing any component in the UI erases its uploaded 3D-model reference and orphans the file.

**Verdict:** confirmed defect (high severity) on the download half; confirmed safe on the upload half.
Residual decision: the other four bundle items — the silently-dropped `PUT` on component types, the missing delete guard for *components*, the guard ordering, and whether `cots_import` should read the taxonomy from the DB — were not part of this lookup and still need you.

_Full detail: [`wave3-lookups.md`](wave3-lookups.md) §A_


**Residual decision — ANSWERED by the maintainer, 2026-08-14.**

**① Silent immutability → 422.** `PUT /component-types/{id}` must not answer 200
while dropping a change to `name` or `deletable`. Determined by `Q-CC-3`
(`ValidationDomainError → 422`) and `P-WARN-0` (no silent discard).

**② Deleting a *component* → guard it, exactly like types.** Refuse the delete
while the component is still referenced by `component_tree.component_id`,
`component_tree.material_id` or `wing_xsec_ted_servos.component_id`. Chosen over an
FK cascade: a referenced motor or material should not disappear out from under an
aircraft. Complements the FK migration decided in `Q-CC-7` (the FK still gets an
explicit `ondelete`, but the service-level guard is what the user meets).

**③ Guard ordering → report both reasons.** The seeded `deletable=False` check
currently short-circuits the reference-count check, so a type that is both seeded
*and* referenced reports only the seed reason. Report every applicable reason
(`P-WARN-0`: do not withhold information).

**④ Duplicate taxonomy → the importer reads it from the database.**
`_VALID_COMPONENT_TYPES` (`cots_import.py:26-40`) duplicates `DEFAULT_SEED_TYPES`
(`component_type_service.py:331`) — 12 names maintained twice. The importer reads
the registry from the DB at runtime. **Maintainer's rationale:** this also makes
*adding a new component type easier*, since a new type no longer requires a code
change in the importer. Single-authority principle, consistent with `Q-MB-1`,
`Q-AA-1` and `Q-WD-1`.

**⑤ Security (already established by lookup) — fix the download path.** Add the
prescribed `Path.resolve()` containment check to `GET /components/{id}/model`,
copying the pattern already used in five other places (e.g. `app/api/v2/endpoints/cad.py:62-74`).
The upload path needs no change.

**⑥ Separate data-loss defect found on the same path.**
`ComponentEditDialog.tsx:173-183` hard-codes `model_ref: null` in its `PUT` body, so
**editing any component in the UI erases its uploaded 3D-model reference** and
orphans the file. Independent of everything above and to be fixed.

---

# versioning

## Q-VS-1 — Snapshots are not actually immutable: should the guard cover every write path?

**Context:** Verified during review. `_guard_immutable` is defined at
`app/services/aeroplane_version_service.py:65` and called from **exactly one**
place — line 151, inside `snapshot()`. Nothing stops
`PUT /aeroplanes/{snapshot_uuid}/wings/…` from mutating a frozen node through the
ordinary wing / fuselage / spar CRUD routes.
**Spec affected:** [`_reversa_sdd/versioning/snapshot-immutability/requirements.md`],
[`_reversa_sdd/adrs/0006-…md`], [`_reversa_sdd/adrs/0007-…md`]
**Question:** Should the guard move into the aeroplane resolver so every write
path inherits it?
**Impact:** The guarantee the whole versioning model — and the copilot's
propose/adopt flow — rests on is currently a convention one code path checks.

**Answer:** **(a) + (b) — move the guard into a write-resolver, AND add a
session-level `before_flush` backstop.** _Answered by the maintainer, 2026-08-13._

Two layers, deliberately:

1. **Write-resolver** (e.g. `get_aeroplane_for_write`) used by every mutating
   endpoint, so all write paths inherit the check. Read paths are unaffected. This
   layer exists for the **error quality**: a clean 409 with an intelligible message.
2. **SQLAlchemy `before_flush` guard** rejecting any modification to rows belonging
   to an immutable aeroplane, at the persistence boundary. This layer exists for
   **completeness**: it also catches service-level paths that never go through the
   resolver — the copilot apply service, future MCP tools, scripts.

**Why both:** the resolver alone is bypassable by construction (it is a convention
about which function you call); the flush guard alone produces technical errors at
the wrong abstraction level. Together, the guarantee is enforced and the failure is
explainable.

**Current state (verified):** `_guard_immutable`
(`app/services/aeroplane_version_service.py:65`) is invoked from **exactly one**
call site — line 151, inside `snapshot()`. Nothing prevents
`PUT /aeroplanes/{snapshot_uuid}/wings/…` from mutating a frozen node through the
ordinary wing / fuselage / spar CRUD routes.

**Why this is a root:** both versioning ADRs rest on this premise. **ADR 0006**
(row-copy versioning) is worthless if history can be rewritten in place; **ADR 0007**
(copilot proposes, human adopts) assumes the base state cannot move underneath a
proposal. The guarantee is currently a convention checked by a single code path —
and epic #901/#902 is being built on top of it.

---

## Q-VS-2 — What is the intended long-term growth bound for snapshots?

**Context:** Every snapshot is a full row-copy of the entire design subgraph, and
`spar_insert_service` snapshots **automatically on every destructive spar
commit**. There is no prune, no size accounting, no cap, and no `preview_png` to
make a snapshot recognisable (the column, the clone reset and the `VersionNode`
field all exist; no code path generates a thumbnail).
**Spec affected:** [`_reversa_sdd/versioning/requirements.md`],
[`_reversa_sdd/adrs/0006-…md`]
**Question:** Is unbounded growth acceptable, or should snapshots expire? And is
thumbnail generation deferred — to which layer (CAD tessellation)?
**Impact:** Compounded by the copilot, which clones a full subgraph per proposal.

**Answer:** 🔴 **UNANSWERED — this question was never put to the maintainer.**

This slot previously held the maintainer's answer to `Q-PT-11` (powertrain route
namespace). It was misfiled here by an edit that matched a generic `**Answer:**`
anchor instead of the question id — the same failure that once wrote `Q-AC-2`'s
confirmation into `Q-CC-16`. The text has been moved to `Q-PT-11`, where it belongs.

Corrected 2026-08-16, found by the GH-issue audit via #906.

<!-- fill in here -->
---

## Q-VS-3 — What should the five dead `design-versions` routes return?

**Context:** All five routes under `/aeroplanes/{uuid}/design-versions` are
registered (`aeroplane/__init__.py:41`) and every one calls a
`design_version_service` stub that unconditionally raises `NotFoundError`. The
service header still says *"TODO(gh-905): replace all functions below"*, but
gh-905 shipped the parallel `/lineages` + `/branches` surface instead.
**Spec affected:** [`_reversa_sdd/versioning/requirements.md`],
[`_reversa_sdd/openapi/da3dalus-v2.yaml`]
**Question:** Remove the routes, or re-point them at the new service? They are
UUID-addressed, which the new service does not support. A 404 from a stub is also
a misleading answer — 410 or 501 would be honest.
**Impact:** Five routes in the published OpenAPI that can never succeed.

**Answer:** _(derived — not a maintainer decision)_ **Remove all five routes and the stub service.**

Follows from **P-DEAD-0** and **Q-MB-1**: the routes can only raise, gh-905 shipped the `/lineages` + `/branches` surface in their place, and they are UUID-addressed in a way the new service does not support — so there is nothing to re-point them at, and 410/501 would only be an honest way of keeping dead surface alive. Q-MB-1's git archaeology identifies them as leftovers of the 2026-04-12 wireframe bulk scaffold (`1bq`), superseded by the real versioning model, which is exactly rule 3's "delete, and record it in the spec as removed". Withdrawing published routes is client-visible and acceptable per **Q-CC-1**.

---

## Q-VS-4 — Should string aeroplane references migrate to real FKs?

**Context:** The clone-coverage test discovers related tables by introspecting
SQLAlchemy `ForeignKey` objects, so the three soft-reference tables
(`component_tree`, `construction_plans`, `construction_parts`) are **invisible**
to it and must be registered by hand. **And one level down**: the registry checks
*tables*, not *columns*, so a column added to a cloned model and forgotten in
`clone_aeroplane_subgraph`'s constructor call is silently lost on every subsequent
version, with no test failing.
**Spec affected:** [`_reversa_sdd/versioning/aeroplane-clone-subgraph/requirements.md`],
[`_reversa_sdd/traceability/spec-impact-matrix.md`] (CS-7)
**Question:** Migrate to real FKs so the test can see them (see Q-CC-7)? And
should the coverage test also assert column parity?
**Impact:** The same class of bug the registry exists to prevent, one level down.

**Answer:** _(derived — not a maintainer decision)_ **Yes to both — the three soft references become real FKs, and the clone-coverage test also asserts column parity.**

Follows from **Q-CC-7**: it migrates `component_tree`, `construction_plans` and `construction_parts` to real `ForeignKey` columns with an explicit `ondelete`, and states that this "resolves the structural half of `Q-VS-4`". The reason it was accepted is that the clone-coverage test is "the only structural guard against silently dropping a table's data when branching or snapshotting" — and a guard that cannot see a column added to a cloned model and forgotten in `clone_aeroplane_subgraph` does not provide that protection. Column parity is therefore part of the same guard, not a separate wish; without it the identical failure simply moves one level down, silently, on every subsequent version.

---

## Q-VS-5 — Should `construction_parts` be copied on clone?

**Context:** They are excluded because they are file-backed, so a branched
aircraft silently loses its construction artefacts.
**Spec affected:** [`_reversa_sdd/versioning/aeroplane-clone-subgraph/requirements.md`]
**Question:** Is that the intended UX, or should the files be copied too?
**Impact:** A branch is not a complete copy of the design.

**Answer:** **ANSWERED by the maintainer, 2026-08-15** (option b) — **`construction_parts` are still not copied on clone, but the omission becomes visible instead of silent.**

The exclusion itself is sound: the parts are file-backed, and construction plans are **re-executable** — the branch can regenerate them from the design it carries. Copying artefacts that can be recreated buys little and multiplies disk per branch, which matters because `spar_insert_service` snapshots automatically on every destructive spar commit.

**What was wrong is that the branch quietly differs from its source.** A user who branches an aircraft and finds the construction artefacts gone has no way to tell whether they were lost, never existed, or were deliberately skipped. That is precisely the undeclared substitution **ADR 0020** forbids — the operation silently returns something other than what "clone" implies.

**So the clone emits a `DesignWarning`** naming how many construction parts were not carried over and stating that they are regenerated by re-running the plan. Severity **domain practice**, not defect: the behaviour is correct, only its silence was not.

**Rejected — option (c), sharing files by reference.** Two branches pointing at the same artefacts means executing a plan on one branch mutates what the other shows, which is the opposite of what branching is for.

_Consistent with the scope principle recorded at `Q-CO-4`: the cheapest change that removes the surprise, rather than machinery for a problem that is not yet real._

---

## Q-VS-6 — Branch and lineage edge cases (bundle)

**Context:** Six items:
- **`discard_branch` truncates the lineage of surviving nodes.** It NULLs every
  inbound `predecessor_id` before deleting, so a node on another branch whose
  history ran through a discarded snapshot loses its chain silently. Should the
  predecessor be re-pointed at the discarded node's own predecessor instead?
- **`list_tree` cannot find orphaned nodes.** It filters
  `id == root_id OR root_id == root_id`, so a node with a NULL `root_id` (a legacy
  row, or a clone created with `root_id=None` — which is accepted with no
  follow-up check) is invisible in the version graph. Should a repair/backfill
  pass exist?
- **Branch names are only unique on rename.** `create_branch` performs no check
  and there is no DB index, so restoring the same snapshot twice produces two
  identically named branches.
- **Forking from a `NULL`-`root_id` node silently starts a new lineage** rooted at
  that node (`root_id = source.id`), which is unlikely to be the caller's intent.
- **`head_id` is effectively write-once** — set at branch creation and never
  advanced. Coherent with the insert-behind snapshot topology, surprising to
  anyone expecting git semantics.
- **`compare` does not diff and does not require a shared lineage.** It returns
  two `_metrics_payload` dicts and two unrelated aircraft can be compared as if
  they were versions of one another. The structural diff endpoint died with
  `design_versions`. Should a server-side diff be reinstated?

**Spec affected:** [`_reversa_sdd/versioning/branch-model/requirements.md`],
[`_reversa_sdd/versioning/snapshot-immutability/requirements.md`]
**Question:** Confirm each.
**Impact:** Six lineage-integrity decisions.

**Answer:** **Re-point predecessors instead of truncating; backfill orphaned
`root_id`.** _Answered by the maintainer, 2026-08-15._

**`discard_branch` must not sever lineage.** It currently NULLs every inbound
`predecessor_id` before deleting, so a node on another branch whose history ran through
the discarded snapshot **loses its chain silently**. Instead the discarded node's own
predecessor becomes the new predecessor of its successors — the same principle as
`git rebase --onto`: removing a node from a chain must not break the chain.

**`list_tree` must be able to see orphans.** It filters `id == root_id OR root_id ==
root_id`, so a node with a `NULL root_id` — a legacy row, or a clone created with
`root_id=None`, which is accepted with no follow-up check — is **invisible in the
version graph**. A backfill makes existing orphans visible, and creating a node with a
null `root_id` should not pass silently.

---

## Q-VS-7 — Should `_metrics_payload` be promoted to a public contract?

**Context:** A `_`-prefixed private function imported by three other modules
(`copilot_apply_service`, `copilot_tools` ×2, the `versioning.py` endpoint). It is
the de-facto public metrics contract, and its name promises an instability its
callers cannot tolerate. It also reads `stability_results[-1]` — the last row in
PK order, not the newest by `computed_at`.
**Spec affected:** [`_reversa_sdd/versioning/contracts.md`],
[`_reversa_sdd/ai-copilot/copilot-tools/requirements.md`]
**Question:** Promote it to a public function with a Pydantic schema? And is PK
order guaranteed to track recency, or should it order by `computed_at`?
**Impact:** Four call sites depend on a private function's shape.

**Answer:** _(derived — not a maintainer decision)_ **Promote it: a public function with a Pydantic response model, and no reliance on implicit row order.**

Follows from **Q-CC-11** and **Q-CC-15**: Q-CC-11 makes generated TypeScript types the client contract and names "fill the missing `response_model` annotations first" as its prerequisite — `_metrics_payload` is returned by an endpoint and imported by three other modules, so it is precisely one of the untyped dicts that must become a typed response. Q-CC-15's ruling that cross-module contracts need a named owner applies for the same stated reason ("unowned means undocumented"). A promoted contract also cannot rest on `stability_results[-1]` happening to track recency, so the query orders explicitly by `computed_at`.

---

## Q-VS-8 — Should the versioning routes expose UUIDs?

**Context:** The versioning routes take the **integer primary key**
(`{aeroplane_id}`, `{snapshot_id}`, `{branch_id}`, `{root_id}`) while every other
v2 route uses the public UUID. `_get_node_by_uuid` exists and is dead. The
OpenAPI document has to type the same path-parameter name as `string/uuid` on one
path and `integer` on another.
**Spec affected:** [`_reversa_sdd/versioning/contracts.md`],
[`_reversa_sdd/openapi/da3dalus-v2.yaml`]
**Question:** Should versioning expose UUIDs, or is leaking the PK a deliberate
part of the lineage contract?
**Impact:** The one place the public API surface is internally inconsistent about
identity.

**Answer:** _derived — not a maintainer decision (ADR 0019 decides it)._

**Versioning exposes UUIDs. The integer primary key is an implementation detail and must
not appear in a path.** This is ADR 0019 clause 1 almost verbatim: the surrogate key is
how the row is stored, not what the resource *is*, and every other v2 route already
addresses by public UUID. Leaking the PK here is not a lineage contract — lineage is
carried by the parent/child edges, which are equally expressible over UUIDs.

**Consequences:**

- `{aeroplane_id}`, `{snapshot_id}`, `{branch_id}` and `{root_id}` become UUIDs, so the
  OpenAPI document stops typing the same parameter name as `integer` on one path and
  `string/uuid` on another — the one place the public surface contradicts itself about
  identity.
- **`_get_node_by_uuid` is not dead code and must not be deleted under ADR 0021.** It is
  the *target* of this change; it is unreached because the migration was never finished,
  which is the same unfinished-additive-migration pattern ADR 0019 describes for
  `/airfoils/db/`.
- Breaking change to the versioning routes, affordable for the same reason as the airfoil
  merge: no external API consumers (ADR 0024). It must land **before** TypeScript client
  generation (`Q-CC-11`).

---

# ai-copilot

## Q-CO-1 — Should the AI audit trail be wired, or removed?

**Context:** Both halves are inert.
`get_or_open_proposal(db, live_id, message_id=None)` accepts a message id for
branch-name traceability, but `_apply_design_edits` calls it **without one**, so
every proposal branch is plain `"copilot-proposal"`. And nothing resolves
`aeroplanes.provenance_message_id` back to a conversation turn, although the FK
exists in the gh-903 migration, `SnapshotRequest` accepts it, `snapshot()` writes
it and `VersionNode` returns it.
**Spec affected:** [`_reversa_sdd/ai-copilot/proposal-adopt-discard/requirements.md`],
[`_reversa_sdd/versioning/copilot-provenance/requirements.md`]
**Question:** Was a "show me the chat that produced this version" view intended?
Should the copilot start supplying the message id?
**Impact:** ADR 0007's accountability story is entirely unimplemented.

**Answer:** **ANSWERED by the maintainer, 2026-08-15** (option a) — **the audit trail is wired: the copilot supplies the message id, and the version graph links back to the conversation turn that produced a version.**

**Without it ADR 0007 is an intention, not a mechanism.** That ADR makes the human the adopting party — the copilot proposes, the maintainer accepts. Accountability is the whole basis of that split, and it is currently unimplemented on both halves:

- `_apply_design_edits` calls `get_or_open_proposal(db, live_id, message_id=None)` without an id, so **every** proposal branch is named the same flat `"copilot-proposal"`. Two proposals in one session are indistinguishable by name.
- `aeroplanes.provenance_message_id` exists as an FK (gh-903 migration), `SnapshotRequest` accepts it, `snapshot()` writes it and `VersionNode` returns it — and **nothing ever resolves it back to a turn**. The data path is built; only the read side is missing.

**So the work is smaller than the finding suggests:** supply the id at the one call site, and add the resolution — *"show me the chat that produced this version"*. The branch name becomes meaningful as a side effect, because it can carry the turn reference.

**Connects to `Q-CO-5`:** conversation branching is planned there, mirroring aeroplane branching. Once a chat can itself branch, a version pointing at a *turn* rather than at a conversation is what keeps the link unambiguous across branches.

---

## Q-CO-2 — Should a malformed tool-argument payload abort the call?

**Context:** A JSON-decode failure on streamed tool arguments **silently becomes
`{}` and the tool is executed anyway** (`copilot_service.py:602-604`). A
truncated stream can therefore call `apply_design_edits` with no ops.
**Spec affected:** [`_reversa_sdd/ai-copilot/copilot-turn-loop/requirements.md`]
**Question:** Should a malformed call be reported to the model as a protocol
error instead?
**Impact:** A write tool executed on garbage input.

**Answer:** _(derived — not a maintainer decision)_ **Yes — a JSON-decode failure on streamed tool arguments is reported back to the model as a protocol error; it never becomes `{}` with the tool executed anyway.**

Follows from **P-WARN-0**: substituting an empty argument object for a decode failure is an undeclared substitution, and here it lets a **write** tool (`apply_design_edits`) run on garbage while returning a plausible result — the "correct-looking output, no effect" shape the policy exists to eliminate. A model can recover from a reported malformed call; it cannot detect a silently emptied one.

---

## Q-CO-3 — Should a retarget failure surface in the tool result?

**Context:** `_effective_target_id` swallows **every** exception
(`except Exception: pass`) and falls back to the live aeroplane, so a retarget
failure is indistinguishable from "no proposal open" — the model then reads the
**live** design while believing it reads its own edits.
**Spec affected:** [`_reversa_sdd/ai-copilot/copilot-tools/requirements.md`]
**Question:** Should the failure be reported?
**Impact:** The model can confidently describe changes it is not looking at.

**Answer:** _(derived — not a maintainer decision)_ **Yes — the retarget failure is reported in the tool result; the `except Exception: pass` goes.**

Follows from **P-WARN-0**, which names "`except Exception: pass` in the copilot retarget" in its own list of violations. Falling back to the live aeroplane changes *which aircraft the answer is about*, so the model can confidently describe changes it is not looking at — that is severity `error`, not a `notice`, and it must be distinguishable from the legitimate "no proposal open" case.

---

## Q-CO-4 — Should a turn be persisted from a background task?

**Context:** The SSE endpoint holds the request-scoped session for the whole turn
(minutes, with two 60 s analyses) and `get_db()` commits only after the generator
is fully consumed — so a client disconnect mid-stream **loses the assistant
message**, while any side effects (a proposal branch) survive. There is also no
heartbeat or keep-alive frame: a 60 s `run_analysis` streams nothing, and an
intermediary proxy may time the connection out mid-turn.
**Spec affected:** [`_reversa_sdd/ai-copilot/copilot-turn-loop/requirements.md`]
**Question:** Should the assistant row be committed in its own session as soon as
the `done` event is produced? Should there be a heartbeat?
**Impact:** A proposal branch can exist with no message explaining it.

**Answer:** **ANSWERED by the maintainer, 2026-08-15** (option a) — **the assistant row is committed in its own session as soon as the `done` event is produced. No heartbeat, no further hardening.**

**The defect worth fixing is the asymmetry, not the disconnect.** Today the SSE endpoint holds the request-scoped session for the whole turn and `get_db()` commits only after the generator is fully consumed. If the stream ends early, the **assistant message is lost while the side effects survive** — so a proposal branch can exist with nothing recording why. That is a coherence problem in the record, and it is worth an isolated fix regardless of how the stream ended.

**Explicitly not done, and this is the maintainer's scope call:** heartbeat frames, proxy-timeout tolerance, resumable streams. The finding reads like a distributed-systems problem; the operating model is one user on one machine (**ADR 0024**), where a mid-stream disconnect means the tab was closed. Building keep-alive machinery for an intermediary that does not exist is hardening against a deployment this project does not have.

_Recorded as a standing principle from the same conversation: **do not harden the software against a specific development state.** The app is pre-release and its data is test data. Robustness work is justified by user data worth preserving or by a real deployment, not by a hypothetical one._

---

## Q-CO-5 — Is conversation branching still planned?

**Context:** `parent_id` is declared on the model and both Pydantic schemas
("Parent message ID for branching") and is **never written and never read** — and
it is a plain `Integer`, not an FK. Relatedly, `sort_index` is assigned as
`COUNT(*)` at append time, so two concurrent appends produce the same index and
an append after `delete_message` reuses one. `role="tool"` rows are supported by
the schema and never written, so the replay branch handling them is dead.
**Spec affected:** [`_reversa_sdd/ai-copilot/copilot-turn-loop/requirements.md`]
**Question:** Is branching still planned? Should ordering move to
`created_at` + `id`, or to a sequence?
**Impact:** Three pieces of dead or unsafe schema in the history model.

**Answer:** **ANSWERED by the maintainer, 2026-08-15** (option b) — **conversation branching stays planned; `parent_id` is built out into a real foreign key. The ordering defect is fixed regardless.**

**The maintainer's reason gives the feature a much stronger justification than "it was declared":** *"wir verzweigen ja eventuell an einem Snapshot. Da wäre es ja auch sinnvoll, den Chat zurückrollen zu können."*

**Conversation branching mirrors aeroplane branching.** A version branch taken at a snapshot puts the design back to an earlier state, and the conversation that led there should be able to follow — so the user can resume the dialogue from the point the design was resumed from. The two structures answer the same question — *what if I had gone the other way here?* — and having one without the other is the asymmetry.

> **⚠ Corrected 2026-08-15.** An earlier version of this answer additionally argued that
> without chat branching *"every later turn reasons from a stale premise."* **The
> maintainer rejected that as a conflation, and they are right: it is a different problem
> with a different solution.** Model staleness is not caused by conversation structure and
> is not fixed by branching — it is fixed by injecting current state into the context
> instead of letting the model pull it through tools. See **`Q-CO-14`**. Branching stands
> on the rollback argument alone.

That makes `parent_id` a **real FK on the message table**, not the bare `Integer` it is today. It also strengthens `Q-CO-1`: a version referencing a *turn* stays unambiguous once conversations themselves branch.

**Fixed regardless of the branching work — this is a live defect, not a design question.** `sort_index` is assigned as `COUNT(*)` at append time, so two concurrent appends collide on one index and an append after `delete_message` **reuses** an index already spent. Ordering moves to `created_at` + `id` (or a sequence). Under branching this matters more, not less: ordering must be well-defined *within a branch*.

**Left open, minor:** `role="tool"` rows are supported by the schema, never written, and the replay branch handling them is unreachable. Deleting it is the ADR 0021 default, but it was not put to the maintainer and it is cheap either way — resolve when that code is next touched.

---

## Q-CO-6 — Should `diff_vs_live` be renamed, removed, or implemented?

**Context:** It carries the **proposal's own before/after**, not
live-vs-proposal, and the system prompt spends a paragraph telling the model not
to use either diff for performance numbers.
**Spec affected:** [`_reversa_sdd/ai-copilot/copilot-tools/requirements.md`]
**Question:** Remove the alias, or implement a real live-vs-proposal diff?
**Impact:** A misleading name that costs prompt tokens to work around.

**Answer:** **ANSWERED by the maintainer, 2026-08-15** (option b) — **implement a real live-vs-proposal diff. The name stays; the content is made to match it.**

The field currently carries the **proposal's own before/after**, not live-versus-proposal — so the name promises a comparison the payload does not contain. The cost is visible in the system prompt, which spends a paragraph telling the model **not** to use either diff for performance numbers: prompt tokens, and a standing instruction to distrust a field, both caused by a mismatch between a name and its content.

Renaming (option a) would have been the cheap fix and is what ADR 0019 strictly requires — *the name describes the thing*. The maintainer chose the other resolution of the same rule: **make the thing match the name.** A live-vs-proposal comparison is what a reviewing human actually needs before adopting — *what changes if I accept this?* — which is precisely the question **ADR 0007** puts to them.

**Consequence:** once the field means what it says, the prompt paragraph warning the model off it can be deleted, and the diff becomes usable in the adopt/discard UI rather than being an internal artefact the model is told to ignore.

---

## Q-CO-7 — `RemoveXsec` sums the sweeps while the comment says "weighted avg": which is intended?

**Context:** `seg_before["sweep"] + seg_after["sweep"]` sits directly under a
comment reading "sweep = weighted avg". A geometry-changing divergence between
comment and code.
**Spec affected:** [`_reversa_sdd/ai-copilot/copilot-tools/requirements.md`]
**Question:** Which is intended?
**Impact:** Every AI-driven station removal changes the planform incorrectly if
the comment is right.

**Answer:** _(expert consensus, endorsed by the maintainer 2026-08-14)_ **The sum is correct and the comment is wrong — sweep is a chordwise *distance* along an invariant `xDir`, so the merged segment must reproduce `x_{j+1} − x_{j−1} = sweep_j + sweep_{j+1}`.**

The representation is pinned independently in two places: `app/schemas/wing.py:200-202` defines sweep as *"Sweep in millimeters, representing the backward translation of the segment's tip cross section relative to the segment's root cross section"*, and `cad_designer/cq_plugins/wing/wing_segment.py:25-29` converts an angle input to a distance **first** (`b = e/cos(radians(sweep))`, `sweep = √(b² − e²)`) and then applies it as a translation `tip_origin = root_plane.origin + root_plane.xDir · sweep`. The dihedral rotation is about the local x axis (`.plane.rotated((tip_dihedral, 0, -tip_incidence))`), so `xDir` is invariant under it: **every segment's sweep offset points along the same global chordwise direction**, the offsets are collinear, and they simply add — `x_k = x_0 + Σ_{i=1..k} sweep_i`. Deleting interior station *j* must leave every surviving station where it was, so the merged segment's single sweep parameter must satisfy `sweep_merged = sweep_before + sweep_after`. ∎ The comment is wrong twice over: if `sweep` *were* an angle Λ the invariant would sit on the **tangent** — `tan Λ_merged = (L_j tan Λ_j + L_{j+1} tan Λ_{j+1})/(L_j + L_{j+1})` — a length-weighted average of `tan Λ`, which equals the weighted average of Λ only to first order in small angles. So "weighted average" is the right *shape* of answer for an angle representation and the wrong answer for a distance representation; it is a fossil from an angle-valued design. Numeric check: two 300 mm segments with sweeps 40 mm and 80 mm have a true root→tip x-offset of 120 mm — the sum gives **120 mm** ✅, the length-weighted average gives **60 mm** ❌, the simple average **60 mm** ❌. **The error equals the sweep itself; this is not a rounding-level divergence.**

Four actions: **(1)** keep the sum and fix the comment to *"sweep offsets are chordwise distances and therefore add; the merged segment must span station j−1 → j+1"*. **(2)** Add the 40 + 80 = 120 mm regression test so the sum can never be "corrected" back to an average by someone reading the old comment. **(3) Warn on dihedral loss** — `merged_length = length_before + length_after` is exact only when the two segments share a dihedral, because `length` is measured in the segment's own (dihedral-rotated) plane, so two segments with different dihedral form a dogleg whose true chord is `L_merged = √(L_a² + L_b² + 2·L_a·L_b·cos Δφ) < L_a + L_b`. At Δφ = 5° (typical polyhedral) two 300 mm segments give 599.4 mm vs 600 mm summed — **0.1 %, negligible**; at Δφ = 30° (winglet junction) 579.6 mm vs 600 mm — **3.4 %**. And the tip's z-position is wrong regardless, because one merged segment carries only one dihedral. Emit a `DesignWarning` (`geometry_simplified`) when the merged segments' dihedrals differ by **> 2°**, escalating to `severity="warning"` when the span error exceeds **0.5 %** (Δφ ≳ 11.5° for equal-length segments). **(4)** Document the length approximation in the same comment.

**Authority:** the derivation is exact and the representation is pinned by two independent places in the codebase (`app/schemas/wing.py:200-202`, `cad_designer/cq_plugins/wing/wing_segment.py:25-32`); no expert source is needed to override another. RC practice contributes only that polyhedral breaks of 3–8° are extremely common on RC gliders, where the length-sum approximation is genuinely negligible (≤ 0.3 %).
**Confidence:** high
Disagreement: none — this is pure geometry, identical at every scale and Reynolds number.

_Full reasoning: [`expert-consensus-aero.md`](expert-consensus-aero.md)_

---

## Q-CO-8 — Is mid-wing `AddXsec` planned, or should the dead branch go?

**Context:** Any interior `at_index` is rejected with a message steering the model
to a tip-append; the splice code exists but is documented as reachable only for an
empty wing. The limitation is discovered through a rejection rather than stated
in the tool description.
**Spec affected:** [`_reversa_sdd/ai-copilot/copilot-tools/requirements.md`]
**Question:** Planned, or remove the dead branch and document the limitation up
front?
**Impact:** The model wastes a turn discovering it.

**Answer:** **ANSWERED by the maintainer, 2026-08-15** (option b) — **mid-wing section insertion is implemented. It is not a convenience; a domain constraint requires it.**

**The maintainer's reason, which reframes the question entirely:** *"wichtig für das Setzen von Control Devices in eine Fläche, die ohne definiert ist. CD sind ja immer über ein Segment definiert."*

**A trailing-edge device is defined over a *segment*, not over a station.** A segment is the span between two adjacent cross-sections. So a wing built without control surfaces has no segment boundary where one is wanted, and **the only way to give it one is to insert a section mid-span**. Steering the model to a tip-append cannot produce it: appending at the tip creates a segment at the tip, which is not where the aileron goes.

That makes the current behaviour a **functional gap**, not a rough edge. Today any interior `at_index` is rejected with a message pushing the model toward a tip-append, and the splice code exists but is documented as reachable only for an empty wing — so adding a control surface to an existing wing is simply not expressible through the copilot.

**Implementation note, from `Q-WD-5`:** segments are built up such that a new segment's root adopts the previous segment's tip — the invariant is a property of the construction API (`add_segment`), which `from_json_dict` bypasses. A mid-span insert has to honour that: the inserted section becomes the tip of the preceding segment **and** the root of the following one, so both neighbours stay consistent. Chord, twist, airfoil and dihedral at the insertion station are interpolated from the two neighbours unless given, so inserting a section without further arguments is geometrically a no-op that only adds a segment boundary.

**The tool description states the capability up front** either way — the model should not have to discover the shape of the API through rejections.

---

## Q-CO-9 — Is a per-user or per-aeroplane quota needed before this is exposed publicly?

**Context:** No rate limit, token budget or cost accounting exists. Nothing bounds
a turn except `MAX_LOOP_ITERATIONS = 6`, and two `run_analysis` calls can hold the
request-scoped DB session for two minutes. The copilot is the only path that costs
money per request.
**Spec affected:** [`_reversa_sdd/ai-copilot/requirements.md`],
[`_reversa_sdd/adrs/0007-…md`]
**Question:** Is a quota needed before public exposure? (See Q-CC-1 — there is no
identity to attach a quota to.)
**Impact:** Unbounded spend on an unauthenticated endpoint.

**Answer:** _(derived — not a maintainer decision)_ **No quota — deliberately out of scope, and documented as such.**

Follows from **Q-CC-1**, which names this question: "Per-user quota (`Q-CO-9`) … [is] **deliberately out of scope, documented as such**, to be revisited if and when multi-user arrives." The question's premise ("before this is exposed publicly") is void under that answer: da3Dalus is a single-user desktop application, the ngrok chain is the maintainer's own testing tool rather than a product surface, and with the loopback defaults there is no public endpoint to bound. `MAX_LOOP_ITERATIONS = 6` remains the only limit, and the spend is the single user's own.

---

## Q-CO-10 — Is the "agentic expert panel" still planned?

**Context:** `COPILOT_EMBEDDING_MODEL` exists with a default
(`text-embedding-3-large`) and nothing reads it; there is no embedding, vector
store or retrieval code. `.env.example` records that the RAG plan was superseded
by gh-929 ("agentic expert panel", lexical retrieval via ripgrep + BM25 + link
graph) — of which nothing is implemented either. Meanwhile the provisional
knowledge tables (static-margin bands per mission, V_H, L/D benchmarks,
first-flight CG) are hard-coded in the prompt string, labelled *"until RAG is
available"*.
**Spec affected:** [`_reversa_sdd/ai-copilot/requirements.md`]
**Question:** Still planned? Should the unused setting be removed until then, and
should the tables be sourced from the `rc-aircraft-designer` / Scholz skill data
rather than duplicated in a string?
**Impact:** The copilot's domain knowledge currently lives in a prompt literal.

**Answer:** **ANSWERED by the maintainer, 2026-08-15** (option b) — **the agentic expert panel stays planned, and its knowledge source is now specified: the same domain-expert skills already in this repository.**

**The maintainer's clarification is the substance:** *"das sind die gleichen Experten-Skills, die auch du aktuell verwendest. Eventuell kommen noch Konstruktionsexperten hinzu."*

That settles what gh-929's *"agentic expert panel"* actually retrieves over. It is **not** a separate corpus to be built, embedded and maintained: it is `/aircraft-design-scholz`, `/aerodynamics-expert`, `/aerosandbox-expert`, `/avl-advisor`, `/rc-aircraft-designer` — the same vaults consulted throughout this interview — with **construction experts** as a likely addition. The authority hierarchy in `CLAUDE.md` transfers unchanged, including *scholz outranks rc-aircraft-designer on conflict*, which the panel must honour rather than average.

This also explains why gh-929 superseded the RAG plan: these vaults are structured markdown with a link graph, so **lexical retrieval (ripgrep + BM25 + links) is the right tool**, not embeddings. It is what the interview's own consultations used, successfully.

**The provisional knowledge tables stay in the prompt for now** — that is what option (b) preserves — but they are recorded as an **ADR 0022 debt, to be discharged when the panel lands.** Static-margin bands per mission, tail volumes, L/D benchmarks and first-flight CG are currently hard-coded in a prompt string while the same numbers live, sourced and citable, in the skill vaults. Two producers of a user-visible number, and the string cannot be kept in sync because nothing links them. For reference, the values this interview extracted: **trainer 5/10/15 %, sport 3/4/5 %, acrobatic 0/1.5/3 % static margin, with a 5 % MAC first-flight floor regardless of mission.**

> **Residual the maintainer may want to overrule.** Option (b) as offered bundled two things, and one of them may not belong: keeping `COPILOT_EMBEDDING_MODEL` (default `text-embedding-3-large`, read by nothing). That setting belongs to the **superseded RAG plan**, not to the agentic panel — under lexical retrieval no embedding model is needed at all. By ADR 0021 it is a config key for an abandoned design and should go. Flagged rather than acted on, since the maintainer's choice was recorded against the bundled option.

---

## Q-CO-11 — Should any system-prompt policy become server-side validation?

**Context:** The highest-value rules are prose only: "never present snapshot L/D
as definitive", "do not mix snapshot cd0 with polar CD", the static-margin / V_H /
L-D bands, and the physics direction checks (V ∝ √(W/S)). Nothing enforces them.
Related: a missing `x_np_m` silently disables the single-source guarantee — the
solver's own neutral point is then reported, which is exactly the divergence the
gh-924 override exists to prevent. And the mm/degrees exception is a standing
trap: five tools speak SI while `get_wing_geometry` speaks mm, documented only in
a module docstring and a `note` field.
**Spec affected:** [`_reversa_sdd/ai-copilot/copilot-tools/requirements.md`],
[`_reversa_sdd/ai-copilot/requirements.md`]
**Question:** Should any of these become server-side validation of the tool
payloads rather than prompt text?
**Impact:** Prompt text is the only guard on the copilot's numeric claims.

**Answer:** **Yes — whatever protects a number is enforced in the tool, not requested
in the prompt.** _Answered by the maintainer, 2026-08-15._

The highest-value rules exist only as prose ("never present snapshot L/D as
definitive", "do not mix snapshot `cd0` with polar `CD`", the static-margin / V_H / L-D
bands, the physics direction checks). An LLM *can* follow them; it cannot be relied
upon to.

**Required:**
- **A missing `x_np_m` must not silently disable the single-source guarantee.** Today
  the solver's own neutral point is reported instead — precisely the divergence the
  gh-924 override exists to prevent. It becomes a `DesignWarning` (`P-WARN-0`).
- **The mm-vs-SI trap belongs in the tool schema.** Five tools speak SI while
  `get_wing_geometry` speaks millimetres, documented only in a module docstring and a
  `note` field. Under ADR 0019 this is an implementation detail leaking into the
  contract: the unit must be explicit in the schema, not a footnote an agent may miss.
- Band and consistency checks that guard reported numbers are evaluated server-side and
  surfaced as warnings, rather than being left to prompt discipline.

---

## Q-CO-12 — Should the proposal branch be typed rather than string-matched?

**Context:** A proposal is identified by `name LIKE 'copilot-proposal%'` plus
`created_by = 'copilot'`. Consequences: a human renaming the branch **orphans**
it (the next AI edit opens a second proposal); `_find_open_proposal` takes the
newest by `id DESC` and `create_branch` has no collision check, so an older
proposal is silently abandoned with its edits; `created_by = 'ai'` is documented
by `BranchRequest` and **would break reuse** because the query filters on
`'copilot'`; a fully-rejected op batch still leaves the branch open, so the UI
shows a proposal containing no changes; and adopt-during-turn is unspecified and
untested — once the proposal becomes `main`, a later tool call in the same turn
opens a *second* proposal from the adopted design.
**Spec affected:** [`_reversa_sdd/ai-copilot/proposal-adopt-discard/requirements.md`],
[`_reversa_sdd/versioning/copilot-provenance/requirements.md`]
**Question:** Would a typed `branch_kind` column be preferable to string matching?
And what should adopt-during-turn do?
**Impact:** Five failure modes with one root cause.

**Answer:** **(a) Full package: typed `branch_kind`, uniqueness, auto-close of
empty proposals, and a specified adopt-during-turn rule.** _Answered by the
maintainer, 2026-08-13._

1. **Typed column** `branch_kind ∈ {main, manual, proposal}` with a `CHECK`
   constraint (the enforcement level chosen in `Q-CC-9`). String matching on
   `name LIKE 'copilot-proposal%'` is removed, so **renaming a branch becomes
   harmless** (failure mode 1).
2. **At most one open proposal per `root_id`**, as a partial unique index. There is
   direct precedent in the schema: the index already enforcing exactly one
   `is_main = true` per `root_id`. This makes failure mode 2 — an older proposal
   silently abandoned along with its edits, because `_find_open_proposal` takes the
   newest by `id DESC` and `create_branch` performs no collision check —
   structurally impossible.
3. **Empty proposals close automatically.** A fully rejected op batch no longer
   leaves an open branch containing no changes (failure mode 4).
4. **Adopt-during-turn is specified and tested:** once a proposal has become `main`,
   subsequent tool calls in the same turn open a **new** proposal from the adopted
   state. This preserves the ADR 0007 invariant that the AI never writes to `main`
   directly. It is already the de-facto behaviour — the change is making it
   intentional and covered by a test (failure mode 5).

**⚠️ Must be implemented together with `Q-CC-9`.** That decision changes
`created_by` to `'ai'` (with the specific agent in a separate detail field), while
the proposal query filters on `created_by = 'copilot'`. Applying `Q-CC-9` alone
would **break proposal reuse** (failure mode 3). The typed `branch_kind` removes the
dependency on `created_by` for identification entirely, which is the clean
resolution.

---

## Q-CO-13 — Should the copilot's polar sweep follow the aircraft's cruise speed?

**Context:** The sweep is hard-coded: α ∈ [−10°, +15°], 26 points, V = 20 m/s,
h = 0. A 30 m/s cruise aircraft is still polared at 20 m/s.
**Spec affected:** [`_reversa_sdd/ai-copilot/copilot-tools/requirements.md`]
**Question:** Should it read the mission's cruise condition?
**Impact:** The model reasons about a polar for the wrong flight condition.

**Answer:** _(expert consensus, endorsed by the maintainer 2026-08-14)_ **Yes — read `ctx["v_cruise_mps"]` exactly as `_run_stability_async` already does in the same file, and replace the fixed α range with a stall-anchored `α ∈ [−6°, +16°]` at 1° steps (23 points).**

The precedent already exists and the polar tool simply never adopted it: `copilot_tools.py:424-428` reads `ctx["v_cruise_mps"]` from `assumption_computation_context` with a 20.0 fallback, carrying a gh-924 comment explaining why the design point must be consistent, while `:336-342` hard-codes `velocity=20.0, altitude=0.0`. In strictly inviscid incompressible flow `C_L(α)` and induced `C_Di` are independent of V, so the polar is speed-dependent **entirely through Reynolds number** (Mach is irrelevant below M ≈ 0.3, i.e. always at this scale): `C_f,lam = 1.328/√Re_c`, `C_f,turb = 0.074/Re_c^{1/5}`, and the transition point `x_cr = μ·Re_{x,cr}/(ρV)` moves forward with V — doubling V from 15 to 30 m/s reduces laminar `C_f` by 29 % and turbulent `C_f` by 13 % before any transition or separation-bubble effects. **At RC scale this stops being academic.** With RC-Network's working formula `Re = v[m/s] · t[mm] · 70`, a 200 mm chord gives Re = 168 000 at 12 m/s (park flyer), **280 000 at the hard-coded 20 m/s**, and 420 000 at 30 m/s — all at or below the critical Reynolds number where model wings live, where RC-Network warns that "flow conditions on wings and tail surfaces can change dramatically with relatively small changes in airspeed" and Lennon quantifies a NACA 0012's `C_Lmax` falling from 1.55 to 0.83 (**−54 %**) with stall α from 17° to 10° and **profile drag nearly doubling**. So polaring a 12 m/s park flyer at 20 m/s can flatter `CD0` by up to ~2× and overstate `C_Lmax` by up to 50 % — **a larger error than the camber issue in Q-VI-8.** The fix costs nothing in runtime: AeroBuildup gets its sectional aerodynamics from NeuralFoil, whose training distribution covers Re ∈ [1.87 k, 262 M] at 95 % so 50 k–500 k is squarely inside it, and AeroBuildup is vectorised over operating points, so the corrected sweep is still a single call.

Five changes: **(1)** read `ctx["v_cruise_mps"]` with the same 20.0 fallback — one design point, one polar, consistent with gh-924 / ADR 0004. **(2)** Report the condition inside the result: add `velocity_mps`, `altitude_m` and the derived `reynolds_number` (= `v · MAC_mm · 70`) to the summary dict, so the model cites the flight condition it reasoned about instead of assuming one. **(3)** Replace the fixed α range with **[−6°, +16°], 1° steps, 23 points** — −6° covers the inverted/dive branch and the zero-lift point of any realistic RC section (`α_L0` reaches −6.05° on the FX 61-184 computed in Q-VI-8), so the current −10° wastes 4 points below any usable condition; +16° is past `C_Lmax` for every section at RC Re (stall α as low as 10°), so the sweep always brackets the peak, where the current +15° can *just* miss it on a high-Re, high-camber section; 1° steps hold `C_Lmax` to better than 2 % (for a quadratic peak sampled at Δα the peak-location error is ≤ Δα/2 and the `C_Lmax` error ≈ ½|d²C_L/dα²|(Δα/2)²), and since the existing 26 points over 25° is 0.96°, this is a **re-aiming, not a refinement**. **(4) Do not sweep velocity** — one polar = one Reynolds number; if a second condition is wanted (approach, dash), run a *second* sweep and label it, never mixing speeds into one curve. **(5)** Take altitude from `profile.environment.altitude_m` rather than the hard-coded 0.0.

**Authority:** Anderson (`C_f,lam`, `C_f,turb`, transition-point dependence on V); Scholz — the aircraft polar is computed *"for all critical flight phases"*, never once at an arbitrary speed (Step 13 of the conceptual design process); RC-Network `Re = v·t·70` and Lennon's −54 % `C_Lmax` / doubled profile drag across the model Re band; AeroSandbox tooling (NeuralFoil training coverage; AeroBuildup vectorisation).
**Confidence:** high
Disagreement: RC practice would accept the fixed sweep for a first-cut trainer, since level-flight `C_L` of 0.2–0.3 stays comfortably in the linear range whatever the Re, while Scholz requires the phase-matched polar. Resolved in favour of Scholz per the authority hierarchy — and here the RC source's own Re data independently supports the academic ruling once the numbers are looked at, so this is agreement rather than a genuine conflict.

_Full reasoning: [`expert-consensus-aero.md`](expert-consensus-aero.md)_

---

# mcp-server

---

## Q-CO-14 — The model's view of the aircraft goes stale, and nothing tells it

**Raised by the maintainer, 2026-08-15**, while correcting `Q-CO-5`. **Direction stated by
the maintainer at the same time**, so this is recorded as a decision rather than an open
question.

**Context — verified in code.** The turn's message list is assembled as
`[system prompt] + [replayed history]` (`app/services/copilot_service.py:485-487`, via
`_history_to_openai`). The history carries **past tool results**, i.e. the aircraft state
as it was when those tools ran. **Nothing re-injects current state at the start of a
turn.**

**The maintainer's observation, which is the defect:** *"das passiert nämlich schon jetzt
— wenn ich etwas verändere, bekommt das aktuell das LLM nicht mit und fühlt sich auch
nicht genötigt, sich neue Daten heranzuziehen."*

Both halves matter. The model is not **told** the design changed, and it has no reason to
**suspect** it — from inside the conversation, the tool result it already has looks
authoritative and current. So it will happily reason, and propose, against geometry that
no longer exists. For a feature whose output is design changes, that is a correctness
problem, not a freshness annoyance.

**Answer:** **DIRECTION SET by the maintainer, 2026-08-15** — **part of the context is
reserved and written by the system with current, valid data on every turn, instead of
being populated by the model through tool calls.**

**Why this is the right shape, not just a fix:**

- **It removes the failure mode rather than guarding it.** Prompting the model to
  "re-fetch if unsure" cannot work: it has no signal that would make it unsure. Telling
  it the truth every turn does not depend on the model noticing anything.
- **It is ADR 0022 applied to the model's context.** Today there are two producers of
  "what is the current state of this aircraft" — the injected system content and whatever
  tool results happen to be replayed in the history — and the second is silently stale.
  One authority: the injected block.
- **It saves a turn.** State the model is given does not have to be fetched, so the common
  case stops spending a tool round-trip on data the server already had.

**Consequences to work out when this is built:**

- **Which state is pinned** — geometry summary, mass and CG, the current aero context
  (`Q-AA-*`), open proposal status. Large enough to be useful, small enough not to crowd
  the window.
- **Replayed tool results become historical, not current.** They should read as such, or
  the model will still treat an old `get_wing_geometry` result as live. Options range from
  stamping them with the turn they came from to eliding superseded ones on replay.
- **Interaction with `Q-CO-5`.** Once conversations branch, the injected block must
  reflect the state of the *branch being continued*, not the live aircraft.

> **Deferred to implementation by the maintainer, 2026-08-15 — and one tension named,
> because it is easy to resolve wrongly.** The three consequences above are to be worked
> through when this is built, *"gerade was eine gewisse Historie angeht, so dass das LLM
> den Effekt seiner Änderungen auch sehen kann."*
>
> **The tension:** the fix above pushes toward *"stop the model treating old tool results
> as current"*, and the obvious implementation — eliding superseded results on replay —
> would also destroy something valuable. A model that cannot see **what its own edits
> did** loses cause and effect within a session: *"I raised dihedral to 4°, and the spiral
> criterion moved from divergent to neutral."* That trajectory is exactly what makes a
> second proposal better than the first, and it is not stale information — it is a record
> of a transition.
>
> **The two requirements are compatible, but only if they are kept distinct:**
>
> | | carries | framing |
> |---|---|---|
> | **pinned block** | the aircraft **now** | authoritative, rewritten every turn |
> | **change record** | what moved, from what, to what — and what it caused | explicitly historical, never a state source |
>
> A replayed raw `get_wing_geometry` result satisfies neither: it reads as current and
> carries no transition. A change record (*"dihedral 3° → 4°; spiral margin 0.68 → 1.25"*)
> is both non-stale **and** causally informative — and it is much smaller than the tool
> output it replaces.
>
> **Not decided here.** Whether that record is derived from the version graph (`Q-CO-1`
> already links versions to turns), from `DesignWarning` deltas, or from the aero context
> is an implementation question. What is decided is that *"remove stale state"* must not
> be implemented as *"remove history"*.

**Related:** `Q-CO-5` (branching — the problem this was mistakenly conflated with),
`Q-CO-1` (provenance), [ADR 0022](adrs/0022-one-authority-per-user-facing-quantity.md),
[ADR 0007](adrs/0007-copilot-proposes-human-adopts.md) — a human can only adopt
responsibly if the proposal was made against the design that actually exists.

---

---

## Q-CO-15 — A domain-specific compaction for the copilot conversation

**Proposed by the maintainer, 2026-08-15**, developing the change record of `Q-CO-14`.
Recorded as a direction; the design is deliberately not finished here.

**The proposal:** instead of generic LLM summarisation, the copilot's history is compacted
into a **structured chronological record** of three event kinds —

1. **stated design goals**,
2. **change actions**,
3. **results, as diffs**

— and *"die Diskussion dazwischen ist für eine Historie irrelevant."*

**Why this fits this domain unusually well, and better than generic compaction:**

- **The truth is not in the transcript.** Unlike open-ended chat, the authoritative state
  of the design lives in the database. The conversation is *about* an object that exists
  independently, so the transcript's job is to record what was **asked for** and what was
  **done** — not to be the record of the thing itself. That is exactly the split
  `Q-CO-14` establishes between the pinned block and history.
- **Design work has a native event structure.** Goal → action → result is not a
  compression heuristic here; it is the actual shape of the work. A summary that follows
  it loses far less than prose summarisation, which discards unpredictably.
- **Most of it can be *derived* rather than summarised — which matters for reliability.**
  Actions are the tool calls that mutated something. Results are diffs already obtainable
  from the version graph (`Q-CO-1` links versions to turns) and the aero context. **Only
  the design goals require extraction from prose**, so exactly one part of the compaction
  needs a model at all, and the rest cannot hallucinate.
- **It solves three problems at once:** context-window growth, the staleness of `Q-CO-14`,
  and the loss of cause-and-effect the maintainer flagged there.

**Design goals are the one part that must survive verbatim.** A goal stated early —
*"45 minutes endurance"*, *"it has to fit in the car"* — constrains every later turn, and
paraphrasing it lets the constraint drift silently. Goals are **quoted**; actions and
results are **structured**.

**One refinement the maintainer may want to weigh, offered rather than assumed.**
*"Discussion is irrelevant"* is right for deliberation, but there is one edge case that
looks like discussion and behaves like an event: **a rejected proposal together with the
reason it was rejected.** If the copilot proposes a change, the maintainer declines it
because of something not otherwise recorded, and the exchange is discarded as chatter,
nothing prevents the same proposal from returning. Under `Q-CO-14` it would return
*confidently*, since the pinned state shows the design unchanged. Treating a rejection as
a fourth event kind — *goal · action · result · rejected-with-reason* — keeps the record
free of prose while preserving the only part of the conversation that constrains the
future.

**Interactions already visible:**

- **`Q-CO-14`** — this *is* the change record; the pinned block remains the state source.
- **`Q-CO-5`** — a branched conversation takes the compacted record up to the branch
  point, which is far cleaner to branch than a raw transcript.
- **`Q-CO-1`** — the provenance link already ties versions to turns, so half the result
  diffs are derivable rather than reconstructed.

### Extension, maintainer 2026-08-15 — make the protocol produce the record

Two additions, the second of which changes the design rather than adding to it.

**① The raw conversation is archived separately.** Compaction becomes a *reduction* —
goal · action · decision — over a transcript that is still kept in full. Nothing is
destroyed; the compact form is a view. That removes the risk in every lossy scheme: when
someone later asks *why*, the answer is still there.

**② The construction agent states the goal explicitly with the designer, and requests
approval before changing the design.** *"Am besten wäre es eigentlich, wenn der
Konstruktions-Agent immer das Ziel klar mit dem Designer formuliert und Freigaben vor
Änderungen am Design klar einfordert. Dies können wir dann auch leichter archivieren."*

**This inverts the problem, and it is the strongest idea in this thread.** Everything above
tries to *recover* structure from prose after the fact — extracting goals, inferring which
exchange was a rejection. If the interaction protocol requires the goal to be agreed and
the change to be approved, those events **already exist as artefacts** at the moment they
happen. The record is a **byproduct of the protocol, not an extraction from it** — so the
compaction needs no model at all, not even for goals, and cannot drift or hallucinate.

It also resolves the rejection edge case identified above by construction: a declined
approval *is* the rejection event, with its reason attached, because declining is a
protocol step rather than a remark in prose.

**And it makes ADR 0007 real at the conversational layer.** That ADR establishes
*copilot proposes, human adopts* — today enforced only by the proposal-branch mechanism,
i.e. structurally, after the fact. Requiring stated goals and explicit approval makes it
the shape of the interaction itself, which is where a user actually experiences it.

The event kinds settle as protocol steps:

| step | produced by | archived as |
|---|---|---|
| **goal agreed** | agent states it, designer confirms | quoted, verbatim |
| **change proposed** | tool call against the proposal branch | structured |
| **approved / declined** | explicit designer decision, reason on decline | structured + quoted reason |
| **result** | diff from the version graph and aero context | derived |

### Granularity — resolved by the maintainer, 2026-08-15

**Approval attaches to the outcome, not to the search.** Given a goal such as *"design a
winglet that reduces the aircraft's induced drag"*, the agent explores, tests and iterates
without asking; the designer approves **the final optimum** — the end result, not the steps
that found it.

**What makes that safe is already in the architecture.** The search runs on the proposal
branch, so nothing it tries touches the live design (ADR 0007). Approval is therefore not
a safety gate on each step — it is the **commit** of a result. Asking per step would be
asking permission for something that has no effect.

**The goal must be made measurable during goal-agreement, and the agent must insist.**
The maintainer's own example, flagged by them: *"mir ist klar, dass 'signifikant' keine
gute Anforderung ist — hier muss der Konstruktionsagent klar mit mir diskutieren, was
'signifikant' in messbaren Zahlen ist."*

This turns goal-agreement from **capture** into **negotiation**, and it is not politeness:

- **An unquantified goal cannot terminate a search.** *"Significantly reduce induced
  drag"* has no stopping condition; *"reduce CDi by ≥8 % at cruise CL without raising root
  bending moment by more than 5 %"* is simultaneously the goal, the acceptance criterion
  and the reason the agent stops. Autonomous search is only terminable against a number.
- **An unquantified goal archives worthless.** The whole value of quoting goals verbatim
  (above) collapses if the quote is *"make it better"*.
- **It is where the domain experts belong.** What counts as a significant CDi reduction at
  RC/UAV scale is exactly the kind of question the expert skills answer (`Q-CO-10`), so
  the agent can propose a defensible number rather than asking the designer to invent one.

**Two refinements, maintainer 2026-08-15:**

**① The search trajectory is *not* persisted — the live session already answers it.**
I had proposed archiving the agent's discarded candidates so *"what else did you try?"*
stays answerable. Over-engineered: *"das würde ich jetzt in der normalen Chathistorie
sehen, aber nicht persistieren. Die Fragen kann ich ja auf dem aktuellen Kontext stellen,
der geht ja nicht verloren."*

The question is asked **while the search is fresh**, and at that moment the raw
conversation is still in context. Building a structured archive of rejected candidates
would serve a question nobody asks a week later. **Scope stands as: goal · action ·
decision · result persisted; the search steps live and die with the session.** The raw
conversation archive (above) remains the fallback for anything else.

**② The agent advises on the number; it does not merely demand one.** Agreed in
principle, with an addition that changes the agent's job: *"der Konstruktionsagent muss
den Designer beraten, was da Sinn macht. Eventuell weiß der Designer gar nicht, wie er
etwas in Zahlen ausdrücken soll. Auch muss eine Plausibilitätsprüfung durch den
Konstruktionsagenten und seine Experten-Berater kommen."*

Two distinct obligations, and the second is the one that saves real time:

- **Translation.** A designer may know exactly what they want and have no idea how to
  state it as a number. *"It should glide better"* has to become a target on L/D or sink
  rate, and it is the **agent's** job to offer the formulation — with the quantity, the
  condition it is evaluated at, and a defensible starting value from the expert skills
  (`Q-CO-10`) — for the designer to accept or adjust. Asking an unaided designer to invent
  a threshold produces either a guess or a stall.
- **Plausibility check, before the search starts.** A goal can be well-formed and still
  unattainable — *"reduce induced drag by 40 % with a winglet"* is a number, and it is not
  achievable. The agent and its expert advisors must say so **up front**, with the reason
  and a realistic band, rather than searching for hours and reporting failure. This is
  also where **ADR 0023** applies: the plausible band must be established at RC/UAV scale,
  not carried over from transport-category literature where winglet gains are quoted
  against very different aspect ratios and Reynolds numbers.

A goal that survives both steps is worth quoting verbatim into the record, because it is
then a specification rather than a wish.

**One caution worth weighing before this is built: approval fatigue.** If every trivial
edit needs a confirmation, users stop reading and rubber-stamp — at which point the gate
has *destroyed* the accountability it was meant to create, while still costing a click.
The granularity question is therefore part of the design, not a detail after it: which
changes need explicit approval (anything altering geometry, mass or a design assumption)
versus which are self-evident from the proposal diff and need only be visible. Getting
this wrong in the tedious direction is worse than not building it, because it produces a
record of approvals nobody actually gave.

**Answer:** _Direction recorded, design deferred to implementation._

---

## Q-MC-1 — MCP writes are discarded: fix the transaction boundary, or formalise MCP as read-only?

**Context:** Verified during review. `_call_endpoint`
(`app/mcp_server.py:96-107`) opens `with SessionLocal() as db:`, calls the
endpoint and returns — **no `commit()`**. `Session.__exit__` rolls back. ~40 of
the 76 tools are mutations returning a convincing payload built from
flushed-but-uncommitted ORM state (readable only because
`expire_on_commit=False`) while persisting nothing. Durability is *inconsistent*,
not merely absent: services that commit themselves (`retrim_service`,
`operating_point_generator_service`, `tessellation_service`) **do** persist. No
test can catch it — the tool tests monkeypatch `_call_endpoint` and the
`_call_endpoint` tests use fake local functions.
**Spec affected:** [`_reversa_sdd/mcp-server/rest-mcp-reuse/requirements.md`],
[`_reversa_sdd/platform-core/requirements.md`] (BR-78),
[`_reversa_sdd/architecture.md`] TD-01
**Question:** Add the commit (or a `get_db()`-equivalent context manager), or
formalise MCP as a read-only agent surface and remove the write tools?
**Impact:** **Fixing it makes ~40 unauthenticated destructive tools actually
work** — see Q-CC-1. And once a commit is added, the self-committing services
need review for nested-commit behaviour: the fix is not a one-line change.

**Answer:** **Fix the transaction boundary — plus a write master-switch and
auto-snapshot before destructive writes.** _Answered by the maintainer,
2026-08-13._

**Base (required): fix `_call_endpoint`.** Use a `get_db()`-equivalent context
manager that **commits on success and rolls back on exception**, i.e. the same
behaviour the REST layer already has. Today `with SessionLocal() as db:` never
commits, so `Session.__exit__` rolls back and ~40 write tools return a convincing
payload — assembled from flushed-but-uncommitted ORM state, readable only because
`expire_on_commit=False` — while persisting nothing. This is the `P-WARN-0` failure
shape again: correct-looking output, no effect.

Also in scope of the fix:
- **Review the self-committing services** (`retrim_service`,
  `operating_point_generator_service`, `tessellation_service`) for nested-commit
  behaviour. Their existing self-commits are why durability today is *inconsistent*
  rather than simply absent. This is explicitly **not a one-line change**.
- **Repair the test arrangement.** No current test can catch this: the tool tests
  monkeypatch `_call_endpoint`, and the `_call_endpoint` tests use fake local
  functions — every test bypasses the defect.

**Layer ① — write master-switch.** `MCP_ALLOW_WRITES`, defaulting to **off**. Write
capability is granted deliberately for a session rather than being permanently on.

**Layer ③ — auto-snapshot before destructive writes.** Destructive MCP tools take a
version snapshot first, making agent edits **recoverable by construction** instead of
merely restricted. This reuses machinery that already exists — `spar_insert_service`
does exactly this (gh-1058, returning `snapshot_id`) — and is only trustworthy
because `Q-VS-1` makes snapshots genuinely immutable.

**Deferred — layer ② (curated write surface).** The ~40 tools are not equally risky
(`add_cross_section` is recoverable; `delete_aeroplane` is not), so restricting the
destructive subset was considered. **Deferred by the maintainer:** it requires a
per-tool review of 40 tools, and layer ③ already makes the damage reversible.

**Security precondition, already satisfied:** fixing this makes ~40 destructive tools
genuinely reachable. `Q-CC-1`'s loopback-by-default exposure guard is what makes that
acceptable.

---

## Q-MC-2 — Is the MCP surface intentionally frozen at the geometry/analysis core?

**Context:** 76 tools vs ~230 REST routes. Versioning, the copilot, the component
tree, components/COTS, construction plans, powertrain, OpenVSP import and mass &
CG have **no** MCP tools at all.
**Spec affected:** [`_reversa_sdd/mcp-server/requirements.md`]
**Question:** Intentionally frozen, or is the drift accidental?
**Impact:** Determines whether the spec describes a deliberate subset or a
maintenance gap.

**Answer:** _derived — not a maintainer decision (settled by ADR 0025)._

**Neither: the surface is neither deliberate nor drifting — it is derived.** The 76 tools
are whatever `_call_endpoint` could mechanically wrap, so the coverage question
("why these modules and not versioning, the copilot, the component tree?") has no design
answer. Nobody chose the subset; the route table did.

**The spec therefore describes it as a generated artefact, not a curated subset**, and
records that ADR 0025 replaces it: the next MCP surface is built on `copilot_tools` and
designed as an **agent capability set**. At that point "which modules are covered" becomes
a real design question with a real answer — and it is answered by what an agent needs, not
by which endpoints happened to be wrappable.

No coverage gap is filed against the current wrapper. Extending a surface that is
scheduled for replacement adds tools to throw away.

---

## Q-MC-3 — Should assets move out of the process?

**Context:** `ASSET_REGISTRY` is process-local, unbounded and never evicted, and
`tmp/mcp_assets/` is never cleaned up — so an `img://…` URI minted by one worker
is a **404 in another**, and multi-worker deployment is silently broken for
assets. `register_file_asset` also copies without a size cap, and
`_normalize_result` base64-encodes image bodies fully in memory. Separately,
`settings.base_url` defaults to `http://localhost:8000` while the service listens
on **8001**, so the asset-URL fallback is wrong out of the box.
**Spec affected:** [`_reversa_sdd/mcp-server/requirements.md`]
**Question:** Is a single-worker deployment assumed (see Q-CC-8), and should
assets move to the DB or a TTL cache?
**Impact:** Three defects with one root cause.

**Answer:** _(derived — not a maintainer decision)_ **Yes, single-worker is assumed and now asserted; assets stay in-process — externalisation is deliberately out of scope.**

Follows from **Q-CC-8** and **Q-CC-1**: Q-CC-8 makes single-worker operation permanent, asserted at startup, and names the MCP `ASSET_REGISTRY` as one of the four legitimately process-local stores, so "an `img://…` URI is a 404 in another worker" collapses to a documented architectural constraint; Q-CC-1 lists asset-registry externalisation among the items out of scope until multi-user arrives. Two residual defects in this question are *not* covered by that and remain real work: the `base_url` 8000-vs-8001 default, which **Q-CC-4** requires re-checking once the settings merge lands, and the unbounded, never-evicted registry plus the un-cleaned `tmp/mcp_assets/`.

---

## Q-MC-4 — Should `_call_endpoint` translate service exceptions and capability guards?

**Context:** The `ServiceException → HTTP` handler is registered on the FastAPI
app, which `_call_endpoint` bypasses, so a `NotFoundError` reaches FastMCP as a
raw Python exception rather than a structured, machine-readable error. For the
same reason `Depends(require_cad)` / `require_aerosandbox` **never run** on this
path, so the clean 503 the REST surface is supposed to return becomes a raw
`ImportError` for an agent. (Note: per the review, that clean 503 barely exists on
the REST side either — see Q-CC-1's neighbour G-C19.) A capability-gated tool also
fails at *call* time, not at *listing* time: an agent discovers the tool in
`tools/list` and only then learns it cannot run.
**Spec affected:** [`_reversa_sdd/mcp-server/rest-mcp-reuse/requirements.md`],
[`_reversa_sdd/mcp-server/tool-registration/requirements.md`]
**Question:** Should `_call_endpoint` map exceptions and apply the capability
guards? Should the tool listing itself be capability-filtered?
**Impact:** An agent currently cannot distinguish a missing aeroplane from a
missing dependency.

**Answer:** _(derived — not a maintainer decision)_ **Yes — `_call_endpoint` maps domain exceptions into the single structured error envelope and applies the capability guards itself.**

Follows from **Q-CC-3**, **P-WARN-0** and **Q-MC-1**: Q-CC-3 makes `{"error": {code, message, details}}` the single contract *everywhere* and counts the MCP layer as one of the two in-repo consumers, so an agent receiving a raw Python exception sits outside the contract; and `capability_unavailable` is a mandated `DesignWarning` category that a bypassed `Depends(require_cad)` / `require_aerosandbox` cannot produce. Q-MC-1 already re-works this wrapper for the transaction boundary, so the translation lands in the same change. *Not settled by this:* whether `tools/list` itself is capability-filtered, which remains a protocol/UX call.

---

## Q-MC-5 — Should `None`-returning endpoints get an explicit MCP result shape?

**Context:** `_normalize_result(None) → {"status": "ok"}`, so a delete that
matched nothing is indistinguishable from one that worked. Compounded by Q-MC-1,
where *every* write reports success.
**Spec affected:** [`_reversa_sdd/mcp-server/rest-mcp-reuse/requirements.md`]
**Question:** Give them an explicit shape?
**Impact:** The agent's only feedback signal on a destructive call.

**Answer:** _(derived — not a maintainer decision)_ **Yes — a `None` return gets an explicit shape that distinguishes "deleted N" from "matched nothing".**

Follows from **P-WARN-0** and **Q-MC-1**: answering `{"status": "ok"}` for a delete that matched nothing is an undeclared no-op reported as success — the same "convincing payload, no effect" shape that kept Q-MC-1's transaction defect invisible in production. Once writes genuinely commit, this result is the agent's only feedback signal on a destructive call, so it must carry the effect rather than a bare status.

---

## Q-MC-6 — Is passing `request=None` safe for every code path in those endpoints?

**Context:** Several tools (`download_export_zip`, `get_aeroplane_three_view`)
pass `request=None` into endpoints that declare a `Request` parameter. This works
only while no endpoint dereferences it, and a future change would break MCP
silently, with no test coverage.
**Spec affected:** [`_reversa_sdd/mcp-server/rest-mcp-reuse/requirements.md`]
**Question:** Confirm it is safe today, and should a test pin it?
**Impact:** A latent break with no detector.

**Answer:** _(resolved by code lookup — not a maintainer decision)_ **Safe on all three paths — every dereference sits behind the same `settings.base_url` fallback, and `request` is typed `Request | None`, so the contract is explicit rather than accidental.**

The three tools passing `request=None` are `download_export_zip` (`app/mcp_server.py:1034`), `analyze_alpha_sweep_diagram` (`:1114`) and `get_aeroplane_three_view` (`:1149`); the guard is the ternary at `app/api/v2/endpoints/cad.py:399-400` and `_resolve_base_url` at `app/api/v2/endpoints/aeroanalysis.py:69-71` (a third identical copy lives at `airfoils.py:199-201`), so MCP consumers always get `settings.base_url`. Confirmed separately on the same three lines, and independent of this question: **`download_export_zip` cannot succeed at all** — it omits `wing_name`, `creator_url_type` and `exporter_url_type`, all required by `cad.download_aeroplane_zip` (`app/api/v2/endpoints/cad.py:379-386`), and `_call_endpoint` injects only `db` and calls the endpoint with no try/except (`app/mcp_server.py:96-107`), so every invocation raises `TypeError` before `request` is ever touched.

**Verdict:** confirmed safe on the `request=None` question; confirmed defect on `download_export_zip`'s three missing arguments.
Residual decision: whether to pin `request=None` with a test — worth it, since nothing else would detect a regression.

_Full detail: [`wave3-lookups.md`](wave3-lookups.md) §N_


**Residual decision — ANSWERED by the maintainer, 2026-08-15: yes, pin it with a
test.**

`request=None` is confirmed safe on all three paths today, but **nothing else would
detect a regression**: if someone later dereferences `request` (e.g. `request.url`)
in one of those endpoints, the MCP call breaks at runtime while every REST test stays
green, because the REST layer always supplies a real `Request`. A test that invokes
the three paths with `request=None` closes that blind spot.
---

## Q-MC-7 — Is the standalone `run_mcp_server` mode still used?

**Context:** It hard-codes `0.0.0.0:8001`, ignoring `UVICORN_HOST`, on a surface
with no authentication. Nothing on the tool path is logged either — no
invocation, duration or error record, which is why a defect of Q-MC-1's severity
was invisible in production.
**Spec affected:** [`_reversa_sdd/mcp-server/tool-registration/requirements.md`]
**Question:** Is standalone mode still used, or is it dead? Should the tool path
be instrumented?
**Impact:** The bind address is a security question (Q-CC-1); the logging is why
the module's headline bug went unnoticed.

**Answer:** **Standalone mode is kept as scaffolding for later — but the MCP surface
will be rebuilt on the copilot tool layer, not carried forward as a REST wrapper.**
_Answered by the maintainer, 2026-08-15._

**Confirmed during the interview:** the in-app copilot does **not** use MCP. It calls
its own purpose-built layer (`copilot_tools.execute(tool_name, db, aeroplane_id,
**args)`, dispatched from `copilot_service`), which contains **no MCP reference at
all**. MCP is a second, independent tool surface built by *mechanically wrapping REST
endpoints* through `_call_endpoint`.

**Standalone mode is the point of MCP** — an external agent connecting without the
app — so it is retained. But it is **not needed now**: it has no caller anywhere
(only `if __name__ == "__main__"` in its own file), no entry point, no client config,
and it would bind the same port 8001 as the normal app. `P-DEAD-0` category 2:
scaffolding for planned work → **kept, marked, and recorded as not part of the
supported surface yet**.

**Fixed immediately regardless:** the hard-coded `host="0.0.0.0"` (it ignores
`UVICORN_HOST` and would serve the ~40 write tools to the local network — `Q-CC-1`).
Note it also bypasses `main.py`'s lifespan, so the CAD process pool would not shut
down cleanly.

**Architectural direction recorded:** when MCP is genuinely needed, it is built **on
`copilot_tools`**, not continued as a REST→MCP conversion. The reasoning is stronger
than mere tidiness: `Q-MC-1`'s transaction defect is an *artefact of the wrapping* —
`_call_endpoint` has to open its own session because a REST endpoint expects one, and
that is where the commit was lost; the same is true of the `request=None` plumbing.
`copilot_tools` already has the right signature. One tool implementation, two
transports (in-app copilot and external MCP agents) — ADR 0022 applied to the tool
layer. The maintainer notes the existing REST→MCP conversion then becomes dead code;
it is **not** dead today, since it is the only MCP surface that exists.

**Sequencing note:** the `Q-MC-1` fix targets the *current* wrapper. With
`MCP_ALLOW_WRITES` defaulting to off, writes are inert by default; if the
copilot-tools rebuild lands first, the wrapper is replaced rather than repaired.

**Logging exception to `Q-PC-3`:** the MCP tool path is instrumented — one record per
invocation (name, duration, outcome). `Q-PC-3` deliberately excluded a metrics stack,
but the total absence of logging here is **why a defect of `Q-MC-1`'s severity stayed
invisible**: ~40 tools reported success, persisted nothing, and left no trace. This is
basic logging, not observability infrastructure.

---

## Q-MC-8 — Is there a review process keeping tool descriptions in sync?

**Context:** Tool descriptions are the **only** documentation — the tool
coroutines carry no docstrings, and the input schema is derived from the
signature (Q-CC-12). Nothing prevents duplicate tool names in `TOOL_SPECS`, and
registration is completely silent — no log line records how many tools a process
exposes.
**Spec affected:** [`_reversa_sdd/mcp-server/tool-registration/requirements.md`]
**Question:** Is there a process keeping descriptions in sync with the endpoint
behaviour they proxy?
**Impact:** An agent's entire understanding of the API comes from these strings.

**Answer:** _derived — not a maintainer decision (ADR 0025) + two defects recorded._

**There is no such process, and under ADR 0025 there should not need to be one.** Keeping
descriptions in sync with proxied endpoint behaviour is a maintenance burden that exists
*only because* the tools are derived from endpoints. Once tools are first-class on
`copilot_tools`, the description is authored next to the implementation and drifts only if
the implementation does — the ordinary case for any docstring.

**Two defects stand independently of the rebuild and are recorded against the current
wrapper:**

- **Duplicate tool names in `TOOL_SPECS` are unguarded.** A duplicate silently shadows,
  and MCP clients read `tools/list` once at connect time, so the loser is invisible.
  A registration-time uniqueness assertion is cheap and belongs there regardless of which
  layer produces the specs.
- **Registration is completely silent.** No log line records how many tools a process
  exposes, so a partially-registered server is indistinguishable from a healthy one.
  ADR 0020's reasoning applies: a surface that comes up smaller than intended must say so.

The tool coroutines' missing docstrings are not separately actionable — under ADR 0025
the description *becomes* the docstring.

---

# platform-core

> Most `platform-core` questions are cross-cutting and appear above as Q-CC-1
> (auth), Q-CC-3 (error envelopes), Q-CC-4 (settings and versions), Q-CC-5
> (German strings), Q-CC-6 (`/api/v2` prefix) and Q-CC-8 (single-process).
> What follows is what is specific to this module.

## Q-PC-1 — Should `NonFiniteSafeJSONResponse` become the app-wide default?

**Context:** It protects exactly one router (`aeroanalysis.py:43`).
`operating_points`, `section_aoa`, `airfoils`, the powertrain routers and the
speed polar all return AeroSandbox numbers over plain `JSONResponse` and can
still 500 on a NaN — Starlette renders with `json.dumps(allow_nan=False)`.
`powertrain` can additionally emit `float("inf")` from `_p_aero` / `_p_elec`, and
a zero capacity makes `raw_c` infinite.
**Spec affected:** [`_reversa_sdd/platform-core/requirements.md`] (BR-PC25, RF-20),
[`_reversa_sdd/adrs/0012-…md`]
**Question:** Make it the app-wide `default_response_class`?
**Impact:** ADR 0012's numeric-safety guarantee currently covers ~7 % of the API.

**Answer:** **(a) Make it the app-wide `default_response_class` — AND have it
declare what it sanitised.** _Answered by the maintainer, 2026-08-14._

**The apparent conflict with `P-WARN-0` is resolved, not overridden.** There are
three behaviours here, not two:

| Behaviour | Result |
|---|---|
| Today (~93 % of the API) | HTTP 500 — the **entire response is lost**, not just the offending field, and the cause is invisible |
| Response class alone | Response arrives with `null` — but "not computed", "not applicable" and "the computation produced NaN" become indistinguishable |
| Response class **+ declaration** | Response arrives with `null`, **plus a `DesignWarning` naming the field and the reason** |

A 500 is therefore **not** the more honest option — it destroys more information,
not less.

**Mechanism:** the response class already knows which keys it replaced. It collects
the sanitised JSON paths and attaches a `DesignWarning`
(`code: NON_FINITE_VALUE`, `context: {paths: [...]}`) automatically, so the
substitution is **declared by construction** without touching every producer.

**Scope of the gap being closed:** `NonFiniteSafeJSONResponse` currently protects
exactly one router (`aeroanalysis.py:43`). `operating_points`, `section_aoa`,
`airfoils`, the powertrain routers and the speed polar all serialise AeroSandbox
numbers through plain `JSONResponse`, which Starlette renders with
`json.dumps(allow_nan=False)` — so any NaN 500s. ADR 0012's numeric-safety
guarantee covers ~7 % of the API today.

**Note on infinities:** `powertrain` can emit `float("inf")` from `_p_aero` /
`_p_elec`, and a zero capacity makes `raw_c` infinite. That is not a serialisation
mishap but a **design statement** (division by zero capacity) and must surface as a
warning, not be quietly nulled.

---

## Q-PC-2 — Should there be a `/ready` endpoint?

**Context:** `/health` is deliberately always 200 so a load balancer can
distinguish "service down" from "service up but degraded" — but it reports **no
readiness**: no Alembic head check, no `cad_available` / `aerosandbox_available`
flags, no background-job state, no dependency status. No startup summary is
logged either, although registered routers, detected capabilities, database URL
and Alembic revision are the four facts an operator most needs.
**Spec affected:** [`_reversa_sdd/platform-core/requirements.md`] (BR-PC30),
[`_reversa_sdd/platform-core/app-bootstrap-lifespan/requirements.md`]
**Question:** Should a `/ready` endpoint exist for deployment gating, and should
startup log a configuration summary?
**Impact:** After a migration-bearing merge there is currently no way to tell
from outside whether the process is on the right schema.

**Answer:** **Yes, but lean: a startup configuration summary plus a small `/ready`
endpoint.** _Answered by the maintainer, 2026-08-14._

The *deployment-gating* rationale is weak here — `Q-CC-1` and `Q-CC-8` establish a
single-user, single-worker desktop application with no load balancer. **The real
motivation is different and concrete:** after merging a migration-bearing PR there
is currently no way to tell whether the running process is on the correct schema.
This is a recurring, documented stumbling block (`alembic upgrade head` must be run
manually; the local SQLite database is not auto-synced), and today it only shows up
as downstream errors.

**Required:**
- **Startup summary** logging the four facts an operator actually needs: registered
  routers, detected capabilities (`cad_available` / `aerosandbox_available`),
  database URL, and the **Alembic revision**. This extends the startup log line
  already mandated by `Q-CC-1` (effective reachability), so the marginal cost is
  near zero.
- **A small `/ready` endpoint** reporting schema agreement (running revision vs
  head) and the capability flags. `/health` keeps its current always-200
  semantics.

---

## Q-PC-3 — Is structured logging planned?

**Context:** stdout only, DEBUG by default, no request-correlation id, no
file/JSON handler, and no metrics of any kind — not for queue depth,
debounce-coalescing rate, job duration, failure rate, transaction duration,
rollbacks or lock waits. The last three are exactly the signals that would have
surfaced both the SQLite contention that forced WAL and the MCP commit defect.
**Spec affected:** [`_reversa_sdd/platform-core/requirements.md`] (BR-PC31)
**Question:** Is structured logging planned for the deployed service?
**Impact:** Determines whether observability belongs in the re-implementation spec.

**Answer:** **Deliberately minimal — configurable log level and meaningful
background-job messages; no JSON handler, no metrics stack.** _Answered by the
maintainer, 2026-08-14._

A full observability stack is **out of scope for a single-user desktop
application** — that is infrastructure for systems with operators. Recorded in the
spec as a **deliberate scope exclusion**, to be revisited together with the
multi-user vision (`Q-CC-1`).

**In scope:**
- A **configurable log level** instead of DEBUG-by-default.
- Meaningful, attributable messages in the background-job system.

**Explicitly out of scope:** JSON/file handlers, request-correlation ids, and
metrics of any kind (queue depth, coalescing rate, job duration, failure rate,
transaction duration, rollbacks, lock waits).

**Acknowledged trade-off:** the last three metrics are exactly the signals that
would have surfaced both the SQLite contention that forced WAL and the MCP commit
defect (`Q-MC-1`). Accepted knowingly — those defects are being fixed directly, and
the instrumentation to have caught them automatically is not proportionate at this
scale.

---

## Q-PC-4 — Is `schedule_retrim`'s short-circuit asymmetry intentional?

**Context:** `schedule_retrim` short-circuits while a job is already `COMPUTING`;
`schedule_recompute_assumptions` does not. So a retrim scheduled during a
compute is **dropped** — the edit that triggered it may never be retrimmed —
while recompute can overlap itself for one aeroplane. Shutdown also cannot
interrupt a worker thread already inside a compute.
**Spec affected:** [`_reversa_sdd/platform-core/background-jobs-invalidation/requirements.md`] (BR-PC28)
**Question:** Is the asymmetry intentional?
**Impact:** Two opposite behaviours for one scheduling problem.

**Answer:** **The asymmetry is a defect. Coalesce instead of dropping.**
_Answered by the maintainer, 2026-08-15._

`schedule_retrim` short-circuits while a job is already `COMPUTING`, so the retrim is
**discarded** — the edit that triggered it may never be retrimmed —
while `schedule_recompute_assumptions` has no such short-circuit.

**It compounds with `Q-AA-6`②:** a dropped retrim leaves the operating points `DIRTY`,
and `DIRTY` was absorbing. Two defects that conceal one another — the points look
"pending" forever and nothing ever picks them up.

Required: when a job is already running and another request arrives, record
"re-run needed" and run **once** on completion (coalescing), rather than discarding the
request. Also note that shutdown cannot interrupt a worker already inside a compute.

---

## Q-PC-5 — Should the airfoil backfill move out of `scripts/`?

**Context:** `schedule_airfoil_low_re_compute(names)` runs a NeuralFoil backfill
in a worker thread — fire-and-forget, no `Job` record — and imports
`scripts.backfill_airfoil_low_re._compute_geometry_stats` **from application
code** (`background_jobs.py:362`). It is the only one of three job families that
is untracked. (See also Q-AF-6.)
**Spec affected:** [`_reversa_sdd/platform-core/background-jobs-invalidation/requirements.md`] (BR-PC29)
**Question:** Should the backfill logic move into a service?
**Impact:** Application code depending on `scripts/` inverts the dependency.

**Answer:** **ANSWERED by the maintainer, 2026-08-15** (option a) — **yes; this is the same decision as `Q-AF-6`, recorded there in full.**

The `platform-core` half of it: `background_jobs.py:362` must stop importing from
`scripts/`. Application code depending on a script inverts the dependency direction, and
depending on a **private** function of one (`_compute_geometry_stats`) means the script
cannot be refactored without breaking the application silently.

After the change, `background_jobs` schedules a service call and the backfill becomes a
tracked `Job` — the third of three job families to get a record, closing the one place
where a background operation can fail with no trace (BR-PC29).

---

## Q-PC-6 — Should a relative `ARTIFACTS_BASE_DIR` be rejected rather than resolved?

**Context:** The `field_validator(mode="after")` calls `.resolve()`, so a
relative env override becomes absolute **against the process CWD** — correct only
when the process starts in the repo root. `AIRFOILS_DIR` was made absolute
precisely because a CWD-relative path hid procedurally generated airfoils after
an OpenVSP import.
**Spec affected:** [`_reversa_sdd/platform-core/config-and-settings/requirements.md`] (BR-PC17)
**Question:** Resolve, or reject a relative value outright?
**Impact:** The same class of bug the `AIRFOILS_DIR` comment documents.

**Answer:** _derived — not a maintainer decision (ADR 0020 decides it)._

**Reject a relative `ARTIFACTS_BASE_DIR` outright.** Calling `.resolve()` on it is an
**undeclared substitution**: the operator supplies one path, the system silently uses a
different one, and which one depends on the process working directory — invisible in the
config, invisible in the logs, and different between `uvicorn` from the repo root, a
worktree, a systemd unit and a Docker entrypoint.

**This exact bug already happened once.** `AIRFOILS_DIR` was made absolute precisely
because a CWD-relative path hid procedurally generated airfoils after an OpenVSP import —
the files were written, just not where the reader looked. Nothing distinguishes
`ARTIFACTS_BASE_DIR` from that case.

**Rule:** the `field_validator(mode="after")` raises when the value is not absolute, with
a message naming the setting and the value received. Startup fails loudly rather than
running against a path nobody chose. This does not conflict with `Q-PC-7`'s
"tolerant startup" pattern — the seeders tolerate a *failure to populate*, whereas this
is a misconfiguration that makes every later write land somewhere unpredictable.

Where relative paths are genuinely convenient (developer shells), the resolution base is
the **repository root**, not the CWD — but that is a convenience the maintainer must
opt into explicitly, not a silent default.

---

## Q-PC-7 — Is `bind_loop` correctly the one intolerant startup step?

**Context:** Every other lifespan failure degrades to a warning — both seeders are
explicitly wrapped so a failure "never blocks startup". `job_tracker.bind_loop`
propagates. Also: importing `app.main` builds the entire FastMCP server as a side
effect, and `run_app` defaults to port 8000 while the documented dev command uses
8001.
**Spec affected:** [`_reversa_sdd/platform-core/app-bootstrap-lifespan/requirements.md`] (BR-PC10, BR-PC12)
**Question:** Confirm — without a bound loop every background job is silently
dropped, so intolerance looks right, but it is the only such step.
**Impact:** One acceptance criterion.

**Answer:** _(derived — not a maintainer decision)_ **Confirmed — `bind_loop`'s intolerance is correct, and it is no longer the only intolerant startup step.**

Follows from **Q-CC-8**, which states the disposition rule for precisely this signature: the application *"refuses to start"* on the misconfiguration because *"failing loudly at boot is preferable to the silent, data-dependent breakage"* — and an unbound loop is that breakage, since every background job is then dropped with no signal. The asymmetry with the two seeders is therefore principled rather than accidental: a failed seed is visible and recoverable, an unbound loop is neither. Q-CC-8's single-worker assertion now stands beside it as a second intolerant step, so the premise "it is the only such step" no longer holds; the `run_app` 8000-vs-8001 default is settled by **Q-CC-4**'s one-class-one-instance merge, not here.

---

# frontend-workbench

> `frontend-workbench` is the least individually documented module — 196 of 210
> production files are covered at module granularity only. These questions are
> the ones that would most improve that.

## Q-FW-1 — Was the server-side proxy layer dropped deliberately?

**Context:** `frontend/CLAUDE.md:12-13` states that all API calls go through
server-side route handlers or server actions "to avoid CORS". There is **no**
`app/**/route.ts`, nothing declares `"use server"`, and no server-side fetching
exists — every call is a direct browser fetch to `NEXT_PUBLIC_API_URL`. The
backend's `allow_origins=["*"]` is the consequence, not an independent choice.
**Spec affected:** [`_reversa_sdd/frontend-workbench/requirements.md`],
[`_reversa_sdd/platform-core/requirements.md`] (BR-PC4)
**Question:** Was the proxy layer dropped deliberately, and should the
documentation or the architecture be corrected?
**Impact:** This is the root cause of the wildcard CORS in Q-CC-1.

**Answer:** **(a′) The documentation is wrong — SPA-direct IS the architecture —
AND the CORS policy is tightened to an allowlist.** _Answered by the maintainer,
2026-08-13._

Two separate corrections, deliberately decoupled: the missing proxy layer is
accepted as the architecture, but the wildcard CORS is **not** accepted as its
consequence. A proxy is not required to fix the CORS hole.

**1. Correct the documentation.** `frontend/CLAUDE.md:12-13` claims all API calls
go through server-side route handlers or server actions "to avoid CORS". No
`route.ts`, no `"use server"`, and no server-side fetching exist. The claim is
removed; the spec records **browser-direct SPA → FastAPI** as the intended
architecture, and notes it as a consequence-of-record alongside ADR 0016.

**2. Tighten CORS to a configured allowlist.** Replace
`allow_origins=["*"]` + `allow_credentials=True` (`app/main.py:234`) with an
env-driven allowlist, e.g. `CORS_ALLOW_ORIGINS`, defaulting to the local frontend
origins.

**Why this is a real defect, not cosmetics** — independent of the ngrok/exposure
question settled in `Q-CC-1`:
- Starlette does **not** send `Access-Control-Allow-Origin: *` when
  `allow_credentials=True`; browsers forbid that pairing, so it **echoes the
  requesting origin** instead. Net effect: *every* origin is allowed, with
  credentials — the most permissive configuration obtainable.
- Combined with the deliberate absence of authentication, any web page open in the
  user's browser can call `http://localhost:<port>` **and read the responses**
  while da3Dalus is running — i.e. enumerate, modify or delete the user's designs.

**Implementation notes:**
- CORS is enforced by the browser against the **frontend document's origin**, so
  this is **independent of where the backend runs** — bare metal, Docker
  (`localhost:8086`) and the ngrok tunnel all use the same allowlist mechanism.
  Only the frontend's origin matters.
- `http://localhost:3000` and `http://127.0.0.1:3000` are **distinct origins** to
  the browser (as is every port); include both to avoid confusing failures.
- Keep it env-configurable so the ngrok host can be added for a test session
  without a code change.
- Container-to-container / server-side calls involve no browser and therefore no
  CORS.

**Rejected:** rebuilding the proxy layer (option b) — disproportionate for a
single-user local application now that CORS can be closed directly; and the
"proxy for writes only" hybrid (option c), which would introduce a second call
convention for no benefit here.

**Consequences for downstream questions:** confirms the SPA-direct premise
underlying `Q-FW-2` (one HTTP client), `Q-FW-3` (global `SWRConfig`) and
`Q-CC-11` (generated TypeScript client); removes the wildcard-CORS finding from
`Q-CC-1`'s residual risk.

---

## Q-FW-2 — Should the hooks migrate onto one HTTP client?

**Context:** `lib/fetcher.ts` (used by the SWR hooks) throws a plain `Error`;
`lib/api.ts` throws a typed `ApiError` with `status` and `details`;
`lib/parseApiError.ts` bridges them **and** absorbs the backend's two envelopes
(Q-CC-3). `lib/fetcher.ts` always calls `res.json()`, so a 204 would throw — only
`lib/api.ts` handles it. `fetchAPI`'s spread order also lets `init` replace the
`Content-Type` header it just merged in.
**Spec affected:** [`_reversa_sdd/frontend-workbench/data-fetching-swr/requirements.md`]
**Question:** Migrate the hooks onto `lib/api.ts`?
**Impact:** Error handling is currently non-uniform across 48 hooks.

**Answer:** _(derived — not a maintainer decision)_ **Yes — the hooks migrate onto one typed HTTP client.**

Follows from **Q-CC-3** and **Q-CC-11**: Q-CC-3 removes `lib/parseApiError.ts`, which is the only thing bridging `lib/fetcher.ts`'s plain `Error` and `lib/api.ts`'s typed `ApiError`, and with a single backend envelope there is exactly one thing to parse — parsing it in two places would recreate the divergence the decision eliminates. Q-CC-11's generated types reinforce a single typed data layer across the 48 hooks. Two latent bugs go with the merge: `lib/fetcher.ts` unconditionally calling `res.json()` (a 204 throws) and `fetchAPI`'s spread order letting `init` overwrite the `Content-Type` header it just merged in.

---

## Q-FW-3 — Is a global `SWRConfig` wanted?

**Context:** There is none, so revalidation, retry and error policy are decided
independently by each of 48 hooks, with no global `onError`. Cross-hook
invalidation also duplicates literal key strings with no shared key module, so a
typo silently no-ops and leaves stale data on screen.
**Spec affected:** [`_reversa_sdd/frontend-workbench/data-fetching-swr/requirements.md`]
**Question:** Is a shared config wanted (e.g. `revalidateOnFocus: false` for the
expensive analysis endpoints), and a shared key module?
**Impact:** Expensive solver endpoints are currently revalidated on window focus.

**Answer:** **ANSWERED by the maintainer, 2026-08-15** (option a) — **a global `SWRConfig` *and* a shared key module. The key module is the more important half.**

**The key module fixes a silent failure.** Cross-hook invalidation currently duplicates
literal key strings across 48 hooks with nothing tying them together, so a typo in a
`mutate` call **silently no-ops** — no error, no warning, and stale data stays on screen
looking current. That is indistinguishable from "the data did not change", which is the
worst kind of failure for a design tool. Centralised key builders make the typo a
compile-time error instead.

**The global config fixes a cost.** With no `SWRConfig`, revalidation, retry and error
policy are decided independently by every hook and there is no global `onError`. The
concrete consequence: **expensive solver endpoints are revalidated on window focus** —
alt-tabbing away and back re-triggers an analysis. `revalidateOnFocus: false` for the
analysis endpoints, with a global `onError` so a failed fetch surfaces somewhere rather
than only in a hook nobody watches.

**Ordering note:** the key module can land first and independently; the config is a small
change once there is one place to put it.

---

## Q-FW-4 — Is there a component size budget?

**Context:** Seven components exceed 1 000 lines: `AnalysisViewerPanel` 1 567,
`MatchingChartTab` 1 518, `AeroplaneTree` 1 197, `PowertrainTab` 1 190,
`VersionGraphOverlay` 1 117, `OperatingPointsPanel` 1 076, `AnalysisConfigPanel`
1 063. The tab *pages* are already thin; the panels are not. Relatedly,
`components/ui/` holds a single primitive (`PillToggle`) while eight shared
building blocks (`TreeCard`, `Field`, `Chip`, `DialogField`, `InfoTooltip`,
`AlertBanner`, `GroupAddMenu`) sit flat among feature components — which is why
`frontend/CLAUDE.md` needs a manual "reuse before creating" checklist.
**Spec affected:** [`_reversa_sdd/frontend-workbench/requirements.md`]
**Question:** Is there a size budget, should the panels be decomposed the way the
tab pages are, and should a real design-system layer be extracted?
**Impact:** These seven files are where a re-implementation would spend most of
its effort with the least guidance.

**Answer:** **ANSWERED by the maintainer, 2026-08-15** (option a) — **extract a design-system layer; decompose the oversized panels opportunistically. No hard line-count budget.**

**The discoverability problem is the one worth fixing now, and it is cheap.**
`components/ui/` holds a **single** primitive (`PillToggle`) while eight shared building
blocks — `TreeCard`, `Field`, `Chip`, `DialogField`, `InfoTooltip`, `AlertBanner`,
`GroupAddMenu` — sit flat among feature components. That is precisely why
`frontend/CLAUDE.md` needs a manual *"reuse before creating"* checklist: the convention
exists because the **directory structure does not encode it**. Moving the eight into
`components/ui/` replaces a checklist a contributor must remember with a location they
cannot miss.

**No hard budget.** Seven components exceed 1 000 lines (`AnalysisViewerPanel` 1 567,
`MatchingChartTab` 1 518, `AeroplaneTree` 1 197, `PowertrainTab` 1 190,
`VersionGraphOverlay` 1 117, `OperatingPointsPanel` 1 076, `AnalysisConfigPanel` 1 063),
and a numeric limit would force splits at arbitrary seams to satisfy a counter rather than
because a boundary exists there. The tab *pages* are already thin, so the pattern is
understood; the panels are large because they are genuinely dense.

**Decompose as they are touched**, extracting into the design-system layer where a piece
turns out to be shared. That way the two halves of this answer reinforce each other rather
than being separate cleanups.

_Consistent with the scope principle from `Q-CO-4`: the change that pays for itself
immediately, not a sweep justified by a metric._

---

## Q-FW-5 — Should the tessellation cache be bounded?

**Context:** It is a module-level unbounded `Map`. Entries are evicted only when
the aeroplane's `updated_at` changes; there is no size cap, no TTL and no LRU, and
full tessellation payloads are large. WebGL contexts also leak if disposal is
missed on any path — the browser limit is hard and the symptom is a blank canvas
with no error. Nothing detects a duplicated three.js instance at runtime, and no
cache hit-rate or tessellation-duration metric exists.
**Spec affected:** [`_reversa_sdd/frontend-workbench/cad-viewer-integration/requirements.md`]
**Question:** Is an LRU bound needed?
**Impact:** A long workbench session on a multi-aircraft project grows without
limit.

**Answer:** _derived — not a maintainer decision (measured, plus `Q-CG-4`)._

**The unbounded cache is moot; the WebGL and observability concerns are not.**

**① The `Map` disappears.** The module-level `tessellationCache` lives in
`frontend/hooks/useTessellation.ts`, which has **zero consumers** — verified 2026-08-15,
no file in `frontend/` imports it outside its own definition. It is part of the subsystem
`Q-CG-4` deletes. No LRU bound is needed for code that is being removed.

**② `CadViewer.tsx` survives and keeps the real risk.** It is still reached from
`construction-plans/ExecutionResultDialog.tsx` — the live plan-execution viewer — so
WebGL context disposal remains load-bearing there. The browser context limit is hard and
the failure mode is a blank canvas with no error, which is precisely a silent failure:
**ADR 0020 applies** — a viewer that cannot acquire a context emits a `DesignWarning`
(severity: defect) rather than rendering nothing.

**③ Metrics stay unbuilt.** Cache hit rate and tessellation duration were metrics *for
the deleted cache*. Nothing measures the plan-execution path today and nothing needs to
at single-user scale (ADR 0024).

---

## Q-FW-6 — What is the plan for moving off the Next.js canary?

**Context:** `next` is pinned to `16.2.1-canary.33`, and `frontend/AGENTS.md`
warns that the APIs differ from documented behaviour. Tests additionally require
**Node 22** — Node ≥ 24 breaks jsdom `localStorage` with spurious failures.
**Spec affected:** [`_reversa_sdd/frontend-workbench/requirements.md`]
**Question:** What is the plan for a stable release?
**Impact:** The spec currently has to document canary-specific behaviour as if it
were the contract.

**Answer:** **ANSWERED by the maintainer, 2026-08-15** (option a) — **move to a stable release. Checked online at the maintainer's request, and the news is better than expected: no major-version jump is needed.**

The project pins `next@16.2.1-canary.33`, and `frontend/AGENTS.md` warns that its APIs
differ from documented behaviour — so the specification has been describing canary
behaviour as if it were the contract.

**Current state of Next.js, checked 2026-08-15:**

| | |
|---|---|
| **16.3.0 LTS** | released **2026-08-03** — the upgrade target |
| 16.3.1 | maintenance: Turbopack fixes, `next/image` improvements, cache and HMR reliability, backported routing/SSR fixes |
| 15 (LTS) | end of support **2026-10-21** |

**The move is `16.2.1-canary.33` → `16.3.x` — same major version.** The maintainer
anticipated possibly needing a major upgrade; that is not the case. It is a canary-to-
stable move within 16, and 16.3.0 is an **LTS**, which is the strongest possible target:
the reason for pinning a canary disappears and the version stops being a moving target.

**Consequences:**

- The spec stops documenting canary-specific behaviour as contract; `frontend/AGENTS.md`'s
  warning can go.
- **Node 22 remains required** for the test suite — Node ≥ 24 breaks jsdom `localStorage`
  with spurious failures. That constraint is independent of the Next version and must be
  re-checked, not assumed fixed, after the upgrade.
- Worth verifying against 16.3's release notes whether whatever motivated the canary pin
  originally has landed; if something is still canary-only, that is a separate decision
  rather than a reason to stay pinned.

_Sources: [Next.js blog](https://nextjs.org/blog) · [Next.js version history](https://versionlog.com/nextjs/) · [Next.js EOL dates](https://eosl.date/eol/product/nextjs/)_

---

## Q-FW-7 — Should the workbench have an error boundary and telemetry?

**Context:** There is no error boundary anywhere: an exception in the metrics
band, the copilot strip or the version overlay **unmounts the whole workbench**.
There is no client-side error reporting and no request timing, so a slow endpoint
is indistinguishable from a slow render. A stale or deleted aeroplane id is never
cleared from the URL or `localStorage` — every panel simply errors — and there is
no `beforeunload` guard, so a reload discards unsaved edits silently (the modal
covers in-app navigation only).
**Spec affected:** [`_reversa_sdd/frontend-workbench/workbench-shell-and-routing/requirements.md`]
**Question:** Should an error boundary, a stale-id reset and a `beforeunload`
guard be added?
**Impact:** Four independent ways to lose the user's session.

**Answer:** **ANSWERED by the maintainer, 2026-08-15** (option a) — **build the error boundary, the stale-id reset and the `beforeunload` guard. No client-side error reporting, no request timing.**

**The three that are built affect a single user on a single machine, which is exactly this
project's operating model (ADR 0024):**

- **Error boundary.** There is none anywhere, so an exception in the metrics band, the
  copilot strip or the version overlay **unmounts the entire workbench**. One failing
  panel taking down the whole tool is a bad outcome at any user count, and boundaries
  around the independent regions are a small, local change.
- **Stale-id reset.** A deleted or renamed aeroplane id is never cleared from the URL or
  `localStorage`, so **every panel errors** and the only escape is for the user to know to
  edit the URL. Clearing an id that no longer resolves turns an unrecoverable state into a
  return to the picker.
- **`beforeunload` guard.** The existing modal covers in-app navigation only, so a browser
  reload **silently discards unsaved edits**. Losing work is the most expensive failure in
  this list and the cheapest to prevent.

**The two that are not built are multi-user / deployed-service concerns:** client-side
error reporting and request timing answer *"what is happening to my users?"*, and there is
one user with a console open. Building telemetry for an audience of one is instrumentation
without a consumer.

_Applies the scope principle recorded at `Q-CO-4`: robustness is justified by the user's
own experience or by data worth preserving — not by a deployment this project does not
have._

---

## Q-FW-8 — Frontend hygiene decisions (bundle)

**Context:** Five small items:
- **`react-plotly.js` is declared and never imported** — the very package whose
  use would break the "no top-level Plotly" rule. Remove, or is a migration
  planned?
- **Nothing prevents a future top-level Plotly import** except a comment — no lint
  rule, no CI bundle-size check.
- **Dark theming is re-declared per figure** (`paper_bgcolor`, `plot_bgcolor`,
  `font.color`) across eight components, hard-coded as literals rather than read
  from the Tailwind theme. Should a shared layout template live in `lib/`?
- **`metricsMock.ts` ships inside the production component folder**
  (`components/workbench/metrics-dashboard/`). Still referenced?
- **Dark theme only** — no light palette, no `prefers-color-scheme`. Intentional
  product decision?

Also: **selection sub-state is not deep-linkable** — only the aircraft is in the
URL, not the selected wing or station — and `treeMode` does not persist.
**Spec affected:** [`_reversa_sdd/frontend-workbench/analysis-dashboards-plotly/requirements.md`],
[`_reversa_sdd/frontend-workbench/workbench-shell-and-routing/requirements.md`]
**Question:** Confirm each.
**Impact:** Six small decisions.

**Answer:** _(resolved by code lookup — not a maintainer decision)_ **On the `metricsMock.ts` item: it is referenced by nothing — zero imports from production, tests or e2e — so it is dead code.**

The file is `frontend/components/workbench/metrics-dashboard/metricsMock.ts` (148 lines). A grep for `metricsMock` across all `.ts`/`.tsx` outside `node_modules` returns exactly four hits and every one is a **comment** (`metrics-dashboard/metricsTypes.ts:2`, `frontend/lib/metricsAdapters.ts:8`, `:218`, `:257`); separate greps over `frontend/__tests__/` and `frontend/e2e/` return nothing. Its own header claim that types are "re-exported here so existing test imports remain valid" (`metricsMock.ts:1-11`) is stale — there are no such imports left. `deps:check` does not flag it because `no-orphans` requires a module with neither incoming *nor* outgoing dependencies and this file still imports `./metricsTypes`, which means the 5-orphan info list in Q-CC-17 is an **undercount** of dead frontend modules.

**Verdict:** confirmed dead code — deletable outright under `P-DEAD-0`; its types already live in `metricsTypes.ts`.
Residual decision: the other five bundle items — dark-theme-only, the shared Plotly layout template, deep-linkable selection state, `treeMode` persistence, and whether the gauge-zone literals duplicated into `frontend/lib/metricsAdapters.ts:257` should be re-homed rather than mirrored by comment — still need you.

_Full detail: [`wave3-lookups.md`](wave3-lookups.md) §P_


**Residual decision — ANSWERED by the maintainer, 2026-08-15.**

**Determined by policy:**
- **`react-plotly.js` is removed** — declared, never imported (`P-DEAD-0`). Notably
  it is the very package whose use would break the "no top-level Plotly import" rule.
- **A lint rule enforces the no-top-level-Plotly convention.** Today only a comment
  guards it, and a comment is not enforcement — the exposure is a ~1.5 MB bundle
  regression.
- **A shared Plotly layout template moves to `lib/`.** Dark theming
  (`paper_bgcolor`, `plot_bgcolor`, `font.color`) is currently re-declared as literals
  across eight components; the template reads the Tailwind theme instead.

**Product decisions by the maintainer:**
1. **Dark theme only** — deliberate. No light palette, no `prefers-color-scheme`
   support. Recorded as an intentional product decision, not an omission.
2. **Selection state is NOT deep-linkable.** Only the aircraft stays in the URL; the
   selected wing and station deliberately do not. No shareable/bookmarkable
   sub-selection.
3. **`treeMode` is not persisted** — and the spec records *why*: it is **derived
   state**, not a user preference. `TreeMode ∈ {wingconfig, asb, fuselage}` follows
   the selected wing's `design_model` and is switched automatically
   (`AeroplaneTree.tsx:751-753`, with an explicit mismatch check at `:878-879`).
   Persisting a mode that the next selection overwrites would be inert at best and
   confusing at worst — the app would briefly restore a mode it immediately leaves.
   Only `fuselage` is a genuine user choice, and that is bound to the selection,
   which decision 2 already keeps out of the URL.
---

## Q-FW-9 — Should the two copilot write tools get explicit labels?

**Context:** `useCopilot.TOOL_LABEL_MAP` labels only 3 of the 6 copilot tools.
`get_wing_geometry`, `apply_design_edits` and `discard_proposal` — **the two write
tools among them** — fall through to the generic `Calling <name>…`.
**Spec affected:** [`_reversa_sdd/frontend-workbench/data-fetching-swr/requirements.md`]
**Question:** Should the write tools get explicit, reassuring labels ("Preparing a
proposal…", "Discarding the proposal…")?
**Impact:** The moments the user most needs to understand what the AI is doing are
the unlabelled ones.

**Answer:** _derived — not a maintainer decision (follows from ADR 0007)._

**Yes — and the two write tools are the ones that most need it.** ADR 0007 makes the
human the adopting party: the copilot proposes, the maintainer accepts. That only works if
the maintainer can see *what is being proposed while it happens*. Falling through to
`Calling apply_design_edits…` is the generic label at exactly the moment the generic label
is least acceptable.

**Labels for all six**, so `TOOL_LABEL_MAP` stops having a fall-through path at all:

| tool | label |
|---|---|
| `apply_design_edits` | *Preparing a proposal…* |
| `discard_proposal` | *Discarding the proposal…* |
| `get_wing_geometry` | *Reading the wing geometry…* |

The three already-labelled read tools keep their labels. A missing entry should be caught
at build time — a `Record<CopilotTool, string>` keyed by the tool-name union makes an
unlabelled tool a TypeScript error rather than a silent generic string.

---

*Related: [`gaps.md`](gaps.md) · [`confidence-report.md`](confidence-report.md)*

---

# Residual register — what the interview did **not** close

> Written 2026-08-15, immediately before the fold-back. All 192 questions carry an answer,
> but a handful of answers deliberately left something open. **These must not be folded
> into the specs as 🟢 CONFIRMED.** Each is listed with the marker it should carry.

| # | item | where | marker | why it is open |
|---|---|---|---|---|
| R1 | ~~`build_yduplicate_sign_map` — mirrored strip-force sign~~ **RESOLVED, see below** | `Q-AV-4` | ✅ | **Premise was wrong.** The sign map is the `CONTROL`-card `SgnDup` (an *input*), not a strip-force correction. AVL applies `IMAGS` internally, so no per-surface sign is needed on forces; `SgnDup` is already emitted from `control_surface_mixing.py:45`. **Disposition: delete** (ADR 0022 + ADR 0021). |
| R2 | **`COPILOT_EMBEDDING_MODEL`** | `Q-CO-10` | 🟡 | Option (b) bundled two things; keeping this setting follows from the bundle, not from the maintainer's reasoning. It belongs to the **superseded** RAG plan — under the lexical retrieval that replaced it, no embedding model is needed. Flagged for the maintainer to overrule. |
| R3 | **`role="tool"` replay branch** | `Q-CO-5` | 🟡 | Schema-supported, never written, replay branch unreachable. ADR 0021's default is deletion, but it was not put to the maintainer. Cheap either way — resolve when that code is next touched. |
| R4 | **Copilot change-record source** | `Q-CO-14`, `Q-CO-15` | 🟡 | *That* a change record exists is decided; whether it derives from the version graph, `DesignWarning` deltas or the aero context is an implementation question. The binding constraint is only that *"remove stale state"* must not be implemented as *"remove history"*. |
| R5 | **Approval granularity / search envelope** | `Q-CO-15` | 🟡 | Direction decided (approval on the outcome, not the search; goals quantified and plausibility-checked). Which changes need explicit approval, and how the search envelope is bounded, is deferred to implementation — with approval fatigue named as the failure mode to avoid. |
| R6 | **Turbulence parameters in the dutch-roll renderer** | `dutch-roll-visualisation/` | 🟡 | Gust RMS 2.2° and correlation time 0.35 s are plausible choices, not derived. They scale amplitude, not the character of the comparison. The mode shape itself (`roll_ratio`, `chi`) **was** validated — the maintainer judged the render realistic. |
| R7 | **Goggle-displayed FOV vs sensor FOV** | `dutch-roll-visualisation/` | 🟡 | 139° horizontal is derived from the Avatar HD V2's 2.1 mm / 160° diagonal under equidistant projection. What the **goggles** display may differ (scaling, crop, headset optics); for perception calibration only the latter matters, and it was not determined. |
| R8 | **Operating-point set vs flying qualities** | `Q-MS-13b` | 🟡 | Maintainer's own forward note: the generated OP set is to be reviewed against *"does it yield statements about the aircraft's flying qualities?"* — not merely *"does each point trim?"*. Explicitly **not** a question for this interview. |

**Two items are decided but not yet executed, and should be tracked as work rather than
as gaps:** the `Q-AV-2` check that AVL geometry generation asserts `y_root ≥ 0` for any
surface carrying `YDUPLICATE` (two stored `Wing` rows violate it, overlapping themselves by
0.41 m), and GitHub issue **#1095** (stability results not invalidated on app-version
change; three rows are `CURRENT` but predate the `gh-788` fix, one of them reporting a
sound aircraft as statically unstable).

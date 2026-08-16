# Import an OpenVSP Model

> **Personas:** RC/UAV designer, Hobbyist, AI-copilot user, MCP-agent client
> **Modules:** `openvsp-import` (+ `fuselage-design`, `wing-design`, `cad-generation`)
> **Primary surface:** `/api/v2/import/openvsp`, `/api/v2/import/openvsp/stream`, `/fuselages/slice`

## Context

A designer who already has an aircraft modelled in NASA OpenVSP — their own
design, or a downloaded reference model — wants to bring it into da3Dalus as a
starting point, usually to rescale it into an RC-sized build. The importer
reads the `.vsp3` file, derives wings and fuselages, detects and normalises
the source length unit, applies an optional rescale, and persists a brand-new
aeroplane. Its scope is deliberately narrow (ADR 0018): geometry and mass
*positions* only, never propulsion, inertia, control-surface gains or VSPAERO
setups — a full-size aircraft's numbers for those would look authoritative
and be meaningless once scaled down. `/api/v2/import/openvsp` is the **only**
router in this API mounted under an `/api/v2` prefix; every other route in
this document set (and the export/plan flows) sits at the application root.

## US-IMPORTVSP-01 — Import a .vsp3 file as a new aeroplane

**As an** RC/UAV designer bringing in an existing OpenVSP design (also the
Hobbyist importing a downloaded community model), **I want** to upload a
`.vsp3` file and get a new aeroplane, **so that** I have a starting point
without redrawing the geometry by hand.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v2/import/openvsp` | Upload a `.vsp3` file and create a new aeroplane |

**Acceptance criteria**

- **AC-1 — A well-formed model imports as a new aeroplane**
  - **Given** the `openvsp` bindings are installed, and a valid `cessna172.vsp3` with 2 wings and 1 fuselage
  - **When** I `POST /api/v2/import/openvsp` (multipart `file`, no query params)
  - **Then** the response is **201** with `OpenVspImportResponseModel {aeroplane_uuid, aeroplane_name: "cessna172", n_wings: 2, n_fuselages: 1, warnings, lossy_components}`
  - **And** a new `aeroplanes` row exists with that UUID
- **AC-2 — A non-`.vsp3` upload is rejected before any parsing**
  - **Given** a file named `model.stl`
  - **When** I `POST` it
  - **Then** the response is **400** `"Expected a .vsp3 file upload."` — note this route answers a bare `{"detail": "…"}` body, and uses **400** (a request-shape error) here rather than the `422 validation_error` most of this API uses for bad input
  - **And** no aeroplane is created
- **AC-3 — The optional binding is missing**
  - **Given** the `openvsp` package is not installed on this deployment
  - **When** I `POST` a valid `.vsp3` file
  - **Then** the response is **503**, with the detail pointing at `docs/md/openvsp-import-setup.md`
  - **And** unlike the CAD export router, this route stays mounted and probes availability in the handler on every call, rather than being conditionally unmounted
- **Confidence:** 🟢 CONFIRMED

## US-IMPORTVSP-02 — Watch import progress live

**As a** Hobbyist or RC/UAV designer watching a slow import in the workbench
UI (fuselage STEP export/sewing/slicing can take real time), also the
AI-copilot user narrating progress to the person driving it, **I want** a
progress stream, **so that** I know the import hasn't stalled.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v2/import/openvsp/stream` | Same import, streamed as Server-Sent Events |

**Acceptance criteria**

- **AC-1 — Progress events precede a single terminal event**
  - **Given** the same valid `.vsp3` file
  - **When** I `POST /api/v2/import/openvsp/stream`
  - **Then** the response is **200** `text/event-stream` with `X-Accel-Buffering: no`
  - **And** I see a sequence of `event: progress` frames (`parsing` at 5 then 15; optionally `units`, `scaling`; `aeroplane` at 20; one `wing` frame per wing in the 25–30 band; one `fuselage` frame group per fuselage in the 30–85 band; optionally `weight_items` at 90; `finalising` at 95) followed by **exactly one** `event: complete` frame carrying the same body as the non-streaming endpoint
  - **And** `units`, `scaling` and `weight_items` are conditional — a client must not assume a fixed step sequence, and `pct` never reaches 100 (the `complete` event is the real terminator)
- **AC-2 — Setup errors happen before the stream opens; run-time errors happen in-band**
  - **Given** an out-of-range `scale_factor`, or the `openvsp` binding missing
  - **When** I `POST .../stream`
  - **Then** the up-front validation (503 / 400 / 413) is raised **before** the `StreamingResponse` is created — I get an ordinary HTTP error status, never an SSE frame, for those cases
  - **And Given** a `ScaleValidationError` or `ImportError` instead occurs mid-run, **Then** it is reported as a single `event: error` frame carrying `{"status": 422 | 503, "detail": "…"}` in-band, because the HTTP status line can no longer be changed once the stream has started
- **Confidence:** 🟢 CONFIRMED

## US-IMPORTVSP-03 — Rescale the model while importing it

**As an** RC/UAV designer scaling a full-size reference aircraft down to a
target wingspan (also the Hobbyist entering a simple multiplier), **I want**
to specify a target span or a scale factor at import time, **so that** the
resulting aeroplane is already sized for my build.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v2/import/openvsp` | `target_span_m` and `scale_factor` query params (mutually exclusive), plus `name` |

**Acceptance criteria**

- **AC-1 — Rescaling by target span leaves masses untouched**
  - **Given** a model whose largest wing span is 10 m
  - **When** I `POST` with `target_span_m=2.0`
  - **Then** every wing `xyz_le`/`chord`, `aeroplane.xyz_ref`, and every weight-item position are multiplied by `0.2`
  - **And** `twist` (angular) and every weight-item **mass** are left completely unchanged, and the response's `warnings` include an `info`-severity `SCALING` entry stating that masses were not scaled
- **AC-2 — Supplying both scaling parameters is a request-shape error**
  - **Given** `target_span_m=2.0` **and** `scale_factor=0.5` in the same request
  - **When** I `POST`
  - **Then** the response is **400** — "mutually exclusive; specify at most one"
- **AC-3 — An out-of-range or inapplicable value is a semantic error**
  - **Given** `scale_factor=20.0` (outside `(0.001, 10.0)`), or `target_span_m=1.5` on a wingless aeroplane
  - **When** I `POST`
  - **Then** the response is **422** — deliberately a *different* status from the mutex case in AC-2, because this is a well-formed value that is simply unusable
- **AC-4 — Naming the imported aeroplane**
  - **Given** `name` is omitted
  - **When** the import completes
  - **Then** `aeroplane_name` defaults to the uploaded filename's stem (never the throwaway temp-file name)
  - **And Given** `name="   "` (whitespace only) is supplied, **Then** it is treated as no override — the filename stem still wins
- **Confidence:** 🟢 CONFIRMED

## US-IMPORTVSP-04 — Understand what did and did not come across

**As an** RC/UAV designer deciding whether an import is a trustworthy starting
point (also the AI-copilot user explaining to a Hobbyist why something is
missing), **I want** the response to tell me what was dropped or approximated,
**so that** I don't mistake a lossy import for a complete one.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v2/import/openvsp` | Same import; the `warnings` and `lossy_components` fields |

**Acceptance criteria**

- **AC-1 — The import scope is geometry and mass positions only, by design**
  - **Given** a full-size `.vsp3` with defined engines, control-surface group gains, inertia tensors and a VSPAERO setup
  - **When** it is imported
  - **Then** none of that data appears anywhere in the response or the persisted aeroplane — this is the deliberate ADR 0018 "RC-scaling inspiration" scope, not a bug: those numbers would look authoritative and be meaningless once the airframe is rescaled
- **AC-2 — Unsupported geometry types are visibly reported**
  - **Given** a `.vsp3` containing a `PROP` (propeller) geom, or any of the 13 other unsupported geom types
  - **When** it is imported
  - **Then** the response is still **201**
  - **And** `warnings` contains an entry naming that `component_type`, and `lossy_components` contains that geom's id
- **AC-3 — Control surfaces vanish with no warning at all (GAP)**
  - **Given** a wing carrying an `SS_CONTROL` sub-surface (e.g. an aileron)
  - **When** the model is imported
  - **Then** the response is **201**, but **no** trailing-edge device is created on the imported wing, and **no** `WING_SS_CONTROL` warning is emitted — the post-pass that would create one is never registered in production, and even if it ran, the persistence schema has no field to carry it. A designer must notice this on their own and re-add control surfaces manually after import.
- **Confidence:** 🟢 CONFIRMED for AC-1/AC-2 · 🔴 GAP called out explicitly for AC-3

## US-IMPORTVSP-05 — Partial failures degrade to warnings, never abort the whole import

**As an** MCP-agent client automating imports in a pipeline (also the RC/UAV
designer importing a large or imperfect model), **I want** one bad wing
section or a failed sub-step to not sink the entire import, **so that** I can
treat a non-2xx response as a small, predictable set of real errors.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v2/import/openvsp` | Same import; the best-effort error policy |

**Acceptance criteria**

- **AC-1 — A degenerate wing section is skipped, not fatal**
  - **Given** a wing section with `Span ≤ 0` inside an otherwise valid model
  - **When** it is imported
  - **Then** the response is still **201**, that section is simply absent from the persisted wing, a `WING_XSEC` warning names it, and its geom id is marked lossy
- **AC-2 — The upload cap is enforced before parsing**
  - **Given** an upload larger than 52 428 800 bytes (50 MB)
  - **When** I `POST` it
  - **Then** the response is **413** — `"Upload exceeds the 50 MB size limit."`
- **AC-3 — Only three failure types ever abort an import**
  - **Given** a persistence failure on one wing, or a failing post-pass
  - **When** the import runs
  - **Then** the response is still **201** with a warning describing the failure, and every other record still persists
  - **And** the only conditions that ever propagate as an aborted import are a missing `openvsp` binding (**503**), bad scaling inputs (**422**/**400**, see US-IMPORTVSP-03), and the upload vanishing mid-import (**500** — the one case in this whole module that is a server error rather than a 4xx or a warning)
- **Confidence:** 🟢 CONFIRMED

## US-IMPORTVSP-06 — Refine a fuselage by slicing an uploaded STEP file

**As an** RC/UAV designer with a standalone STEP fuselage (not from an
OpenVSP import) who wants superellipse cross-sections fitted to it, **I want**
a slicing endpoint that fits a fuselage schema to my STEP file, **so that** I
can bring third-party or hand-modelled geometry into the same pipeline the
importer itself uses internally to refine fuselages.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| POST | `/fuselages/slice` | Fit superellipse cross-sections to an uploaded STEP file |

**Acceptance criteria**

- **AC-1 — A STEP file yields a fitted fuselage schema and fidelity metrics**
  - **Given** a valid STEP file whose solid looks like a fuselage
  - **When** I `POST /fuselages/slice` (multipart `file`, defaults `number_of_slices=50`, `points_per_slice=30`, `slice_axis="auto"`, `fuselage_name="Imported Fuselage"`)
  - **Then** the response is **200** with a `FuselageSliceResponse`: a `FuselageSchema` (`x_secs`, each with `xyz`/`a`/`b`/`n`) plus `volume_ratio` and `area_ratio` describing how closely the fit reproduces the original solid
  - **And** this route is standalone — it persists nothing; the caller must separately `PUT` the returned fuselage under an aeroplane at `/aeroplanes/{id}/fuselages/{name}` to save it
- **AC-2 — Wrong file type and missing CAD kernel are both rejected cleanly**
  - **Given** a file that is not `.step`/`.stp`
  - **When** I `POST /fuselages/slice`
  - **Then** the response is **422**
  - **And Given** CadQuery/OCP is not available on this platform, **When** I `POST` a valid STEP file, **Then** the response is **501 Not Implemented** — a bare `{"detail": "…"}` body, distinct from both the `503` this module's import routes use for a missing `openvsp` binding and the `{"error": {...}}` envelope used elsewhere in the API
- **Confidence:** 🟢 CONFIRMED (the 501 status was verified directly against `app/api/v2/endpoints/fuselage_slice.py`)

## Open questions 🔴

- **A wing-only model gets no unit detection at all.** Source-unit detection
  measures a fuselage's exported STEP against its handler-side span; a model
  with no fuselage (e.g. a flying wing) skips detection entirely, so a
  feet-modelled flying wing imports **3.28× too large with zero warning**.
  This is arguably the single most user-impacting gap in the whole flow.
- **`n_wings` / `n_fuselages` count parsed components, not persisted ones.** A
  wing that failed to persist is still counted in these numbers; only the
  accompanying `WING` warning reveals the discrepancy — a naive integration
  that checks the counts without reading `warnings` will over-trust the result.
- **The gh-647 geometry cross-check (`validate_geometry`) is shipped and unit
  tested but never wired into the real import path** — a >1% span/area/MAC
  mismatch against VSP's own totals currently contributes no warning at all.
- **A downloadable `solid_step_path` can be malformed at sharp fuselage
  fillets** (a known open issue) with nothing in the response flagging it —
  the x-section slicing path already avoids the solid for this reason, but
  the construction-download path does not.

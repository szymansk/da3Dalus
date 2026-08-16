# frontend-workbench / data-fetching-swr — Implementation Tasks

> Parent module task list: [`../tasks.md`](../tasks.md).

## Prerequisites

- [ ] `swr 2.4`; Node **22** for tests (jsdom `localStorage` breaks on ≥ 24).
- [ ] A reachable backend at `NEXT_PUBLIC_API_URL` with wide-open CORS.
- [ ] `AeroplaneContext` providing `aeroplaneId` and `hydrated`.

## Tasks

- [ ] **T-01 — `lib/fetcher.ts`.**
  `API_BASE`; `fetcher<T>(path)` (GET; on non-2xx throw
  `Error("<status> <statusText>: <body>")`); `putJson<T>(path, body)` (PUT with
  `Content-Type`, error message prefixed `PUT <path> failed:`); re-export
  `API_BASE`.
  - Legacy origin: `frontend/lib/fetcher.ts`
  - Definition of done: this is the client the SWR hooks use. **Record** that it
    always calls `res.json()`, so a 204 would throw.
  - Confidence: 🟢

- [ ] **T-02 — `lib/api.ts`.**
  `ApiError(status, message, details)`; `fetchAPI` merging
  `{"Content-Type": "application/json"}` with `init.headers`, throwing
  `ApiError` on non-2xx and returning `undefined` on **204**; the
  `api.{get,post,put,delete}` helper.
  - Legacy origin: `frontend/lib/api.ts`
  - Definition of done: 204 → `undefined`. Reproduce the spread order as-is and
    **record** that `init` can replace the headers object it merges into.
  - Confidence: 🟢

- [ ] **T-03 — `lib/sseStream.ts`.**
  `parseSseStream<T>` as an async generator; `parseRecord` (default event
  `"message"`, multiple `data:` lines joined with `\n`); `decodePayload`
  (JSON with a raw-string fallback); buffer the trailing fragment; flush a
  trailing record after `done`; `releaseLock` in `finally` inside a `try/catch`.
  - Legacy origin: `frontend/lib/sseStream.ts`
  - Definition of done: five tests — split record, two `data:` lines, non-JSON
    payload, missing final blank line, already-closed reader. Carry the header
    comment: `EventSource` is GET-only and both streams are POST.
  - Confidence: 🟢

- [ ] **T-04 — `lib/parseApiError.ts`.**
  Accept a plain `Error` from `fetcher`, an `ApiError` from `api`, and both
  backend body shapes (`{"error": {code, message, details}}` and
  `{"detail": …}`); return a displayable message.
  - Legacy origin: `frontend/lib/parseApiError.ts`
  - Definition of done: all four combinations produce a message. **Record** that
    this module exists only because of two backend envelopes × two frontend
    clients.
  - Confidence: 🟢

- [ ] **T-05 — The hook template.**
  Compute a literal path or `null`; `useSWR<T>(path, fetcher)`; return renamed
  fields plus `isLoading`, `error`, `mutate`.
  - Legacy origin: `frontend/hooks/` (48 files)
  - Definition of done: codify the template once, then apply it. A hook that
    returns `data`, or that fetches with nothing selected, is a defect —
    consider an eslint rule or a test that walks the hooks directory.
  - Confidence: 🟢

- [ ] **T-06 — Query-parameter keys.**
  Interpolate filters into the key so each variant is its own cache entry
  (`/construction-plans?plan_type={}`, `/airfoils/db/suitability?{}`,
  `/aeroplanes/{}/matching-chart?{}`,
  `/aeroplanes/{}/loading-scenarios/templates?aircraft_class={}`).
  - Legacy origin: the corresponding hooks
  - Definition of done: two different filters produce two cache entries; a
    filter change refetches.
  - Confidence: 🟢

- [ ] **T-07 — Write + revalidate.**
  `putJson` / `api.*` followed by the hook's own `mutate()`.
  - Legacy origin: the editor hooks
  - Definition of done: the panel reflects the saved value without a reload.
  - Confidence: 🟢

- [ ] **T-08 — Cross-hook invalidation.**
  `useSWRConfig().mutate(<exact literal path>)` for keys owned by other hooks —
  e.g. every version action revalidates both `/lineages/{root}/tree` and
  `/aeroplanes`.
  - Legacy origin: `frontend/hooks/useVersioning.ts`
  - Definition of done: an adopt refreshes both the graph and the picker.
    **Record** that a typo in the duplicated key string silently no-ops — a
    shared key module would remove the class of bug.
  - Confidence: 🟢

- [ ] **T-09 — The 48 hooks.**
  One per capability, grouped: aeroplane/geometry, mass & mission, powertrain,
  components, construction, airfoils, versioning, copilot. The full endpoint
  inventory is in [`../contracts.md`](../contracts.md).
  - Legacy origin: `frontend/hooks/`
  - Definition of done: every hook follows T-05; every path in the contract
    inventory has exactly one owning hook.
  - Confidence: 🟢

- [ ] **T-10 — SSE consumers.**
  `useCopilot` (token / tool_call / tool_result / done / error; `mutate` the
  history key on `done`; surface `truncated`) and the OpenVSP import progress
  bar (gh-737).
  - Legacy origin: `frontend/hooks/useCopilot.ts`,
    `frontend/components/workbench/ImportProgressBar.tsx`
  - Definition of done: streamed text is replaced by the revalidated persisted
    history on `done`, so the user never sees a duplicate message.
  - Confidence: 🟢

### Remediation (behaviour changes — each needs a decision)

- [ ] **T-11 — Introduce a global `SWRConfig`.**
  Shared `revalidateOnFocus`, retry policy and `onError`.
  - Legacy origin: — (none exists)
  - Definition of done: policy lives in one place instead of 48 implicit
    decisions. Verify that no hook depended on the previous defaults.
  - Confidence: 🟡 (a decision)

- [ ] **T-12 — Collapse to one HTTP client.**
  Keep the typed `ApiError` client and make it the SWR fetcher.
  - Legacy origin: BR-FE8
  - Definition of done: `parseApiError` shrinks to handling only the two
    **backend** envelopes; the 204 behaviour becomes uniform.
  - Confidence: 🟡 (a decision)

- [ ] **T-13 — Generate types from `/openapi.json`.**
  Replace the hand-mirrored interfaces.
  - Legacy origin: BR-FE11
  - Definition of done: a backend field rename breaks the build immediately,
    rather than only where a fixture happens to disagree.
  - Confidence: 🟡 (a decision)

- [ ] **T-14 — A shared key module.**
  Central path builders used by both the producing hook and every invalidation
  site.
  - Legacy origin: BR-FE7
  - Definition of done: no literal path string appears twice.
  - Confidence: 🟡 (a decision)

## Test Tasks

- [ ] **TT-01 — `fetcher`:** success, non-2xx message content, and the 204 throw
      (characterisation).
- [ ] **TT-02 — `putJson`:** header, body, and the error message prefix.
- [ ] **TT-03 — `fetchAPI`:** `ApiError` fields; 204 → `undefined`.
- [ ] **TT-04 — `parseApiError`:** both client error types × both backend
      envelopes.
- [ ] **TT-05 — Null key:** no fetch occurs.
- [ ] **TT-06 — Renamed returns:** a directory walk asserts no hook returns
      `data`.
- [ ] **TT-07 — Query keys:** two filters ⇒ two cache entries.
- [ ] **TT-08 — Write + revalidate:** `mutate` called after a save.
- [ ] **TT-09 — Cross-hook invalidation:** an adopt revalidates the tree and the
      aeroplanes list.
- [ ] **TT-10 — SSE:** split record, multiple `data:` lines, non-JSON payload,
      missing trailing blank line, reader release.
- [ ] **TT-11 — Copilot stream:** tokens accumulate; `done` triggers history
      revalidation; `truncated` surfaced; `error` sets the message.
- [ ] **TT-12 — Types:** `npx tsc --noEmit` on Node 22.

## Suggested Order

1. **T-01 → T-04** the wrappers and the error bridge. Their error shapes
   determine how every hook and panel behaves on failure.
2. **T-05 → T-06** the hook template and key conventions. Add TT-05 and TT-06 as
   guards immediately — 48 hooks drift without an enforced template.
3. **T-07 → T-08** writes and invalidation, with the version hooks as the
   worked example (they invalidate two foreign keys).
4. **T-09** the remaining hooks, grouped by feature area.
5. **T-10** the SSE consumers, once `parseSseStream` is proven.
6. **T-11 → T-14** the remediations. T-12 (one client) makes T-11 (global
   config) simpler, and T-13 (generated types) is the highest-value change for
   catching backend drift.

## Pending Gaps

- **Should there be a global `SWRConfig`** with a shared revalidation, retry and
  error policy?
- **Should the two HTTP clients collapse into one?** The richer one is currently
  the less-used one.
- **Should response types be generated from `/openapi.json`** instead of
  hand-mirrored per hook?
- **Should SWR keys come from a shared module**, so an invalidation typo cannot
  silently no-op?
- **Should `fetcher` handle 204** like `lib/api.ts` does?
- **Should there be client-side error reporting** — an error boundary, a global
  `onError`, telemetry?
- **Should the backend's two error envelopes be unified**, letting
  `parseApiError` disappear? (That decision belongs to `platform-core`.)

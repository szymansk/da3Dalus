/**
 * gh-630: Playwright-BDD step definitions for polar-design-warning badge visibility.
 *
 * Strategy: use `page.route()` to stub the computation-context API response so
 * each scenario controls the `polar_by_config.clean.rejection` value precisely,
 * without needing to seed or mutate a real backend database record. A real
 * aeroplane is still required to give the app a valid `aeroplaneId`; we reuse
 * `ensureTestAeroplaneId()` to either create or locate an existing one.
 *
 * The route handler is scoped to the computation-context path only, so all
 * other API calls (assumptions list, wings, etc.) still hit the real backend.
 */

import { createBdd } from "playwright-bdd";
import { expect } from "@playwright/test";

const { Given, When, Then } = createBdd();

const API =
  process.env.API_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8001";

const TEST_AEROPLANE_NAME = "PolarWarningE2ETest";

// ── Minimal computation-context fixture ──────────────────────────────────────

/** A bare-bones ComputationContext with no wing data — sufficient for
 *  AssumptionsPanel to render the Aerodynamics group and the polar badges. */
function baseContext() {
  return {
    v_cruise_mps: 15,
    v_stall_mps: 9,
    reynolds: 200000,
    mac_m: 0.2,
    x_np_m: 0.12,
    target_static_margin: 0.1,
    cg_agg_m: 0.1,
    is_glider: false,
    computed_at: new Date().toISOString(),
  };
}

function polarSuccess(): Record<string, unknown> {
  return {
    cd0: 0.025,
    e_oswald: 0.8,
    cl_max: 1.4,
    e_oswald_r2: 0.98,
    e_oswald_quality: "high",
    flap_deflection_deg: 0,
    provenance: "aerobuildup",
    rejection: null,
  };
}

function polarDesignRejection(): Record<string, unknown> {
  return {
    cd0: null,
    e_oswald: null,
    cl_max: 1.4,
    e_oswald_r2: null,
    e_oswald_quality: "unknown",
    flap_deflection_deg: 0,
    provenance: "aerobuildup",
    rejection: {
      gate: "negative_slope_k",
      category: "design",
      fitted_value: -0.03,
      threshold: "k > 0",
      hint: "Fitted induced-drag factor k ≤ 0 (−0.030) — check aspect ratio and Oswald efficiency inputs.",
    },
  };
}

function polarSweepRejection(): Record<string, unknown> {
  return {
    cd0: null,
    e_oswald: null,
    cl_max: 1.4,
    e_oswald_r2: null,
    e_oswald_quality: "unknown",
    flap_deflection_deg: 0,
    provenance: "aerobuildup",
    rejection: {
      gate: "insufficient_points",
      category: "sweep",
      fitted_value: null,
      threshold: "n_points >= 5",
      hint: "Not enough sweep points to fit a parabolic polar — run a wider sweep.",
    },
  };
}

// ── Shared state ─────────────────────────────────────────────────────────────

/** aeroplaneId resolved once per worker; shared across scenarios. */
let resolvedAeroplaneId = "";

async function ensureTestAeroplaneId(
  request: import("@playwright/test").APIRequestContext,
): Promise<string> {
  if (resolvedAeroplaneId) return resolvedAeroplaneId;

  const listRes = await request.get(`${API}/aeroplanes`);
  const body = (await listRes.json()) as {
    aeroplanes: { id: string; name: string }[];
  };

  const existing = body.aeroplanes?.find(
    (a) => a.name === TEST_AEROPLANE_NAME,
  );
  if (existing) {
    resolvedAeroplaneId = existing.id;
    return resolvedAeroplaneId;
  }

  const createRes = await request.post(
    `${API}/aeroplanes?name=${encodeURIComponent(TEST_AEROPLANE_NAME)}`,
  );
  expect(createRes.ok()).toBeTruthy();
  const created = (await createRes.json()) as { id: string };
  resolvedAeroplaneId = created.id;
  return resolvedAeroplaneId;
}

// ── Seed helpers — inject design assumptions so AssumptionsPanel renders ─────

/**
 * Seed the minimum design assumptions so the Aerodynamics group is non-empty.
 * POST /aeroplanes/{id}/assumptions is idempotent — it seeds defaults and is safe
 * to call even if assumptions already exist.
 */
async function ensureAssumptionsExist(
  request: import("@playwright/test").APIRequestContext,
  aeroplaneId: string,
): Promise<void> {
  // POST is idempotent — seeds defaults if not already seeded, no-ops otherwise.
  await request.post(`${API}/aeroplanes/${aeroplaneId}/assumptions`);
}

// ── Given steps: stub the computation-context response ───────────────────────

Given(
  "an aeroplane whose clean parabolic-polar fit fails with a negative-slope design rejection",
  async ({ page, request }) => {
    const id = await ensureTestAeroplaneId(request);
    await ensureAssumptionsExist(request, id);

    const ctxPattern = `**/aeroplanes/${id}/assumptions/computation-context`;
    await page.route(ctxPattern, (route) => {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ...baseContext(),
          polar_by_config: {
            clean: polarDesignRejection(),
            takeoff: polarSuccess(),
            landing: polarSuccess(),
          },
        }),
      });
    });
  },
);

Given(
  "an aeroplane whose clean parabolic-polar fit fails with an insufficient-points sweep rejection",
  async ({ page, request }) => {
    const id = await ensureTestAeroplaneId(request);
    await ensureAssumptionsExist(request, id);

    const ctxPattern = `**/aeroplanes/${id}/assumptions/computation-context`;
    await page.route(ctxPattern, (route) => {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ...baseContext(),
          polar_by_config: {
            clean: polarSweepRejection(),
            takeoff: polarSuccess(),
            landing: polarSuccess(),
          },
        }),
      });
    });
  },
);

Given(
  "an aeroplane whose three parabolic-polar fits all succeed",
  async ({ page, request }) => {
    const id = await ensureTestAeroplaneId(request);
    await ensureAssumptionsExist(request, id);

    const ctxPattern = `**/aeroplanes/${id}/assumptions/computation-context`;
    await page.route(ctxPattern, (route) => {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ...baseContext(),
          polar_by_config: {
            clean: polarSuccess(),
            takeoff: polarSuccess(),
            landing: polarSuccess(),
          },
        }),
      });
    });
  },
);

// ── When: navigate to the analysis dashboard ─────────────────────────────────

When("I open the analysis dashboard", async ({ page }) => {
  // resolvedAeroplaneId is set by the Given step (ensureTestAeroplaneId)
  // and shared across steps in the same worker-scoped module.
  const id = resolvedAeroplaneId;

  // Navigate to the analysis page. The Assumptions tab is the default active
  // tab (useState("Assumptions") in AnalysisPage), so AssumptionsPanel renders
  // immediately without any tab click.
  await page.goto(`/workbench/analysis?id=${encodeURIComponent(id)}`);

  // Wait for the Aerodynamics group header to confirm the panel is rendered.
  await page
    .getByTestId("assumption-group-aerodynamics")
    .waitFor({ state: "visible", timeout: 15000 });
});

// ── Then: assertions ─────────────────────────────────────────────────────────

Then(
  "a visible design-warning badge displays the rejection hint",
  async ({ page }) => {
    const container = page.getByTestId("polar-rejection-badges");
    // The badge is scoped to the polar-rejection-badges container to avoid
    // false positives from other role="alert" elements (e.g. pitch warning).
    const badge = container.getByRole("alert").first();
    await expect(badge).toBeVisible({ timeout: 5000 });
    // The hint text should be present (partial match is sufficient).
    await expect(badge).toContainText("Design issue:");
  },
);

Then(
  "the badge has the accessible role {string}",
  async ({ page }, _role: string) => {
    // Already asserted via getByRole("alert") above; this step confirms the
    // attribute is present on the rendered element.
    const container = page.getByTestId("polar-rejection-badges");
    const badge = container.locator('[role="alert"]').first();
    await expect(badge).toBeVisible({ timeout: 5000 });
    await expect(badge).toHaveAttribute("role", "alert");
  },
);

Then("no polar-design-warning badge is visible", async ({ page }) => {
  const container = page.getByTestId("polar-rejection-badges");
  // The container itself may or may not be present; if present, it should
  // contain no alert-role elements.
  const containerVisible = await container
    .isVisible({ timeout: 5000 })
    .catch(() => false);

  if (containerVisible) {
    const badge = container.locator('[role="alert"]');
    await expect(badge).toHaveCount(0, { timeout: 3000 });
  }
  // If the container is not present at all, the assertion passes trivially.
});

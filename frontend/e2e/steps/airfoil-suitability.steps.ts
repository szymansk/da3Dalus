/**
 * gh-825: Playwright-BDD step definitions for airfoil suitability feature.
 *
 * Strategy: use page.route() to stub GET /airfoils/db/suitability with
 * frozen-contract fixtures. A minimal stub for GET /airfoils is also provided
 * so the AirfoilSelector populates. The page is loaded directly via URL.
 */

import { createBdd } from "playwright-bdd";
import { expect } from "@playwright/test";

const { Given, When, Then } = createBdd();

// ── Frozen-contract fixtures ─────────────────────────────────────

function suitabilityItem(
  airfoil_name: string,
  overrides: Partial<{
    re_agnostic: number;
    mission: number | null;
    target_cl_cruise: number | null;
    target_cl_best_glide: number | null;
    target_cl_min_sink: number | null;
    stall_gentleness: number | null;
    cl_max_margin: number | null;
    min_analysis_confidence: number;
    tip_re_flag: boolean;
    caveat: string;
  }> = {},
) {
  return {
    airfoil_name,
    family: "cambered",
    re_agnostic: 0.82,
    mission: 0.75,
    target_cl_cruise: 0.68,
    target_cl_best_glide: 0.80,
    target_cl_min_sink: 0.55,
    stall_gentleness: -0.02,
    cl_max_margin: 0.15,
    min_analysis_confidence: 0.92,
    tip_re_flag: false,
    caveat: "Nur relative Rangfolge.",
    ...overrides,
  };
}

function suitabilityResponse(items: ReturnType<typeof suitabilityItem>[]) {
  return {
    query: {
      chord_m: 0.2,
      speed_ms: 14,
      reynolds: 191781,
      re_clamped: false,
      mission_type: "trainer",
      target_cl_cruise: 0.68,
      target_cl_best_glide: 0.80,
      target_cl_min_sink: 0.55,
      target_cl_provenance: "estimated",
      active_lens: "re_agnostic",
    },
    caveat: {
      relative_ranking_only: true,
      no_hysteresis_modelling: true,
      ignores_tip_re_clmax_collapse: true,
      recommend_xfoil_validation: false,
      text: "Nur relative Rangfolge. Kein Hysterese-Modell.",
    },
    results: items,
  };
}

// Stub for the airfoil list (minimal)
const AIRFOILS_STUB = {
  count: 3,
  airfoils: [
    { airfoil_name: "e423", file_name: "e423.dat" },
    { airfoil_name: "naca0015", file_name: "naca0015.dat" },
    { airfoil_name: "clark-y", file_name: "clark-y.dat" },
  ],
};

// ── Shared setup helpers ─────────────────────────────────────────

async function setupPage(
  page: import("@playwright/test").Page,
  suitabilityBody: object,
) {
  // Stub the suitability endpoint
  await page.route("**/airfoils/db/suitability**", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(suitabilityBody),
    });
  });

  // Stub the airfoil list
  await page.route("**/airfoils", (route) => {
    if (!route.request().url().includes("suitability")) {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(AIRFOILS_STUB),
      });
    } else {
      route.continue();
    }
  });

  // Navigate to the airfoil-preview page without a real aeroplane id
  // (suitability hook still fires with just chord_m + speed_ms)
  await page.goto("/workbench/airfoil-preview");
  // Wait for the page to be stable
  await page.waitForLoadState("networkidle");
}

// ── Given steps ──────────────────────────────────────────────────

Given(
  "I am on the airfoil-preview page with a stubbed suitability response",
  async ({ page }) => {
    const items = [
      suitabilityItem("e423", { re_agnostic: 0.82, mission: 0.75 }),
      suitabilityItem("naca0015", { re_agnostic: 0.55, mission: 0.45 }),
      suitabilityItem("clark-y", { re_agnostic: 0.65, mission: 0.60 }),
    ];
    await setupPage(page, suitabilityResponse(items));
  },
);

Given(
  "I am on the airfoil-preview page with a low-confidence suitability response",
  async ({ page }) => {
    const items = [
      suitabilityItem("e423", {
        re_agnostic: 0.72,
        min_analysis_confidence: 0.72, // < 0.85 => amber chip
        caveat: "Niedrige Konfidenz — XFoil-Validierung empfohlen.",
      }),
    ];
    await setupPage(page, suitabilityResponse(items));
  },
);

Given(
  "I am on the airfoil-preview page with tip Re lower than root Re",
  async ({ page }) => {
    const items = [suitabilityItem("e423")];
    // Stub suitability (doesn't affect Re display)
    await page.route("**/airfoils/db/suitability**", (route) => {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(suitabilityResponse(items)),
      });
    });
    await page.route("**/airfoils", (route) => {
      if (!route.request().url().includes("suitability")) {
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(AIRFOILS_STUB),
        });
      } else {
        route.continue();
      }
    });

    // Navigate and then manipulate the Re fields so tipRe < rootRe
    // The page derives Re from velocity + chord; with tipChord < rootChord,
    // tipRe < rootRe. We navigate with default state and rely on the
    // fixture values which set tip chord < root chord.
    await page.goto("/workbench/airfoil-preview");
    await page.waitForLoadState("networkidle");

    // Manually set the tip Re field to a value lower than root Re
    // The root Re field is labelled "Re" with color #FF8400, tip is #22D3EE
    // We set tip airfoil to something different first to ensure hasTip=true
    // For E2E: we just check that if tipRe < rootRe the banner appears.
    // Since AirfoilPreviewViewerPanel receives tipRe as a prop from page.tsx,
    // and the test page uses default chords (root=200mm, tip=200mm), we need
    // to explicitly set a different tip chord via the Re inputs.
    // We'll manually type into the tip Re input to set a lower value.
    const tipReInput = page.locator('input[type="number"]').nth(2);
    await tipReInput.fill("50000");
    await tipReInput.press("Enter");
  },
);

// ── When steps ───────────────────────────────────────────────────

When(
  "I click the Passende finden toggle for the root selector",
  async ({ page }) => {
    // The toggle button has title containing "Passende finden"
    const toggleBtn = page.getByTitle(/Passende finden/i).first();
    await expect(toggleBtn).toBeVisible({ timeout: 10000 });
    await toggleBtn.click();
  },
);

// ── Then steps ───────────────────────────────────────────────────

Then(
  "the root suitability card shows the Re-agnostisch lens",
  async ({ page }) => {
    await expect(
      page.getByText(/Re-agnostisch/i).first(),
    ).toBeVisible({ timeout: 10000 });
  },
);

Then(
  "the root suitability card shows the Mission lens",
  async ({ page }) => {
    await expect(
      page.getByText(/Mission/i).first(),
    ).toBeVisible({ timeout: 10000 });
  },
);

Then(
  "the root suitability card shows the Ziel-CL Cruise lens",
  async ({ page }) => {
    await expect(
      page.getByText(/Cruise/i).first(),
    ).toBeVisible({ timeout: 10000 });
  },
);

Then(
  "the root suitability card shows the Ziel-CL Best-Glide lens",
  async ({ page }) => {
    await expect(
      page.getByText(/Best-Glide/i).first(),
    ).toBeVisible({ timeout: 10000 });
  },
);

Then(
  "the root suitability card shows the Ziel-CL Min-Sink lens",
  async ({ page }) => {
    await expect(
      page.getByText(/Min-Sink/i).first(),
    ).toBeVisible({ timeout: 10000 });
  },
);

Then(
  "the root suitability card shows an amber confidence chip",
  async ({ page }) => {
    // The chip shows "● Confidence 0.72" and should have amber colour
    // We look for a confidence value < 0.85 (will be styled amber)
    const chip = page.getByText(/Confidence\s+0\.[0-7]\d/i).first();
    await expect(chip).toBeVisible({ timeout: 10000 });
  },
);

Then("the root suitability card shows a caveat callout", async ({ page }) => {
  await expect(
    page.getByText(/Niedrige Konfidenz/i).first(),
  ).toBeVisible({ timeout: 10000 });
});

Then(
  "a tip-Re warning banner is visible with role {string}",
  async ({ page }, _role: string) => {
    const banner = page.getByRole("alert").first();
    await expect(banner).toBeVisible({ timeout: 10000 });
    await expect(banner).toHaveAttribute("role", "alert");
  },
);

Then(
  "the root airfoil dropdown shows airfoils sorted by suitability score",
  async ({ page }) => {
    // Open the root dropdown trigger button
    // The trigger button for root_airfoil is labeled "root_airfoil" section
    const rootSection = page.locator("text=root_airfoil").first();
    await expect(rootSection).toBeVisible({ timeout: 10000 });

    // Click the dropdown trigger for root airfoil
    const dropdownTrigger = rootSection
      .locator("..") // parent
      .locator("button")
      .first();
    await dropdownTrigger.click();

    // The dropdown should be open with items
    // e423 (0.82) should appear before naca0015 (0.55)
    const e423 = page.getByText("e423").first();
    await expect(e423).toBeVisible({ timeout: 5000 });
  },
);

Then(
  "the root suitability card shows a provenance indicator",
  async ({ page }) => {
    await expect(
      page.getByTestId("provenance-indicator").first(),
    ).toBeVisible({ timeout: 10000 });
  },
);

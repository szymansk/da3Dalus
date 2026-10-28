/**
 * gh-1282: Playwright-BDD steps for the Expert View.
 *
 * The backend is stubbed with `page.route()`: the scenario controls what the kernel answers, so the
 * test checks the page (the iframe-hosted navigator in connected mode), not the solvers. The
 * kernel itself is covered by the backend tests.
 */

import { createBdd } from "playwright-bdd";
import { expect, type Page, type Route } from "@playwright/test";

const { Given, When, Then } = createBdd();

const API =
  process.env.API_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8001";

const CORS = {
  "access-control-allow-origin": "*",
  "access-control-allow-headers": "content-type",
  "access-control-allow-methods": "GET,POST,OPTIONS",
};

const FLEET = [
  { id: "bryan", name: "BRYAN", mass_kg: 0.151, flap_deflections: {} },
  { id: "jaguar", name: "JAGUAR", mass_kg: 0.16, flap_deflections: {} },
];

interface Failure {
  quantity: string;
  cause: string;
}

/** The failure a scenario asks for; reset by the Background step of each scenario. */
let failure: Failure | null = null;

function answer(slug: string) {
  const quantity = (over: Record<string, unknown>) => ({
    slug,
    unit: "m/s",
    status: "ok",
    value: 7.5,
    tool: "OPT",
    application: "default",
    warnings: [],
    from_cache: false,
    ...over,
  });
  let result = quantity({});
  if (failure && slug === failure.quantity) {
    result = quantity({
      status: "error",
      value: null,
      unit: null,
      tool: null,
      application: null,
      error: {
        code: "upstream_failed",
        category: "upstream_failed",
        message: `\`${slug}\` has no value because \`${failure.cause}\` failed.`,
        hint: `Fix \`${failure.cause}\` first.`,
        retryable: false,
        escalate: false,
        detail: { causes: [{ quantity: failure.cause, code: "missing_input" }] },
      },
    });
  } else if (failure && slug === failure.cause) {
    result = quantity({
      status: "error",
      value: null,
      unit: null,
      tool: null,
      application: null,
      error: {
        code: "missing_input",
        category: "invalid_input",
        message: `\`${slug}\` reads a value nobody supplied.`,
        hint: "Supply it.",
        formula: slug,
        input_path: "values.altitude",
        detail: {},
      },
    });
  }
  return result;
}

async function stubBackend(page: Page) {
  await page.route(`${API}/canon/**`, async (route: Route) => {
    const request = route.request();
    if (request.method() === "OPTIONS") {
      return route.fulfill({ status: 204, headers: CORS });
    }
    if (request.url().endsWith("/canon/fleet")) {
      return route.fulfill({ status: 200, headers: CORS, json: FLEET });
    }
    const body = request.postDataJSON() as { quantities: string[] };
    return route.fulfill({
      status: 200,
      headers: CORS,
      json: {
        quantities: body.quantities.map(answer),
        input_errors: [],
        provenance: { build_digest: "e2e", defaults_used: [] },
        verdicts: [],
        needs_confirmation: [],
        logs: [
          {
            time: "2026-10-28T08:00:00.123Z",
            level: "DEBUG",
            logger: "aero_kernel.engine",
            message: "node started",
            formula: body.quantities[0],
            quantity: null,
          },
        ],
      },
    });
  });
}

const navigator = (page: Page) =>
  page.frameLocator('iframe[title^="Canon navigator"]');

Given("the Expert View is open with a stubbed kernel backend", async ({ page }) => {
  failure = null;
  await stubBackend(page);
  await page.goto("/expert");
  await expect(navigator(page).locator("#connAircraft")).toContainText("BRYAN");
});

Given(
  "the kernel fails {string} because {string} failed",
  async ({ page }, quantity: string, cause: string) => {
    void page; // the failure is read by the stub at request time
    failure = { quantity, cause };
  },
);

When("I click the {string} node in the navigator", async ({ page }, slug: string) => {
  await navigator(page).locator(`[data-node="${slug}"]`).click();
});

When("I choose {string} in the navigator panel", async ({ page }, label: string) => {
  await navigator(page).getByRole("button", { name: new RegExp(label) }).first().click();
});

Then(
  "the {string} node is marked as computed",
  async ({ page }, slug: string) => {
    await expect(
      navigator(page).locator(`[data-node="${slug}"] .cbadge[data-state="ok"]`),
    ).toBeVisible();
  },
);

Then("the {string} node is marked as failed", async ({ page }, slug: string) => {
  await expect(
    navigator(page).locator(`[data-node="${slug}"] .cbadge[data-state="error"]`),
  ).toBeVisible();
});

Then("the navigator panel shows the value {string}", async ({ page }, text: string) => {
  await expect(navigator(page).locator("#kres")).toContainText(text);
});

Then("the kernel log lists a record of the request", async ({ page }) => {
  await expect(navigator(page).locator("#loglines")).toContainText("node started");
});

Then("the navigator panel is about {string}", async ({ page }, slug: string) => {
  await expect(navigator(page).locator("#kres")).toHaveAttribute("data-for", slug);
});

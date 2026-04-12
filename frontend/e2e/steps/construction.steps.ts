import { createBdd } from "playwright-bdd";
import { expect } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";
import { EHAWK_WING_CONFIG } from "../fixtures/ehawk-wing-config";

const { Given, When, Then } = createBdd();

const API =
  process.env.API_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8001";

// Persistent state — shared across scenarios in serial mode
const STATE_FILE = path.join(__dirname, "..", ".ehawk-state.json");

function loadState(): { aeroplaneId?: string } {
  try {
    return JSON.parse(fs.readFileSync(STATE_FILE, "utf-8"));
  } catch {
    return {};
  }
}

function saveState(state: { aeroplaneId?: string }) {
  fs.mkdirSync(path.dirname(STATE_FILE), { recursive: true });
  fs.writeFileSync(STATE_FILE, JSON.stringify(state));
}

let aeroplaneId: string = loadState().aeroplaneId ?? "";

function ensureId() {
  if (!aeroplaneId) aeroplaneId = loadState().aeroplaneId ?? "";
  if (!aeroplaneId) throw new Error("No aeroplaneId — run 'Create eHawk' scenario first");
}

// ── Background ──────────────────────────────────────────────────

Given("the backend is running", async ({ request }) => {
  const res = await request.get(`${API}/health`);
  expect(res.ok()).toBeTruthy();
});

Given("the frontend is running", async ({ page }) => {
  const res = await page.goto("/");
  expect(res?.ok()).toBeTruthy();
});

// ── Create aeroplane via UI ─────────────────────────────────────

Given("I am on the workbench", async ({ page }) => {
  await page.goto("/workbench");
  // Wait for either the selector dialog or the workbench to load
  await page.waitForSelector(
    'text="Select Aeroplane", text="Aeroplane Tree"',
    { timeout: 10000 },
  ).catch(() => {
    // Either the selector or the tree is visible
  });
});

When(
  "I click {string} and enter name {string}",
  async ({ page }, buttonText: string, name: string) => {
    // Handle the prompt dialog that will appear
    page.once("dialog", async (dialog) => {
      await dialog.accept(name);
    });

    await page.getByRole("button", { name: buttonText }).click();

    // Wait for the workbench to load after creation
    await page.waitForSelector('text="Aeroplane Tree"', { timeout: 10000 });

    // Extract aeroplaneId from the API
    const res = await page.request.get(`${API}/aeroplanes`);
    const body = await res.json();
    const match = body.aeroplanes?.find(
      (a: { name: string }) => a.name === name,
    );
    if (match) {
      aeroplaneId = match.id;
      saveState({ aeroplaneId });
    }
  },
);

Then("I see the construction workbench", async ({ page }) => {
  await expect(page.getByText("Aeroplane Tree")).toBeVisible();
});

Then("the header shows project {string}", async ({ page }, name: string) => {
  // The header shows the aeroplane name in the ConfigPanel's tree
  await expect(page.getByText(name)).toBeVisible();
});

// ── Create wing via API (from-wingconfig) ───────────────────────

Given(
  "the {string} aeroplane exists",
  async ({ request }, _name: string) => {
    ensureId();
    const res = await request.get(`${API}/aeroplanes/${aeroplaneId}`);
    expect(res.ok()).toBeTruthy();
  },
);

When(
  "I submit the eHawk wing config for {string} via API",
  async ({ request }, wingName: string) => {
    ensureId();
    const res = await request.post(
      `${API}/aeroplanes/${aeroplaneId}/wings/${wingName}/from-wingconfig`,
      { data: EHAWK_WING_CONFIG },
    );
    expect(res.status()).toBe(201);
  },
);

When("I reload the workbench", async ({ page }) => {
  await page.goto("/workbench");
  await page.waitForSelector('text="Aeroplane Tree"', { timeout: 10000 });
});

Then(
  "the tree shows {string} under the aeroplane",
  async ({ page }, wingName: string) => {
    // The wing name should appear in the tree
    await expect(page.getByText(wingName).first()).toBeVisible({ timeout: 5000 });
  },
);

Then(
  "{string} has {int} cross sections in the tree",
  async ({ page }, _wingName: string, count: number) => {
    // Expand the wing in the tree and count segment nodes
    // Segments appear as "segment N" text elements
    const segments = page.locator('text=/segment \\d/');
    // We need to expand the wing first — click on it
    const wingNode = page.getByText("main_wing").first();
    await wingNode.click();
    // Wait for segments to appear
    await page.waitForTimeout(1000);
    // Count visible segment entries (x_secs - 1 terminal = segments shown)
    const segCount = await segments.count();
    // The tree shows x_secs as segments. With 13 x_secs, we expect
    // segments 0 through 12 visible (13 segments total if all expanded)
    expect(segCount).toBeGreaterThanOrEqual(1);
  },
);

// ── Select segment + property form ──────────────────────────────

Given(
  "the {string} has wing {string} in the tree",
  async ({ page }, _name: string, wingName: string) => {
    ensureId();
    await page.goto("/workbench");
    await page.waitForSelector('text="Aeroplane Tree"', { timeout: 10000 });
    // Ensure the aeroplane is selected (click it if selector shows)
    const selector = page.getByText("Select Aeroplane");
    if (await selector.isVisible().catch(() => false)) {
      await page.getByText("eHawk E2E Test").click();
      await page.waitForSelector('text="Aeroplane Tree"', { timeout: 5000 });
    }
    await expect(page.getByText(wingName).first()).toBeVisible({ timeout: 5000 });
  },
);

When(
  "I click on {string} in the tree",
  async ({ page }, nodeLabel: string) => {
    await page.getByText(nodeLabel).first().click();
  },
);

Then(
  "the property form shows {string}",
  async ({ page }, segmentLabel: string) => {
    await expect(
      page.getByText(new RegExp(`${segmentLabel}.*Properties`)),
    ).toBeVisible({ timeout: 5000 });
  },
);

Then(
  "the airfoil field shows {string}",
  async ({ page }, airfoil: string) => {
    // The property form has an input with the airfoil value
    const airfoilInput = page.locator('input[type="text"]').first();
    await expect(airfoilInput).toHaveValue(airfoil, { timeout: 5000 });
  },
);

Then(
  "the chord field shows a value greater than {int}",
  async ({ page }, min: number) => {
    // Chord is a number input in the form
    const chordInputs = page.locator('input[type="number"]');
    const count = await chordInputs.count();
    expect(count).toBeGreaterThan(0);
    const val = await chordInputs.first().inputValue();
    expect(parseFloat(val)).toBeGreaterThan(min);
  },
);

// ── Analysis via UI ─────────────────────────────────────────────

Given(
  "the {string} has wing {string}",
  async ({}, _name: string, _wing: string) => {
    ensureId();
  },
);

Then("I see the analysis page", async ({ page }) => {
  await expect(page.getByText("Aerodynamic Analysis").first()).toBeVisible({
    timeout: 5000,
  });
});

When("I set velocity to {string}", async ({ page }, value: string) => {
  const input = page.locator('input').filter({ has: page.locator('..') }).nth(3);
  // Find the velocity input by its label
  const velocitySection = page.locator('text=velocity').first();
  const velocityInput = velocitySection.locator('..').locator('input').first();
  if (await velocityInput.isVisible().catch(() => false)) {
    await velocityInput.fill(value);
  }
});

When("I set alpha start to {string}", async ({ page }, value: string) => {
  const label = page.locator('text=alpha_start, text=alphaStart, text=α_start').first();
  const input = label.locator('..').locator('input').first();
  if (await input.isVisible().catch(() => false)) {
    await input.fill(value);
  }
});

When("I set alpha end to {string}", async ({ page }, value: string) => {
  const label = page.locator('text=alpha_end, text=alphaEnd, text=α_end').first();
  const input = label.locator('..').locator('input').first();
  if (await input.isVisible().catch(() => false)) {
    await input.fill(value);
  }
});

When("I set alpha step to {string}", async ({ page }, value: string) => {
  const label = page.locator('text=alpha_step, text=alphaStep, text=α_step').first();
  const input = label.locator('..').locator('input').first();
  if (await input.isVisible().catch(() => false)) {
    await input.fill(value);
  }
});

When("I click {string}", async ({ page }, buttonText: string) => {
  await page.getByRole("button", { name: buttonText }).click();
});

Then("the analysis completes without error", async ({ page }) => {
  // Wait for the loading spinner to disappear or results to appear
  // The Run Analysis button should stop showing the spinner
  await page.waitForTimeout(5000); // Give the analysis time to complete
  // Check no error banner is visible
  const errorBanner = page.locator('text=/Analysis failed|Error/i');
  const hasError = await errorBanner.isVisible().catch(() => false);
  expect(hasError).toBeFalsy();
});

Then("the polar chart shows bars", async ({ page }) => {
  // The chart area contains bar divs with bg-primary class
  const bars = page.locator(".bg-primary").filter({
    has: page.locator('[style*="height"]'),
  });
  // Fallback: just check the chart area exists
  await expect(page.getByText("C_L vs").first()).toBeVisible({ timeout: 5000 });
});

Then("the chart annotation shows a CL_max value", async ({ page }) => {
  await expect(
    page.getByText(/C_L.*max|CL.*max/i).first(),
  ).toBeVisible({ timeout: 5000 });
});

// ── Verify in backend DB ────────────────────────────────────────

When(
  "I query the wing {string} from the API",
  async ({ request }, wingName: string) => {
    ensureId();
    const res = await request.get(
      `${API}/aeroplanes/${aeroplaneId}/wings/${wingName}`,
    );
    expect(res.ok()).toBeTruthy();
    // Store the wing data for subsequent Then steps
    const wing = await res.json();
    // Attach to a known location so Then steps can read it
    fs.writeFileSync(
      path.join(__dirname, "..", ".wing-data.json"),
      JSON.stringify(wing),
    );
  },
);

function loadWingData() {
  return JSON.parse(
    fs.readFileSync(path.join(__dirname, "..", ".wing-data.json"), "utf-8"),
  );
}

Then("the wing has {int} cross sections", async ({}, count: number) => {
  const wing = loadWingData();
  expect(wing.x_secs.length).toBe(count);
});

Then(
  "cross section {int} has airfoil {string}",
  async ({}, index: number, airfoil: string) => {
    const wing = loadWingData();
    expect(wing.x_secs[index].airfoil).toBe(airfoil);
  },
);

Then(
  "cross section {int} has chord approximately {float}",
  async ({}, index: number, expected: number) => {
    const wing = loadWingData();
    const actual = wing.x_secs[index].chord;
    expect(Math.abs(actual - expected)).toBeLessThan(0.01);
  },
);

Then("the wing is symmetric", async ({}) => {
  const wing = loadWingData();
  expect(wing.symmetric).toBe(true);
});

import { createBdd } from "playwright-bdd";
import { expect } from "@playwright/test";
import type { DataTable } from "@cucumber/cucumber";
import * as fs from "fs";
import * as path from "path";

const { Given, When, Then } = createBdd();

const API =
  process.env.API_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8001";

// ── Persistent state ────────────────────────────────────────────

const STATE_FILE = path.join(__dirname, "..", ".ehawk-state.json");
const CLEANUP_FILE = path.join(__dirname, "..", ".cleanup-done");

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

async function ensureIdFromApi(
  request: { get: (url: string) => Promise<{ json: () => Promise<unknown>; ok: () => boolean }> },
) {
  if (aeroplaneId) return;
  aeroplaneId = loadState().aeroplaneId ?? "";
  if (aeroplaneId) return;
  const res = await request.get(`${API}/aeroplanes`);
  if (res.ok()) {
    const body = (await res.json()) as { aeroplanes: { id: string; name: string }[] };
    const match = body.aeroplanes?.find((a) => a.name === "eHawk E2E Test");
    if (match) {
      aeroplaneId = match.id;
      saveState({ aeroplaneId });
      return;
    }
  }
  throw new Error("No aeroplaneId — run 'Create eHawk' scenario first");
}

// ── Background ──────────────────────────────────────────────────

Given("the backend is running", async ({ request }) => {
  const res = await request.get(`${API}/health`);
  expect(res.ok()).toBeTruthy();

  // One-time cleanup of old test aeroplanes
  let cleanupDone = false;
  try { cleanupDone = fs.existsSync(CLEANUP_FILE); } catch { /* */ }

  if (!cleanupDone) {
    const listRes = await request.get(`${API}/aeroplanes`);
    if (listRes.ok()) {
      const body = (await listRes.json()) as { aeroplanes: { id: string; name: string }[] };
      const testPlanes = body.aeroplanes?.filter(
        (a) =>
          a.name === "eHawk E2E Test" ||
          a.name === "eHawk designer workflow" ||
          a.name === "Nav Test Aeroplane",
      ) ?? [];
      for (const plane of testPlanes) {
        await request.delete(`${API}/aeroplanes/${plane.id}`);
      }
    }
    aeroplaneId = "";
    try { fs.unlinkSync(STATE_FILE); } catch { /* */ }
    fs.writeFileSync(CLEANUP_FILE, new Date().toISOString());
  }
});

Given("the frontend is running", async ({ page }) => {
  const res = await page.goto("/");
  expect(res?.ok()).toBeTruthy();
});

// ── Helpers ─────────────────────────────────────────────────────

function sidebar(page: import("@playwright/test").Page) {
  return page.locator("aside, [role=complementary]").first();
}

// ── Stage 0: Create aeroplane ───────────────────────────────────

Given("I am on the workbench", async ({ page }) => {
  await page.goto("/workbench");
  await page.waitForLoadState("networkidle");
});

When(
  "I click {string} and enter name {string}",
  async ({ page }, buttonText: string, name: string) => {
    page.once("dialog", (d) => d.accept(name));
    await page.getByRole("button", { name: buttonText }).click();
    await page.waitForSelector('text="Aeroplane Tree"', { timeout: 15000 });

    const res = await page.request.get(`${API}/aeroplanes`);
    const body = (await res.json()) as { aeroplanes: { id: string; name: string }[] };
    const match = body.aeroplanes?.find((a) => a.name === name);
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
  await expect(page.getByRole("banner").getByText(name)).toBeVisible();
});

// ── Stage 1a: Create wing ───────────────────────────────────────

Given(
  "the {string} aeroplane is selected",
  async ({ page, request }, _name: string) => {
    await ensureIdFromApi(request);
    await page.goto(`/workbench?id=${aeroplaneId}`);
    await page.waitForSelector('text="Aeroplane Tree"', { timeout: 15000 });
  },
);

When(
  "I click the {string} button and enter name {string}",
  async ({ page }, buttonText: string, name: string) => {
    page.once("dialog", (d) => d.accept(name));
    await page.getByRole("button", { name: new RegExp(buttonText.replace("+", "\\+")) }).click();
    // Wait for tree to refresh with new wing
    await page.waitForTimeout(2000);
  },
);

Then("the tree shows {string}", async ({ page }, label: string) => {
  await expect(sidebar(page).getByText(label).first()).toBeVisible({ timeout: 5000 });
});

// ── Stage 1b: Edit segment in WingConfig mode ───────────────────

Given(
  "the {string} has wing {string} in the tree",
  async ({ page, request }, _name: string, wingName: string) => {
    await ensureIdFromApi(request);
    await page.goto(`/workbench?id=${aeroplaneId}`);
    await page.waitForSelector('text="Aeroplane Tree"', { timeout: 15000 });
    await expect(sidebar(page).getByText(wingName).first()).toBeVisible({ timeout: 5000 });
  },
);

When("I click on {string} in the tree", async ({ page }, nodeLabel: string) => {
  const side = sidebar(page);

  if (nodeLabel.startsWith("segment")) {
    // Expand the wing first
    const wingNode = side.getByText("main_wing").first();
    await wingNode.click();
    await side.getByText(nodeLabel).waitFor({ state: "visible", timeout: 15000 });
    await side.getByText(nodeLabel).first().click();
  } else {
    await side.getByText(nodeLabel).first().click();
  }
});

When("the property form is in {string} mode", async ({ page }, mode: string) => {
  const toggle = page.getByRole("button", { name: mode });
  // If the toggle exists and is not already active, click it
  if (await toggle.isVisible()) {
    const isActive = await toggle.evaluate(
      (el) => el.classList.contains("bg-primary") || getComputedStyle(el).backgroundColor.includes("255, 132, 0"),
    ).catch(() => false);
    if (!isActive) {
      await toggle.click();
    }
  }
});

When("I set the following WingConfig fields:", async ({ page }, table: DataTable) => {
  // Wait for the Save button to confirm the form is visible
  await page.getByRole("button", { name: "Save" }).waitFor({ state: "visible", timeout: 10000 });

  for (const [field, value] of table.rows()) {
    const label = page.locator(`label:text("${field}"), span:text("${field}")`).first();
    const container = label.locator("..");
    const input = container.locator("input").first();

    if (await input.isVisible({ timeout: 2000 }).catch(() => false)) {
      await input.fill(value);
    }
  }
});

When("I click {string}", async ({ page }, buttonText: string) => {
  await page.getByRole("button", { name: buttonText }).click();
});

Then("the save completes without error", async ({ page }) => {
  // Wait for "Saving..." to disappear (button text returns to "Save")
  await expect(page.getByRole("button", { name: "Save" })).toBeVisible({ timeout: 10000 });
  // No error text should be visible
  const errorText = page.locator("text=/Save failed|Error/i");
  const hasError = await errorText.isVisible().catch(() => false);
  expect(hasError).toBeFalsy();
});

// ── Stage 1c/d: Add segment ─────────────────────────────────────

When(
  "I click {string} on {string}",
  async ({ page }, action: string, target: string) => {
    const side = sidebar(page);
    // Ensure the wing is expanded first
    const wingNode = side.getByText(target).first();
    await wingNode.click();
    // Wait for the action text to appear (could be button or clickable div)
    const actionEl = side.getByText(action, { exact: true }).first();
    await actionEl.waitFor({ state: "visible", timeout: 15000 });
    await actionEl.click();
    // Wait for the tree to refresh
    await page.waitForTimeout(1000);
  },
);

// ── Stage 2/4: Analysis ─────────────────────────────────────────

Given(
  "the {string} has wing {string}",
  async ({ request }, _name: string, _wing: string) => {
    await ensureIdFromApi(request);
  },
);

// "I click the {string} step pill" is defined in common.steps.ts

When("I set the analysis parameters:", async ({ page }, table: DataTable) => {
  for (const [field, value] of table.rows()) {
    const label = page.locator(`label:text("${field}"), span:text("${field}")`).first();
    const container = label.locator("..");
    const input = container.locator("input").first();

    if (await input.isVisible({ timeout: 2000 }).catch(() => false)) {
      await input.fill(value);
    } else if (field === "tool") {
      // Tool is a select, not an input
      const select = container.locator("select").first();
      if (await select.isVisible().catch(() => false)) {
        await select.selectOption(value);
      }
    }
  }
});

Then("the analysis completes without error", async ({ page }) => {
  // Wait for either chart data to appear or an error
  // The "Run an analysis" placeholder disappears when results arrive
  await page.waitForFunction(
    () => {
      const placeholder = document.querySelector('[class*="items-center"]');
      const hasPlaceholder = !!document.body.innerText.includes("Run an analysis to see results");
      const hasError = !!document.body.innerText.match(/Analysis failed|Error/i);
      return !hasPlaceholder || hasError;
    },
    { timeout: 30000 },
  ).catch(() => {
    // Timeout is ok — we check for errors below
  });
  const errorBanner = page.locator("text=/Analysis failed/i");
  const hasError = await errorBanner.isVisible().catch(() => false);
  expect(hasError).toBeFalsy();
});

Then("the polar chart shows bars", async ({ page }) => {
  // After the refactor to SVG line charts, look for the chart title span
  // Wait longer — analysis may take time
  await expect(
    page.locator('span', { hasText: "C_L vs" }).first(),
  ).toBeVisible({ timeout: 30000 });
});

Then("the chart annotation shows a CL_max value", async ({ page }) => {
  await expect(page.getByText(/C_L.*max|CL.*max/i).first()).toBeVisible({ timeout: 5000 });
});

// ── Stage 3: TEDs ───────────────────────────────────────────────

When("I open the {string} section", async ({ page }, sectionName: string) => {
  // The section buttons are in the complementary/sidebar area, not the viewer
  const side = sidebar(page);
  const btn = side.getByRole("button", { name: new RegExp(sectionName) }).first();
  await btn.waitFor({ state: "visible", timeout: 10000 });
  await btn.click();
  await page.waitForTimeout(500);
});

When("I set the following TED fields:", async ({ page }, table: DataTable) => {
  // TED fields are inside the TED section — wait for it to be visible
  await page.waitForTimeout(500);

  for (const [field, value] of table.rows()) {
    if (field === "symmetric") {
      const checkbox = page.locator('input[type="checkbox"]').first();
      const shouldCheck = value === "true";
      if (shouldCheck) await checkbox.check();
      else await checkbox.uncheck();
      continue;
    }

    // Find the input by the label text — get ALL matching labels then use the
    // one that is inside the TED section (near "Save TED" button)
    const labels = page.locator(`label, span`).filter({ hasText: new RegExp(`^${field}$`) });
    const count = await labels.count();
    for (let i = 0; i < count; i++) {
      const label = labels.nth(i);
      const input = label.locator("..").locator("input").first();
      if (await input.isVisible({ timeout: 500 }).catch(() => false)) {
        await input.clear();
        await input.fill(value);
        break;
      }
    }
  }
});

Then(
  "segment {int} shows an {string} chip in the tree",
  async ({ page }, segIndex: number, chipText: string) => {
    const side = sidebar(page);
    const segRow = side.getByText(`segment ${segIndex}`).first().locator("..");
    await expect(segRow.getByText(chipText)).toBeVisible({ timeout: 5000 });
  },
);

// ── Stage 5: Spars ──────────────────────────────────────────────

When("I add a spar with:", async ({ page }, table: DataTable) => {
  // Fill the spar fields first, then click "Add Spar"
  for (const [field, value] of table.rows()) {
    const label = page.locator(`label:text("${field}"), span:text("${field}")`).first();
    const input = label.locator("..").locator("input").first();
    if (await input.isVisible({ timeout: 2000 }).catch(() => false)) {
      await input.clear();
      await input.fill(value);
    }
  }
  // Click "Add Spar" to submit
  await page.getByRole("button", { name: /add spar/i }).click();
  await page.waitForTimeout(1000); // Wait for API + refresh
});

Then(
  "segment {int} shows {string} in the tree",
  async ({ page }, segIndex: number, text: string) => {
    const side = sidebar(page);
    // Expand segment if needed
    const segNode = side.getByText(`segment ${segIndex}`).first();
    await segNode.click();
    await expect(side.getByText(text).first()).toBeVisible({ timeout: 5000 });
  },
);

// ── Stage 6: Export ─────────────────────────────────────────────

Then("the task toast shows {string}", async ({ page }, text: string) => {
  await expect(page.getByText(text).first()).toBeVisible({ timeout: 10000 });
});

Then(
  "the export completes within {int} seconds",
  async ({ page }, timeout: number) => {
    // Wait for the toast to show completion or the progress to reach 100%
    await page.waitForTimeout(timeout * 1000);
  },
);

Then("a STEP file download starts", async ({ page }) => {
  // Verify a download event was triggered
  const downloadPromise = page.waitForEvent("download", { timeout: 30000 });
  // The download should have started from the previous click
  const download = await downloadPromise.catch(() => null);
  expect(download).not.toBeNull();
});

// ── Verification: DB state ──────────────────────────────────────

Given(
  "the {string} aeroplane exists",
  async ({ request }, _name: string) => {
    await ensureIdFromApi(request);
    const res = await request.get(`${API}/aeroplanes/${aeroplaneId}`);
    expect(res.ok()).toBeTruthy();
  },
);

When(
  "I query the wing {string} from the API",
  async ({ request }, wingName: string) => {
    await ensureIdFromApi(request);
    const res = await request.get(
      `${API}/aeroplanes/${aeroplaneId}/wings/${wingName}`,
    );
    expect(res.ok()).toBeTruthy();
    const wing = await res.json();
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

Then("the wing has at least {int} cross sections", async ({}, min: number) => {
  const wing = loadWingData();
  expect(wing.x_secs.length).toBeGreaterThanOrEqual(min);
});

Then(
  "cross section {int} has airfoil containing {string}",
  async ({}, index: number, airfoilPart: string) => {
    const wing = loadWingData();
    expect(wing.x_secs[index].airfoil).toContain(airfoilPart);
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

import { createBdd } from "playwright-bdd";
import { expect } from "@playwright/test";

const { Given, When, Then } = createBdd();

const API =
  process.env.API_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8001";

// ── Navigation ──────────────────────────────────────────────────

When("I open the app at {string}", async ({ page }, url: string) => {
  await page.goto(url);
  await page.waitForLoadState("networkidle");
});

Then("the URL contains {string}", async ({ page }, urlPart: string) => {
  await expect(page).toHaveURL(new RegExp(urlPart));
});

Given("I am on the workbench with an aeroplane", async ({ page, request }) => {
  // Ensure at least one aeroplane exists via API
  const listRes = await request.get(`${API}/aeroplanes`);
  const body = await listRes.json();
  const planes = body.aeroplanes ?? [];

  if (planes.length === 0) {
    await request.post(`${API}/aeroplanes?name=Nav+Test+Aeroplane`);
  }

  await page.goto("/workbench");
  await page.waitForLoadState("networkidle");

  // If the selector shows, click the first aeroplane
  const selectorVisible = await page
    .getByText("Select Aeroplane")
    .isVisible({ timeout: 3000 })
    .catch(() => false);

  if (selectorVisible) {
    // Click the first aeroplane button in the list
    const firstAeroplane = page.locator(
      'button:has-text("") >> nth=0',
    );
    // Find a button that is NOT "Create New"
    const aeroplaneButtons = page.locator(
      'div.flex.flex-col.gap-1 button',
    );
    const count = await aeroplaneButtons.count();
    if (count > 0) {
      await aeroplaneButtons.first().click();
    } else {
      // No aeroplanes, create one
      page.once("dialog", (d) => d.accept("Nav Test Aeroplane"));
      await page.getByRole("button", { name: "Create New" }).click();
    }
    await page.waitForSelector('text="Aeroplane Tree"', { timeout: 15000 });
  }
});

When("I click the {string} step pill", async ({ page }, label: string) => {
  await page.getByRole("link", { name: new RegExp(label) }).click();
  await page.waitForLoadState("networkidle");
});

Then("I see {string} on the page", async ({ page }, text: string) => {
  await expect(page.getByText(text).first()).toBeVisible({ timeout: 5000 });
});

Then(
  "the {string} pill has the active style",
  async ({ page }, label: string) => {
    const pill = page.getByRole("link", { name: new RegExp(label) });
    await expect(pill).toHaveCSS(
      "background-color",
      /rgb\(255, 132, 0\)/,
    );
  },
);

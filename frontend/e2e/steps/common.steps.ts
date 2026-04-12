import { createBdd } from "playwright-bdd";
import { expect } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

const { Given, When, Then } = createBdd();

const API =
  process.env.API_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8001";

const STATE_FILE = path.join(__dirname, "..", ".ehawk-state.json");

// ── Navigation ──────────────────────────────────────────────────

When("I open the app at {string}", async ({ page }, url: string) => {
  await page.goto(url);
  await page.waitForLoadState("networkidle");
});

Then("the URL contains {string}", async ({ page }, path: string) => {
  await expect(page).toHaveURL(new RegExp(path));
});

Given("I am on the workbench with an aeroplane", async ({ page }) => {
  await page.goto("/workbench");
  await page.waitForLoadState("networkidle");

  // If the selector dialog appears, create or pick an aeroplane
  const selectorVisible = await page
    .getByText("Select Aeroplane")
    .isVisible()
    .catch(() => false);

  if (selectorVisible) {
    // Check if there are existing aeroplanes to pick
    const existingButton = page
      .locator("button")
      .filter({ hasText: /^(?!.*Create)/ })
      .first();
    const hasExisting = await existingButton.isVisible().catch(() => false);

    if (hasExisting) {
      await existingButton.click();
    } else {
      page.once("dialog", async (dialog) => {
        await dialog.accept("Nav Test Aeroplane");
      });
      await page.getByRole("button", { name: "Create New" }).click();
    }
    await page.waitForSelector('text="Aeroplane Tree"', { timeout: 10000 });
  }
});

When(
  "I click the {string} step pill",
  async ({ page }, label: string) => {
    await page.getByRole("link", { name: new RegExp(label) }).click();
    await page.waitForLoadState("networkidle");
  },
);

Then("I see {string} on the page", async ({ page }, text: string) => {
  await expect(page.getByText(text).first()).toBeVisible({ timeout: 5000 });
});

Then(
  "the {string} pill has the active style",
  async ({ page }, label: string) => {
    const pill = page.getByRole("link", { name: new RegExp(label) });
    // Active pills have bg-primary class (orange background)
    await expect(pill).toHaveCSS("background-color", /rgb\(255, 132, 0\)/);
  },
);

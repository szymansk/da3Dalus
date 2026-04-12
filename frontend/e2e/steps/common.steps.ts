import { createBdd } from "playwright-bdd";
import { expect } from "@playwright/test";

const { Given, When, Then } = createBdd();

// ── Navigation ──────────────────────────────────────────────

Given("I am on the workbench", async ({ page }) => {
  await page.goto("/workbench");
  await expect(page.locator("header")).toBeVisible();
});

Given("I am on the mission page", async ({ page }) => {
  await page.goto("/workbench/mission");
  await expect(page.getByText("Mission Objectives")).toBeVisible();
});

Given("I am on the analysis page", async ({ page }) => {
  await page.goto("/workbench/analysis");
  await expect(page.getByText("Aerodynamic Analysis")).toBeVisible();
});

Given("I am on the components page", async ({ page }) => {
  await page.goto("/workbench/components");
  await expect(page.getByText("Component Library")).toBeVisible();
});

Given("I am on the weight page", async ({ page }) => {
  await page.goto("/workbench/weight");
  await expect(page.getByText("Weight Items")).toBeVisible();
});

Given("I am on {string}", async ({ page }, path: string) => {
  await page.goto(path);
});

When("I navigate to {string}", async ({ page }, path: string) => {
  await page.goto(path);
});

When("I click the {string} step pill", async ({ page }, label: string) => {
  await page.getByRole("link", { name: new RegExp(label) }).click();
});

Then("I see the {string} page", async ({ page }, heading: string) => {
  await expect(page.getByText(heading)).toBeVisible();
});

Then("I am redirected to {string}", async ({ page }, path: string) => {
  await expect(page).toHaveURL(new RegExp(path));
});

// ── UI state ────────────────────────────────────────────────

Then(
  "the {string} pill is highlighted in orange",
  async ({ page }, label: string) => {
    const pill = page.getByRole("link", { name: new RegExp(label) });
    await expect(pill).toHaveClass(/bg-primary/);
  },
);

Then("the other pills are not highlighted", async ({ page }) => {
  const inactivePills = page.locator("nav a.bg-card-muted");
  await expect(inactivePills).not.toHaveCount(0);
});

Then(
  "I see an alert banner with {string}",
  async ({ page }, text: string) => {
    await expect(page.getByText(text)).toBeVisible();
  },
);

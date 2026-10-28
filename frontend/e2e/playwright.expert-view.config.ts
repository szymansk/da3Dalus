/**
 * Standalone Playwright-BDD config for the Expert View feature (gh-1282).
 *
 * Scopes features and steps to the Expert View, so it runs without the step definitions other
 * feature files lack, and on a port of its own (the backend is stubbed in the steps).
 *
 * Run with:
 *   npx -p playwright-bdd bddgen -c e2e/playwright.expert-view.config.ts
 *   npx playwright test -c e2e/playwright.expert-view.config.ts
 *
 * Or via the package.json script:
 *   npm run test:e2e:expert-view
 */

import { defineConfig, devices } from "@playwright/test";
import { defineBddConfig } from "playwright-bdd";

const testDir = defineBddConfig({
  features: "features/expert-view.feature",
  steps: "steps/expert-view.steps.ts",
  outputDir: ".features-gen-expert-view",
});

const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000";

export default defineConfig({
  testDir,
  timeout: 60_000,
  retries: 1,
  fullyParallel: false,
  workers: 1,
  reporter: [["html", { open: "never", outputFolder: "playwright-report-expert-view" }]],
  use: {
    baseURL,
    screenshot: "only-on-failure",
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: `npm run dev -- --port ${new URL(baseURL).port || "3000"}`,
    url: baseURL,
    reuseExistingServer: true,
    env: {
      NEXT_PUBLIC_API_URL: process.env.API_URL ?? "http://localhost:8001",
    },
  },
});

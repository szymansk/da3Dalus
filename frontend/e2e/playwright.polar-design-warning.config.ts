/**
 * Standalone Playwright-BDD config for the polar-design-warning feature (gh-630).
 *
 * This config scopes both features and steps to just the polar-design-warning
 * files, avoiding the "85 missing step definitions" error caused by other
 * feature files that have Gherkin but not yet step implementations.
 *
 * Run with:
 *   npx -p playwright-bdd bddgen -c e2e/playwright.polar-design-warning.config.ts
 *   npx playwright test -c e2e/playwright.polar-design-warning.config.ts
 *
 * Or via the package.json script:
 *   npm run test:e2e:polar-warning
 */

import { defineConfig, devices } from "@playwright/test";
import { defineBddConfig } from "playwright-bdd";

const testDir = defineBddConfig({
  // Only include the polar-design-warning feature and its step file.
  features: "features/polar-design-warning.feature",
  steps: [
    "steps/polar-design-warning.steps.ts",
    // common.steps.ts is pulled in so any shared When/Then steps are available.
    "steps/common.steps.ts",
  ],
  // Output the generated spec into a subdirectory to avoid collisions.
  outputDir: ".features-gen-polar-warning",
});

export default defineConfig({
  testDir,
  timeout: 60_000,
  retries: 1,
  fullyParallel: false,
  workers: 1,
  reporter: [["html", { open: "never", outputFolder: "playwright-report-polar-warning" }]],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000",
    screenshot: "only-on-failure",
    trace: "on-first-retry",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
  webServer: {
    command: "npm run dev",
    port: parseInt(process.env.PLAYWRIGHT_BASE_URL?.split(":")[2] ?? "3000"),
    reuseExistingServer: true,
    env: {
      NEXT_PUBLIC_API_URL: process.env.API_URL ?? "http://localhost:8001",
    },
  },
});

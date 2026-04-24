/**
 * Verifies that next.config.ts sets a webpack alias to deduplicate three.js.
 *
 * The bug: three-cad-viewer bundles its own copy of three.js (e.g. 0.183.0)
 * alongside the project's top-level three (0.183.2). When the renderer from
 * one copy receives a Color object from the other, instanceof checks fail
 * and uniform3fv crashes. The fix is a webpack resolve alias that forces
 * all imports of "three" to resolve to the single top-level copy.
 */
import { describe, it, expect } from "vitest";
import path from "node:path";

describe("next.config three.js deduplication (webpack + turbopack)", () => {
  it("aliases 'three' to the top-level node_modules copy", async () => {
    // Dynamic-import the config (it's an ES module with default export)
    const mod = await import("../next.config");
    const config = mod.default;

    // The config must have a webpack function
    expect(config.webpack).toBeDefined();
    expect(typeof config.webpack).toBe("function");

    // Simulate calling the webpack function with a minimal config object
    const fakeWebpackConfig = {
      resolve: {
        alias: {} as Record<string, string>,
      },
    };

    const result = config.webpack!(
      fakeWebpackConfig as Parameters<NonNullable<typeof config.webpack>>[0],
      {} as Parameters<NonNullable<typeof config.webpack>>[1],
    );

    // The alias for "three" must point to the top-level node_modules/three
    const expectedPath = path.resolve("node_modules", "three");
    expect(result.resolve.alias).toHaveProperty("three");
    expect(result.resolve.alias.three).toBe(expectedPath);
  });

  it("preserves existing aliases", async () => {
    const mod = await import("../next.config");
    const config = mod.default;

    const fakeWebpackConfig = {
      resolve: {
        alias: { existing: "/some/path" } as Record<string, string>,
      },
    };

    const result = config.webpack!(
      fakeWebpackConfig as Parameters<NonNullable<typeof config.webpack>>[0],
      {} as Parameters<NonNullable<typeof config.webpack>>[1],
    );

    // Existing alias must still be present
    expect(result.resolve.alias.existing).toBe("/some/path");
    // And the three alias must also be set
    expect(result.resolve.alias).toHaveProperty("three");
  });

  it("sets turbopack.resolveAlias for three.js", async () => {
    const mod = await import("../next.config");
    const config = mod.default;

    expect(config.turbopack).toBeDefined();
    expect(config.turbopack!.resolveAlias).toBeDefined();

    const expectedPath = path.resolve("node_modules", "three");
    expect((config.turbopack!.resolveAlias as Record<string, string>).three).toBe(expectedPath);
  });
});

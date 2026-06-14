import { describe, it, expect } from "vitest";
import { STEPS } from "@/components/workbench/Header";

describe("Workbench top-level nav — Powertrain step", () => {
  it("places Powertrain as a top-level step immediately after Analysis and before Components", () => {
    const labels = STEPS.map((s) => s.label);
    const analysis = labels.indexOf("Analysis");
    const powertrain = labels.indexOf("Powertrain");
    const components = labels.indexOf("Components");

    expect(powertrain).toBeGreaterThan(-1);
    expect(powertrain).toBe(analysis + 1);
    expect(components).toBe(powertrain + 1);
  });

  it("links Powertrain to its own top-level route", () => {
    const step = STEPS.find((s) => s.label === "Powertrain");
    expect(step?.href).toBe("/workbench/powertrain");
  });

  it("numbers the steps sequentially (1..n)", () => {
    STEPS.forEach((step, i) => expect(step.num).toBe(i + 1));
  });
});

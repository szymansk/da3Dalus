import { describe, it, expectTypeOf } from "vitest";
import type {
  TrimEnrichment,
  ControlEffectiveness,
  StabilityClassification,
  MixerValues,
} from "@/hooks/useOperatingPoints";

describe("TrimEnrichment type", () => {
  it("includes all enrichment fields", () => {
    expectTypeOf<TrimEnrichment>().toHaveProperty("analysis_goal");
    expectTypeOf<TrimEnrichment>().toHaveProperty("result_summary");
    expectTypeOf<TrimEnrichment>().toHaveProperty("trim_method");
    expectTypeOf<TrimEnrichment>().toHaveProperty("trim_score");
    expectTypeOf<TrimEnrichment>().toHaveProperty("trim_residuals");
    expectTypeOf<TrimEnrichment>().toHaveProperty("deflection_reserves");
    expectTypeOf<TrimEnrichment>().toHaveProperty("design_warnings");
    expectTypeOf<TrimEnrichment>().toHaveProperty("effectiveness");
    expectTypeOf<TrimEnrichment>().toHaveProperty("stability_classification");
    expectTypeOf<TrimEnrichment>().toHaveProperty("mixer_values");
    expectTypeOf<TrimEnrichment>().toHaveProperty("aero_coefficients");
  });
});

describe("ControlEffectiveness type", () => {
  it("has required fields", () => {
    expectTypeOf<ControlEffectiveness>().toHaveProperty("derivative");
    expectTypeOf<ControlEffectiveness>().toHaveProperty("coefficient");
    expectTypeOf<ControlEffectiveness>().toHaveProperty("surface");
  });
});

describe("StabilityClassification type", () => {
  it("has required fields", () => {
    expectTypeOf<StabilityClassification>().toHaveProperty("is_statically_stable");
    expectTypeOf<StabilityClassification>().toHaveProperty("overall_class");
    expectTypeOf<StabilityClassification>().toHaveProperty("static_margin");
  });
});

describe("MixerValues type", () => {
  it("has required fields", () => {
    expectTypeOf<MixerValues>().toHaveProperty("symmetric_offset");
    expectTypeOf<MixerValues>().toHaveProperty("differential_throw");
    expectTypeOf<MixerValues>().toHaveProperty("role");
  });
});

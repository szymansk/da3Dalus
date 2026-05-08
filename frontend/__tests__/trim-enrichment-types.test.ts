import { describe, it, expect } from "vitest";
import type {
  TrimEnrichment,
  DeflectionReserve,
  DesignWarning,
} from "@/hooks/useOperatingPoints";

describe("TrimEnrichment types", () => {
  it("TrimEnrichment satisfies the shape", () => {
    const enrichment: TrimEnrichment = {
      analysis_goal: "Can the aircraft trim near stall?",
      trim_method: "opti",
      trim_score: 0.02,
      trim_residuals: { cm: 0.001, cy: 0.0 },
      deflection_reserves: {
        "[elevator]Elevator": {
          deflection_deg: -5.0,
          max_pos_deg: 25.0,
          max_neg_deg: 25.0,
          usage_fraction: 0.2,
        },
      },
      design_warnings: [],
    };
    expect(enrichment.analysis_goal).toBe("Can the aircraft trim near stall?");
    expect(enrichment.deflection_reserves["[elevator]Elevator"].usage_fraction).toBe(0.2);
  });

  it("DeflectionReserve type works standalone", () => {
    const r: DeflectionReserve = {
      deflection_deg: -5,
      max_pos_deg: 25,
      max_neg_deg: 25,
      usage_fraction: 0.2,
    };
    expect(r.usage_fraction).toBe(0.2);
  });

  it("DesignWarning type works standalone", () => {
    const w: DesignWarning = {
      level: "warning",
      category: "authority",
      surface: "[elevator]Elevator",
      message: "85% authority used",
    };
    expect(w.level).toBe("warning");
  });
});

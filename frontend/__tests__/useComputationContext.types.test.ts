import { describe, it, expectTypeOf } from "vitest";
import type {
  ComputationContext,
  PolarRejection,
  PolarRejectionGate,
  PolarRejectionCategory,
} from "@/hooks/useComputationContext";

describe("useComputationContext types (gh-630)", () => {
  it("PolarRejection has the six gate literals", () => {
    expectTypeOf<PolarRejectionGate>().toEqualTypeOf<
      | "insufficient_points"
      | "non_monotonic_polar"
      | "negative_slope_k"
      | "non_positive_cd0"
      | "unphysical_e_oswald"
      | "cd0_stability_mismatch"
    >();
  });

  it("PolarRejection has the four category literals", () => {
    expectTypeOf<PolarRejectionCategory>().toEqualTypeOf<
      "sweep" | "data" | "design" | "consistency"
    >();
  });

  it("PolarRejection shape matches the backend schema", () => {
    expectTypeOf<PolarRejection>().toMatchTypeOf<{
      gate: PolarRejectionGate;
      category: PolarRejectionCategory;
      fitted_value: number | null;
      threshold: string;
      hint: string;
    }>();
  });

  it("ComputationContext.polar_by_config carries optional rejection per config", () => {
    expectTypeOf<ComputationContext["polar_by_config"]>().toMatchTypeOf<
      | {
          clean: { rejection: PolarRejection | null };
          takeoff: { rejection: PolarRejection | null };
          landing: { rejection: PolarRejection | null };
        }
      | undefined
    >();
  });
});

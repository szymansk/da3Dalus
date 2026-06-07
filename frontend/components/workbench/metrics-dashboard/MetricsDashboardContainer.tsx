"use client";

// gh-881: Live container that wires the MetricsDashboard presentational component
// to real data from useComputationContext, useTailSizing and useEndurance.
//
// Reads aeroplaneId from AeroplaneContext (same pattern as InfoChipRow).
// Runs all five adapter functions and passes the results as props.

import { useAeroplaneContext } from "@/components/workbench/AeroplaneContext";
import { useComputationContext } from "@/hooks/useComputationContext";
import { useTailSizing } from "@/hooks/useTailSizing";
import { useEndurance } from "@/hooks/useEndurance";
import { useDesignAssumptions } from "@/hooks/useDesignAssumptions";
import {
  toSpeedData,
  toGeometryItems,
  toBalanceData,
  toQualityGauges,
  toQualityRaw,
  toTail,
  toPowertrainItems,
  toPMarginGauge,
} from "@/lib/metricsAdapters";
import { MetricsDashboard } from "./MetricsDashboard";

export function MetricsDashboardContainer() {
  const { aeroplaneId } = useAeroplaneContext();

  const { data: ctx, isLoading: ctxLoading } = useComputationContext(aeroplaneId);
  const { data: tailSizing, isLoading: tailLoading } = useTailSizing(aeroplaneId);
  const { data: endurance, isLoading: enduranceLoading } = useEndurance(aeroplaneId);
  // gh-889: fetch design assumptions to get the component/calculated CG (cg_x)
  // as a fallback when cg_agg_m is null (i.e., not yet aerodynamically balanced).
  const { data: assumptionsData, isLoading: assumptionsLoading } = useDesignAssumptions(aeroplaneId);

  // No aeroplane selected → render empty state
  if (!aeroplaneId) {
    return <MetricsDashboard
      speed={null}
      geometryItems={[]}
      balance={null}
      qualityGauges={[]}
      qualityRaw={[]}
      tail={null}
      powertrain={{ items: [], detail: { pReqVmd: null, pReqVminSink: null, pMarginClass: null, batteryMassPredicted: null, confidence: "estimated" } }}
      empty
    />;
  }

  const loading = ctxLoading || tailLoading || enduranceLoading || assumptionsLoading;

  // gh-889: derive component/calculated CG from design assumptions (same pattern
  // as analysis/page.tsx derives designCgX).  This is the cg_x assumption's
  // effective_value (metres), which may be either a user estimate or a value
  // calculated from the component tree.
  const cgComponentM =
    assumptionsData?.assumptions.find((a) => a.parameter_name === "cg_x")
      ?.effective_value ?? undefined;

  // Adapter calls — pure transforms, safe to call with null inputs
  const speed = toSpeedData(ctx);
  const geometryItems = toGeometryItems(ctx);
  // Pass cgComponentM as the fallback CG for when cg_agg_m is null.
  const balance = toBalanceData(ctx, cgComponentM);

  // Quality gauges: base from ctx, then append P_margin from endurance
  const baseGauges = toQualityGauges(ctx);
  const pMarginGauge = toPMarginGauge(endurance);
  const qualityGauges = pMarginGauge != null
    ? [...baseGauges, pMarginGauge]
    : baseGauges;

  const qualityRaw = toQualityRaw(ctx);
  const tail = toTail(tailSizing, ctx);
  const powertrain = toPowertrainItems(endurance);

  return (
    <MetricsDashboard
      speed={speed}
      geometryItems={geometryItems}
      balance={balance}
      qualityGauges={qualityGauges}
      qualityRaw={qualityRaw}
      tail={tail}
      powertrain={powertrain}
      loading={loading}
    />
  );
}

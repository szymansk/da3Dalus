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

  const loading = ctxLoading || tailLoading || enduranceLoading;

  // Adapter calls — pure transforms, safe to call with null inputs
  const speed = toSpeedData(ctx);
  const geometryItems = toGeometryItems(ctx);
  const balance = toBalanceData(ctx);

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

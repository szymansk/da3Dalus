// Shared type definitions for the metrics dashboard.
// Extracted from metricsMock.ts so app code (MetricsDashboard, primitives,
// metricsAdapters) can import types without pulling in mock data.

export type SectionState = "collapsed" | "compact" | "large";

export type Quality = "good" | "caution" | "bad";

export interface SpeedMarker {
  readonly symbol: string;
  readonly label: string;
  readonly value: number; // m/s
  readonly aoa?: number; // deg, where available
  readonly kind: "stall" | "normal" | "caution" | "ne"; // drives zone colour
}

export interface SpeedData {
  readonly markers: readonly SpeedMarker[];
  readonly wMin: number; // min sink rate, m/s
  readonly isGlider: boolean;
}

export interface BalanceData {
  readonly cg: number; // m
  readonly np: number; // m
  readonly macStart: number; // m, LE of MAC
  readonly macLength: number; // m
  readonly smPercent: number; // % MAC
  readonly targetSmMin: number;
  readonly targetSmMax: number;
  readonly cgComponent?: number; // component-derived CG, m
}

export interface GaugeZone {
  readonly from: number;
  readonly to: number;
  readonly quality: Quality; // good / caution / bad → green / amber / red
}

export interface GaugeData {
  readonly symbol: string;
  readonly label: string;
  readonly value: number;
  readonly unit?: string;
  readonly min: number;
  readonly max: number;
  readonly zones: readonly GaugeZone[]; // traffic-light scale, must span [min, max]
  readonly quality: Quality; // quality of the current value (matches its zone)
  readonly description: string;
  readonly format?: (v: number) => string;
}

export interface MetricItem {
  readonly symbol: string;
  readonly label: string;
  readonly value: string;
  readonly unit?: string;
  readonly description: string;
}

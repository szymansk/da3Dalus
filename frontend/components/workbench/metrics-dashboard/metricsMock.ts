// Click-dummy (#881): hardcoded representative data for the metrics dashboard.
// No backend wiring — every value here is fake but plausible for a small electric glider.

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

// ── Speed envelope ──────────────────────────────────────────────
export const speedMock: SpeedData = {
  isGlider: false,
  wMin: 0.55,
  markers: [
    { symbol: "V_stall", label: "Stall", value: 8.2, aoa: 4.1, kind: "stall" },
    { symbol: "V_min_sink", label: "Min sink", value: 9.1, aoa: 5.0, kind: "normal" },
    { symbol: "V_md", label: "Min drag (L/D)", value: 11.0, aoa: 2.3, kind: "normal" },
    { symbol: "V_cruise", label: "Cruise", value: 14.0, kind: "normal" },
    { symbol: "V_x", label: "Best climb angle", value: 12.5, kind: "normal" },
    { symbol: "V_y", label: "Best climb rate", value: 13.5, kind: "normal" },
    { symbol: "V_a", label: "Manoeuvring", value: 17.5, kind: "caution" },
    { symbol: "V_max", label: "Max operating", value: 22.0, kind: "caution" },
    { symbol: "V_dive", label: "Never exceed", value: 30.8, kind: "ne" },
  ],
};

// ── Balance ─────────────────────────────────────────────────────
export const balanceMock: BalanceData = {
  cg: 0.132,
  np: 0.143,
  macStart: 0.06,
  macLength: 0.135,
  smPercent: 8.1,
  targetSmMin: 5,
  targetSmMax: 15,
  cgComponent: 0.129,
};

// ── Güte / quality gauges ───────────────────────────────────────
export const gueteMock: readonly GaugeData[] = [
  {
    symbol: "(L/D)_max", label: "Max glide ratio", value: 21.0, min: 5, max: 35, quality: "good",
    zones: [{ from: 5, to: 12, quality: "bad" }, { from: 12, to: 18, quality: "caution" }, { from: 18, to: 35, quality: "good" }],
    description: "Best lift-to-drag ratio — the headline efficiency number.",
    format: (v) => v.toFixed(1),
  },
  {
    symbol: "e", label: "Oswald efficiency", value: 0.79, min: 0.5, max: 1.0, quality: "good",
    zones: [{ from: 0.5, to: 0.7, quality: "bad" }, { from: 0.7, to: 0.78, quality: "caution" }, { from: 0.78, to: 0.95, quality: "good" }, { from: 0.95, to: 1.0, quality: "caution" }],
    description: "Span efficiency factor from the Trefftz-plane analysis.",
    format: (v) => v.toFixed(2),
  },
  {
    symbol: "ρ", label: "Polar health", value: 0.70, min: 0, max: 1, quality: "caution",
    zones: [{ from: 0, to: 0.5, quality: "bad" }, { from: 0.5, to: 0.75, quality: "caution" }, { from: 0.75, to: 1, quality: "good" }],
    description: "(C_L,md / C_L,max)² — how much margin to stall at best glide.",
    format: (v) => v.toFixed(2),
  },
  {
    symbol: "SM", label: "Static margin", value: 8.1, min: -5, max: 25, quality: "good",
    zones: [{ from: -5, to: 3, quality: "bad" }, { from: 3, to: 5, quality: "caution" }, { from: 5, to: 15, quality: "good" }, { from: 15, to: 20, quality: "caution" }, { from: 20, to: 25, quality: "bad" }],
    description: "Longitudinal stability margin as % of MAC — too low is unstable, too high is sluggish.",
    format: (v) => `${v.toFixed(1)}%`,
  },
  {
    symbol: "L_land", label: "Landing field", value: 24, min: 0, max: 60, quality: "good",
    zones: [{ from: 0, to: 35, quality: "good" }, { from: 35, to: 60, quality: "bad" }],
    description: "Required landing field length vs. available 35 m.",
    format: (v) => `${v.toFixed(0)} m ✓`,
  },
  {
    symbol: "P_margin", label: "Motor reserve", value: 0.18, min: -0.3, max: 0.6, quality: "caution",
    zones: [{ from: -0.3, to: 0, quality: "bad" }, { from: 0, to: 0.2, quality: "caution" }, { from: 0.2, to: 0.6, quality: "good" }],
    description: "(P_motor − P_req@V_md) / P_motor — 'feasible but tight'.",
    format: (v) => `${(v * 100).toFixed(0)}%`,
  },
];

// raw polar numbers shown inline in the large state
export const gueteRawMock: readonly MetricItem[] = [
  { symbol: "Re", label: "Reynolds (cruise)", value: "2.3e5", description: "MAC-based Reynolds number at cruise." },
  { symbol: "C_D0", label: "Zero-lift drag", value: "0.0158", description: "Parasite drag coefficient." },
  { symbol: "k", label: "Induced factor", value: "0.0357", description: "k = 1/(π·e·AR)." },
  { symbol: "C_L_max", label: "Max lift", value: "1.18", description: "Max lift coefficient (AeroBuildup)." },
  { symbol: "C_L_md", label: "C_L best glide", value: "0.62", description: "Lift coefficient at best L/D." },
];

// ── Geometry ────────────────────────────────────────────────────
export const geometryMock: readonly MetricItem[] = [
  { symbol: "S_ref", label: "Reference area", value: "0.200", unit: "m²", description: "Wing reference area." },
  { symbol: "MAC", label: "Mean aero chord", value: "0.135", unit: "m", description: "Reference chord for pitching moment." },
  { symbol: "B_ref", label: "Reference span", value: "1.500", unit: "m", description: "Wing span." },
  { symbol: "AR", label: "Aspect ratio", value: "11.3", description: "Span² / area — higher ⇒ less induced drag." },
];

// ── Antrieb / powertrain ────────────────────────────────────────
export const antriebMock: readonly MetricItem[] = [
  { symbol: "Battery", label: "Battery pack", value: "3S · 2200", unit: "mAh", description: "LiPo configuration and capacity." },
  { symbol: "Endurance", label: "Endurance (min-sink)", value: "42", unit: "min", description: "Max endurance at V_min_sink." },
  { symbol: "Range", label: "Range (V_md)", value: "38", unit: "km", description: "Max range at min-drag speed." },
  { symbol: "P/W", label: "Power-to-weight", value: "4.1", unit: "W/N", description: "Continuous motor power per unit weight." },
];

export const antriebDetailMock = {
  pReqVmd: 24.5, // W
  pReqVminSink: 19.8, // W
  pMarginClass: "feasible but tight",
  batteryMassPredicted: 188, // g
  confidence: "estimated" as const,
  warnings: ["e_oswald fallback used — polar fit quality is moderate."],
};

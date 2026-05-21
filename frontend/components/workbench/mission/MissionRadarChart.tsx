"use client";

import React, { useState } from "react";
import type { MissionKpiSet } from "@/hooks/useMissionKpis";
import type { MissionPreset, AxisName } from "@/hooks/useMissionPresets";
import {
  AXES,
  AXIS_UNITS,
  computeAxisRanges,
  normalizedToRaw,
  polarToCartesian,
  renormalise,
} from "@/lib/missionScale";

interface Props {
  readonly kpis: MissionKpiSet;
  readonly activeMissions: MissionPreset[]; // first is "active"; rest are ghosts
  readonly onAxisClick: (axis: AxisName) => void;
}

const R = 80; // base radius — 1.0 = R
const GHOST_COLORS = ["#66ccff", "#ff8888", "#a0e7a0", "#ffd966"];

const AXIS_LABELS: Record<AxisName, string> = {
  stall_safety: "Stall Safety",
  glide: "Glide",
  climb: "Climb",
  cruise: "Cruise",
  maneuver: "Maneuver",
  wing_loading: "W/S",
  field_friendliness: "Field",
};

const badgeColor = (p: "computed" | "estimated" | "missing"): string => {
  if (p === "computed") return "#22dd66";
  if (p === "estimated") return "#f0c75e";
  return "#555";
};

const toPointsAttr = (pts: { x: number; y: number }[]): string =>
  pts.map((p) => `${p.x},${p.y}`).join(" ");

const fmt = (n: number): string =>
  Math.abs(n) >= 100 ? n.toFixed(0) : n.toFixed(2);

/**
 * Quadrant-aware placement helper for the axis hover tooltip (gh-609).
 *
 * The tooltip foreignObject is anchored near the axis-label coordinate. To
 * prevent the box from being clipped at the SVG viewport edges, we choose
 * which corner of the box sits at the anchor based on the axis quadrant:
 *
 *   - cos(angle) > 0 → axis on the right half → grow leftward (right-anchored).
 *   - sin(angle) > 0 → axis below center  → grow upward   (bottom-anchored).
 *
 * The small `dx` / `dy` offsets nudge the box away from the label so it
 * doesn't visually overlap.
 *
 * @param axisIndex zero-based axis index.
 * @param n total number of axes (7 here, but generic).
 */
export function tooltipAnchor(
  axisIndex: number,
  n: number,
): {
  dx: number;
  dy: number;
  xAlign: "left" | "right";
  yAlign: "top" | "bottom";
} {
  const angle = (2 * Math.PI * axisIndex) / n - Math.PI / 2;
  const cos = Math.cos(angle);
  const sin = Math.sin(angle);
  // cos > 0  → right half → box extends LEFT  → small leftward nudge
  // cos < 0  → left half  → box extends RIGHT → small rightward nudge
  let dx = 0;
  if (cos > 0.2) dx = -8;
  else if (cos < -0.2) dx = 8;
  // sin > 0  → bottom half (SVG-y is inverted) → box extends UP
  // sin < 0  → top half → box extends DOWN
  let dy = 0;
  if (sin > 0.2) dy = -8;
  else if (sin < -0.2) dy = 8;
  return {
    dx,
    dy,
    xAlign: cos > 0.2 ? "right" : "left",
    yAlign: sin > 0.2 ? "bottom" : "top",
  };
}

/** SVG path for the radial hit-wedge at axis index `i` (out of N). */
function wedgePath(i: number, n: number, outerRadius: number): string {
  const half = Math.PI / n; // half of the angular slice
  const center = (Math.PI * 2 * i) / n - Math.PI / 2;
  const a0 = center - half;
  const a1 = center + half;
  const x0 = Math.cos(a0) * outerRadius;
  const y0 = Math.sin(a0) * outerRadius;
  const x1 = Math.cos(a1) * outerRadius;
  const y1 = Math.sin(a1) * outerRadius;
  // sweep = 1 (clockwise in SVG); large-arc = 0 since slice < 180°
  return `M 0 0 L ${x0} ${y0} A ${outerRadius} ${outerRadius} 0 0 1 ${x1} ${y1} Z`;
}

export function MissionRadarChart({
  kpis,
  activeMissions,
  onAxisClick,
}: Props) {
  const [hoveredAxis, setHoveredAxis] = useState<AxisName | null>(null);
  // Pass the Ist kpis in so axis ranges include the aircraft's actual
  // values; this prevents the orange polygon collapsing to the chart
  // center when the active mission's `axis_ranges` are narrower than
  // the aircraft's KPI band (gh-601).
  const globalRanges = computeAxisRanges(activeMissions, kpis);

  const istPoints = AXES.map((axis, i) => {
    const k = kpis.ist_polygon[axis];
    const local: [number, number] = [k.range_min, k.range_max];
    const score = k.score_0_1 ?? 0;
    const global = renormalise(score, local, globalRanges[axis]);
    return polarToCartesian(i, global, R);
  });

  const [active, ...ghosts] = activeMissions;

  const sollPoints = active
    ? AXES.map((axis, i) => {
        const localScore = active.target_polygon[axis];
        const local = active.axis_ranges[axis];
        const global = renormalise(localScore, local, globalRanges[axis]);
        return polarToCartesian(i, global, R);
      })
    : null;

  const ghostPolygons = ghosts.map((g) =>
    AXES.map((axis, i) => {
      const score = g.target_polygon[axis];
      const local = g.axis_ranges[axis];
      const global = renormalise(score, local, globalRanges[axis]);
      return polarToCartesian(i, global, R);
    }),
  );

  return (
    <svg
      viewBox="-150 -150 300 300"
      className="w-full max-w-[360px] aspect-square mx-auto"
    >
      {/* Outer dashed neighbour ring at 1.3 × R */}
      <polygon
        className="radar-grid-outer"
        fill="none"
        stroke="#1f1f1f"
        strokeWidth="0.4"
        strokeDasharray="3 3"
        points={toPointsAttr(
          AXES.map((_, i) => polarToCartesian(i, 1.3, R)),
        )}
      />

      {/* Concentric grid rings */}
      {[0.33, 0.66, 1].map((ring) => (
        <polygon
          key={ring}
          className="radar-grid"
          fill="none"
          stroke="#2a2a2a"
          strokeWidth="0.6"
          points={toPointsAttr(
            AXES.map((_, i) => polarToCartesian(i, ring, R)),
          )}
        />
      ))}

      {/* Axes (spokes + dashed extensions to outer ring) */}
      {AXES.map((axis, i) => {
        const tip = polarToCartesian(i, 1, R);
        const tipOuter = polarToCartesian(i, 1.3, R);
        return (
          <g key={axis}>
            <line
              x1={0}
              y1={0}
              x2={tip.x}
              y2={tip.y}
              stroke="#444"
              strokeWidth="0.6"
            />
            <line
              x1={tip.x}
              y1={tip.y}
              x2={tipOuter.x}
              y2={tipOuter.y}
              stroke="#444"
              strokeWidth="0.4"
              strokeDasharray="2 2"
            />
          </g>
        );
      })}

      {/* Ghost polygons (additional active missions) */}
      {ghostPolygons.map((pts, idx) => {
        const color = GHOST_COLORS[idx % GHOST_COLORS.length];
        return (
          <polygon
            key={ghosts[idx].id}
            className="radar-ghost"
            fill={`${color}1a`}
            stroke={color}
            strokeWidth="0.9"
            strokeDasharray="2 2"
            points={toPointsAttr(pts)}
          />
        );
      })}

      {/* Soll (active mission target) */}
      {sollPoints && (
        <polygon
          className="radar-soll"
          fill="none"
          stroke="#fff"
          strokeWidth="1.4"
          strokeDasharray="4 3"
          points={toPointsAttr(sollPoints)}
        />
      )}

      {/* Ist (current aircraft) */}
      <polygon
        className="radar-ist"
        fill="rgba(255,132,0,0.34)"
        stroke="#FF8400"
        strokeWidth="1.8"
        points={toPointsAttr(istPoints)}
      />

      {/* Ist vertex dots — transparent fill where provenance is missing */}
      {istPoints.map((p, i) => {
        const axis = AXES[i];
        const k = kpis.ist_polygon[axis];
        return (
          <circle
            key={axis}
            cx={p.x}
            cy={p.y}
            r="2.6"
            fill={k.provenance === "missing" ? "transparent" : "#FF8400"}
            stroke="#fff"
            strokeWidth="0.6"
          />
        );
      })}

      {/* Axis labels + provenance badges (clickable) */}
      {AXES.map((axis, i) => {
        const labelPos = polarToCartesian(i, 1.5, R);
        const k = kpis.ist_polygon[axis];
        return (
          <g
            key={axis}
            data-axis={axis}
            onClick={() => onAxisClick(axis)}
            style={{ cursor: "pointer" }}
          >
            <text
              x={labelPos.x}
              y={labelPos.y}
              textAnchor="middle"
              fill="#ccc"
              fontSize="10"
              fontWeight="600"
            >
              {AXIS_LABELS[axis]}
            </text>
            <circle
              cx={labelPos.x + 18}
              cy={labelPos.y - 4}
              r="2.6"
              fill={badgeColor(k.provenance)}
            />
          </g>
        );
      })}

      {/* Invisible hover wedges — one per axis. Sits on top of polygons so
          mouse events are captured. Fill is transparent but pointer-events
          are enabled. */}
      {AXES.map((axis, i) => (
        <path
          key={`wedge-${axis}`}
          data-testid={`hover-wedge-${axis}`}
          d={wedgePath(i, AXES.length, R * 1.4)}
          fill="transparent"
          stroke="none"
          style={{ pointerEvents: "all", cursor: "pointer" }}
          onMouseEnter={() => setHoveredAxis(axis)}
          onMouseLeave={() => setHoveredAxis(null)}
        />
      ))}

      {/* Hover tooltip — anchored near the hovered axis label. */}
      {hoveredAxis && (
        <AxisTooltip
          axis={hoveredAxis}
          kpis={kpis}
          active={active}
          ghosts={ghosts}
        />
      )}
    </svg>
  );
}

interface AxisTooltipProps {
  readonly axis: AxisName;
  readonly kpis: MissionKpiSet;
  readonly active: MissionPreset | undefined;
  readonly ghosts: MissionPreset[];
}

function AxisTooltip({ axis, kpis, active, ghosts }: AxisTooltipProps) {
  const i = AXES.indexOf(axis);
  const anchor = polarToCartesian(i, 1.55, R);
  const unit = AXIS_UNITS[axis];

  const k = kpis.ist_polygon[axis];
  const istValue =
    k.score_0_1 !== null
      ? normalizedToRaw(k.score_0_1, [k.range_min, k.range_max])
      : null;

  const sollValue = active
    ? normalizedToRaw(active.target_polygon[axis], active.axis_ranges[axis])
    : null;

  const ghostValues = ghosts.map((g, idx) => ({
    label: g.label,
    color: GHOST_COLORS[idx % GHOST_COLORS.length],
    value: normalizedToRaw(g.target_polygon[axis], g.axis_ranges[axis]),
  }));

  // Position the tooltip box. Width/height are estimates; we offset so the
  // tooltip stays inside the SVG viewport for all axes (gh-609).
  //
  // Anchor logic: pick the corner of the box that sits at the anchor based on
  // the axis quadrant. cos > 0 (right half) → grow leftward; sin > 0 (bottom
  // half) → grow upward. This keeps the box inside the viewBox for all 7
  // axes, including the previously-clipped Cruise (bottom-right) and W/S
  // (left) labels.
  const boxW = 150;
  const baseH = 56;
  const extraH = 14 * ghostValues.length;
  const boxH = baseH + extraH;
  const { dx, dy, xAlign, yAlign } = tooltipAnchor(i, AXES.length);
  const tx = (xAlign === "right" ? anchor.x - boxW : anchor.x) + dx;
  const ty = (yAlign === "bottom" ? anchor.y - boxH : anchor.y) + dy;
  // Grow the box from the anchor corner so transitions / hover layout feel
  // natural even though we render statically.
  const transformOrigin = `${xAlign} ${yAlign}`;

  return (
    <foreignObject
      x={tx}
      y={ty}
      width={boxW}
      height={boxH}
      style={{ pointerEvents: "none" }}
      data-testid={`axis-tooltip-${axis}`}
      data-x-align={xAlign}
      data-y-align={yAlign}
    >
      <div
        // xmlns required so React renders HTML inside foreignObject
        xmlns="http://www.w3.org/1999/xhtml"
        className="rounded border border-border bg-background/95 p-1.5 font-mono text-[10px] leading-tight text-foreground shadow-lg"
        style={{
          width: "100%",
          boxSizing: "border-box",
          textAlign: xAlign,
          transformOrigin,
        }}
      >
        <div
          data-testid={`axis-tooltip-${axis}-header`}
          className="mb-1 font-semibold text-orange-400"
        >
          {AXIS_LABELS[axis]}
          {active && (
            <span className="ml-1 font-normal text-muted-foreground">
              {" · "}
              {active.label}
            </span>
          )}
        </div>

        <div className="flex items-center justify-between gap-2">
          <span className="text-muted-foreground">Ist:</span>
          <span className="tabular-nums">
            {istValue === null ? "—" : `${fmt(istValue)} ${unit}`}
          </span>
          <span
            aria-hidden="true"
            style={{
              display: "inline-block",
              width: 6,
              height: 6,
              borderRadius: "50%",
              background: badgeColor(k.provenance),
            }}
          />
        </div>

        {active && sollValue !== null && (
          <div
            data-testid={`axis-tooltip-${axis}-soll`}
            className="flex items-center justify-between gap-2"
          >
            <span className="text-muted-foreground">Soll:</span>
            <span className="tabular-nums">
              {fmt(sollValue)} {unit}
            </span>
          </div>
        )}

        {ghostValues.map((g) => (
          <div
            key={g.label}
            className="flex items-center justify-between gap-2"
          >
            <span style={{ color: g.color }}>{g.label}:</span>
            <span className="tabular-nums">
              {fmt(g.value)} {unit}
            </span>
          </div>
        ))}
      </div>
    </foreignObject>
  );
}

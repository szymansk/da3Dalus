"use client";

import React from "react";
import type { MissionKpiSet } from "@/hooks/useMissionKpis";
import type { MissionPreset, AxisName } from "@/hooks/useMissionPresets";
import {
  AXES,
  computeAxisRanges,
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

export function MissionRadarChart({
  kpis,
  activeMissions,
  onAxisClick,
}: Props) {
  const globalRanges = computeAxisRanges(activeMissions);

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
    </svg>
  );
}

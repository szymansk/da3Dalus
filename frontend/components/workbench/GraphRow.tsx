"use client";

/**
 * GraphRow — one row in the GitKraken-style version graph (gh-961).
 *
 * Layout: [compare checkbox] [graph SVG cell] [version cell]
 *
 * Version cell:
 *   line 1: <avatar> <label> <tag (snapshot|HEAD)> [branch pill on tips]
 *   line 2: <author> · <relative date+time> · <note|state>
 */

import React from "react";
import { Bot, User } from "lucide-react";
import type { GraphRow as GraphRowData } from "@/types/versionGraph";
import { isAgentAuthor, authorLabel } from "@/lib/versionProvenance";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

export const LANE_X0 = 12;
export const LANE_GAP = 22;
/** Full height of a row's SVG cell in px. */
export const ROW_HEIGHT = 38;
/** Dot radius px. */
const DOT_R = 5;
/** Hollow ring stroke width. */
const DOT_STROKE = 2;

// ---------------------------------------------------------------------------
// SVG helpers
// ---------------------------------------------------------------------------

function laneX(lane: number): number {
  return LANE_X0 + lane * LANE_GAP;
}

function svgWidth(laneCount: number): number {
  return LANE_X0 + Math.max(1, laneCount) * LANE_GAP;
}

// ---------------------------------------------------------------------------
// Avatar
// ---------------------------------------------------------------------------

function NodeAvatar({ createdBy }: { readonly createdBy: string | null }) {
  const isAi = isAgentAuthor(createdBy);
  return (
    <span
      className={`inline-flex h-4 w-4 shrink-0 items-center justify-center rounded-full ${
        isAi ? "bg-violet-500/20 text-violet-400" : "bg-sidebar-accent text-muted-foreground"
      }`}
      aria-label={isAi ? "Created by AI" : "Created by human"}
    >
      {isAi ? <Bot size={9} /> : <User size={9} />}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Relative date formatter
// ---------------------------------------------------------------------------

function formatRelative(iso: string): string {
  try {
    const diff = Date.now() - new Date(iso).getTime();
    const mins = Math.round(diff / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.round(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.round(hours / 24);
    if (days < 30) return `${days}d ago`;
    // Fall back to a short date string
    return new Date(iso).toLocaleDateString("en-GB", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

// ---------------------------------------------------------------------------
// Graph SVG cell
// ---------------------------------------------------------------------------

interface GraphSvgCellProps {
  readonly row: GraphRowData;
  readonly laneCount: number;
}

function GraphSvgCell({ row, laneCount }: GraphSvgCellProps) {
  const width = svgWidth(laneCount);
  const midY = ROW_HEIGHT / 2;
  const nodeLaneX = laneX(row.lane);

  return (
    <svg
      width={width}
      height={ROW_HEIGHT}
      className="shrink-0"
      aria-hidden="true"
    >
      {/* Rails: vertical lines per lane, drawn first (behind dots) */}
      {row.rails.map((rail) => {
        const x = laneX(rail.lane);
        const yTop = rail.top ? 0 : midY;
        const yBottom = rail.bottom ? ROW_HEIGHT : midY;
        return (
          <line
            key={`rail-${rail.lane}`}
            x1={x}
            y1={yTop}
            x2={x}
            y2={yBottom}
            stroke={rail.color}
            strokeWidth={2}
          />
        );
      })}

      {/* Fork bézier curve (child lane → parent lane, on parent row) */}
      {row.fork && (() => {
        const cx = laneX(row.fork.childLane);
        const px = laneX(row.fork.parentLane);
        // Curve from top-of-row at childLane down to midY at parentLane
        const d = `M ${cx} 0 C ${cx} ${midY * 0.6} ${px} ${midY * 0.4} ${px} ${midY}`;
        return (
          <path
            d={d}
            stroke={row.fork.color}
            strokeWidth={2}
            fill="none"
          />
        );
      })()}

      {/* Node dot */}
      {row.dotStyle === "hollow" ? (
        <circle
          cx={nodeLaneX}
          cy={midY}
          r={DOT_R}
          fill="var(--color-card, #1c1c1e)"
          stroke={row.color}
          strokeWidth={DOT_STROKE}
          data-dot-style="hollow"
        />
      ) : (
        <circle
          cx={nodeLaneX}
          cy={midY}
          r={DOT_R}
          fill={row.color}
          data-dot-style="filled"
        />
      )}
    </svg>
  );
}

// ---------------------------------------------------------------------------
// GraphRow
// ---------------------------------------------------------------------------

export interface GraphRowProps {
  readonly row: GraphRowData;
  readonly laneCount: number;
  readonly isSelected: boolean;
  readonly isChecked: boolean;
  readonly currentHeadId: number | null;
  readonly onSelect: (nodeId: number) => void;
  readonly onCheck: (nodeId: number) => void;
}

export function GraphRow({
  row,
  laneCount,
  isSelected,
  isChecked,
  currentHeadId,
  onSelect,
  onCheck,
}: GraphRowProps) {
  const { node } = row;
  const label = node.version_label ?? node.name;
  const isCurrentHead = node.id === currentHeadId;

  const authorText = authorLabel(node.created_by);

  const secondLine = [
    authorText,
    formatRelative(node.created_at),
    node.version_note ?? (node.is_head && !node.is_immutable ? "editable" : undefined),
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <div
      data-testid={`graph-row-${node.id}`}
      role="row"
      aria-selected={isSelected}
      onClick={() => onSelect(node.id)}
      className={`flex cursor-pointer select-none items-center gap-2 px-2 transition-colors ${
        isSelected
          ? "border-l-2 border-primary bg-primary/5"
          : "border-l-2 border-transparent hover:bg-sidebar-accent/30"
      }`}
      style={{ minHeight: ROW_HEIGHT }}
    >
      {/* Compare checkbox */}
      <input
        type="checkbox"
        checked={isChecked}
        onChange={(e) => {
          e.stopPropagation();
          onCheck(node.id);
        }}
        onClick={(e) => e.stopPropagation()}
        aria-label={`Select node ${label} for comparison`}
        className="h-3.5 w-3.5 shrink-0 cursor-pointer rounded accent-primary"
      />

      {/* Graph SVG */}
      <GraphSvgCell row={row} laneCount={laneCount} />

      {/* Version info */}
      <div className="min-w-0 flex-1 py-1">
        {/* Line 1: avatar + label + tag + pill */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <NodeAvatar createdBy={node.created_by} />
          <span className="truncate font-[family-name:var(--font-jetbrains-mono)] text-[11px] font-medium text-foreground max-w-[180px]">
            {label}
          </span>
          {node.is_immutable && (
            <span className="shrink-0 rounded-full bg-amber-500/15 px-1 py-0.5 text-[9px] font-medium text-amber-400">
              snapshot
            </span>
          )}
          {isCurrentHead && (
            <span className="shrink-0 rounded-full bg-primary/20 px-1 py-0.5 text-[9px] font-medium text-primary">
              HEAD
            </span>
          )}
          {/* Branch pill on tip nodes */}
          {row.pill && (
            <span
              className="shrink-0 rounded px-1.5 py-0.5 text-[9px] font-semibold"
              style={{
                backgroundColor: `${row.pill.color}22`,
                color: row.pill.color,
              }}
            >
              {row.pill.text}
            </span>
          )}
        </div>

        {/* Line 2: author · date · note */}
        {secondLine && (
          <p className="mt-0.5 truncate text-[9px] text-muted-foreground">
            {secondLine}
          </p>
        )}
      </div>
    </div>
  );
}

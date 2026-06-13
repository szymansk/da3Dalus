"use client";

/**
 * Collapsible "Geometry changes" section for the version-compare view (gh-971).
 *
 * Sits BELOW the metric compare sections. Reuses the metric-compare 3-column
 * grid styling (A | param | B, amber on change). It owns the `expanded` and
 * `showAll` state and delegates the lazy fetch+diff to useGeometryDiff:
 *
 *   - Collapsed by default → the hook is called with enabled=false → NO fetch.
 *   - On first expand → enabled=true → the hook fetches every wing's WingConfig
 *     for both nodes and computes a pure GeometryDiff.
 *   - `showAll` flips the diff between changes-only (default) and show-all
 *     (every section + every core param, changes still highlighted amber).
 *
 * Failure is contained: an error renders an inline block inside the section, it
 * never throws up into the compare view. Units are mm / degrees (WingConfig).
 */

import React, { useState } from "react";
import { ChevronRight, ChevronDown, Loader2 } from "lucide-react";

import { useGeometryDiff } from "@/hooks/useGeometryDiff";
import type {
  GeometryDiff,
  WingDiff,
  SectionDiff,
  ChangeKind,
  SubElementFlag,
} from "@/lib/geometryDiff";

export interface GeometryDiffSectionProps {
  readonly nodeAUuid: string | null;
  readonly nodeBUuid: string | null;
  readonly wingNames: string[];
  readonly labelA: string;
  readonly labelB: string;
}

// ---------------------------------------------------------------------------
// Presentational helpers
// ---------------------------------------------------------------------------

/** "N changed · M added · K removed" summary for the collapsed header. */
function summaryText(diff: GeometryDiff | null): string {
  if (diff == null) return "";
  const { sectionsChanged, sectionsAdded, sectionsRemoved } = diff.counts;
  return `${sectionsChanged} changed · ${sectionsAdded} added · ${sectionsRemoved} removed`;
}

function KindBadge({ kind }: { readonly kind: ChangeKind }) {
  if (kind === "changed") return null;
  const cls =
    kind === "added"
      ? "bg-emerald-500/15 text-emerald-400"
      : "bg-rose-500/15 text-rose-400";
  return (
    <span
      className={`rounded-full px-1 py-0.5 text-[9px] font-medium ${cls}`}
    >
      {kind}
    </span>
  );
}

/** A | param | B value row, amber when the two sides differ. */
interface DiffRowProps {
  readonly paramKey: string;
  readonly a: string | null;
  readonly b: string | null;
  readonly differs: boolean;
  readonly kind?: ChangeKind;
}

function DiffRow({ paramKey, a, b, differs, kind }: DiffRowProps) {
  const dash = "—";
  return (
    <div
      className={`grid grid-cols-[1fr_auto_1fr] items-center gap-2 rounded px-2 py-1 font-[family-name:var(--font-geist-mono)] text-[11px] ${
        differs ? "bg-amber-500/10" : ""
      }`}
      data-testid={`geometry-diff-row-${paramKey}`}
      data-differs={differs ? "true" : undefined}
    >
      <span
        className={`text-right ${differs ? "font-semibold text-foreground" : "text-muted-foreground"}`}
      >
        {a ?? dash}
      </span>
      <span className="flex min-w-[72px] items-center justify-center gap-1 text-center text-subtle-foreground">
        {paramKey}
        {kind != null && <KindBadge kind={kind} />}
      </span>
      <span
        className={`text-left ${differs ? "font-semibold text-foreground" : "text-muted-foreground"}`}
      >
        {b ?? dash}
      </span>
    </div>
  );
}

function SectionSubheader({ section }: { readonly section: SectionDiff }) {
  return (
    <div
      className="mt-1 flex items-center gap-1.5 px-2 text-[10px] font-medium text-subtle-foreground"
      data-testid={`geometry-diff-section-${section.index}`}
    >
      <span>{section.label}</span>
      <KindBadge kind={section.kind} />
    </div>
  );
}

/** Indented sub-row for field-level detail beneath a sub-element flag row. */
function SubFieldRow({ paramKey, a, b }: { readonly paramKey: string; readonly a: string | null; readonly b: string | null }) {
  const dash = "—";
  const differs = a !== b;
  return (
    <div
      className={`grid grid-cols-[1fr_auto_1fr] items-center gap-2 rounded pl-6 pr-2 py-0.5 font-[family-name:var(--font-geist-mono)] text-[10px] ${
        differs ? "bg-amber-500/10" : ""
      }`}
      data-testid={`geometry-diff-subrow-${paramKey}`}
      data-differs={differs ? "true" : undefined}
    >
      <span className={`text-right ${differs ? "font-medium text-foreground/80" : "text-muted-foreground/70"}`}>
        {a ?? dash}
      </span>
      <span className="min-w-[72px] text-center text-[9px] text-subtle-foreground/70">{paramKey}</span>
      <span className={`text-left ${differs ? "font-medium text-foreground/80" : "text-muted-foreground/70"}`}>
        {b ?? dash}
      </span>
    </div>
  );
}

function FlagWithFields({ flagItem, sectionIndex }: { readonly flagItem: SubElementFlag; readonly sectionIndex: number }) {
  return (
    <>
      <DiffRow
        key={`${sectionIndex}-f-${flagItem.key}`}
        paramKey={flagItem.key}
        a={flagItem.a}
        b={flagItem.b}
        differs={flagItem.a !== flagItem.b}
        kind={flagItem.kind}
      />
      {flagItem.fields?.map((field) => (
        <SubFieldRow
          key={`${sectionIndex}-sf-${field.key}`}
          paramKey={field.key}
          a={field.a}
          b={field.b}
        />
      ))}
    </>
  );
}

function WingBlock({ wing }: { readonly wing: WingDiff }) {
  return (
    <div className="mb-3">
      <div className="mb-1 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-widest text-subtle-foreground">
        <span>{wing.name}</span>
        <KindBadge kind={wing.kind} />
      </div>
      <div className="flex flex-col gap-0.5">
        {wing.sections.map((section) => (
          <div key={section.index}>
            <SectionSubheader section={section} />
            {section.params.map((p) => (
              <DiffRow
                key={`${section.index}-p-${p.key}`}
                paramKey={p.key}
                a={p.a}
                b={p.b}
                differs={p.a !== p.b}
              />
            ))}
            {section.flags.map((f) => (
              <FlagWithFields
                key={`${section.index}-f-${f.key}`}
                flagItem={f}
                sectionIndex={section.index}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

/** Conservative geometry hints block (gh-973). */
function HintsBlock({ diff }: { readonly diff: GeometryDiff }) {
  const hints = diff.hints;
  if (hints.length === 0) return null;
  return (
    <div
      role="note"
      aria-label="Geometry observations"
      data-testid="geometry-diff-hints"
      className="mt-3 rounded border border-border/50 bg-sidebar-accent/30 px-3 py-2 text-[10px] text-muted-foreground"
    >
      <span className="font-medium text-subtle-foreground">Rough guide (verify with analysis):</span>
      <ul className="mt-1 list-inside list-disc space-y-0.5">
        {hints.map((h) => (
          <li key={h}>{h}</li>
        ))}
      </ul>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section body (only mounted while expanded)
// ---------------------------------------------------------------------------

interface DiffBodyProps {
  readonly diff: GeometryDiff | null;
  readonly isLoading: boolean;
  readonly error: Error | null;
  readonly showAll: boolean;
  readonly onToggleShowAll: () => void;
}

function DiffBody({ diff, isLoading, error, showAll, onToggleShowAll }: DiffBodyProps) {
  if (isLoading) {
    return (
      <div
        data-testid="geometry-diff-loading"
        className="flex items-center gap-2 px-2 py-3 text-[11px] text-muted-foreground"
      >
        <Loader2 size={13} className="animate-spin" aria-hidden="true" />
        Loading geometry changes…
      </div>
    );
  }

  if (error != null) {
    return (
      <div
        role="alert"
        data-testid="geometry-diff-error"
        className="rounded border border-destructive/30 bg-destructive/10 p-3 text-[11px] text-destructive"
      >
        Could not load geometry changes: {error.message}
      </div>
    );
  }

  if (diff == null || !diff.hasAnyChange) {
    return (
      <p className="px-2 py-2 text-[11px] text-muted-foreground">
        No geometry changes.
      </p>
    );
  }

  return (
    <div>
      <div className="mb-2 flex justify-end px-2">
        <button
          type="button"
          data-testid="geometry-diff-showall-toggle"
          aria-pressed={showAll}
          onClick={onToggleShowAll}
          className="rounded border border-border px-2 py-0.5 text-[10px] text-muted-foreground hover:bg-sidebar-accent"
        >
          {showAll ? "Changes only" : "Show all"}
        </button>
      </div>
      <div data-testid="geometry-diff-table">
        {diff.wings.map((wing) => (
          <WingBlock key={wing.name} wing={wing} />
        ))}
      </div>
      <HintsBlock diff={diff} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function GeometryDiffSection({
  nodeAUuid,
  nodeBUuid,
  wingNames,
  labelA,
  labelB,
}: GeometryDiffSectionProps) {
  const [expanded, setExpanded] = useState(false);
  const [showAll, setShowAll] = useState(false);

  // Lazy: the hook fetches only when `expanded` is true.
  const { diff, isLoading, error } = useGeometryDiff(
    nodeAUuid,
    nodeBUuid,
    wingNames,
    expanded,
    showAll,
  );

  const Chevron = expanded ? ChevronDown : ChevronRight;

  return (
    <div
      data-testid="geometry-diff-section"
      className="mt-4 border-t border-border pt-3"
    >
      <button
        type="button"
        data-testid="geometry-diff-header"
        aria-expanded={expanded}
        aria-controls="geometry-diff-body"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center gap-1.5 text-left text-[11px] font-semibold text-foreground hover:text-primary"
      >
        <Chevron size={13} className="shrink-0 text-muted-foreground" aria-hidden="true" />
        <span>Geometry changes</span>
        <span className="font-normal text-muted-foreground">— {summaryText(diff)}</span>
      </button>

      {/* The metric-compare grid uses A | label | B; mirror the label row so
          this section reads the same as the sections above it. */}
      {expanded && (
        <div id="geometry-diff-body">
          <div
            className="mt-2 mb-1 grid grid-cols-[1fr_auto_1fr] gap-2 px-2 text-[10px] font-medium text-subtle-foreground"
            aria-hidden="true"
          >
            <span className="text-right">{labelA}</span>
            <span className="min-w-[72px] text-center">param</span>
            <span className="text-left">{labelB}</span>
          </div>
          <DiffBody
            diff={diff}
            isLoading={isLoading}
            error={error}
            showAll={showAll}
            onToggleShowAll={() => setShowAll((v) => !v)}
          />
        </div>
      )}
    </div>
  );
}

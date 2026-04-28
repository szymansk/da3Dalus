"use client";

import { useState, useCallback } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

interface SegmentPaginatorProps {
  current: number;
  total: number;
  onChange: (index: number) => Promise<void>;
  disabled?: boolean;
}

function buildPageIndices(current: number, total: number): (number | "ellipsis")[] {
  if (total <= 5) {
    return Array.from({ length: total }, (_, i) => i);
  }
  const pages = new Set<number>();
  pages.add(0);
  pages.add(total - 1);
  for (let i = current - 1; i <= current + 1; i++) {
    if (i >= 0 && i < total) pages.add(i);
  }
  const sorted = [...pages].sort((a, b) => a - b);
  const result: (number | "ellipsis")[] = [];
  for (let i = 0; i < sorted.length; i++) {
    if (i > 0 && sorted[i] - sorted[i - 1] > 1) {
      result.push("ellipsis");
    }
    result.push(sorted[i]);
  }
  return result;
}

export function SegmentPaginator({ current, total, onChange, disabled }: Readonly<SegmentPaginatorProps>) {
  const [loading, setLoading] = useState(false);
  const isDisabled = disabled || loading;

  const handleClick = useCallback(async (index: number) => {
    if (index === current) return;
    setLoading(true);
    try {
      await onChange(index);
    } finally {
      setLoading(false);
    }
  }, [current, onChange]);

  const pages = buildPageIndices(current, total);

  return (
    <div className="flex items-center gap-1">
      <button
        aria-label="Previous segment"
        disabled={isDisabled || current === 0}
        onClick={() => handleClick(current - 1)}
        className="flex size-6 items-center justify-center rounded text-muted-foreground hover:text-foreground disabled:opacity-30 disabled:cursor-not-allowed"
      >
        <ChevronLeft size={14} />
      </button>

      {pages.map((page, i) =>
        page === "ellipsis" ? (
          <span key={`ellipsis-${i}`} className="px-0.5 text-[12px] text-muted-foreground">
            …
          </span>
        ) : (
          <button
            key={page}
            title={`Segment ${page}`}
            disabled={isDisabled}
            onClick={() => handleClick(page)}
            className={`flex size-6 items-center justify-center rounded font-[family-name:var(--font-jetbrains-mono)] text-[11px] ${
              page === current
                ? "bg-primary text-primary-foreground font-bold"
                : "border border-border text-muted-foreground hover:bg-sidebar-accent"
            } disabled:opacity-30 disabled:cursor-not-allowed`}
          >
            {page}
          </button>
        ),
      )}

      <button
        aria-label="Next segment"
        disabled={isDisabled || current === total - 1}
        onClick={() => handleClick(current + 1)}
        className="flex size-6 items-center justify-center rounded text-muted-foreground hover:text-foreground disabled:opacity-30 disabled:cursor-not-allowed"
      >
        <ChevronRight size={14} />
      </button>
    </div>
  );
}

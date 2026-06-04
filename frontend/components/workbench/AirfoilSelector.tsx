"use client";

import { useState, useRef, useEffect, useMemo } from "react";
import useSWR from "swr";
import { ChevronDown, ChevronUp, Search, Check } from "lucide-react";
import { fetcher } from "@/lib/fetcher";

interface AirfoilListResponse {
  count: number;
  airfoils: { airfoil_name: string; file_name: string }[];
}

interface SuitabilityToggle {
  /** Whether ranked / "Passende finden" mode is currently active */
  active: boolean;
  onToggle: () => void;
}

interface AirfoilSelectorProps {
  label: string;
  value: string;
  onChange?: (value: string) => void;
  onPreviewToggle?: (active: boolean) => void;
  /** Existing slot: right-aligned badge text per airfoil name */
  stats?: Record<string, string>;
  /**
   * gh-825 ADDITIVE: explicit id for the <label htmlFor> and trigger <button id>.
   * When provided, overrides the label-derived id fallback.
   * Use this to avoid duplicate-id violations when label='' (e.g. in
   * AirfoilPreviewConfigPanel where the visible heading is a sibling <span>).
   */
  id?: string;
  /**
   * gh-822 ADDITIVE: pre-sorted list of airfoil names (desc by score).
   * When provided, the dropdown renders in this order instead of the
   * alphabetical default.
   */
  sortedNames?: string[];
  /**
   * gh-822 ADDITIVE: when provided, renders a "🔍 Passende finden" toggle
   * button next to the dropdown trigger.
   */
  suitabilityToggle?: SuitabilityToggle;
}

const MAX_VISIBLE = 50;

// Score badge colour: green ≥ 0.7, amber 0.4–0.7, red < 0.4
function scoreBadgeColor(scoreStr: string): string {
  const v = Number.parseFloat(scoreStr);
  if (Number.isNaN(v)) return "#9CA3AF"; // neutral gray
  if (v >= 0.7) return "#34D399";
  if (v >= 0.4) return "#FBBF24";
  return "#F87171";
}

export function AirfoilSelector({
  label,
  value,
  onChange,
  onPreviewToggle,
  stats,
  id: idProp,
  sortedNames,
  suitabilityToggle,
}: Readonly<AirfoilSelectorProps>) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  // Fetch airfoil list from backend (cached by SWR, fetched once)
  const { data } = useSWR<AirfoilListResponse>("/airfoils", fetcher, {
    revalidateOnFocus: false,
    dedupingInterval: 60_000,
  });

  const allNames = useMemo(() => {
    // gh-822: when sortedNames is provided, use that order (ranked by suitability)
    if (sortedNames && sortedNames.length > 0) return sortedNames;
    return data?.airfoils?.map((a) => a.airfoil_name) ?? [];
  }, [data, sortedNames]);

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    if (!q) return allNames.slice(0, MAX_VISIBLE);
    return allNames.filter((n) => n.toLowerCase().includes(q)).slice(0, MAX_VISIBLE);
  }, [allNames, search]);

  const totalMatches = useMemo(() => {
    if (!search) return allNames.length;
    const q = search.toLowerCase();
    return allNames.filter((n) => n.toLowerCase().includes(q)).length;
  }, [allNames, search]);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
        onPreviewToggle?.(false);
      }
    }
    if (open) {
      document.addEventListener("mousedown", handleClick);
      return () => document.removeEventListener("mousedown", handleClick);
    }
  }, [open, onPreviewToggle]);

  useEffect(() => {
    if (open) searchRef.current?.focus();
  }, [open]);

  // Resolve the effective id: use idProp when provided, else derive from label.
  // This avoids duplicate-id violations when label='' (both selectors would
  // otherwise get id='airfoil-').
  const effectiveId = idProp ?? `airfoil-${label.toLowerCase().replaceAll(/\s+/g, "-")}`;

  const toggle = () => {
    const next = !open;
    setOpen(next);
    onPreviewToggle?.(next);
    if (!next) setSearch("");
  };

  const select = (name: string) => {
    onChange?.(name);
    setOpen(false);
    onPreviewToggle?.(false);
    setSearch("");
  };

  return (
    <div ref={containerRef} className="relative flex flex-1 flex-col gap-1">
      <div className="flex items-center gap-1">
        <label htmlFor={effectiveId} className="flex-1 text-[11px] text-muted-foreground">{label}</label>
        {/* gh-822 ADDITIVE: Passende finden toggle */}
        {suitabilityToggle && (
          <button
            type="button"
            title="🔍 Passende finden"
            onClick={suitabilityToggle.onToggle}
            className={`text-[10px] transition-colors ${
              suitabilityToggle.active
                ? "text-primary font-medium"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            🔍
          </button>
        )}
      </div>

      {/* Trigger */}
      <button
        id={effectiveId}
        onClick={toggle}
        className={`flex items-center gap-2 rounded-xl px-3 py-2 transition-colors ${
          open ? "border-2 border-primary bg-input" : "border border-border bg-input"
        }`}
      >
        <span className="text-[13px] text-foreground">{value || "—"}</span>
        <div className="flex-1" />
        {open ? (
          <ChevronUp size={12} className="text-primary" />
        ) : (
          <ChevronDown size={12} className="text-muted-foreground" />
        )}
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute top-full z-50 mt-1 w-full rounded-xl border border-border bg-card shadow-lg">
          {/* Search */}
          <div className="flex items-center gap-2 border-b border-border px-3 py-2">
            <Search size={13} className="text-muted-foreground" />
            <input
              ref={searchRef}
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search airfoils…"
              className="flex-1 bg-transparent text-[13px] text-foreground placeholder:text-subtle-foreground outline-none"
            />
          </div>

          {/* List */}
          <div className="max-h-[240px] overflow-y-auto py-1">
            {filtered.length === 0 ? (
              <div className="px-3 py-3 text-center text-[12px] text-muted-foreground">
                No airfoils found
              </div>
            ) : (
              filtered.map((name) => (
                <button
                  key={name}
                  onClick={() => select(name)}
                  className="flex w-full items-center gap-2 px-3 py-1.5 hover:bg-sidebar-accent"
                >
                  {name === value ? (
                    <Check size={12} className="text-primary" />
                  ) : (
                    <div className="w-3" />
                  )}
                  <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-foreground">
                    {name}
                  </span>
                  {stats?.[name] && (
                    <>
                      <span className="flex-1" />
                      <span
                        data-testid="score-badge"
                        className="rounded-full border border-current px-1.5 py-0.5 font-[family-name:var(--font-jetbrains-mono)] text-[10px]"
                        style={{
                          color: scoreBadgeColor(stats[name]),
                          backgroundColor: `${scoreBadgeColor(stats[name])}1a`,
                          borderColor: `${scoreBadgeColor(stats[name])}40`,
                        }}
                      >
                        {stats[name]}
                      </span>
                    </>
                  )}
                </button>
              ))
            )}
          </div>

          {/* Footer */}
          {totalMatches > MAX_VISIBLE && (
            <div className="border-t border-border px-3 py-2 text-center">
              <span className="text-[11px] text-subtle-foreground">
                {totalMatches - MAX_VISIBLE} more — type to narrow
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

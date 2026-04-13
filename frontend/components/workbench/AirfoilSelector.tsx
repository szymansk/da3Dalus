"use client";

import { useState, useRef, useEffect, useMemo } from "react";
import useSWR from "swr";
import { ChevronDown, ChevronUp, Search, Check } from "lucide-react";
import { fetcher } from "@/lib/fetcher";

interface AirfoilListResponse {
  count: number;
  airfoils: { airfoil_name: string; file_name: string }[];
}

interface AirfoilSelectorProps {
  label: string;
  value: string;
  onChange?: (value: string) => void;
  onPreviewToggle?: (active: boolean) => void;
}

const MAX_VISIBLE = 50;

export function AirfoilSelector({
  label,
  value,
  onChange,
  onPreviewToggle,
}: AirfoilSelectorProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  // Fetch airfoil list from backend (cached by SWR, fetched once)
  const { data } = useSWR<AirfoilListResponse>("/airfoils", fetcher, {
    revalidateOnFocus: false,
    dedupingInterval: 60_000,
  });

  const allNames = useMemo(
    () => data?.airfoils?.map((a) => a.airfoil_name) ?? [],
    [data],
  );

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
      <label className="text-[11px] text-muted-foreground">{label}</label>

      {/* Trigger */}
      <button
        onClick={toggle}
        className={`flex items-center gap-2 rounded-[--radius-s] px-3 py-2 transition-colors ${
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
        <div className="absolute top-full z-50 mt-1 w-full rounded-[--radius-m] border border-border bg-card shadow-lg">
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

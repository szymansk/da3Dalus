"use client";

import { useState, useRef, useEffect } from "react";
import { ChevronDown, ChevronUp, Search, Check } from "lucide-react";

interface AirfoilEntry {
  name: string;
  tc: string;
  ld: number;
}

const AIRFOILS: AirfoilEntry[] = [
  { name: "mh32", tc: "8.9%", ld: 68 },
  { name: "mh45", tc: "9.6%", ld: 72 },
  { name: "rg15", tc: "8.9%", ld: 65 },
  { name: "sd7037", tc: "9.2%", ld: 70 },
  { name: "e387", tc: "9.1%", ld: 63 },
];

interface AirfoilSelectorProps {
  label: string;
  value: string;
  onChange?: (value: string) => void;
  onPreviewToggle?: (active: boolean) => void;
}

export function AirfoilSelector({
  label,
  value,
  onChange,
  onPreviewToggle,
}: AirfoilSelectorProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);

  /* Close on outside click */
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
        onPreviewToggle?.(false);
      }
    }
    if (open) {
      document.addEventListener("mousedown", handleClick);
      return () => document.removeEventListener("mousedown", handleClick);
    }
  }, [open, onPreviewToggle]);

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

  const filtered = AIRFOILS.filter((a) =>
    a.name.toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <div ref={containerRef} className="relative flex flex-1 flex-col gap-1">
      <label className="text-[11px] text-muted-foreground">{label}</label>

      {/* ── Trigger ── */}
      <button
        onClick={toggle}
        className={`flex items-center gap-2 rounded-[--radius-s] px-3 py-2 transition-colors ${
          open
            ? "border-2 border-primary bg-input"
            : "border border-border bg-input"
        }`}
      >
        <span className="text-[13px] text-foreground">{value}</span>
        <div className="flex-1" />
        {open ? (
          <ChevronUp size={12} className="text-primary" />
        ) : (
          <ChevronDown size={12} className="text-muted-foreground" />
        )}
      </button>

      {/* ── Dropdown ── */}
      {open && (
        <div className="absolute top-full z-50 mt-1 w-full rounded-[--radius-m] border border-border bg-card shadow-lg">
          {/* Search */}
          <div className="flex items-center gap-2 border-b border-border px-3 py-2">
            <Search size={13} className="text-muted-foreground" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search airfoils..."
              className="flex-1 bg-transparent text-[13px] text-foreground placeholder:text-subtle-foreground outline-none"
              autoFocus
            />
          </div>

          {/* List */}
          <div className="max-h-[200px] overflow-y-auto py-1">
            {filtered.map((airfoil) => (
              <button
                key={airfoil.name}
                onClick={() => select(airfoil.name)}
                className="flex w-full items-center gap-2 px-3 py-1.5 hover:bg-sidebar-accent"
              >
                {airfoil.name === value ? (
                  <Check size={12} className="text-primary" />
                ) : (
                  <div className="w-3" />
                )}
                <span className="font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground">
                  {airfoil.name}
                </span>
                <div className="flex-1" />
                <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-muted-foreground">
                  {airfoil.tc} &middot; L/D {airfoil.ld}
                </span>
              </button>
            ))}
          </div>

          {/* Footer */}
          <div className="border-t border-border px-3 py-2 text-center">
            <span className="font-[family-name:var(--font-geist-sans)] text-[11px] text-subtle-foreground">
              98 more airfoils&hellip;
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

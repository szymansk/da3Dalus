"use client";

import { useState, useMemo } from "react";
import { ChevronUp, ChevronDown } from "lucide-react";
import type { StoredOperatingPoint } from "@/hooks/useOperatingPoints";
import { displaySurfaceName } from "./utils";

const RAD_TO_DEG = 180 / Math.PI;

// Role priority for ordering the dynamic control-surface columns (gh-863).
const ROLE_ORDER = [
  "elevator",
  "stabilator",
  "elevon",
  "ruddervator",
  "aileron",
  "flaperon",
  "flap",
  "rudder",
];

type FixedKey = "name" | "alpha" | "reserve" | "cl" | "cd" | "ld";
type SortKey = FixedKey | `surf:${string}`;
type SortDir = "asc" | "desc";

interface RowData {
  id: number;
  name: string;
  alpha_deg: number;
  reserve_pct: number; // binding (max) authority used across the OP's surfaces
  cl: number | null;
  cd: number | null;
  ld: number | null;
  deflections: Record<string, number>; // display surface name → deflection [deg]
}

interface Props {
  readonly points: StoredOperatingPoint[];
}

export function OpComparisonTable({ points }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("reserve");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const { surfaces, rows, computing } = useMemo(() => {
    const roleByDisplay = new Map<string, string>();
    const rowData: RowData[] = points
      .filter((p) => p.status === "TRIMMED" && p.trim_enrichment)
      .map((p) => {
        const enrichment = p.trim_enrichment!;
        const deflections: Record<string, number> = {};
        let maxUsage = 0;
        for (const [key, reserve] of Object.entries(enrichment.deflection_reserves)) {
          const dn = displaySurfaceName(key);
          deflections[dn] = reserve.deflection_deg;
          if (!roleByDisplay.has(dn)) {
            roleByDisplay.set(dn, (/^\[(\w+)\]/.exec(key)?.[1] ?? "").toLowerCase());
          }
          maxUsage = Math.max(maxUsage, reserve.usage_fraction);
        }
        const cl = enrichment.aero_coefficients?.CL ?? null;
        const cd = enrichment.aero_coefficients?.CD ?? null;
        const ld = cl !== null && cd !== null && cd > 0 ? cl / cd : null;
        return {
          id: p.id,
          name: p.name,
          alpha_deg: p.alpha * RAD_TO_DEG,
          reserve_pct: Math.round(maxUsage * 100),
          cl,
          cd,
          ld,
          deflections,
        };
      });

    const roleRank = (dn: string): number => {
      const idx = ROLE_ORDER.indexOf(roleByDisplay.get(dn) ?? "");
      return idx < 0 ? ROLE_ORDER.length : idx;
    };
    const surfaceNames = [...roleByDisplay.keys()].sort((a, b) => {
      const ra = roleRank(a);
      const rb = roleRank(b);
      return ra === rb ? a.localeCompare(b) : ra - rb;
    });
    // gh-865: OPs still being computed appear as greyed placeholder rows.
    const computingNames = points
      .filter((p) => p.status === "COMPUTING")
      .map((p) => p.name);
    return { surfaces: surfaceNames, rows: rowData, computing: computingNames };
  }, [points]);

  const sorted = useMemo(() => {
    const cmpFor = (a: RowData, b: RowData): number => {
      if (sortKey.startsWith("surf:")) {
        const s = sortKey.slice(5);
        return (a.deflections[s] ?? 0) - (b.deflections[s] ?? 0);
      }
      switch (sortKey) {
        case "name":
          return a.name.localeCompare(b.name);
        case "alpha":
          return a.alpha_deg - b.alpha_deg;
        case "reserve":
          return a.reserve_pct - b.reserve_pct;
        case "cl":
          return (a.cl ?? 0) - (b.cl ?? 0);
        case "cd":
          return (a.cd ?? 0) - (b.cd ?? 0);
        case "ld":
          return (a.ld ?? 0) - (b.ld ?? 0);
        default:
          return 0;
      }
    };
    return [...rows].sort((a, b) => (sortDir === "asc" ? cmpFor(a, b) : -cmpFor(a, b)));
  }, [rows, sortKey, sortDir]);

  const worstId = useMemo(() => {
    if (rows.length === 0) return null;
    return rows.reduce((worst, r) => (r.reserve_pct > worst.reserve_pct ? r : worst), rows[0]).id;
  }, [rows]);

  if (rows.length === 0 && computing.length === 0) return null;

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  const columns: { key: SortKey; label: string }[] = [
    { key: "name", label: "OP" },
    { key: "alpha", label: "α (°)" },
    ...surfaces.map((s) => ({ key: `surf:${s}` as SortKey, label: `${s} (°)` })),
    { key: "reserve", label: "Reserve" },
    { key: "cl", label: "CL" },
    { key: "cd", label: "CD" },
    { key: "ld", label: "L/D" },
  ];

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2 rounded-xl border border-border bg-card-muted p-4">
      <span className="font-[family-name:var(--font-geist-sans)] text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
        OP Comparison
      </span>
      <div className="min-h-0 flex-1 overflow-auto">
        <table className="w-full text-left font-[family-name:var(--font-jetbrains-mono)] text-[11px]">
          <thead className="sticky top-0 z-10 bg-card-muted">
            <tr className="border-b border-border">
              {columns.map((col) => (
                <th
                  key={col.key}
                  onClick={() => handleSort(col.key)}
                  className="cursor-pointer px-2 py-1.5 text-muted-foreground hover:text-foreground"
                >
                  <span className="inline-flex items-center gap-1">
                    {col.label}
                    {sortKey === col.key &&
                      (sortDir === "asc" ? (
                        <ChevronUp className="h-3 w-3" />
                      ) : (
                        <ChevronDown className="h-3 w-3" />
                      ))}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((row) => (
              <tr
                key={row.id}
                data-testid={`op-row-${row.id}`}
                className={`border-b border-border/50 ${
                  row.id === worstId ? "bg-red-500/10 text-red-400" : "text-foreground"
                }`}
              >
                <td className="px-2 py-1.5 font-medium">{row.name}</td>
                <td className="px-2 py-1.5">{row.alpha_deg.toFixed(1)}</td>
                {surfaces.map((s) => (
                  <td key={s} className="px-2 py-1.5">
                    {row.deflections[s] === undefined ? "—" : row.deflections[s].toFixed(1)}
                  </td>
                ))}
                <td className="px-2 py-1.5">{row.reserve_pct}%</td>
                <td className="px-2 py-1.5">{row.cl !== null ? row.cl.toFixed(3) : "—"}</td>
                <td className="px-2 py-1.5">{row.cd !== null ? row.cd.toFixed(4) : "—"}</td>
                <td className="px-2 py-1.5">{row.ld !== null ? row.ld.toFixed(1) : "—"}</td>
              </tr>
            ))}
            {/* gh-865: rows still being computed, greyed with a live indicator */}
            {computing.map((name) => (
              <tr
                key={`computing-${name}`}
                data-testid={`op-computing-${name}`}
                className="animate-pulse border-b border-border/50 text-subtle-foreground"
              >
                <td className="px-2 py-1.5 font-medium">{name}</td>
                <td className="px-2 py-1.5" colSpan={columns.length - 1}>
                  rechnet…
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

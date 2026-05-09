"use client";

import { useState, useMemo } from "react";
import { ChevronUp, ChevronDown } from "lucide-react";
import type { StoredOperatingPoint } from "@/hooks/useOperatingPoints";

const RAD_TO_DEG = 180 / Math.PI;

type SortKey = "name" | "alpha" | "elevator" | "reserve" | "cl" | "cd" | "ld";
type SortDir = "asc" | "desc";

interface RowData {
  id: number;
  name: string;
  alpha_deg: number;
  elevator_deg: number | null;
  reserve_pct: number;
  cl: number | null;
  cd: number | null;
  ld: number | null;
}

function extractElevator(enrichment: NonNullable<StoredOperatingPoint["trim_enrichment"]>): {
  deg: number | null;
  reserve: number;
} {
  const elevatorEntry = Object.entries(enrichment.deflection_reserves).find(([key]) =>
    key.toLowerCase().includes("elevator"),
  );
  if (!elevatorEntry) {
    const firstEntry = Object.entries(enrichment.deflection_reserves)[0];
    if (!firstEntry) return { deg: null, reserve: 0 };
    return { deg: firstEntry[1].deflection_deg, reserve: firstEntry[1].usage_fraction };
  }
  return { deg: elevatorEntry[1].deflection_deg, reserve: elevatorEntry[1].usage_fraction };
}

interface Props {
  readonly points: StoredOperatingPoint[];
}

export function OpComparisonTable({ points }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("reserve");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const rows: RowData[] = useMemo(() => {
    return points
      .filter((p) => p.status === "TRIMMED" && p.trim_enrichment)
      .map((p) => {
        const enrichment = p.trim_enrichment!;
        const { deg, reserve } = extractElevator(enrichment);
        const cl = enrichment.aero_coefficients?.CL ?? null;
        const cd = enrichment.aero_coefficients?.CD ?? null;
        const ld = cl !== null && cd !== null && cd > 0 ? cl / cd : null;
        return {
          id: p.id,
          name: p.name,
          alpha_deg: p.alpha * RAD_TO_DEG,
          elevator_deg: deg,
          reserve_pct: Math.round(reserve * 100),
          cl,
          cd,
          ld,
        };
      });
  }, [points]);

  const sorted = useMemo(() => {
    return [...rows].sort((a, b) => {
      let cmp = 0;
      switch (sortKey) {
        case "name":
          cmp = a.name.localeCompare(b.name);
          break;
        case "alpha":
          cmp = a.alpha_deg - b.alpha_deg;
          break;
        case "elevator":
          cmp = (a.elevator_deg ?? 0) - (b.elevator_deg ?? 0);
          break;
        case "reserve":
          cmp = a.reserve_pct - b.reserve_pct;
          break;
        case "cl":
          cmp = (a.cl ?? 0) - (b.cl ?? 0);
          break;
        case "cd":
          cmp = (a.cd ?? 0) - (b.cd ?? 0);
          break;
        case "ld":
          cmp = (a.ld ?? 0) - (b.ld ?? 0);
          break;
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [rows, sortKey, sortDir]);

  const worstId = useMemo(() => {
    if (rows.length === 0) return null;
    return rows.reduce((worst, r) => (r.reserve_pct > worst.reserve_pct ? r : worst), rows[0]).id;
  }, [rows]);

  if (rows.length === 0) return null;

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
    { key: "elevator", label: "Elev (°)" },
    { key: "reserve", label: "Reserve" },
    { key: "cl", label: "CL" },
    { key: "cd", label: "CD" },
    { key: "ld", label: "L/D" },
  ];

  return (
    <div className="flex flex-col gap-2 rounded-xl border border-border bg-card-muted p-4">
      <span className="font-[family-name:var(--font-geist-sans)] text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
        OP Comparison
      </span>
      <div className="overflow-x-auto">
        <table className="w-full text-left font-[family-name:var(--font-jetbrains-mono)] text-[11px]">
          <thead>
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
                <td className="px-2 py-1.5">
                  {row.elevator_deg !== null ? row.elevator_deg.toFixed(1) : "—"}
                </td>
                <td className="px-2 py-1.5">{row.reserve_pct}%</td>
                <td className="px-2 py-1.5">{row.cl !== null ? row.cl.toFixed(3) : "—"}</td>
                <td className="px-2 py-1.5">{row.cd !== null ? row.cd.toFixed(4) : "—"}</td>
                <td className="px-2 py-1.5">{row.ld !== null ? row.ld.toFixed(1) : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

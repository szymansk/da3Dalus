"use client";

import { Scale, Plus, Settings, X } from "lucide-react";
import { WorkbenchTwoPanel } from "@/components/workbench/WorkbenchTwoPanel";
import { AlertBanner } from "@/components/workbench/AlertBanner";
import { WeightTree } from "@/components/workbench/WeightTree";

const WEIGHT_ITEMS = [
  {
    name: "FC-4 Pix32",
    category: "flight_controller",
    mass: "0.038",
    x: "0.12",
    y: "0.00",
    z: "0.02",
  },
  {
    name: "LiPo 4S 5200",
    category: "battery",
    mass: "0.560",
    x: "0.20",
    y: "0.00",
    z: "-0.01",
  },
  {
    name: "Sony RX1R II",
    category: "payload",
    mass: "0.507",
    x: "0.30",
    y: "0.00",
    z: "-0.03",
  },
  {
    name: "CF spar D10 \u00d72",
    category: "structure",
    mass: "0.072",
    x: "0.50",
    y: "0.00",
    z: "0.00",
  },
];

const COLUMN_HEADERS = [
  "NAME",
  "MASS_KG",
  "X [M]",
  "Y [M]",
  "Z [M]",
  "ACTIONS",
];

export default function WeightPage() {
  return (
    <WorkbenchTwoPanel>
      <WeightTree />

      <div className="flex w-full flex-col gap-6 overflow-y-auto">
        {/* Header */}
        <div className="flex items-center gap-2.5">
          <Scale className="size-5 text-primary" />
          <h1 className="font-[family-name:var(--font-jetbrains-mono)] text-[20px] text-foreground">
            Weight Items
          </h1>
          <span className="flex-1" />
          <button className="flex items-center gap-1.5 rounded-[--radius-pill] bg-primary px-3.5 py-2 text-[13px] text-primary-foreground">
            <Plus className="size-3.5" />+ Item
          </button>
        </div>

        {/* Alert banner */}
        <AlertBanner>
          Weight Items needs backend resource. The table below writes to browser
          state until the resource lands.
        </AlertBanner>

        {/* Weight table */}
        <div className="overflow-hidden rounded-[--radius-m] border border-border bg-card">
          {/* Header row */}
          <div className="flex items-center rounded-t-[--radius-m] border-b border-border bg-card-muted px-4 py-3">
            <span className="flex-1 font-[family-name:var(--font-jetbrains-mono)] text-[11px] uppercase tracking-wide text-muted-foreground">
              {COLUMN_HEADERS[0]}
            </span>
            {COLUMN_HEADERS.slice(1, 5).map((h) => (
              <span
                key={h}
                className="w-24 text-right font-[family-name:var(--font-jetbrains-mono)] text-[11px] uppercase tracking-wide text-muted-foreground"
              >
                {h}
              </span>
            ))}
            <span className="w-16 text-right font-[family-name:var(--font-jetbrains-mono)] text-[11px] uppercase tracking-wide text-muted-foreground">
              {COLUMN_HEADERS[5]}
            </span>
          </div>

          {/* Data rows */}
          {WEIGHT_ITEMS.map((item) => (
            <div
              key={item.name}
              className="flex items-center border-t border-border px-4 py-3"
            >
              <div className="flex flex-1 flex-col">
                <span className="text-[13px] text-foreground">{item.name}</span>
                <span className="text-[11px] text-muted-foreground">
                  {item.category}
                </span>
              </div>
              {[item.mass, item.x, item.y, item.z].map((val, i) => (
                <span
                  key={i}
                  className="w-24 text-right font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-foreground"
                >
                  {val}
                </span>
              ))}
              <div className="flex w-16 justify-end gap-1.5">
                <button className="flex size-6 items-center justify-center rounded-full border border-border bg-card-muted">
                  <Settings className="size-3 text-muted-foreground" />
                </button>
                <button className="flex size-6 items-center justify-center rounded-full border border-border bg-card-muted">
                  <X className="size-3 text-muted-foreground" />
                </button>
              </div>
            </div>
          ))}

          {/* Totals row */}
          <div className="flex items-center rounded-b-[--radius-m] border-t border-border bg-sidebar-accent px-4 py-3">
            <span className="flex-1 font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">
              {"\u03A3"} TOTAL
            </span>
            <span className="w-24 text-right font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-primary">
              1.177
            </span>
            <span className="w-24" />
            <span className="w-24" />
            <span className="w-24" />
            <span className="w-16" />
          </div>
        </div>
      </div>
    </WorkbenchTwoPanel>
  );
}

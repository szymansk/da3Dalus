"use client";

import {
  Package,
  Search,
  ArrowLeft,
  Cpu,
  BatteryMedium,
  Wind,
  Wifi,
  Camera,
  Layers,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { WorkbenchTwoPanel } from "@/components/workbench/WorkbenchTwoPanel";
import { AlertBanner } from "@/components/workbench/AlertBanner";
import { ComponentTree } from "@/components/workbench/ComponentTree";

const COMPONENTS: {
  icon: LucideIcon;
  chip: string;
  title: string;
  subtitle: string;
  specs: [string, string][];
}[] = [
  {
    icon: Cpu,
    chip: "flight_controller",
    title: "FC-4 Pix32",
    subtitle: "Pixhawk-class autopilot",
    specs: [
      ["mass", "38 g"],
      ["v", "7.4\u201326.4 V"],
    ],
  },
  {
    icon: BatteryMedium,
    chip: "battery",
    title: "LiPo 4S 5200",
    subtitle: "14.8 V 5200 mAh",
    specs: [
      ["mass", "560 g"],
      ["cap", "77 Wh"],
    ],
  },
  {
    icon: Wind,
    chip: "motor",
    title: "T-Motor AT2820",
    subtitle: "880 KV outrunner",
    specs: [
      ["mass", "132 g"],
      ["kv", "880"],
    ],
  },
  {
    icon: Wifi,
    chip: "telemetry",
    title: "RFD900x",
    subtitle: "868/915 MHz modem",
    specs: [
      ["mass", "14 g"],
      ["range", "40 km"],
    ],
  },
  {
    icon: Camera,
    chip: "payload",
    title: "Sony RX1R II",
    subtitle: "42 MP full-frame",
    specs: [
      ["mass", "507 g"],
      ["vol", "1.2 L"],
    ],
  },
  {
    icon: Layers,
    chip: "structure",
    title: "CF spar D10",
    subtitle: "Carbon fibre tube",
    specs: [
      ["mass", "18 g/m"],
      ["d", "10 mm"],
    ],
  },
];

export default function ComponentsPage() {
  return (
    <WorkbenchTwoPanel>
      <ComponentTree />

      <div className="flex w-full flex-col gap-6 overflow-y-auto">
        {/* Header */}
        <div className="flex items-center gap-2.5">
          <Package className="size-5 text-primary" />
          <h1 className="font-[family-name:var(--font-jetbrains-mono)] text-[20px] text-foreground">
            Component Library
          </h1>
          <span className="flex-1" />
          <div className="flex w-60 items-center gap-2 rounded-xl border border-border bg-input px-3 py-2">
            <Search className="size-3.5 text-muted-foreground" />
            <span className="text-[12px] text-subtle-foreground">
              Search components...
            </span>
          </div>
        </div>

        {/* Alert banner */}
        <AlertBanner>
          Component Library needs backend resource. The card grid below is a
          static preview.
        </AlertBanner>

        {/* Drag hint */}
        <div className="flex items-center gap-1.5">
          <ArrowLeft size={12} className="text-subtle-foreground" />
          <span className="text-[11px] text-subtle-foreground">
            Drag components to the Aeroplane Tree to add them
          </span>
        </div>

        {/* Card grid */}
        <div className="grid grid-cols-3 gap-4">
          {COMPONENTS.map((comp) => {
            const Icon = comp.icon;
            return (
              <div
                key={comp.chip}
                className="flex flex-col gap-3 rounded-[--radius-m] border border-border bg-card p-4"
              >
                {/* Card header */}
                <div className="flex items-center">
                  <div className="flex size-8 items-center justify-center rounded-xl bg-card-muted">
                    <Icon className="size-4 text-primary" />
                  </div>
                  <span className="flex-1" />
                  <span className="rounded-[--radius-pill] bg-sidebar-accent px-2 py-0.5 font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-muted-foreground">
                    {comp.chip}
                  </span>
                </div>

                {/* Title + subtitle */}
                <div className="font-[family-name:var(--font-jetbrains-mono)] text-[14px] text-foreground">
                  {comp.title}
                </div>
                <div className="text-[12px] text-muted-foreground">
                  {comp.subtitle}
                </div>

                {/* Specs */}
                <div className="flex flex-col gap-1">
                  {comp.specs.map(([key, val]) => (
                    <div key={key} className="flex items-center">
                      <span className="text-[11px] text-muted-foreground">
                        {key}
                      </span>
                      <span className="flex-1" />
                      <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-foreground">
                        {val}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </WorkbenchTwoPanel>
  );
}

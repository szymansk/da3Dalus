"use client";

import { usePathname } from "next/navigation";
import { GuardedLink } from "./GuardedLink";
import {
  History,
  ChevronDown,
  Save,
  Settings,
  ArrowLeftRight,
} from "lucide-react";
import { useAeroplaneContext } from "./AeroplaneContext";
import { useAeroplanes } from "@/hooks/useAeroplanes";

const STEPS = [
  { num: 1, label: "Mission", href: "/workbench/mission" },
  { num: 2, label: "Construction", href: "/workbench" },
  { num: 3, label: "Analysis", href: "/workbench/analysis" },
  { num: 4, label: "Components", href: "/workbench/components" },
  { num: 5, label: "Plans", href: "/workbench/construction-plans" },
] as const;

function isActive(href: string, pathname: string) {
  if (href === "/workbench")
    return (
      pathname === "/workbench" ||
      pathname === "/workbench/airfoil-preview"
    );
  return pathname.startsWith(href);
}

export function Header() {
  const pathname = usePathname();
  const { aeroplaneId, selectedWing, selectedXsecIndex, setAeroplaneId } = useAeroplaneContext();
  const { aeroplanes } = useAeroplanes();
  const aeroplaneName = aeroplanes.find((a) => a.id === aeroplaneId)?.name ?? "da3Dalus";

  return (
    <header className="flex h-16 shrink-0 items-center gap-6 border-b border-border bg-card px-6">
      {/* Left cluster */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => setAeroplaneId(null)}
          className="flex items-center gap-2 rounded-full bg-sidebar-accent px-3 py-1.5 font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-foreground hover:bg-sidebar-accent/80"
          title="Switch aeroplane"
        >
          {aeroplaneName}
          <ArrowLeftRight size={12} className="text-muted-foreground" />
        </button>
        <span className="text-sm text-muted-foreground">/</span>
        <span className="text-sm text-muted-foreground">
          {selectedWing ?? "\u2014"}
          {pathname === "/workbench/airfoil-preview" && selectedXsecIndex != null && (
            <> / segment {selectedXsecIndex}</>
          )}
        </span>
      </div>

      {/* Step pills */}
      <nav className="flex flex-1 items-center justify-center gap-1">
        {STEPS.map((step) => {
          const active = isActive(step.href, pathname);
          return (
            <GuardedLink
              key={step.num}
              href={step.href}
              className={`flex items-center gap-2 rounded-full px-4 py-2 text-[13px] transition-colors ${
                active
                  ? "bg-primary text-primary-foreground"
                  : "bg-card-muted text-muted-foreground hover:bg-sidebar-accent"
              }`}
            >
              <span className="font-[family-name:var(--font-jetbrains-mono)]">
                {step.num} &middot;
              </span>
              <span className="font-[family-name:var(--font-geist-sans)]">
                {step.label}
              </span>
            </GuardedLink>
          );
        })}
      </nav>

      {/* Right cluster */}
      <div className="flex items-center gap-3">
        <button className="flex items-center gap-1.5 rounded-full border border-border bg-card-muted px-3 py-2 text-[13px] text-foreground hover:bg-sidebar-accent">
          <History size={14} />
          <span className="font-[family-name:var(--font-geist-sans)]">v3</span>
          <ChevronDown size={12} className="text-muted-foreground" />
        </button>
        <button className="flex h-8 w-8 items-center justify-center rounded-full border border-border bg-card-muted hover:bg-sidebar-accent">
          <Save size={16} />
        </button>
        <button className="flex h-8 w-8 items-center justify-center rounded-full border border-border bg-card-muted hover:bg-sidebar-accent">
          <Settings size={16} />
        </button>
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary font-[family-name:var(--font-jetbrains-mono)] text-xs text-primary-foreground">
          SZ
        </div>
      </div>
    </header>
  );
}

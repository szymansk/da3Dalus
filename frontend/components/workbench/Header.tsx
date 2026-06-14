"use client";

import { useState, useCallback } from "react";
import { usePathname } from "next/navigation";
import { GuardedLink } from "./GuardedLink";
import {
  History,
  ChevronDown,
  Save,
  Settings,
  ArrowLeftRight,
  GitBranch,
  Bot,
} from "lucide-react";
import { useAeroplaneContext } from "./AeroplaneContext";
import { useAeroplanes } from "@/hooks/useAeroplanes";
import { useVersionActions } from "@/hooks/useVersioning";
import { SnapshotDialog } from "./SnapshotDialog";

export const STEPS = [
  { num: 1, label: "Mission", href: "/workbench/mission" },
  { num: 2, label: "Construction", href: "/workbench" },
  { num: 3, label: "Analysis", href: "/workbench/analysis" },
  { num: 4, label: "Powertrain", href: "/workbench/powertrain" },
  { num: 5, label: "Components", href: "/workbench/components" },
  { num: 6, label: "Plans", href: "/workbench/construction-plans" },
] as const;

function branchIndicatorClass(isAiBranch: boolean, isMainBranch: boolean | null): string {
  if (isAiBranch) return "bg-violet-500/15 text-violet-400";
  if (isMainBranch === false) return "bg-amber-500/15 text-amber-400";
  return "bg-sidebar-accent text-muted-foreground";
}

function isActive(href: string, pathname: string) {
  if (href === "/workbench")
    return (
      pathname === "/workbench" ||
      pathname === "/workbench/airfoil-preview"
    );
  return pathname.startsWith(href);
}

interface HeaderProps {
  /** Called when the user clicks the v3/history button — opens the History panel. */
  onOpenHistory?: () => void;
}

export function Header({ onOpenHistory }: HeaderProps) {
  const pathname = usePathname();
  const { aeroplaneId, selectedWing, selectedXsecIndex, openPicker } = useAeroplaneContext();
  const { aeroplanes } = useAeroplanes();

  const currentAeroplane = aeroplanes.find((a) => a.id === aeroplaneId);
  const aeroplaneName = currentAeroplane?.name ?? "da3Dalus";

  // Versioning metadata from the list response.
  const intId = currentAeroplane?.int_id ?? null;
  const rootId = currentAeroplane?.root_id ?? null;
  const branchName = currentAeroplane?.branch_name ?? null;
  const isMainBranch = currentAeroplane?.is_main_branch ?? null;
  const isAiBranch = branchName != null && branchName.startsWith("ai/");

  const { snapshot } = useVersionActions(intId, rootId);

  const [snapshotOpen, setSnapshotOpen] = useState(false);
  const handleOpenSnapshot = useCallback(() => setSnapshotOpen(true), []);
  const handleCloseSnapshot = useCallback(() => setSnapshotOpen(false), []);

  const handleSnapshot = useCallback(
    async (label: string, note: string) => {
      await snapshot({ label, note: note || undefined });
    },
    [snapshot],
  );

  return (
    <>
      <header className="flex h-16 shrink-0 items-center gap-6 border-b border-border bg-card px-6">
        {/* Left cluster */}
        <div className="flex items-center gap-3">
          <button
            onClick={openPicker}
            className="flex items-center gap-2 rounded-full bg-sidebar-accent px-3 py-1.5 font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-foreground hover:bg-sidebar-accent/80"
            title="Switch aeroplane"
          >
            {aeroplaneName}
            <ArrowLeftRight size={12} className="text-muted-foreground" />
          </button>

          {/* Branch indicator */}
          {branchName != null && (
            <>
              <span className="text-sm text-muted-foreground">/</span>
              <span
                className={`flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium ${branchIndicatorClass(isAiBranch, isMainBranch)}`}
                title={`On branch: ${branchName}`}
                aria-label={`Branch: ${branchName}`}
              >
                {isAiBranch ? (
                  <Bot size={10} aria-hidden="true" />
                ) : (
                  <GitBranch size={10} aria-hidden="true" />
                )}
                {branchName}
              </span>
            </>
          )}

          <span className="text-sm text-muted-foreground">/</span>
          <span className="text-sm text-muted-foreground">
            {selectedWing ?? "—"}
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
          <button
            onClick={onOpenHistory}
            aria-label="Open history and variants panel"
            className="flex items-center gap-1.5 rounded-full border border-border bg-card-muted px-3 py-2 text-[13px] text-foreground hover:bg-sidebar-accent"
          >
            <History size={14} />
            <ChevronDown size={12} className="text-muted-foreground" />
          </button>
          <button
            onClick={intId != null ? handleOpenSnapshot : undefined}
            disabled={intId == null}
            aria-label="Save a snapshot of the current design"
            title={intId == null ? "Select an aeroplane to save a snapshot" : "Save snapshot"}
            className="flex h-8 w-8 items-center justify-center rounded-full border border-border bg-card-muted hover:bg-sidebar-accent disabled:cursor-not-allowed disabled:opacity-40"
          >
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

      {/* Snapshot dialog */}
      <SnapshotDialog
        open={snapshotOpen}
        onClose={handleCloseSnapshot}
        onSnapshot={handleSnapshot}
      />
    </>
  );
}

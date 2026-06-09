"use client";

import { useState, useCallback } from "react";
import { Suspense } from "react";
import { Header } from "@/components/workbench/Header";
import { CopilotStrip } from "@/components/workbench/CopilotStrip";
import { MetricsDashboardContainer } from "@/components/workbench/metrics-dashboard/MetricsDashboardContainer";
import { AeroplaneProvider } from "@/components/workbench/AeroplaneContext";
import { UnsavedChangesProvider } from "@/components/workbench/UnsavedChangesContext";
import { UnsavedChangesModal } from "@/components/workbench/UnsavedChangesModal";
import { AeroplanePickerHost } from "@/components/workbench/AeroplanePickerHost";
import { WorkbenchImportWarningBanner } from "@/components/workbench/WorkbenchImportWarningBanner";
import { VersionHistoryPanel } from "@/components/workbench/VersionHistoryPanel";
import { useAeroplaneContext } from "@/components/workbench/AeroplaneContext";
import { useAeroplanes } from "@/hooks/useAeroplanes";

/**
 * Inner layout — needs AeroplaneProvider context to read aeroplaneId.
 * Manages the History/Variants panel open state.
 */
function WorkbenchInner({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const { aeroplaneId, setAeroplaneId } = useAeroplaneContext();
  const { aeroplanes } = useAeroplanes();
  const [historyOpen, setHistoryOpen] = useState(false);

  const currentAeroplane = aeroplanes.find((a) => a.id === aeroplaneId);
  const intId = currentAeroplane?.int_id ?? null;
  const rootId = currentAeroplane?.root_id ?? null;

  const handleOpenHistory = useCallback(() => setHistoryOpen(true), []);
  const handleCloseHistory = useCallback(() => setHistoryOpen(false), []);

  return (
    <UnsavedChangesProvider>
      <div className="flex h-full flex-col bg-background text-foreground font-[family-name:var(--font-geist-sans)]">
        <Header onOpenHistory={handleOpenHistory} />
        <div className="px-4 pt-4">
          <WorkbenchImportWarningBanner />
        </div>
        <main className="flex min-h-0 flex-1 overflow-hidden p-4 gap-4">
          {children}
          {historyOpen && (
            <VersionHistoryPanel
              rootId={rootId}
              currentHeadId={intId}
              aeroplaneId={intId}
              onClose={handleCloseHistory}
              onSwitchAeroplane={setAeroplaneId}
            />
          )}
        </main>
        {/* gh-881: global metrics panel, docked above the copilot strip on every tab */}
        <div className="shrink-0 px-4 pb-2">
          <MetricsDashboardContainer />
        </div>
        <CopilotStrip onOpenHistory={handleOpenHistory} />
      </div>
      <UnsavedChangesModal />
      <AeroplanePickerHost />
    </UnsavedChangesProvider>
  );
}

export default function WorkbenchLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <Suspense>
      <AeroplaneProvider>
        <WorkbenchInner>{children}</WorkbenchInner>
      </AeroplaneProvider>
    </Suspense>
  );
}

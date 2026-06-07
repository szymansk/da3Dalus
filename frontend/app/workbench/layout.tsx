import { Suspense } from "react";
import { Header } from "@/components/workbench/Header";
import { CopilotStrip } from "@/components/workbench/CopilotStrip";
import { MetricsDashboard } from "@/components/workbench/metrics-dashboard/MetricsDashboard";
import { AeroplaneProvider } from "@/components/workbench/AeroplaneContext";
import { UnsavedChangesProvider } from "@/components/workbench/UnsavedChangesContext";
import { UnsavedChangesModal } from "@/components/workbench/UnsavedChangesModal";
import { AeroplanePickerHost } from "@/components/workbench/AeroplanePickerHost";
import { WorkbenchImportWarningBanner } from "@/components/workbench/WorkbenchImportWarningBanner";

export default function WorkbenchLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <Suspense>
      <AeroplaneProvider>
        <UnsavedChangesProvider>
          <div className="flex h-full flex-col bg-background text-foreground font-[family-name:var(--font-geist-sans)]">
            <Header />
            <div className="px-4 pt-4">
              <WorkbenchImportWarningBanner />
            </div>
            <main className="flex min-h-0 flex-1 overflow-hidden p-4 gap-4">
              {children}
            </main>
            {/* gh-881: global metrics panel, docked above the copilot strip on every tab */}
            <div className="shrink-0 px-4 pb-2">
              <MetricsDashboard />
            </div>
            <CopilotStrip />
          </div>
          <UnsavedChangesModal />
          <AeroplanePickerHost />
        </UnsavedChangesProvider>
      </AeroplaneProvider>
    </Suspense>
  );
}

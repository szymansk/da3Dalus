import { Suspense } from "react";
import { Header } from "@/components/workbench/Header";
import { CopilotStrip } from "@/components/workbench/CopilotStrip";
import { AeroplaneProvider } from "@/components/workbench/AeroplaneContext";

export default function WorkbenchLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <Suspense>
      <AeroplaneProvider>
        <div className="flex h-full flex-col bg-background text-foreground font-[family-name:var(--font-geist-sans)]">
          <Header />
          <main className="flex flex-1 overflow-hidden p-4 gap-4">
            {children}
          </main>
          <CopilotStrip />
        </div>
      </AeroplaneProvider>
    </Suspense>
  );
}

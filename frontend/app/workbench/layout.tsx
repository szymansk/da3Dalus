export default function WorkbenchLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-full flex-col bg-background text-foreground font-sans">
      {/* Header — Phase 1 (cad-modelling-service-lvx) */}
      <header className="flex h-16 shrink-0 items-center gap-6 border-b border-border bg-card px-6">
        <span className="rounded-full bg-sidebar-accent px-3 py-1.5 font-mono text-sm text-foreground">
          eHawk
        </span>
        <span className="text-sm text-muted-foreground">/ main_wing</span>
        <div className="flex-1" />
        <span className="text-xs text-subtle-foreground">
          Construction Workbench
        </span>
      </header>

      {/* Main content */}
      <main className="flex flex-1 overflow-hidden">{children}</main>

      {/* Copilot strip — Phase 1 (cad-modelling-service-lvx) */}
      <footer className="flex h-10 shrink-0 items-center gap-3 border-t border-border bg-sidebar px-6">
        <span className="text-sm text-subtle-foreground">
          Ask the copilot…
        </span>
      </footer>
    </div>
  );
}

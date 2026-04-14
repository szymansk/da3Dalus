/**
 * TreeCard — visual card shell for tree panels.
 *
 * Provides a consistent header (title, optional badge, optional actions slot)
 * and a scrollable body for tree content. Extracted from AeroplaneTree.tsx
 * to be reused by Weight Tree and other tree panels.
 */

interface TreeCardProps {
  title: string;
  badge?: string;
  badgeVariant?: "primary" | "muted";
  actions?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

export function TreeCard({
  title,
  badge,
  badgeVariant = "muted",
  actions,
  children,
  className,
}: TreeCardProps) {
  return (
    <div
      className={`rounded-xl border border-border bg-card overflow-hidden flex flex-col${className ? ` ${className}` : ""}`}
    >
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">
          {title}
        </span>
        {badge && (
          <span
            className={`font-[family-name:var(--font-jetbrains-mono)] text-[11px] ${badgeVariant === "primary" ? "text-primary" : "text-muted-foreground"}`}
          >
            {badge}
          </span>
        )}
        <div className="flex-1" />
        {actions}
      </div>
      {/* Scrollable body */}
      <div className="flex-1 overflow-y-auto px-4 pb-3">{children}</div>
    </div>
  );
}

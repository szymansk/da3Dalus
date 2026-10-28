import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export const metadata = {
  title: "Expert View · da3Dalus",
  description: "Canon/kernel view (development), experts only",
};

export default function ExpertLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <div className="flex h-full flex-col bg-background text-foreground font-[family-name:var(--font-geist-sans)]">
      <header className="flex h-16 shrink-0 items-center gap-4 border-b border-border bg-card px-6">
        <Link
          href="/workbench"
          className="flex items-center gap-2 rounded-full bg-sidebar-accent px-3 py-1.5 text-[13px] text-foreground hover:bg-sidebar-accent/80"
        >
          <ArrowLeft size={14} aria-hidden="true" />
          Workbench
        </Link>
        <h1 className="text-[15px] font-medium">Expert View</h1>
      </header>
      <main className="flex min-h-0 flex-1 flex-col p-4">{children}</main>
    </div>
  );
}

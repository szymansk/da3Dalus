import { Info } from "lucide-react";

interface AlertBannerProps {
  title?: string;
  children: React.ReactNode;
}

export function AlertBanner({
  title = "Coming soon \u2014 backend wiring in progress",
  children,
}: Readonly<AlertBannerProps>) {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-primary bg-[#2A1F10] p-4">
      <Info className="size-4 shrink-0 text-primary" />
      <div className="flex flex-col gap-0.5">
        <span className="text-[13px] font-semibold text-foreground">
          {title}
        </span>
        <span className="text-[12px] text-muted-foreground">{children}</span>
      </div>
    </div>
  );
}

"use client";

import { Separator } from "react-resizable-panels";
import { ChevronRight } from "lucide-react";

interface SplitHandleProps {
  onCollapse?: () => void;
  collapsed?: boolean;
}

export function SplitHandle({ onCollapse, collapsed }: Readonly<SplitHandleProps>) {
  return (
    <Separator className="group relative flex w-1 items-center justify-center bg-border transition-colors hover:bg-primary/50 data-[resize-handle-active]:bg-primary/50">
      {/* Grip dots */}
      <div className="flex flex-col gap-1">
        {[0, 1, 2].map((dot) => (
          <div key={`grip-${dot}`} className="size-[3px] rounded-full bg-muted-foreground opacity-50" />
        ))}
      </div>
      {/* Collapse chevron */}
      {onCollapse && (
        <button
          onClick={(e) => { e.stopPropagation(); onCollapse(); }}
          className="absolute -left-1.5 top-1/2 flex w-4 h-6 -translate-y-1/2 items-center justify-center rounded-[4px] border border-border bg-card-muted"
        >
          <ChevronRight
            size={12}
            className={`text-muted-foreground transition-transform ${collapsed ? "" : "rotate-180"}`}
          />
        </button>
      )}
    </Separator>
  );
}

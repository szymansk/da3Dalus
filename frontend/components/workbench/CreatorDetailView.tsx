"use client";

import type { CreatorInfo, CreatorCategory } from "@/hooks/useCreators";

const CATEGORY_LABELS: Record<CreatorCategory, string> = {
  wing: "Wing",
  fuselage: "Fuselage",
  cad_operations: "CAD Ops",
  export_import: "Export / Import",
  components: "Components",
};

interface CreatorDetailViewProps {
  creator: CreatorInfo;
  onBack: () => void;
}

/**
 * Read-only detail view for a Creator — shown when clicking a creator
 * in the gallery without a plan selected. Displays description,
 * parameter documentation, and output info.
 */
export function CreatorDetailView({ creator, onBack }: CreatorDetailViewProps) {
  const category = CATEGORY_LABELS[creator.category as CreatorCategory] ?? creator.category;
  const userParams = creator.parameters;

  return (
    <div className="flex flex-col gap-4">
      <button
        onClick={onBack}
        className="self-start text-[11px] text-primary hover:underline"
      >
        &larr; Back to catalog
      </button>

      {/* Header */}
      <div className="flex flex-col gap-1.5">
        <h3 className="font-[family-name:var(--font-jetbrains-mono)] text-[15px] text-foreground">
          {creator.class_name}
        </h3>
        <span className="rounded-full bg-card-muted px-2.5 py-0.5 font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-muted-foreground self-start">
          {category}
        </span>
      </div>

      {/* Description */}
      {creator.description && (
        <div className="rounded-xl border border-border bg-card-muted p-3">
          <p className="text-[12px] leading-relaxed text-foreground">
            {creator.description}
          </p>
        </div>
      )}

      {/* Parameters */}
      <div className="flex flex-col gap-2">
        <h4 className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">
          Parameters
          <span className="ml-1.5 text-[10px] text-subtle-foreground">
            ({userParams.length})
          </span>
        </h4>
        {userParams.length === 0 ? (
          <p className="text-[11px] text-subtle-foreground">
            No user-configurable parameters.
          </p>
        ) : (
          <div className="flex flex-col gap-1">
            {userParams.map((param) => (
              <div
                key={param.name}
                className="flex flex-col gap-0.5 rounded-lg border border-border bg-card p-2.5"
              >
                <div className="flex items-baseline gap-1.5">
                  <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-foreground">
                    {param.name}
                  </span>
                  <span className="font-[family-name:var(--font-jetbrains-mono)] text-[9px] text-subtle-foreground">
                    {param.type}
                  </span>
                  {param.required ? (
                    <span className="rounded bg-primary/20 px-1.5 py-0.5 text-[8px] text-primary">
                      required
                    </span>
                  ) : (
                    <span className="text-[9px] text-subtle-foreground">
                      = {param.default != null ? String(param.default) : "None"}
                    </span>
                  )}
                </div>
                {param.description && (
                  <p className="text-[11px] leading-snug text-muted-foreground">
                    {param.description}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Output */}
      <div className="flex flex-col gap-1.5">
        <h4 className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">
          Output
        </h4>
        <p className="text-[11px] text-subtle-foreground">
          Produces shape keys prefixed with the step&apos;s <code className="rounded bg-card-muted px-1 py-0.5 text-[10px]">creator_id</code>.
        </p>
      </div>
    </div>
  );
}

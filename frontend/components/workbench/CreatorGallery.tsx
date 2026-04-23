"use client";

import { useState } from "react";
import { Search } from "lucide-react";
import type { CreatorInfo, CreatorCategory } from "@/hooks/useCreators";
import { CREATOR_CATEGORIES } from "@/hooks/useCreators";
import { InfoTooltip } from "./InfoTooltip";

const CATEGORY_LABELS: Record<CreatorCategory, string> = {
  wing: "Wing",
  fuselage: "Fuselage",
  cad_operations: "CAD Ops",
  export_import: "Export",
  components: "Components",
};

interface CreatorGalleryProps {
  creators: CreatorInfo[];
  onSelect: (creator: CreatorInfo) => void;
}

export function CreatorGallery({ creators, onSelect }: Readonly<CreatorGalleryProps>) {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState<CreatorCategory | null>(null);

  const filtered = creators.filter((c) => {
    if (category && c.category !== category) return false;
    if (search && !c.class_name.toLowerCase().includes(search.toLowerCase()))
      return false;
    return true;
  });

  return (
    <div className="flex flex-col gap-3">
      {/* Search */}
      <div className="flex items-center gap-2 rounded-xl border border-border bg-input px-3 py-2">
        <Search className="size-3.5 text-muted-foreground" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search creators..."
          className="flex-1 bg-transparent text-[12px] text-foreground outline-none placeholder:text-subtle-foreground"
        />
      </div>

      {/* Category tabs */}
      <div className="flex items-center gap-1 rounded-full border border-border bg-card p-1 self-start flex-wrap">
        <button
          onClick={() => setCategory(null)}
          className={`rounded-full px-3 py-1 text-[11px] ${
            category === null
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          All
        </button>
        {CREATOR_CATEGORIES.map((cat) => (
          <button
            key={cat}
            onClick={() => setCategory(cat)}
            className={`rounded-full px-3 py-1 text-[11px] ${
              category === cat
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {CATEGORY_LABELS[cat]}
          </button>
        ))}
      </div>

      {/* Grid */}
      {filtered.length === 0 ? (
        <p className="py-8 text-center text-[13px] text-muted-foreground">
          No creators match your filter
        </p>
      ) : (
        <div className="grid grid-cols-2 gap-2">
          {filtered.map((creator) => (
            <button
              key={creator.class_name}
              onClick={() => onSelect(creator)}
              className="group/card flex flex-col gap-1 rounded-xl border border-border bg-card p-3 text-left hover:border-primary/50 hover:bg-sidebar-accent"
            >
              <span className="flex items-center gap-1.5">
                <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-foreground">
                  {creator.class_name}
                </span>
                {creator.description && (
                  <InfoTooltip text={creator.description} />
                )}
              </span>
              <span className="rounded-full bg-card-muted px-2 py-0.5 font-[family-name:var(--font-jetbrains-mono)] text-[9px] text-muted-foreground self-start">
                {CATEGORY_LABELS[creator.category as CreatorCategory] ?? creator.category}
              </span>
              {creator.description && (
                <span className="text-[10px] text-subtle-foreground line-clamp-2">
                  {creator.description}
                </span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

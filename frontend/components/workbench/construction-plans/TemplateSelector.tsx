"use client";

import { useState } from "react";
import { ChevronDown, Search } from "lucide-react";
import type { MockTemplate } from "./types";

interface TemplateSelectorProps {
  templates: MockTemplate[];
  selectedId: number | null;
  onSelect: (id: number) => void;
}

export function TemplateSelector({ templates, selectedId, onSelect }: Readonly<TemplateSelectorProps>) {
  const [search, setSearch] = useState("");
  const [open, setOpen] = useState(false);

  const filtered = templates.filter((t) =>
    t.name.toLowerCase().includes(search.toLowerCase()),
  );
  const selected = templates.find((t) => t.id === selectedId);

  return (
    <div className="relative">
      <div
        className="flex items-center gap-2 rounded-xl border border-border bg-input px-3 py-2 cursor-pointer"
        onClick={() => setOpen(!open)}
        onKeyDown={(e) => { if (e.key === "Enter") setOpen(!open); }}
        role="combobox"
        aria-expanded={open}
        tabIndex={0}
      >
        <Search className="size-3.5 text-muted-foreground" />
        <input
          type="text"
          value={open ? search : selected?.name ?? ""}
          onChange={(e) => {
            setSearch(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          placeholder="Select template..."
          className="flex-1 bg-transparent text-[12px] text-foreground outline-none placeholder:text-subtle-foreground"
        />
        <ChevronDown size={12} className="text-muted-foreground" />
      </div>
      {open && (
        <div className="absolute left-0 top-full z-50 mt-1 max-h-[200px] w-full overflow-y-auto rounded-xl border border-border bg-card shadow-lg">
          {filtered.length === 0 ? (
            <p className="px-3 py-2 text-[12px] text-muted-foreground">No templates found</p>
          ) : (
            filtered.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => {
                  onSelect(t.id);
                  setSearch("");
                  setOpen(false);
                }}
                className={`block w-full px-3 py-2 text-left text-[12px] hover:bg-sidebar-accent ${
                  t.id === selectedId ? "bg-sidebar-accent text-primary" : "text-foreground"
                }`}
              >
                <span className="font-[family-name:var(--font-jetbrains-mono)]">{t.name}</span>
                <span className="ml-2 text-[10px] text-muted-foreground">
                  {t.creators.length} steps
                </span>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}

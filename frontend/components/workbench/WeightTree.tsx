"use client";

import { useState } from "react";
import { TreeCard } from "@/components/workbench/TreeCard";
import {
  SimpleTreeRow,
  type SimpleTreeNode,
} from "@/components/workbench/SimpleTreeRow";

const STATIC_NODES: SimpleTreeNode[] = [
  {
    id: "root",
    label: "eHawk",
    level: 0,
    annotation: "1.177 kg",
    annotationPrimary: true,
  },
  { id: "mw", label: "main_wing", level: 1, annotation: "0.985 kg" },
  { id: "s0", label: "segment 0 (root)", level: 2 },
  { id: "s1", label: "segment 1", level: 2 },
  { id: "s2", label: "segment 2 \u00b7 aileron", level: 2, chip: "AILERON" },
  { id: "s3", label: "segment 3 \u00b7 aileron", level: 2 },
  { id: "ew", label: "elevator_wing", level: 1, annotation: "0.120 kg" },
  {
    id: "fuse",
    label: "fuselage",
    level: 1,
    leaf: true,
    annotation: "0.072 kg",
  },
];

export function WeightTree() {
  const [expanded, setExpanded] = useState<Set<string>>(
    new Set(["root", "mw"]),
  );

  const toggle = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const visible = STATIC_NODES.filter((node) => {
    if (node.level === 0) return true;
    if (node.level === 1) return expanded.has("root");
    if (node.level === 2) {
      if (!expanded.has("root")) return false;
      const idx = STATIC_NODES.indexOf(node);
      for (let i = idx - 1; i >= 0; i--) {
        if (STATIC_NODES[i].level === 1)
          return expanded.has(STATIC_NODES[i].id);
      }
    }
    return true;
  });

  return (
    <TreeCard title="Weight Tree" badge="1.177 kg" badgeVariant="primary">
      <div className="flex flex-col gap-0.5">
        {visible.map((node) => (
          <SimpleTreeRow
            key={node.id}
            node={{
              ...node,
              expanded: expanded.has(node.id),
              leaf: node.leaf ?? node.level === 2,
            }}
            onToggle={() => toggle(node.id)}
          />
        ))}
      </div>
    </TreeCard>
  );
}

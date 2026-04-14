"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, Plus, Trash2, Eye, EyeOff, Loader, PanelLeftClose } from "lucide-react";
import { useAeroplaneContext } from "@/components/workbench/AeroplaneContext";
import { useWing } from "@/hooks/useWings";
import type { XSec } from "@/hooks/useWings";
import { API_BASE } from "@/lib/fetcher";

// ── Types ───────────────────────────────────────────────────────

interface TreeNode {
  id: string;
  label: string;
  level: number;
  expanded?: boolean;
  selected?: boolean;
  leaf?: boolean;
  mono?: boolean;
  muted?: boolean;
  chip?: string;
  onClick?: () => void;
  onDelete?: () => void;
  isInsertPoint?: boolean;
  onInsert?: () => void;
  previewVisible?: boolean;
  previewLoading?: boolean;
  onPreviewToggle?: () => void;
}

// ── Build nodes for WingConfig mode (segments) ──────────────────

function buildSegmentNodes(
  wingName: string,
  wing: { name: string; symmetric: boolean; x_secs: XSec[] } | null,
  selectedWing: string | null,
  selectedXsecIndex: number | null,
  expandedSet: Set<string>,
  selectWing: (n: string | null) => void,
  selectXsec: (i: number | null) => void,
  onAddSegment: (wn: string) => void,
  onDeleteXsec: (wn: string, i: number) => void,
  onInsertXsec: (wn: string, i: number) => void,
): TreeNode[] {
  const nodes: TreeNode[] = [];
  const wingExpanded = expandedSet.has(`wing-${wingName}`);

  nodes.push({
    id: `wing-${wingName}`,
    label: wingName,
    level: 1,
    expanded: wingExpanded,
    onClick: () => selectWing(wingName),
    onDelete: () => {
      if (confirm(`Delete wing "${wingName}"?`)) {
        onDeleteXsec(wingName, -1); // -1 signals delete wing
      }
    },
  });

  if (!wingExpanded) return nodes;
  if (!wing || wing.name !== wingName) {
    nodes.push({ id: `${wingName}-loading`, label: "Loading…", level: 2, leaf: true, muted: true });
    return nodes;
  }

  // nose_pnt row
  const nosePnt = wing.x_secs[0]?.xyz_le;
  if (nosePnt) {
    nodes.push({
      id: `${wingName}-nosepnt`,
      label: `nose_pnt [${nosePnt.map((v: number) => (v * 1000).toFixed(0)).join(", ")}] mm`,
      level: 2, leaf: true, muted: true, mono: true,
    });
  }

  // Segments (each segment = pair of consecutive x_secs)
  const segCount = wing.x_secs.length - 1;
  for (let i = 0; i < segCount; i++) {
    const root = wing.x_secs[i];
    const tip = wing.x_secs[i + 1];
    const segId = `${wingName}-seg${i}`;
    const isSelected = selectedWing === wingName && selectedXsecIndex === i;
    const segExpanded = expandedSet.has(segId);

    // Insert point before this segment (except before first)
    if (i > 0) {
      nodes.push({
        id: `${wingName}-ins-${i}`,
        label: "insert",
        level: 2,
        isInsertPoint: true,
        onInsert: () => onInsertXsec(wingName, i),
      });
    }

    const chipLabel = getChipLabel(root);

    nodes.push({
      id: segId,
      label: i === 0 ? `segment ${i} (root)` : `segment ${i}`,
      level: 2,
      expanded: segExpanded,
      selected: isSelected,
      chip: chipLabel,
      onClick: () => { selectWing(wingName); selectXsec(i); },
      onDelete: () => {
        if (confirm(`Delete segment ${i}?`)) onDeleteXsec(wingName, i);
      },
    });

    // Expanded segment details
    if (segExpanded) {
      const rootChord = (root.chord * 1000).toFixed(1);
      const tipChord = (tip.chord * 1000).toFixed(1);
      const length = (Math.abs(tip.xyz_le[1] - root.xyz_le[1]) * 1000).toFixed(1);
      const sweep = ((tip.xyz_le[0] - root.xyz_le[0]) * 1000).toFixed(1);

      nodes.push({
        id: `${segId}-root`, label: `root: ${airfoilShort(root.airfoil)} · ${rootChord} mm`,
        level: 3, leaf: true, muted: true,
      });
      nodes.push({
        id: `${segId}-tip`, label: `tip: ${airfoilShort(tip.airfoil)} · ${tipChord} mm`,
        level: 3, leaf: true, muted: true,
      });
      nodes.push({
        id: `${segId}-dims`, label: `length ${length} mm · sweep ${sweep} mm`,
        level: 3, leaf: true, muted: true, mono: true,
      });
      const spareCount = Array.isArray(root.spare_list) ? root.spare_list.length : 0;
      if (spareCount > 0) {
        nodes.push({ id: `${segId}-spars`, label: `spars (${spareCount})`, level: 3, expanded: false });
      }
    }
  }

  // "+ segment" at the end
  nodes.push({
    id: `${wingName}-add`,
    label: "+ segment",
    level: 2, leaf: true, muted: true,
    onClick: () => onAddSegment(wingName),
  });

  return nodes;
}

// ── Build nodes for ASB mode (x_secs) ───────────────────────────

function buildXsecNodes(
  wingName: string,
  wing: { name: string; symmetric: boolean; x_secs: XSec[] } | null,
  selectedWing: string | null,
  selectedXsecIndex: number | null,
  expandedSet: Set<string>,
  selectWing: (n: string | null) => void,
  selectXsec: (i: number | null) => void,
  onDeleteXsec: (wn: string, i: number) => void,
): TreeNode[] {
  const nodes: TreeNode[] = [];
  const wingExpanded = expandedSet.has(`wing-${wingName}`);

  nodes.push({
    id: `wing-${wingName}`,
    label: wingName,
    level: 1,
    expanded: wingExpanded,
    onClick: () => selectWing(wingName),
  });

  if (!wingExpanded) return nodes;
  if (!wing || wing.name !== wingName) {
    nodes.push({ id: `${wingName}-loading`, label: "Loading…", level: 2, leaf: true, muted: true });
    return nodes;
  }

  wing.x_secs.forEach((xsec, i) => {
    const xsecId = `${wingName}-xsec${i}`;
    const isSelected = selectedWing === wingName && selectedXsecIndex === i;
    const xsecExpanded = expandedSet.has(xsecId);

    nodes.push({
      id: xsecId,
      label: `x_sec ${i}`,
      level: 2,
      expanded: xsecExpanded,
      selected: isSelected,
      chip: getChipLabel(xsec),
      onClick: () => { selectWing(wingName); selectXsec(i); },
      onDelete: () => {
        if (confirm(`Delete x_sec ${i}?`)) onDeleteXsec(wingName, i);
      },
    });

    if (xsecExpanded) {
      nodes.push({
        id: `${xsecId}-airfoil`,
        label: `airfoil · ${airfoilShort(xsec.airfoil)}`,
        level: 3, leaf: true, muted: true,
      });
      nodes.push({
        id: `${xsecId}-chord`,
        label: `chord ${xsec.chord}`,
        level: 3, leaf: true, muted: true, mono: true,
      });
      nodes.push({
        id: `${xsecId}-twist`,
        label: `twist ${xsec.twist}°`,
        level: 3, leaf: true, muted: true, mono: true,
      });
      nodes.push({
        id: `${xsecId}-xyz`,
        label: `xyz_le [${xsec.xyz_le.map((v: number) => v.toFixed(4)).join(", ")}]`,
        level: 3, leaf: true, muted: true, mono: true,
      });
      const spareCount = Array.isArray(xsec.spare_list) ? xsec.spare_list.length : 0;
      if (spareCount > 0) {
        nodes.push({ id: `${xsecId}-spars`, label: `spars (${spareCount})`, level: 3, expanded: false });
      }
    }
  });

  return nodes;
}

// ── Helpers ──────────────────────────────────────────────────────

function airfoilShort(raw: string): string {
  return (raw.split("/").pop() ?? raw).replace(/\.dat$/i, "");
}

function getChipLabel(xsec: XSec): string | undefined {
  const ted = xsec.trailing_edge_device;
  if (ted && typeof ted === "object" && "name" in ted) return String(ted.name).toUpperCase();
  const cs = xsec.control_surface;
  if (cs && typeof cs === "object" && "name" in cs) return String(cs.name).toUpperCase();
  return undefined;
}

// ── Props ───────────────────────────────────────────────────────

interface AeroplaneTreeProps {
  aeroplaneId: string | null;
  wingNames: string[];
  aeroplaneName?: string;
  isWingVisible?: (wingName: string) => boolean;
  isWingLoading?: (wingName: string) => boolean;
  onTogglePreview?: (wingName: string) => void;
  onToggleAllPreview?: (wingNames: string[]) => void;
  onCollapseTree?: () => void;
}

// ── Component ───────────────────────────────────────────────────

export function AeroplaneTree({ aeroplaneId, wingNames, aeroplaneName, isWingVisible, isWingLoading, onTogglePreview, onToggleAllPreview, onCollapseTree }: AeroplaneTreeProps) {
  const { selectedWing, selectedXsecIndex, selectWing, selectXsec, treeMode, setTreeMode } =
    useAeroplaneContext();
  const { wing, isLoading, mutate: mutateWing } = useWing(aeroplaneId, selectedWing);

  const [expandedSet, setExpandedSet] = useState<Set<string>>(() => {
    const s = new Set<string>();
    s.add("root");
    if (wingNames.length > 0) s.add(`wing-${wingNames[0]}`);
    return s;
  });

  function toggleExpand(nodeId: string) {
    setExpandedSet((prev) => {
      const next = new Set(prev);
      if (next.has(nodeId)) next.delete(nodeId);
      else next.add(nodeId);
      return next;
    });
  }

  async function handleAddSegment(wingName: string) {
    if (!aeroplaneId) return;
    const xsecCount = wing?.x_secs.length ?? 0;
    const lastXsec = wing?.x_secs[xsecCount - 1];
    const newXsec = {
      xyz_le: [(lastXsec?.xyz_le[0] ?? 0), (lastXsec?.xyz_le[1] ?? 0) + 0.1, (lastXsec?.xyz_le[2] ?? 0)],
      chord: lastXsec?.chord ?? 0.1,
      twist: 0,
      airfoil: lastXsec?.airfoil ?? "naca0015",
    };
    const res = await fetch(
      `${API_BASE}/aeroplanes/${aeroplaneId}/wings/${wingName}/cross_sections/${xsecCount}`,
      { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(newXsec) },
    );
    if (res.ok) {
      await mutateWing();
      selectXsec(xsecCount - 1);
    }
  }

  async function handleDeleteXsec(wingName: string, index: number) {
    if (!aeroplaneId) return;
    if (index === -1) {
      const res = await fetch(`${API_BASE}/aeroplanes/${aeroplaneId}/wings/${wingName}`, { method: "DELETE" });
      if (!res.ok) { alert(`Delete wing failed: ${res.status}`); return; }
      selectWing(null);
    } else {
      const res = await fetch(
        `${API_BASE}/aeroplanes/${aeroplaneId}/wings/${wingName}/cross_sections/${index}`,
        { method: "DELETE" },
      );
      if (!res.ok) { alert(`Delete failed: ${res.status}`); return; }
    }
    await mutateWing();
  }

  async function handleInsertXsec(wingName: string, atIndex: number) {
    if (!aeroplaneId || !wing) return;
    const before = wing.x_secs[atIndex - 1];
    const after = wing.x_secs[atIndex];
    const newXsec = {
      xyz_le: [
        (before.xyz_le[0] + after.xyz_le[0]) / 2,
        (before.xyz_le[1] + after.xyz_le[1]) / 2,
        (before.xyz_le[2] + after.xyz_le[2]) / 2,
      ],
      chord: (before.chord + after.chord) / 2,
      twist: (before.twist + after.twist) / 2,
      airfoil: before.airfoil,
    };
    const res = await fetch(
      `${API_BASE}/aeroplanes/${aeroplaneId}/wings/${wingName}/cross_sections/${atIndex}`,
      { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(newXsec) },
    );
    if (res.ok) {
      await mutateWing();
      selectXsec(atIndex);
    }
  }

  // Build tree data
  const treeData: TreeNode[] = [];
  const rootExpanded = expandedSet.has("root");
  const anyWingVisible = onTogglePreview ? wingNames.some((wn) => isWingVisible?.(wn)) : false;
  const anyWingLoading = onTogglePreview ? wingNames.some((wn) => isWingLoading?.(wn)) : false;

  treeData.push({
    id: "root",
    label: aeroplaneName ?? "Aeroplane",
    level: 0,
    expanded: rootExpanded,
    previewVisible: anyWingVisible,
    previewLoading: anyWingLoading,
    onPreviewToggle: onToggleAllPreview
      ? () => onToggleAllPreview(wingNames)
      : undefined,
  });

  if (rootExpanded) {
    for (const wn of wingNames) {
      const nodes = treeMode === "wingconfig"
        ? buildSegmentNodes(wn, wing, selectedWing, selectedXsecIndex, expandedSet, selectWing, selectXsec, handleAddSegment, handleDeleteXsec, handleInsertXsec)
        : buildXsecNodes(wn, wing, selectedWing, selectedXsecIndex, expandedSet, selectWing, selectXsec, handleDeleteXsec);
      // Attach preview toggle to the wing root node
      if (nodes.length > 0 && onTogglePreview) {
        nodes[0].previewVisible = isWingVisible?.(wn) ?? false;
        nodes[0].previewLoading = isWingLoading?.(wn) ?? false;
        nodes[0].onPreviewToggle = () => onTogglePreview(wn);
      }
      treeData.push(...nodes);
    }
  }

  return (
    <div className="rounded-[--radius-m] border border-border bg-card p-3 px-4">
      {/* Header with collapse + mode toggle */}
      <div className="mb-2 flex items-center gap-2">
        {onCollapseTree && (
          <button
            onClick={onCollapseTree}
            className="flex size-6 items-center justify-center rounded-lg text-muted-foreground hover:bg-sidebar-accent"
            title="Collapse tree panel"
          >
            <PanelLeftClose size={14} />
          </button>
        )}
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">
          Aeroplane Tree
        </span>
        <div className="flex-1" />
        <div className="flex overflow-hidden rounded-lg border border-border">
          <button
            onClick={() => setTreeMode("wingconfig")}
            className={`px-2.5 py-1 font-[family-name:var(--font-jetbrains-mono)] text-[10px] ${
              treeMode === "wingconfig"
                ? "bg-primary text-primary-foreground"
                : "bg-card-muted text-muted-foreground hover:text-foreground"
            }`}
          >
            Segments
          </button>
          <button
            onClick={() => setTreeMode("asb")}
            className={`px-2.5 py-1 font-[family-name:var(--font-jetbrains-mono)] text-[10px] ${
              treeMode === "asb"
                ? "bg-primary text-primary-foreground"
                : "bg-card-muted text-muted-foreground hover:text-foreground"
            }`}
          >
            X-Secs
          </button>
        </div>
        <button className="flex h-6 w-6 items-center justify-center rounded-lg text-muted-foreground hover:bg-sidebar-accent">
          <Plus size={14} />
        </button>
      </div>

      {/* Tree rows */}
      <div className="flex flex-col gap-0.5">
        {isLoading && wingNames.length === 0 ? (
          <span className="text-[13px] text-muted-foreground">Loading...</span>
        ) : (
          treeData.map((node) => (
            <TreeRow key={node.id} node={node} onToggle={() => toggleExpand(node.id)} />
          ))
        )}
      </div>
    </div>
  );
}

// ── TreeRow ─────────────────────────────────────────────────────

function TreeRow({ node, onToggle }: { node: TreeNode; onToggle: () => void }) {
  if (node.isInsertPoint) {
    return (
      <div
        className="flex items-center gap-1 py-0.5 opacity-30 hover:opacity-100"
        style={{ paddingLeft: `${node.level * 20}px` }}
      >
        <div className="h-px flex-1 bg-border" />
        <button
          onClick={() => node.onInsert?.()}
          className="flex items-center gap-1 rounded-[--radius-pill] px-2 py-0.5 text-[9px] text-muted-foreground hover:text-primary"
        >
          <Plus size={10} />
          insert
        </button>
        <div className="h-px flex-1 bg-border" />
      </div>
    );
  }

  const indent = node.level * 20;
  const isLeaf = node.leaf;

  function handleClick() {
    if (!isLeaf) onToggle();
    node.onClick?.();
  }

  return (
    <div
      className={`group flex items-center gap-2 rounded-lg py-1.5 hover:bg-sidebar-accent ${
        node.selected ? "bg-sidebar-accent font-semibold" : ""
      }`}
      style={{ paddingLeft: `${indent}px`, cursor: "pointer" }}
      onClick={handleClick}
    >
      {!isLeaf && (
        <span className="flex h-3 w-3 shrink-0 items-center justify-center text-muted-foreground">
          {node.expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        </span>
      )}
      {isLeaf && <span className="w-3 shrink-0" />}

      <span className={`text-[13px] ${
        node.muted ? "text-[12px] text-muted-foreground" : "text-foreground"
      } ${node.mono ? "font-[family-name:var(--font-jetbrains-mono)]" : ""}`}>
        {node.label}
      </span>

      {node.chip && (
        <span className="rounded bg-card-muted px-1.5 py-0.5 font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-primary">
          {node.chip}
        </span>
      )}

      <span className="flex-1" />

      {node.onDelete && (
        <button
          onClick={(e) => { e.stopPropagation(); node.onDelete?.(); }}
          className="hidden h-5 w-5 items-center justify-center rounded-lg group-hover:flex"
        >
          <Trash2 size={12} className="text-destructive" />
        </button>
      )}

      {node.onPreviewToggle && (
        <button
          onClick={(e) => { e.stopPropagation(); node.onPreviewToggle?.(); }}
          className={`flex h-5 w-5 items-center justify-center rounded-lg ${
            node.previewVisible ? "text-primary" : "text-muted-foreground opacity-40 group-hover:opacity-100"
          }`}
          title={node.previewVisible ? "Hide 3D preview" : "Show 3D preview"}
        >
          {node.previewLoading ? (
            <Loader size={12} className="animate-spin" />
          ) : node.previewVisible ? (
            <Eye size={12} />
          ) : (
            <EyeOff size={12} />
          )}
        </button>
      )}
    </div>
  );
}

"use client";

import { useState, useEffect } from "react";
import { ChevronDown, ChevronRight, Plus, Trash2, Eye, EyeOff, Loader, PanelLeftClose, Pencil } from "lucide-react";
import { useAeroplaneContext } from "@/components/workbench/AeroplaneContext";
import { useWing } from "@/hooks/useWings";
import type { XSec } from "@/hooks/useWings";
import { useWingConfig } from "@/hooks/useWingConfig";
import { API_BASE } from "@/lib/fetcher";
import { useFuselage } from "@/hooks/useFuselage";
import { useFuselages } from "@/hooks/useFuselages";
import { ImportFuselageDialog } from "./ImportFuselageDialog";
import { CreateWingDialog } from "./CreateWingDialog";

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
  detail?: string;
  onClick?: () => void;
  onDelete?: () => void;
  isInsertPoint?: boolean;
  onInsert?: () => void;
  previewVisible?: boolean;
  previewLoading?: boolean;
  onPreviewToggle?: () => void;
  onAdd?: (e: React.MouseEvent) => void;
  onEdit?: () => void;
}

// ── Callback & context interfaces for build*Nodes ──────────────

interface BuildNodeCallbacks {
  selectWing: (n: string | null) => void;
  selectXsec: (i: number | null) => void;
  onDeleteXsec: (wn: string, i: number) => void;
  onEditNode?: () => void;
  onEditSpar?: (wingName: string, xsecIndex: number, sparIndex: number, data: Record<string, unknown>) => void;
  onDeleteSpar?: (wingName: string, xsecIndex: number, sparIndex: number) => void;
  onEditTed?: (wingName: string, xsecIndex: number, data: Record<string, unknown>) => void;
  onDeleteTed?: (wingName: string, xsecIndex: number) => void;
  onAddSpar?: (wingName: string, xsecIndex: number) => void;
  onAddTed?: (wingName: string, xsecIndex: number) => void;
  onAddMenu?: (wingName: string, xsecIndex: number, hasTed: boolean, x: number, y: number) => void;
  onAddSegment?: (wn: string) => void;
  onInsertXsec?: (wn: string, i: number) => void;
}

interface BuildNodeContext {
  wingName: string;
  wing: { name: string; symmetric: boolean; x_secs: XSec[] } | null;
  selectedWing: string | null;
  selectedXsecIndex: number | null;
  expandedSet: Set<string>;
  callbacks: BuildNodeCallbacks;
}

// ── Shared helpers ─────────────────────────────────────────────

function getTedData(xsec: XSec): Record<string, unknown> | null {
  const ted = xsec.trailing_edge_device ?? xsec.control_surface;
  if (ted && typeof ted === "object" && Object.keys(ted).length > 0) {
    return ted;
  }
  return null;
}

// ── Shared TED / Spar node builders ─────────────────────────────

function buildTedNode(
  id: string,
  wingName: string,
  xsecIndex: number,
  xsec: XSec,
  callbacks: BuildNodeCallbacks,
): TreeNode | null {
  const tedObj = getTedData(xsec);
  if (!tedObj) return null;

  const tedName = (tedObj.name as string) ?? "TED";
  return {
    id: `${id}-ted`,
    label: `TED: ${tedName}`,
    level: 3,
    leaf: true,
    chip: "TED",
    onEdit: callbacks.onEditTed ? () => callbacks.onEditTed!(wingName, xsecIndex, tedObj) : undefined,
    onDelete: callbacks.onDeleteTed ? () => {
      if (confirm(`Delete control surface "${tedName}"?`)) callbacks.onDeleteTed!(wingName, xsecIndex);
    } : undefined,
  };
}

function buildSparNodes(
  id: string,
  wingName: string,
  xsecIndex: number,
  xsec: XSec,
  callbacks: BuildNodeCallbacks,
): TreeNode[] {
  const spareList = Array.isArray(xsec.spare_list) ? xsec.spare_list as Record<string, unknown>[] : [];
  const nodes: TreeNode[] = [];

  for (let s = 0; s < spareList.length; s++) {
    const sp = spareList[s];
    const pos = ((sp.spare_position_factor as number ?? 0) * 100).toFixed(0);
    const w = ((sp.spare_support_dimension_width as number ?? 0) * 1000).toFixed(1);
    const h = ((sp.spare_support_dimension_height as number ?? 0) * 1000).toFixed(1);
    nodes.push({
      id: `${id}-spar-${s}`,
      label: `spar @ ${pos}%`,
      level: 3,
      leaf: true,
      detail: `${w}x${h} mm`,
      onEdit: callbacks.onEditSpar ? () => callbacks.onEditSpar!(wingName, xsecIndex, s, sp) : undefined,
      onDelete: callbacks.onDeleteSpar ? () => {
        if (confirm(`Delete spar ${s}?`)) callbacks.onDeleteSpar!(wingName, xsecIndex, s);
      } : undefined,
    });
  }

  return nodes;
}

/** Build the add-button handler for a segment/xsec node. */
function buildAddHandler(
  wingName: string,
  index: number,
  xsec: XSec,
  callbacks: BuildNodeCallbacks,
): ((e: React.MouseEvent) => void) | undefined {
  if (!callbacks.onAddSpar && !callbacks.onAddTed) return undefined;

  const hasTed = getTedData(xsec) !== null;

  return (e: React.MouseEvent) => {
    if (hasTed) {
      callbacks.onAddSpar?.(wingName, index);
    } else {
      callbacks.onAddMenu?.(wingName, index, hasTed, e.clientX, e.clientY);
    }
  };
}

/** Build detail rows for an expanded segment (chord, dimensions, TED, spars). */
function buildExpandedSegmentDetails(
  segId: string,
  wingName: string,
  segIdx: number,
  root: XSec,
  tip: XSec,
  callbacks: BuildNodeCallbacks,
): TreeNode[] {
  const nodes: TreeNode[] = [];
  const rootChord = (root.chord * 1000).toFixed(1);
  const tipChord = (tip.chord * 1000).toFixed(1);
  const length = (Math.abs(tip.xyz_le[1] - root.xyz_le[1]) * 1000).toFixed(1);
  const sweep = ((tip.xyz_le[0] - root.xyz_le[0]) * 1000).toFixed(1);

  nodes.push(
    {
      id: `${segId}-root`, label: `root: ${airfoilShort(root.airfoil)} · ${rootChord} mm`,
      level: 3, leaf: true, muted: true,
    },
    {
      id: `${segId}-tip`, label: `tip: ${airfoilShort(tip.airfoil)} · ${tipChord} mm`,
      level: 3, leaf: true, muted: true,
    },
    {
      id: `${segId}-dims`, label: `length ${length} mm · sweep ${sweep} mm`,
      level: 3, leaf: true, muted: true, mono: true,
    },
  );

  const tedNode = buildTedNode(segId, wingName, segIdx, root, callbacks);
  if (tedNode) nodes.push(tedNode);

  nodes.push(...buildSparNodes(segId, wingName, segIdx, root, callbacks));
  return nodes;
}

// ── Build tree nodes for a single segment (extracted for complexity) ──

function buildSingleSegmentNodes(ctx: BuildNodeContext, i: number): TreeNode[] {
  const { wingName, wing, selectedWing, selectedXsecIndex, expandedSet, callbacks } = ctx;
  if (!wing) return [];
  const root = wing.x_secs[i];
  const tip = wing.x_secs[i + 1];
  const segId = `${wingName}-seg${i}`;
  const isSelected = selectedWing === wingName && selectedXsecIndex === i;
  const segExpanded = expandedSet.has(segId);
  const nodes: TreeNode[] = [];

  // Insert point before this segment (except before first)
  if (i > 0 && callbacks.onInsertXsec) {
    nodes.push({
      id: `${wingName}-ins-${i}`,
      label: "insert",
      level: 2,
      isInsertPoint: true,
      onInsert: () => callbacks.onInsertXsec!(wingName, i),
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
    onClick: () => { callbacks.selectWing(wingName); callbacks.selectXsec(i); },
    onEdit: callbacks.onEditNode ? () => { callbacks.selectWing(wingName); callbacks.selectXsec(i); callbacks.onEditNode!(); } : undefined,
    onDelete: callbacks.onDeleteXsec ? () => {
      if (confirm(`Delete segment ${i}?`)) callbacks.onDeleteXsec(wingName, i);
    } : undefined,
    onAdd: buildAddHandler(wingName, i, root, callbacks),
  });

  // Expanded segment details
  if (segExpanded) {
    nodes.push(...buildExpandedSegmentDetails(segId, wingName, i, root, tip, callbacks));
  }

  return nodes;
}

// ── Build nodes for WingConfig mode (segments) ──────────────────

function buildSegmentNodes(
  ctx: BuildNodeContext,
  nosePntMm: number[] | null,
): TreeNode[] {
  const { wingName, wing, expandedSet, callbacks } = ctx;
  const nodes: TreeNode[] = [];
  const wingExpanded = expandedSet.has(`wing-${wingName}`);

  nodes.push({
    id: `wing-${wingName}`,
    label: wingName,
    level: 1,
    expanded: wingExpanded,
    chip: "WING",
    onClick: () => callbacks.selectWing(wingName),
    onDelete: () => {
      if (confirm(`Delete wing "${wingName}"?`)) {
        callbacks.onDeleteXsec(wingName, -1);
      }
    },
  });

  if (!wingExpanded) return nodes;
  if (wing?.name !== wingName) {
    nodes.push({ id: `${wingName}-loading`, label: "Loading…", level: 2, leaf: true, muted: true });
    return nodes;
  }

  // nose_pnt row — from WingConfig (nose_pnt is in meters, display in mm)
  if (nosePntMm) {
    nodes.push({
      id: `${wingName}-nosepnt`,
      label: `nose_pnt [${nosePntMm.map((v: number) => v.toFixed(1)).join(", ")}] mm`,
      level: 2, leaf: true, muted: true, mono: true,
    });
  }

  // Segments (each segment = pair of consecutive x_secs)
  const segCount = wing.x_secs.length - 1;
  for (let i = 0; i < segCount; i++) {
    nodes.push(...buildSingleSegmentNodes(ctx, i));
  }

  // "+ segment" at the end
  if (callbacks.onAddSegment) {
    nodes.push({
      id: `${wingName}-add`,
      label: "+ segment",
      level: 2, leaf: true, muted: true,
      onClick: () => callbacks.onAddSegment!(wingName),
    });
  }

  return nodes;
}

// ── Build nodes for ASB mode (x_secs) ───────────────────────────

function buildXsecNodes(ctx: BuildNodeContext): TreeNode[] {
  const { wingName, wing, selectedWing, selectedXsecIndex, expandedSet, callbacks } = ctx;
  const nodes: TreeNode[] = [];
  const wingExpanded = expandedSet.has(`wing-${wingName}`);

  nodes.push({
    id: `wing-${wingName}`,
    label: wingName,
    level: 1,
    expanded: wingExpanded,
    chip: "WING",
    onClick: () => callbacks.selectWing(wingName),
    onDelete: () => {
      if (confirm(`Delete wing "${wingName}"?`)) {
        callbacks.onDeleteXsec(wingName, -1);
      }
    },
  });

  if (!wingExpanded) return nodes;
  if (wing?.name !== wingName) {
    nodes.push({ id: `${wingName}-loading`, label: "Loading…", level: 2, leaf: true, muted: true });
    return nodes;
  }

  wing.x_secs.forEach((xsec, i) => {
    if (i > 0 && callbacks.onInsertXsec) {
      nodes.push({
        id: `${wingName}-xsec-ins-${i}`,
        label: "insert",
        level: 2,
        isInsertPoint: true,
        onInsert: () => callbacks.onInsertXsec!(wingName, i),
      });
    }

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
      onClick: () => { callbacks.selectWing(wingName); callbacks.selectXsec(i); },
      onEdit: callbacks.onEditNode ? () => { callbacks.selectWing(wingName); callbacks.selectXsec(i); callbacks.onEditNode!(); } : undefined,
      onDelete: callbacks.onDeleteXsec ? () => {
        if (confirm(`Delete x_sec ${i}?`)) callbacks.onDeleteXsec(wingName, i);
      } : undefined,
      onAdd: buildAddHandler(wingName, i, xsec, callbacks),
    });

    if (xsecExpanded) {
      nodes.push(
        {
          id: `${xsecId}-airfoil`,
          label: `airfoil · ${airfoilShort(xsec.airfoil)}`,
          level: 3, leaf: true, muted: true,
        },
        {
          id: `${xsecId}-chord`,
          label: `chord ${(xsec.chord * 1000).toFixed(1)} mm`,
          level: 3, leaf: true, muted: true, mono: true,
        },
        {
          id: `${xsecId}-twist`,
          label: `twist ${xsec.twist}°`,
          level: 3, leaf: true, muted: true, mono: true,
        },
        {
          id: `${xsecId}-xyz`,
          label: `xyz_le [${xsec.xyz_le.map((v: number) => (v * 1000).toFixed(1)).join(", ")}] mm`,
          level: 3, leaf: true, muted: true, mono: true,
        },
      );

      const tedNode = buildTedNode(xsecId, wingName, i, xsec, callbacks);
      if (tedNode) nodes.push(tedNode);

      nodes.push(...buildSparNodes(xsecId, wingName, i, xsec, callbacks));
    }
  });

  if (callbacks.onAddSegment) {
    nodes.push({
      id: `${wingName}-xsec-add`,
      label: "+ x_sec",
      level: 2, leaf: true, muted: true,
      onClick: () => callbacks.onAddSegment!(wingName),
    });
  }

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

// ── Build callbacks object — single conditional instead of 18 ternaries ──

interface BuildCallbacksOptions {
  isCrossModelView: boolean;
  selectWing: (n: string | null) => void;
  selectXsec: (i: number | null) => void;
  handleDeleteXsec: (wn: string, i: number) => void;
  handleAddSegment: (wn: string) => void;
  handleInsertXsec: (wn: string, i: number) => void;
  setSegAddMenu: (v: { wingName: string; xsecIndex: number; hasTed: boolean; x: number; y: number }) => void;
  onNodeEdit?: () => void;
  onEditSpar?: (wingName: string, xsecIndex: number, sparIndex: number, data: Record<string, unknown>) => void;
  onDeleteSpar?: (wingName: string, xsecIndex: number, sparIndex: number) => void;
  onEditTed?: (wingName: string, xsecIndex: number, data: Record<string, unknown>) => void;
  onDeleteTed?: (wingName: string, xsecIndex: number) => void;
  onAddSpar?: (wingName: string, xsecIndex: number) => void;
  onAddTed?: (wingName: string, xsecIndex: number) => void;
}

function buildCallbacks(opts: BuildCallbacksOptions): BuildNodeCallbacks {
  const noOp = () => {};

  if (opts.isCrossModelView) {
    return {
      selectWing: opts.selectWing,
      selectXsec: opts.selectXsec,
      onDeleteXsec: noOp,
      onAddSegment: noOp,
      onInsertXsec: noOp,
    };
  }

  return {
    selectWing: opts.selectWing,
    selectXsec: opts.selectXsec,
    onDeleteXsec: opts.handleDeleteXsec,
    onEditNode: opts.onNodeEdit,
    onEditSpar: opts.onEditSpar,
    onDeleteSpar: opts.onDeleteSpar,
    onEditTed: opts.onEditTed,
    onDeleteTed: opts.onDeleteTed,
    onAddSpar: opts.onAddSpar,
    onAddTed: opts.onAddTed,
    onAddMenu: (wn, xi, hasTed, cx, cy) => opts.setSegAddMenu({ wingName: wn, xsecIndex: xi, hasTed, x: cx, y: cy }),
    onAddSegment: opts.handleAddSegment,
    onInsertXsec: opts.handleInsertXsec,
  };
}

// ── Build complete tree data ────────────────────────────────────

interface BuildTreeDataParams {
  wingNames: string[];
  fuselageNames: string[];
  aeroplaneName?: string;
  expandedSet: Set<string>;
  wing: { name: string; symmetric: boolean; x_secs: XSec[] } | null;
  wingConfig: { nose_pnt: number[] | null } | null;
  treeMode: string;
  selectedWing: string | null;
  selectedXsecIndex: number | null;
  selectedFuselage: string | null;
  selectedFuselageXsecIndex: number | null;
  fuselage: { x_secs: { a: number; b: number; n: number }[] } | null;
  isWingVisible?: (wingName: string) => boolean;
  isWingLoading?: (wingName: string) => boolean;
  isFuselageVisible?: (name: string) => boolean;
  onTogglePreview?: (wingName: string) => void;
  onToggleAllPreview?: (wingNames: string[]) => void;
  onToggleFuselagePreview?: (name: string) => void;
  onNodeEdit?: () => void;
  callbacks: BuildNodeCallbacks;
  selectFuselage: (name: string | null) => void;
  selectFuselageXsec: (i: number | null) => void;
  handleDeleteFuselage: (fusName: string) => void;
  handleDeleteFuselageXsec: (fusName: string, index: number) => void;
  setAddMenuOpen: (v: boolean | ((prev: boolean) => boolean)) => void;
}

function buildTreeData(params: BuildTreeDataParams): TreeNode[] {
  const treeData: TreeNode[] = [];
  const rootExpanded = params.expandedSet.has("root");
  const anyWingVisible = params.onTogglePreview ? params.wingNames.some((wn) => params.isWingVisible?.(wn)) : false;
  const anyWingLoading = params.onTogglePreview ? params.wingNames.some((wn) => params.isWingLoading?.(wn)) : false;

  treeData.push({
    id: "root",
    label: params.aeroplaneName ?? "Aeroplane",
    level: 0,
    expanded: rootExpanded,
    previewVisible: anyWingVisible,
    previewLoading: anyWingLoading,
    onPreviewToggle: params.onToggleAllPreview
      ? () => params.onToggleAllPreview!(params.wingNames)
      : undefined,
    onAdd: () => params.setAddMenuOpen((v: boolean) => !v),
  });

  if (!rootExpanded) return treeData;

  // Wing nodes
  for (const wn of params.wingNames) {
    const ctx: BuildNodeContext = {
      wingName: wn,
      wing: params.wing,
      selectedWing: params.selectedWing,
      selectedXsecIndex: params.selectedXsecIndex,
      expandedSet: params.expandedSet,
      callbacks: params.callbacks,
    };

    const nodes = params.treeMode === "wingconfig"
      ? buildSegmentNodes(ctx, params.wingConfig?.nose_pnt ?? null)
      : buildXsecNodes(ctx);

    // Attach preview toggle to the wing root node
    if (nodes.length > 0 && params.onTogglePreview) {
      nodes[0].previewVisible = params.isWingVisible?.(wn) ?? false;
      nodes[0].previewLoading = params.isWingLoading?.(wn) ?? false;
      nodes[0].onPreviewToggle = () => params.onTogglePreview!(wn);
    }
    treeData.push(...nodes);
  }

  // Fuselage nodes
  buildFuselageNodes(treeData, params);

  return treeData;
}

function buildFuselageNodes(treeData: TreeNode[], params: BuildTreeDataParams): void {
  for (const fn of params.fuselageNames) {
    const fusExpanded = params.expandedSet.has(`fuselage-${fn}`);
    treeData.push({
      id: `fuselage-${fn}`,
      label: fn,
      level: 1,
      expanded: fusExpanded,
      chip: "FUSELAGE",
      onClick: () => {
        params.selectFuselage(fn);
      },
      onDelete: () => params.handleDeleteFuselage(fn),
      previewVisible: params.isFuselageVisible?.(fn) ?? true,
      onPreviewToggle: params.onToggleFuselagePreview
        ? () => params.onToggleFuselagePreview!(fn)
        : undefined,
    });

    if (!fusExpanded) continue;

    const hasFusData = params.fuselage && params.selectedFuselage === fn && params.fuselage.x_secs;
    if (!hasFusData) {
      treeData.push({
        id: `fuselage-${fn}-loading`,
        label: "loading\u2026",
        level: 2,
        leaf: true,
        muted: true,
      });
      continue;
    }

    for (let i = 0; i < params.fuselage!.x_secs.length; i++) {
      const xs = params.fuselage!.x_secs[i];
      const isXsSelected = params.selectedFuselageXsecIndex === i;
      treeData.push({
        id: `fuselage-${fn}-xsec-${i}`,
        label: `xsec ${i}`,
        level: 2,
        expanded: false,
        leaf: true,
        selected: isXsSelected,
        detail: `a=${(xs.a * 1000).toFixed(1)}mm b=${(xs.b * 1000).toFixed(1)}mm n=${xs.n.toFixed(1)}`,
        onClick: () => {
          params.selectFuselage(fn);
          params.selectFuselageXsec(i);
        },
        onEdit: () => {
          params.selectFuselage(fn);
          params.selectFuselageXsec(i);
          params.onNodeEdit?.();
        },
        onDelete: () => params.handleDeleteFuselageXsec(fn, i),
      });
    }
  }
}

// ── Props ───────────────────────────────────────────────────────

interface AeroplaneTreeProps {
  aeroplaneId: string | null;
  wingNames: string[];
  fuselageNames?: string[];
  aeroplaneName?: string;
  isWingVisible?: (wingName: string) => boolean;
  isWingLoading?: (wingName: string) => boolean;
  onTogglePreview?: (wingName: string) => void;
  onToggleAllPreview?: (wingNames: string[]) => void;
  isFuselageVisible?: (name: string) => boolean;
  onToggleFuselagePreview?: (name: string) => void;
  onCollapseTree?: () => void;
  onNodeEdit?: () => void;
  onWingSaved?: () => void;
  onFuselageSaved?: () => void;
  onEditSpar?: (wingName: string, xsecIndex: number, sparIndex: number, data: Record<string, unknown>) => void;
  onDeleteSpar?: (wingName: string, xsecIndex: number, sparIndex: number) => void;
  onEditTed?: (wingName: string, xsecIndex: number, data: Record<string, unknown>) => void;
  onDeleteTed?: (wingName: string, xsecIndex: number) => void;
  onAddSpar?: (wingName: string, xsecIndex: number) => void;
  onAddTed?: (wingName: string, xsecIndex: number) => void;
}

// ── Component ───────────────────────────────────────────────────

export function AeroplaneTree(props: Readonly<AeroplaneTreeProps>) {
  const { aeroplaneId, wingNames, fuselageNames = [], aeroplaneName, isWingVisible, isWingLoading, onTogglePreview, onToggleAllPreview, isFuselageVisible, onToggleFuselagePreview, onCollapseTree, onNodeEdit, onWingSaved, onFuselageSaved, onEditSpar, onDeleteSpar, onEditTed, onDeleteTed, onAddSpar, onAddTed } = props;
  const { selectedWing, selectedXsecIndex, selectWing, selectXsec, selectedFuselage, selectedFuselageXsecIndex, selectFuselage, selectFuselageXsec, treeMode, setTreeMode } =
    useAeroplaneContext();
  const { wing, isLoading, mutate: mutateWing } = useWing(aeroplaneId, selectedWing);
  const { wingConfig } = useWingConfig(aeroplaneId, selectedWing);

  // When the selected wing has a design_model, default to its preferred tree mode
  const wingDesignModel = wing?.design_model ?? null;

  // Auto-set treeMode to match wing's design_model when selecting a wing
  useEffect(() => {
    if (wingDesignModel === "wc" && treeMode !== "wingconfig") {
      setTreeMode("wingconfig");
    } else if (wingDesignModel === "asb" && treeMode !== "asb" && treeMode !== "fuselage") {
      setTreeMode("asb");
    }
  }, [wingDesignModel, selectedWing]); // eslint-disable-line react-hooks/exhaustive-deps

  const [expandedSet, setExpandedSet] = useState<Set<string>>(() => {
    const s = new Set<string>();
    s.add("root");
    if (wingNames.length > 0) s.add(`wing-${wingNames[0]}`);
    return s;
  });

  // Load data for the selected fuselage (set by clicking a fuselage node)
  const { fuselage, mutate: mutateFuselage } = useFuselage(aeroplaneId, selectedFuselage);
  const { mutate: mutateFuselageList } = useFuselages(aeroplaneId);

  // Add menu state
  const [addMenuOpen, setAddMenuOpen] = useState(false);
  const [importFuselageOpen, setImportFuselageOpen] = useState(false);
  const [createWingOpen, setCreateWingOpen] = useState(false);
  // Segment add menu: tracks which segment has an open add menu + click position
  const [segAddMenu, setSegAddMenu] = useState<{ wingName: string; xsecIndex: number; hasTed: boolean; x: number; y: number } | null>(null);

  function handleAddWing() {
    setAddMenuOpen(false);
    setCreateWingOpen(true);
  }

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
      airfoil: lastXsec?.airfoil ?? "naca0012",
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
      onWingSaved?.();
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

  async function handleDeleteFuselage(fusName: string) {
    if (!aeroplaneId) return;
    if (!confirm(`Delete fuselage "${fusName}"?`)) return;
    const res = await fetch(
      `${API_BASE}/aeroplanes/${aeroplaneId}/fuselages/${encodeURIComponent(fusName)}`,
      { method: "DELETE" },
    );
    if (!res.ok) { alert(`Delete fuselage failed: ${res.status}`); return; }
    if (selectedFuselage === fusName) selectFuselage(null);
    await mutateFuselageList();
  }

  async function handleDeleteFuselageXsec(fusName: string, index: number) {
    if (!aeroplaneId) return;
    const res = await fetch(
      `${API_BASE}/aeroplanes/${aeroplaneId}/fuselages/${encodeURIComponent(fusName)}/cross_sections/${index}`,
      { method: "DELETE" },
    );
    if (!res.ok) { alert(`Delete xsec failed: ${res.status}`); return; }
    await mutateFuselage();
    if (selectedFuselageXsecIndex !== null && selectedFuselageXsecIndex >= index) {
      selectFuselageXsec(Math.max(0, selectedFuselageXsecIndex - 1));
    }
  }

  // Determine cross-model view once, build callbacks once
  const isCrossModelView = wingDesignModel != null && (
    (wingDesignModel === "wc" && treeMode === "asb") ||
    (wingDesignModel === "asb" && treeMode === "wingconfig")
  );

  const callbacks = buildCallbacks({
    isCrossModelView,
    selectWing, selectXsec,
    handleDeleteXsec, handleAddSegment, handleInsertXsec,
    setSegAddMenu,
    onNodeEdit, onEditSpar, onDeleteSpar, onEditTed, onDeleteTed, onAddSpar, onAddTed,
  });

  // Build tree data
  const treeData = buildTreeData({
    wingNames,
    fuselageNames,
    aeroplaneName,
    expandedSet,
    wing,
    wingConfig,
    treeMode,
    selectedWing,
    selectedXsecIndex,
    selectedFuselage,
    selectedFuselageXsecIndex,
    fuselage,
    isWingVisible,
    isWingLoading,
    isFuselageVisible,
    onTogglePreview,
    onToggleAllPreview,
    onToggleFuselagePreview,
    onNodeEdit,
    callbacks,
    selectFuselage,
    selectFuselageXsec,
    handleDeleteFuselage,
    handleDeleteFuselageXsec,
    setAddMenuOpen,
  });

  return (
    <div className="flex h-full min-h-0 flex-col rounded-xl border border-border bg-card p-3 px-4 overflow-hidden">
      {/* Header with collapse button */}
      <div className="mb-2 flex items-center gap-2">
        {onCollapseTree && (
          <button
            onClick={onCollapseTree}
            className="flex size-6 items-center justify-center rounded-xl text-muted-foreground hover:bg-sidebar-accent"
            title="Collapse tree panel"
          >
            <PanelLeftClose size={14} />
          </button>
        )}
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">
          Aeroplane Tree
        </span>
      </div>

      {/* Tree rows */}
      <div className="relative flex flex-1 flex-col gap-0.5 overflow-y-auto">
        {isLoading && wingNames.length === 0 ? (
          <span className="text-[13px] text-muted-foreground">Loading...</span>
        ) : (
          treeData.map((node) => (
            <TreeRow key={node.id} node={node} onToggle={() => toggleExpand(node.id)} onNodeEdit={onNodeEdit} />
          ))
        )}
        {addMenuOpen && (
          <>
            <div className="fixed inset-0 z-30" aria-hidden="true" onClick={() => setAddMenuOpen(false)} onKeyDown={(e) => { if (e.key === "Escape") setAddMenuOpen(false); }} />
            <div className="absolute right-2 top-1 z-40 w-44 rounded-xl border border-border bg-card shadow-lg">
              <button
                onClick={() => { setAddMenuOpen(false); handleAddWing(); }}
                className="flex w-full items-center gap-2 px-3 py-2 text-[12px] text-foreground hover:bg-sidebar-accent rounded-t-xl"
              >
                <Plus size={12} />
                Wing
              </button>
              <button
                onClick={() => { setAddMenuOpen(false); setImportFuselageOpen(true); }}
                className="flex w-full items-center gap-2 px-3 py-2 text-[12px] text-foreground hover:bg-sidebar-accent rounded-b-xl"
              >
                <Plus size={12} />
                Fuselage
              </button>
            </div>
          </>
        )}
      </div>

      {/* Segment add menu (Spar / Control Surface) — positioned at click location */}
      {segAddMenu && (
        <>
          <div className="fixed inset-0 z-30" aria-hidden="true" onClick={() => setSegAddMenu(null)} onKeyDown={(e) => { if (e.key === "Escape") setSegAddMenu(null); }} />
          <div
            className="fixed z-40 w-52 rounded-xl border border-border bg-card shadow-lg"
            style={{ left: segAddMenu.x, top: segAddMenu.y }}
          >
            <button
              onClick={() => { onAddSpar?.(segAddMenu.wingName, segAddMenu.xsecIndex); setSegAddMenu(null); }}
              className="flex w-full items-center gap-2 px-3 py-2 text-[12px] text-foreground hover:bg-sidebar-accent rounded-t-xl"
            >
              <Plus size={12} />
              Add Spar
            </button>
            {!segAddMenu.hasTed && (
              <button
                onClick={() => { onAddTed?.(segAddMenu.wingName, segAddMenu.xsecIndex); setSegAddMenu(null); }}
                className="flex w-full items-center gap-2 px-3 py-2 text-[12px] text-foreground hover:bg-sidebar-accent rounded-b-xl"
              >
                <Plus size={12} />
                Add Control Surface
              </button>
            )}
          </div>
        </>
      )}

      <CreateWingDialog
        open={createWingOpen}
        onClose={() => setCreateWingOpen(false)}
        aeroplaneId={aeroplaneId}
        onCreated={async (wingName, designModel) => {
          onWingSaved?.();
          await mutateWing();
          selectWing(wingName);
          setTreeMode(designModel === "wc" ? "wingconfig" : "asb");
        }}
      />

      <ImportFuselageDialog
        open={importFuselageOpen}
        onClose={() => setImportFuselageOpen(false)}
        aeroplaneId={aeroplaneId}
        onSaved={() => {
          mutateFuselageList();
          onFuselageSaved?.();
        }}
      />
    </div>
  );
}

// ── TreeRow ─────────────────────────────────────────────────────

function TreeRow({ node, onToggle }: Readonly<{ node: TreeNode; onToggle: () => void; onNodeEdit?: () => void }>) {
  if (node.isInsertPoint) {
    return (
      <div
        className="flex items-center gap-1 py-0.5 opacity-30 hover:opacity-100"
        style={{ paddingLeft: `${node.level * 20}px` }}
      >
        <div className="h-px flex-1 bg-border" />
        <button
          onClick={() => node.onInsert?.()}
          className="flex items-center gap-1 rounded-full px-2 py-0.5 text-[9px] text-muted-foreground hover:text-primary"
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
      className={`group flex items-center gap-2 rounded-xl py-1.5 hover:bg-sidebar-accent ${
        node.selected ? "bg-sidebar-accent font-semibold" : ""
      }`}
      style={{ paddingLeft: `${indent}px`, cursor: "pointer" }}
      role="treeitem"
      aria-selected={node.selected ?? false}
      tabIndex={0}
      onClick={handleClick}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); handleClick(); } }}
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

      {node.detail && (
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[9px] text-muted-foreground">
          {node.detail}
        </span>
      )}

      <span className="flex-1" />

      {node.onEdit && (
        <button
          onClick={(e) => { e.stopPropagation(); node.onEdit?.(); }}
          className="hidden h-5 w-5 items-center justify-center rounded-xl text-muted-foreground hover:bg-sidebar-accent hover:text-foreground group-hover:flex"
          title="Edit"
        >
          <Pencil size={10} />
        </button>
      )}

      {node.onDelete && (
        <button
          onClick={(e) => { e.stopPropagation(); node.onDelete?.(); }}
          className="hidden h-5 w-5 items-center justify-center rounded-xl group-hover:flex"
        >
          <Trash2 size={12} className="text-destructive" />
        </button>
      )}

      {node.onAdd && (
        <button
          onClick={(e) => { e.stopPropagation(); node.onAdd?.(e); }}
          className="hidden h-5 w-5 items-center justify-center rounded-xl text-muted-foreground hover:bg-sidebar-accent hover:text-foreground group-hover:flex"
          title="Add"
        >
          <Plus size={12} />
        </button>
      )}

      {node.onPreviewToggle && (
        <button
          onClick={(e) => { e.stopPropagation(); node.onPreviewToggle?.(); }}
          className={`flex h-5 w-5 items-center justify-center rounded-xl ${
            node.previewVisible ? "text-primary" : "text-muted-foreground opacity-40 group-hover:opacity-100"
          }`}
          title={node.previewVisible ? "Hide 3D preview" : "Show 3D preview"}
        >
          {node.previewLoading && <Loader size={12} className="animate-spin" />}
          {!node.previewLoading && node.previewVisible && <Eye size={12} />}
          {!node.previewLoading && !node.previewVisible && <EyeOff size={12} />}
        </button>
      )}
    </div>
  );
}

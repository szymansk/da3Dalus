"use client";

/**
 * VersionGraphOverlay — GitKraken-style version graph modal (gh-961).
 *
 * Replaces `VersionHistoryPanel` as the entry point for version history.
 * Renders as a large centered modal (~80vw, max-w-[1100px], ~80vh).
 *
 * Props:
 *   rootId           — integer PK of the lineage root; null disables fetching
 *   currentHeadId    — integer PK of the current head node
 *   aeroplaneId      — integer PK used for snapshot/branch actions
 *   aeroplaneLabel   — display name for the aircraft (shown in header)
 *   onClose          — called when the user dismisses the overlay
 *   onSwitchAeroplane — called after branch operations with the new head UUID
 */

import { useState, useCallback, useEffect, useMemo, useRef, useLayoutEffect } from "react";
import { X, GitBranch, Camera, GitFork, RotateCcw, Star, Trash2, Pencil, ChevronDown, ListFilter } from "lucide-react";
import { useLineageTree, useVersionActions, useCompareNodes } from "@/hooks/useVersioning";
import { VersionCompareView } from "@/components/workbench/VersionCompareView";
import { VersionGraph } from "@/components/workbench/VersionGraph";
import {
  getVersionGraphViewState,
  patchVersionGraphViewState,
} from "@/lib/versionGraphViewState";
import type { TreeOut, TreeNodeOut, BranchOut } from "@/types/versioning";

// ---------------------------------------------------------------------------
// Re-used inline branch/snapshot name input
// ---------------------------------------------------------------------------

interface NameInputProps {
  placeholder?: string;
  ariaLabel?: string;
  initialValue?: string;
  onConfirm: (name: string) => void;
  onCancel: () => void;
  busy: boolean;
  confirmLabel?: string;
  confirmAriaLabel?: string;
}

function NameInput({
  placeholder,
  ariaLabel = "Branch name",
  initialValue = "",
  onConfirm,
  onCancel,
  busy,
  confirmLabel = "OK",
  confirmAriaLabel = "Confirm branch name",
}: NameInputProps) {
  const [value, setValue] = useState(initialValue);

  return (
    <div className="flex gap-1.5 mt-1">
      <input
        autoFocus
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && value.trim()) onConfirm(value.trim());
          if (e.key === "Escape") onCancel();
        }}
        placeholder={placeholder ?? "name"}
        disabled={busy}
        aria-label={ariaLabel}
        className="min-w-0 flex-1 rounded border border-border bg-card-muted px-2 py-1 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-50"
      />
      <button
        type="button"
        onClick={() => { if (value.trim()) onConfirm(value.trim()); }}
        disabled={busy || !value.trim()}
        aria-label={confirmAriaLabel}
        className="rounded bg-primary px-2 py-1 text-[11px] font-medium text-primary-foreground disabled:opacity-50"
      >
        {confirmLabel}
      </button>
      <button
        type="button"
        onClick={onCancel}
        disabled={busy}
        aria-label="Cancel"
        className="rounded bg-sidebar-accent px-2 py-1 text-[11px] text-muted-foreground disabled:opacity-50"
      >
        ✕
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Toolbar button
// ---------------------------------------------------------------------------

interface ToolbarButtonProps {
  readonly label: string;
  readonly icon: React.ReactNode;
  readonly onClick: () => void;
  readonly disabled: boolean;
  readonly title?: string;
  readonly destructive?: boolean;
  readonly ariaLabel?: string;
}

function ToolbarButton({
  label,
  icon,
  onClick,
  disabled,
  title,
  destructive = false,
  ariaLabel,
}: ToolbarButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={title}
      aria-label={ariaLabel ?? label}
      className={`flex items-center gap-1.5 rounded px-3 py-1.5 text-[11px] font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${
        destructive
          ? "bg-destructive/10 text-destructive hover:bg-destructive/20"
          : "bg-sidebar-accent text-muted-foreground hover:bg-sidebar-accent/80 hover:text-foreground"
      }`}
    >
      {icon}
      {label}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Toolbar
// ---------------------------------------------------------------------------

type ToolbarAction = "snapshot" | "branchFrom" | "restore" | "adopt" | "discard" | "rename" | null;

interface VersionGraphToolbarProps {
  readonly selectedNode: TreeNodeOut | null;
  readonly selectedBranch: BranchOut | null;
  readonly compareSet: Set<number>;
  readonly busy: boolean;
  readonly discardPending: boolean;
  readonly adoptPending: boolean;
  readonly activeInput: ToolbarAction;
  readonly onActionClick: (action: ToolbarAction) => void;
  readonly onNameConfirm: (name: string) => void;
  readonly onNameCancel: () => void;
  readonly onConfirmDiscard: () => void;
  readonly onCancelDiscard: () => void;
  readonly onConfirmAdopt: () => void;
  readonly onCancelAdopt: () => void;
  readonly onOpenCompare: () => void;
}

function VersionGraphToolbar({
  selectedNode,
  selectedBranch,
  compareSet,
  busy,
  discardPending,
  adoptPending,
  activeInput,
  onActionClick,
  onNameConfirm,
  onNameCancel,
  onConfirmDiscard,
  onCancelDiscard,
  onConfirmAdopt,
  onCancelAdopt,
  onOpenCompare,
}: VersionGraphToolbarProps) {
  // Derive enable rules from spec toolbar table
  const hasSelection = selectedNode !== null;
  const isOnMain = selectedBranch?.is_main ?? false;
  const isSnapshot = selectedNode?.is_immutable ?? false;
  const isEditableHead =
    hasSelection && !isSnapshot && (selectedNode?.is_head ?? false);
  const isSelectedBranchHead =
    hasSelection && (selectedNode?.is_head ?? false);

  // Snapshot: selected node is the editable head of its branch
  const snapshotEnabled = isEditableHead && isSelectedBranchHead && !busy;
  // Branch from: any selection
  const branchFromEnabled = hasSelection && !busy;
  // Restore: selected is_immutable (snapshot)
  const restoreEnabled = hasSelection && isSnapshot && !busy;
  // Adopt / Discard: selected node's branch is not main
  const adoptEnabled = hasSelection && !isOnMain && !busy;
  const discardEnabled = hasSelection && !isOnMain && !busy;
  // Rename: a branch is selected
  const renameEnabled = selectedBranch !== null && !busy;

  const compareCount = compareSet.size;
  const compareEnabled = compareCount === 2 && !busy;

  const selectedBranchName = selectedBranch?.name ?? "this branch";

  // Plain-language action tooltips (gh-964 §1). When a button is disabled we
  // surface the reason WHY; otherwise we explain what the action does.
  const getSnapshotTitle = () => {
    if (!hasSelection) return "Select a node first";
    if (isSnapshot) return "Cannot snapshot an immutable node";
    if (!isEditableHead) return "Only the editable head can be snapshotted";
    return "Save an immutable checkpoint of the current design";
  };

  const getBranchFromTitle = () => {
    if (!hasSelection) return "Select a node first";
    return "Start a new variant from the selected version";
  };

  const getRestoreTitle = () => {
    if (!hasSelection) return "Select a node first";
    if (!isSnapshot) return "Only snapshot nodes can be restored";
    return "Create a new editable branch from this snapshot";
  };

  const getAdoptTitle = () => {
    if (!hasSelection) return "Select a node first";
    if (isOnMain) return "This branch is already main";
    return "Make this branch the active design (main); the current main becomes a normal branch";
  };

  const getDiscardTitle = () => {
    if (!hasSelection) return "Select a node first";
    if (isOnMain) return "Cannot discard the main branch";
    return "Delete this branch and its versions — does not affect the active design";
  };

  const getRenameTitle = () => {
    if (selectedBranch === null) return "Select a branch first";
    return "Rename this branch";
  };

  return (
    <div className="flex flex-col gap-1 border-b border-border px-4 py-2">
      <div className="flex items-center gap-2 flex-wrap">
        {/* Snapshot */}
        <ToolbarButton
          label="Snapshot"
          icon={<Camera size={12} />}
          onClick={() => onActionClick("snapshot")}
          disabled={!snapshotEnabled}
          title={getSnapshotTitle()}
        />

        {/* Branch from */}
        <ToolbarButton
          label="Branch from"
          icon={<GitFork size={12} />}
          onClick={() => onActionClick("branchFrom")}
          disabled={!branchFromEnabled}
          title={getBranchFromTitle()}
        />

        {/* Restore */}
        <ToolbarButton
          label="Restore"
          icon={<RotateCcw size={12} />}
          onClick={() => onActionClick("restore")}
          disabled={!restoreEnabled}
          title={getRestoreTitle()}
        />

        {/* Rename */}
        <ToolbarButton
          label="Rename"
          icon={<Pencil size={12} />}
          onClick={() => onActionClick("rename")}
          disabled={!renameEnabled}
          title={getRenameTitle()}
        />

        {/* Separator */}
        <div className="h-5 w-px bg-border" />

        {/* Adopt — two-step confirm naming the branch */}
        {!adoptPending ? (
          <ToolbarButton
            label="Adopt"
            icon={<Star size={12} />}
            onClick={() => onActionClick("adopt")}
            disabled={!adoptEnabled}
            title={getAdoptTitle()}
          />
        ) : (
          <div className="flex items-center gap-1.5">
            <span className="text-[11px] font-medium text-foreground" aria-live="polite">
              Make &quot;{selectedBranchName}&quot; the active design? The current main becomes a normal branch.
            </span>
            <button
              type="button"
              onClick={onConfirmAdopt}
              disabled={busy}
              aria-label="Confirm adopt"
              className="rounded bg-primary px-2 py-1 text-[11px] font-medium text-primary-foreground disabled:opacity-50"
            >
              Yes, adopt
            </button>
            <button
              type="button"
              onClick={onCancelAdopt}
              disabled={busy}
              aria-label="Cancel adopt"
              className="rounded bg-sidebar-accent px-2 py-1 text-[11px] text-muted-foreground disabled:opacity-50"
            >
              Cancel
            </button>
          </div>
        )}

        {/* Discard — two-step confirm naming the branch */}
        {!discardPending ? (
          <ToolbarButton
            label="Discard"
            icon={<Trash2 size={12} />}
            onClick={() => onActionClick("discard")}
            disabled={!discardEnabled}
            title={getDiscardTitle()}
            destructive
          />
        ) : (
          <div className="flex items-center gap-1.5">
            <span className="text-[11px] font-medium text-destructive" aria-live="polite">
              Delete branch &quot;{selectedBranchName}&quot; and its versions? Your active design is not affected.
            </span>
            <button
              type="button"
              onClick={onConfirmDiscard}
              disabled={busy}
              aria-label="Confirm discard"
              className="rounded bg-destructive px-2 py-1 text-[11px] font-medium text-white disabled:opacity-50"
            >
              Yes, delete
            </button>
            <button
              type="button"
              onClick={onCancelDiscard}
              disabled={busy}
              aria-label="Cancel discard"
              className="rounded bg-sidebar-accent px-2 py-1 text-[11px] text-muted-foreground disabled:opacity-50"
            >
              Cancel
            </button>
          </div>
        )}

        {/* Spacer */}
        <div className="flex-1" />

        {/* Compare */}
        <button
          type="button"
          onClick={onOpenCompare}
          disabled={!compareEnabled}
          aria-label={`Compare (${compareCount})`}
          className="flex items-center gap-1.5 rounded bg-primary/10 px-3 py-1.5 text-[11px] font-medium text-primary transition-colors disabled:cursor-not-allowed disabled:opacity-40 hover:bg-primary/20"
        >
          Compare ({compareCount})
        </button>
      </div>

      {/* Inline name input for snapshot/branchFrom/restore */}
      {activeInput === "snapshot" && (
        <NameInput
          placeholder="snapshot label (e.g. v2.0)"
          ariaLabel="Snapshot label"
          confirmLabel="OK"
          confirmAriaLabel="Confirm snapshot"
          onConfirm={onNameConfirm}
          onCancel={onNameCancel}
          busy={busy}
        />
      )}
      {activeInput === "branchFrom" && (
        <NameInput
          placeholder="new-branch-name"
          ariaLabel="Branch name"
          confirmAriaLabel="Confirm branch name"
          onConfirm={onNameConfirm}
          onCancel={onNameCancel}
          busy={busy}
        />
      )}
      {activeInput === "restore" && (
        <NameInput
          placeholder={`restored-from-${selectedNode?.version_label ?? selectedNode?.id ?? "snapshot"}`}
          ariaLabel="Branch name"
          confirmAriaLabel="Confirm branch name"
          onConfirm={onNameConfirm}
          onCancel={onNameCancel}
          busy={busy}
        />
      )}
      {activeInput === "rename" && (
        <div className="flex flex-col gap-1">
          {/* Name the rename target explicitly so it's unambiguous which branch
              is affected, regardless of any compare checkboxes that are set. */}
          <span className="text-[10px] text-muted-foreground">
            Rename branch{" "}
            <span className="font-medium text-foreground">
              &ldquo;{selectedBranch?.name}&rdquo;
            </span>
          </span>
          <NameInput
            placeholder="branch name"
            ariaLabel={`Rename branch ${selectedBranch?.name ?? ""}`}
            initialValue={selectedBranch?.name ?? ""}
            confirmAriaLabel="Confirm rename"
            onConfirm={onNameConfirm}
            onCancel={onNameCancel}
            busy={busy}
          />
          <span className="text-[9px] text-subtle-foreground">
            Must be unique within this aircraft.
          </span>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Branch filter (gh-981) — dropdown of branch checkboxes
// ---------------------------------------------------------------------------

interface BranchFilterProps {
  readonly branches: readonly BranchOut[];
  readonly visibleBranchIds: ReadonlySet<number>;
  readonly onToggleBranch: (branchId: number) => void;
  readonly onToggleAll: () => void;
  /**
   * Controlled open state. Owned by the parent overlay so the Escape chain
   * can close the dropdown before closing the overlay itself.
   */
  readonly open: boolean;
  /** Called when the dropdown requests to open or close. */
  readonly onOpenChange: (open: boolean) => void;
}

function BranchFilter({ branches, visibleBranchIds, onToggleBranch, onToggleAll, open, onOpenChange }: BranchFilterProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  // Close on outside click so the dropdown doesn't linger.
  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        onOpenChange(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open, onOpenChange]);

  const total = branches.length;
  const shown = branches.filter((b) => visibleBranchIds.has(b.id)).length;
  const someHidden = shown < total;
  const allVisible = shown === total;
  const PANEL_ID = "branch-filter-panel";

  return (
    <div ref={containerRef} data-testid="branch-filter" className="relative">
      <button
        type="button"
        onClick={() => onOpenChange(!open)}
        aria-expanded={open}
        aria-haspopup="true"
        aria-controls={PANEL_ID}
        aria-label="Filter branches"
        className="flex items-center gap-1 rounded bg-sidebar-accent px-2 py-1 text-[10px] font-medium text-muted-foreground transition-colors hover:bg-sidebar-accent/80 hover:text-foreground"
      >
        <ListFilter size={11} className="shrink-0" />
        Show branches
        {someHidden && (
          <span className="text-subtle-foreground">
            ({shown} of {total} branches)
          </span>
        )}
        <ChevronDown size={11} className="shrink-0" />
      </button>

      {open && (
        <div
          id={PANEL_ID}
          role="group"
          aria-label="Branch visibility"
          className="absolute left-0 top-full z-10 mt-1 flex max-h-64 min-w-[180px] flex-col gap-0.5 overflow-y-auto rounded border border-border bg-card p-1.5 shadow-xl"
        >
          {/* All / None quick toggle (gh-981 hobbyist P1) */}
          <div className="flex items-center gap-1.5 border-b border-border pb-1 mb-0.5">
            <button
              type="button"
              onClick={onToggleAll}
              aria-label={allVisible ? "Hide all branches" : "Show all branches"}
              className="rounded px-2 py-0.5 text-[10px] font-medium text-primary hover:bg-sidebar-accent"
            >
              {allVisible ? "None" : "All"}
            </button>
          </div>
          {branches.map((b) => (
            <label
              key={b.id}
              className="flex cursor-pointer items-center gap-2 rounded px-1.5 py-1 text-[11px] text-foreground hover:bg-sidebar-accent"
            >
              <input
                type="checkbox"
                checked={visibleBranchIds.has(b.id)}
                onChange={() => onToggleBranch(b.id)}
                aria-label={b.name}
                className="accent-primary"
              />
              <span className="truncate">{b.name}</span>
            </label>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Panel content (handles null root / loading / empty states)
// ---------------------------------------------------------------------------

interface OverlayContentProps {
  readonly rootId: number | null;
  readonly isLoading: boolean;
  readonly tree: TreeOut | undefined;
  readonly currentHeadId: number | null;
  readonly selectedNodeId: number | null;
  readonly compareSet: Set<number>;
  /** Undefined means "show all" — passes through to VersionGraph's fast-path. */
  readonly visibleBranchIds?: ReadonlySet<number>;
  readonly onSelectNode: (nodeId: number) => void;
  readonly onCheckNode: (nodeId: number) => void;
}

function OverlayContent({
  rootId,
  isLoading,
  tree,
  currentHeadId,
  selectedNodeId,
  compareSet,
  visibleBranchIds,
  onSelectNode,
  onCheckNode,
}: OverlayContentProps) {
  if (rootId === null) {
    return (
      <p className="px-4 py-4 text-[12px] text-muted-foreground">
        No aeroplane selected. Open an aeroplane to view its version history.
      </p>
    );
  }
  if (isLoading) {
    return <p className="px-4 py-4 text-[12px] text-muted-foreground">Loading version graph…</p>;
  }
  if (!tree || tree.nodes.length === 0) {
    return (
      <p className="px-4 py-4 text-[12px] text-muted-foreground">
        No version history yet. Use the Save button to create your first snapshot.
      </p>
    );
  }
  return (
    <VersionGraph
      tree={tree}
      currentHeadId={currentHeadId}
      selectedNodeId={selectedNodeId}
      compareSet={compareSet}
      visibleBranchIds={visibleBranchIds}
      onSelectNode={onSelectNode}
      onCheckNode={onCheckNode}
    />
  );
}

// ---------------------------------------------------------------------------
// Main overlay
// ---------------------------------------------------------------------------

export interface VersionGraphOverlayProps {
  readonly rootId: number | null;
  readonly currentHeadId: number | null;
  readonly aeroplaneId: number | null;
  readonly aeroplaneLabel?: string;
  readonly onClose: () => void;
  /** Called after a branch operation lands — argument is the new head's UUID. */
  readonly onSwitchAeroplane?: (uuid: string) => void;
}

export function VersionGraphOverlay({
  rootId,
  currentHeadId,
  aeroplaneId,
  aeroplaneLabel,
  onClose,
  onSwitchAeroplane,
}: VersionGraphOverlayProps) {
  const { tree, isLoading, error, mutate } = useLineageTree(rootId);
  const actions = useVersionActions(aeroplaneId, rootId);

  // gh-981 §3 — restore view state (scroll/selection/filter) saved when the
  // overlay was last closed for THIS lineage root. The overlay unmounts on
  // close, so the state lives in a module-level cache keyed by rootId. Read
  // once at mount time; `null` rootId (no aeroplane) has no cached entry.
  const cachedViewState = rootId !== null ? getVersionGraphViewState(rootId) : undefined;

  // Map from branch id → branch name, used in VersionCompareView.
  const branchNameMap = useMemo(
    () => new Map((tree?.branches ?? []).map((b) => [b.id, b.name])),
    [tree],
  );

  // Selection state — restored from the view-state cache on mount.
  const [selectedNodeId, setSelectedNodeId] = useState<number | null>(
    () => cachedViewState?.selectedNodeId ?? null,
  );

  // Compare state
  const [compareSet, setCompareSet] = useState<Set<number>>(new Set());
  const [compareOpen, setCompareOpen] = useState(false);

  // Busy / error state
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // Toolbar inline input
  const [activeInput, setActiveInput] = useState<
    "snapshot" | "branchFrom" | "restore" | "rename" | null
  >(null);

  // Discard / adopt two-step confirm
  const [discardPending, setDiscardPending] = useState(false);
  const [adoptPending, setAdoptPending] = useState(false);

  // Branch filter (gh-981). hiddenBranchIds is initialised DIRECTLY from the
  // cache (which now stores hidden ids) — no dependency on `tree` or
  // `allBranchIds`. This fixes the SWR cold-load race: even when tree is
  // undefined at mount we can restore the correct filter state immediately.
  const [hiddenBranchIds, setHiddenBranchIds] = useState<Set<number>>(
    () => new Set(cachedViewState?.hiddenBranchIds ?? []),
  );

  // Lift filter-dropdown open state so the Escape handler can close it first.
  const [filterOpen, setFilterOpen] = useState(false);

  const allBranchIds = useMemo(
    () => (tree?.branches ?? []).map((b) => b.id),
    [tree],
  );

  // When nothing is hidden, pass undefined to VersionGraph so the
  // applyBranchFilter fast-path (=== undefined → return tree unchanged) fires.
  const visibleBranchIds = useMemo((): ReadonlySet<number> | undefined => {
    if (hiddenBranchIds.size === 0) return undefined;
    return new Set(allBranchIds.filter((id) => !hiddenBranchIds.has(id)));
  }, [allBranchIds, hiddenBranchIds]);

  const handleToggleBranch = useCallback((branchId: number) => {
    setHiddenBranchIds((prev) => {
      const next = new Set(prev);
      if (next.has(branchId)) {
        next.delete(branchId);
      } else {
        next.add(branchId);
      }
      return next;
    });
  }, []);

  const handleToggleAll = useCallback(() => {
    setHiddenBranchIds((prev) => {
      // If anything is hidden, restore all; if all visible, hide all.
      if (prev.size > 0) return new Set();
      return new Set(allBranchIds);
    });
  }, [allBranchIds]);

  // gh-981 §3 — scroll container ref. Restore the saved scroll position after
  // the graph paints. Because SWR may deliver the tree after mount (cold load),
  // we re-run whenever `isLoading` flips to false AND the container is actually
  // scrollable. A one-shot ref prevents fighting the user's later scrolling.
  const scrollRef = useRef<HTMLDivElement>(null);
  const scrollRestoredRef = useRef<number | null>(null); // tracks which rootId we restored for

  useLayoutEffect(() => {
    if (rootId === null) return;
    if (isLoading) return;
    // Only restore once per rootId across re-renders (tree arrives async).
    if (scrollRestoredRef.current === rootId) return;
    const el = scrollRef.current;
    const saved = getVersionGraphViewState(rootId)?.scrollTop;
    if (el && saved !== undefined && saved > 0) {
      // Restore even when scrollHeight === 0 (jsdom/SSR): the browser will
      // silently clamp to the max valid value, so setting it is always safe.
      el.scrollTop = saved;
      scrollRestoredRef.current = rootId;
    } else if (el) {
      // saved=0 or no saved state: nothing to restore; mark done anyway.
      scrollRestoredRef.current = rootId;
    }
  // Include isLoading so the effect re-fires when SWR data arrives after cold mount.
  }, [rootId, isLoading]);

  const handleScroll = useCallback(() => {
    if (rootId === null) return;
    const el = scrollRef.current;
    if (el) {
      patchVersionGraphViewState(rootId, { scrollTop: el.scrollTop });
    }
  }, [rootId]);

  // gh-981 §3 — persist selection + filter to the view-state cache whenever
  // they change, so a close→reopen for the same root restores them. Store the
  // explicit hidden-branch list (empty array = "show all"). Storing HIDDEN ids
  // (not visible ids) means restoration works immediately at mount, even when
  // tree is still loading (no dependency on allBranchIds at restore time).
  useEffect(() => {
    if (rootId === null) return;
    patchVersionGraphViewState(rootId, {
      selectedNodeId,
      hiddenBranchIds: [...hiddenBranchIds],
    });
  }, [rootId, selectedNodeId, hiddenBranchIds]);

  // gh-981 §4 — Tombstone clearing: if the cached selectedNodeId references a
  // node that no longer exists in the loaded tree, clear the selection so we
  // don't persist a stale pointer indefinitely.
  useEffect(() => {
    if (!tree || selectedNodeId === null) return;
    const nodeExists = tree.nodes.some((n) => n.id === selectedNodeId);
    if (!nodeExists) {
      setSelectedNodeId(null);
    }
  }, [tree, selectedNodeId]);

  // Derive compare fetch IDs. Sort so A/B assignment is deterministic (lower
  // node id = A), independent of the order the user ticked the checkboxes.
  const compareIds =
    compareSet.size === 2 ? [...compareSet].sort((a, b) => a - b) : null;
  const compareIdA = compareIds?.[0] ?? null;
  const compareIdB = compareIds?.[1] ?? null;

  const {
    compareOut,
    isLoading: compareLoading,
    error: compareError,
  } = useCompareNodes(
    compareOpen ? compareIdA : null,
    compareOpen ? compareIdB : null,
  );

  // Derived: find the selected node + its branch
  const selectedNode =
    selectedNodeId !== null
      ? (tree?.nodes.find((n) => n.id === selectedNodeId) ?? null)
      : null;

  const selectedBranch =
    selectedNode?.branch_id !== undefined && selectedNode.branch_id !== null
      ? (tree?.branches.find((b) => b.id === selectedNode.branch_id) ?? null)
      : null;

  // ---------------------------------------------------------------------------
  // Keyboard: Escape to close
  // ---------------------------------------------------------------------------

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key !== "Escape") return;
      // Dismiss the innermost open layer first, only closing the overlay last.
      if (activeInput !== null) {
        setActiveInput(null);
      } else if (discardPending) {
        setDiscardPending(false);
      } else if (adoptPending) {
        setAdoptPending(false);
      } else if (filterOpen) {
        // Close the branch filter dropdown before closing the overlay (Issue 5).
        setFilterOpen(false);
      } else if (compareOpen) {
        setCompareOpen(false);
      } else {
        onClose();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose, compareOpen, filterOpen, activeInput, discardPending, adoptPending]);

  // ---------------------------------------------------------------------------
  // Orchestration helpers (lifted from VersionHistoryPanel)
  // ---------------------------------------------------------------------------

  const runBranchOp = useCallback(
    async <T,>(fn: () => Promise<T>, getHeadId: (result: T) => number) => {
      setBusy(true);
      setActionError(null);
      try {
        const result = await fn();
        const freshTree = await mutate();
        if (onSwitchAeroplane) {
          const headId = getHeadId(result);
          const headNode = freshTree?.nodes.find((n) => n.id === headId);
          if (headNode) {
            onSwitchAeroplane(headNode.uuid);
          } else {
            // The op landed on the backend but we couldn't locate the new head
            // in the refetched tree — surface it rather than leaving the user
            // on a stale head with no feedback.
            setActionError(
              "Operation succeeded but the workbench could not switch to the new version. Reload to continue editing it.",
            );
          }
        }
      } catch (err) {
        setActionError(err instanceof Error ? err.message : "Action failed.");
      } finally {
        setBusy(false);
      }
    },
    [mutate, onSwitchAeroplane],
  );

  const run = useCallback(
    async (fn: () => Promise<unknown>) => {
      setBusy(true);
      setActionError(null);
      try {
        await fn();
        await mutate();
      } catch (err) {
        setActionError(err instanceof Error ? err.message : "Action failed.");
      } finally {
        setBusy(false);
      }
    },
    [mutate],
  );

  // ---------------------------------------------------------------------------
  // Compare handlers
  // ---------------------------------------------------------------------------

  // Selecting a different node clears any stale action error and dismisses the
  // inline input / discard-confirm that belonged to the previous selection.
  const handleSelectNode = useCallback((nodeId: number) => {
    setSelectedNodeId(nodeId);
    setActionError(null);
    setActiveInput(null);
    setDiscardPending(false);
    setAdoptPending(false);
  }, []);

  const handleCheckNode = useCallback((nodeId: number) => {
    setCompareSet((prev) => {
      const next = new Set(prev);
      if (next.has(nodeId)) {
        next.delete(nodeId);
      } else if (next.size < 2) {
        next.add(nodeId);
      }
      // If size >= 2 and nodeId not already in set, ignore (cap at 2)
      return next;
    });
  }, []);

  // ---------------------------------------------------------------------------
  // Toolbar action handlers
  // ---------------------------------------------------------------------------

  const handleToolbarActionClick = useCallback(
    (action: "snapshot" | "branchFrom" | "restore" | "adopt" | "discard" | "rename" | null) => {
      if (action === "adopt") {
        if (!selectedBranch) {
          setActionError("No branch selected — cannot adopt.");
          return;
        }
        // Two-step confirm: show the confirm copy first (mirrors discard).
        setAdoptPending(true);
        return;
      }
      if (action === "discard") {
        setDiscardPending(true);
        return;
      }
      // snapshot / branchFrom / restore / rename → show inline input
      setActiveInput(action as "snapshot" | "branchFrom" | "restore" | "rename" | null);
    },
    [selectedBranch],
  );

  const handleNameConfirm = useCallback(
    async (name: string) => {
      if (activeInput === "snapshot") {
        if (!aeroplaneId) {
          setActionError("No aeroplane selected — cannot snapshot.");
          return;
        }
        await run(() => actions.snapshot({ label: name }));
        setActiveInput(null);
        return;
      }
      if (activeInput === "branchFrom") {
        if (!selectedNode) {
          setActionError("No node selected — cannot branch.");
          return;
        }
        await runBranchOp(
          () => actions.createBranch(selectedNode.id, { name }),
          (branch) => branch.head_id,
        );
        setActiveInput(null);
        return;
      }
      if (activeInput === "restore") {
        if (!selectedNode) {
          setActionError("No node selected — cannot restore.");
          return;
        }
        await runBranchOp(
          () => actions.restore(selectedNode.id, { name }),
          (branch) => branch.head_id,
        );
        setActiveInput(null);
        return;
      }
      if (activeInput === "rename") {
        if (!selectedBranch) {
          setActionError("No branch selected — cannot rename.");
          return;
        }
        await run(() => actions.renameBranch(selectedBranch.id, name));
        setActiveInput(null);
      }
    },
    [activeInput, aeroplaneId, selectedNode, selectedBranch, actions, run, runBranchOp],
  );

  const handleNameCancel = useCallback(() => {
    setActiveInput(null);
  }, []);

  const handleConfirmDiscard = useCallback(() => {
    if (!selectedBranch) {
      setActionError("No branch selected — cannot discard.");
      return;
    }
    setDiscardPending(false);
    void run(() => actions.discardBranch(selectedBranch.id));
  }, [selectedBranch, actions, run]);

  const handleCancelDiscard = useCallback(() => {
    setDiscardPending(false);
  }, []);

  const handleConfirmAdopt = useCallback(() => {
    if (!selectedBranch) {
      setActionError("No branch selected — cannot adopt.");
      return;
    }
    setAdoptPending(false);
    void runBranchOp(
      () => actions.adoptBranch(selectedBranch.id),
      (branch) => branch.head_id,
    );
  }, [selectedBranch, actions, runBranchOp]);

  const handleCancelAdopt = useCallback(() => {
    setAdoptPending(false);
  }, []);

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  const headerTitle = aeroplaneLabel
    ? `Version graph — ${aeroplaneLabel}`
    : "Version graph";

  return (
    /* Backdrop */
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      {/* Native button covers the backdrop so click-outside-to-close is keyboard-
          accessible without putting handlers on non-interactive divs. Not a tab
          stop (Escape and the × button are the keyboard paths). */}
      <button
        type="button"
        data-testid="version-graph-backdrop"
        aria-label="Dismiss version graph"
        tabIndex={-1}
        onClick={onClose}
        className="absolute inset-0 cursor-default"
      />
      {/* Modal card — sits above the backdrop button; clicks on it never reach
          the button, so no stopPropagation handler is needed. */}
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Version graph"
        className="relative flex max-h-[80vh] w-[80vw] max-w-[1100px] flex-col rounded-xl border border-border bg-card shadow-2xl"
      >
        {/* Header */}
        <div className="flex shrink-0 items-center gap-2 border-b border-border px-4 py-3">
          <GitBranch size={15} className="shrink-0 text-muted-foreground" />
          <span className="flex-1 truncate text-[13px] font-semibold text-foreground">
            {headerTitle}
          </span>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close version graph"
            className="flex h-6 w-6 shrink-0 items-center justify-center rounded hover:bg-sidebar-accent"
          >
            <X size={13} />
          </button>
        </div>

        {/* Toolbar */}
        <VersionGraphToolbar
          selectedNode={selectedNode}
          selectedBranch={selectedBranch}
          compareSet={compareSet}
          busy={busy}
          discardPending={discardPending}
          adoptPending={adoptPending}
          activeInput={activeInput}
          onActionClick={handleToolbarActionClick}
          onNameConfirm={(name) => { void handleNameConfirm(name); }}
          onNameCancel={handleNameCancel}
          onConfirmDiscard={handleConfirmDiscard}
          onCancelDiscard={handleCancelDiscard}
          onConfirmAdopt={handleConfirmAdopt}
          onCancelAdopt={handleCancelAdopt}
          onOpenCompare={() => setCompareOpen(true)}
        />

        {/* Legend + sorted-by-date note (gh-964 §3). The vertical order is by
            date, NOT causality — lane colour encodes the branch. */}
        <div
          data-testid="version-graph-legend"
          role="note"
          aria-label="Graph legend"
          className="flex shrink-0 flex-wrap items-center gap-x-3 gap-y-1 border-b border-border px-4 py-1.5 text-[10px] text-muted-foreground"
        >
          {(tree?.branches.length ?? 0) > 0 && (
            <BranchFilter
              branches={tree?.branches ?? []}
              visibleBranchIds={visibleBranchIds ?? new Set(allBranchIds)}
              onToggleBranch={handleToggleBranch}
              onToggleAll={handleToggleAll}
              open={filterOpen}
              onOpenChange={setFilterOpen}
            />
          )}
          <span><span aria-hidden>●</span> snapshot</span>
          <span><span aria-hidden>○</span> editable head</span>
          <span><span aria-hidden>★</span> active</span>
          <span><span aria-hidden>⎇</span> branch</span>
          <span>colour = branch</span>
          <span className="flex-1" />
          <span className="italic">Sorted by date · lane colour = branch</span>
        </div>

        {/* Error banner */}
        {(actionError ?? error) && (
          <div
            role="alert"
            className="shrink-0 border-b border-destructive/30 bg-destructive/10 px-4 py-2 text-[11px] text-destructive"
          >
            {actionError ?? error?.message}
          </div>
        )}

        {/* Content area */}
        {compareOpen ? (
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
            <VersionCompareView
              compareOut={compareOut ?? null}
              isLoading={compareLoading}
              error={compareError?.message ?? null}
              onClose={() => setCompareOpen(false)}
              branchNameMap={branchNameMap}
            />
          </div>
        ) : (
          <div
            ref={scrollRef}
            data-testid="version-graph-scroll"
            onScroll={handleScroll}
            className="min-h-0 flex-1 overflow-y-auto"
          >
            <OverlayContent
              rootId={rootId}
              isLoading={isLoading}
              tree={tree}
              currentHeadId={currentHeadId}
              selectedNodeId={selectedNodeId}
              compareSet={compareSet}
              visibleBranchIds={visibleBranchIds}
              onSelectNode={handleSelectNode}
              onCheckNode={handleCheckNode}
            />
          </div>
        )}
      </div>
    </div>
  );
}

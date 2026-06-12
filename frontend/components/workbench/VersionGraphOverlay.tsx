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

import { useState, useCallback, useEffect } from "react";
import { X, GitBranch, Camera, GitFork, RotateCcw, Star, Trash2 } from "lucide-react";
import { useLineageTree, useVersionActions, useCompareNodes } from "@/hooks/useVersioning";
import { VersionCompareView } from "@/components/workbench/VersionCompareView";
import { VersionGraph } from "@/components/workbench/VersionGraph";
import type { TreeOut, TreeNodeOut, BranchOut } from "@/types/versioning";

// ---------------------------------------------------------------------------
// Re-used inline branch/snapshot name input
// ---------------------------------------------------------------------------

interface NameInputProps {
  placeholder?: string;
  ariaLabel?: string;
  onConfirm: (name: string) => void;
  onCancel: () => void;
  busy: boolean;
  confirmLabel?: string;
  confirmAriaLabel?: string;
}

function NameInput({
  placeholder,
  ariaLabel = "Branch name",
  onConfirm,
  onCancel,
  busy,
  confirmLabel = "OK",
  confirmAriaLabel = "Confirm branch name",
}: NameInputProps) {
  const [value, setValue] = useState("");

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

type ToolbarAction = "snapshot" | "branchFrom" | "restore" | "adopt" | "discard" | null;

interface VersionGraphToolbarProps {
  readonly selectedNode: TreeNodeOut | null;
  readonly selectedBranch: BranchOut | null;
  readonly compareSet: Set<number>;
  readonly busy: boolean;
  readonly discardPending: boolean;
  readonly activeInput: ToolbarAction;
  readonly onActionClick: (action: ToolbarAction) => void;
  readonly onNameConfirm: (name: string) => void;
  readonly onNameCancel: () => void;
  readonly onConfirmDiscard: () => void;
  readonly onCancelDiscard: () => void;
  readonly onOpenCompare: () => void;
}

function VersionGraphToolbar({
  selectedNode,
  selectedBranch,
  compareSet,
  busy,
  discardPending,
  activeInput,
  onActionClick,
  onNameConfirm,
  onNameCancel,
  onConfirmDiscard,
  onCancelDiscard,
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

  const compareCount = compareSet.size;
  const compareEnabled = compareCount === 2 && !busy;

  const getSnapshotTitle = () => {
    if (!hasSelection) return "Select a node first";
    if (isSnapshot) return "Cannot snapshot an immutable node";
    if (!isEditableHead) return "Only the editable head can be snapshotted";
    return undefined;
  };

  const getRestoreTitle = () => {
    if (!hasSelection) return "Select a node first";
    if (!isSnapshot) return "Only snapshot nodes can be restored";
    return undefined;
  };

  const getAdoptTitle = () => {
    if (!hasSelection) return "Select a node first";
    if (isOnMain) return "This branch is already main";
    return undefined;
  };

  const getDiscardTitle = () => {
    if (!hasSelection) return "Select a node first";
    if (isOnMain) return "Cannot discard the main branch";
    return undefined;
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
          title={!hasSelection ? "Select a node first" : undefined}
        />

        {/* Restore */}
        <ToolbarButton
          label="Restore"
          icon={<RotateCcw size={12} />}
          onClick={() => onActionClick("restore")}
          disabled={!restoreEnabled}
          title={getRestoreTitle()}
        />

        {/* Separator */}
        <div className="h-5 w-px bg-border" />

        {/* Adopt */}
        <ToolbarButton
          label="Adopt"
          icon={<Star size={12} />}
          onClick={() => onActionClick("adopt")}
          disabled={!adoptEnabled}
          title={getAdoptTitle()}
        />

        {/* Discard */}
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
          <span className="flex items-center gap-1.5">
            <span className="text-[11px] font-medium text-destructive" aria-live="polite">
              Delete all nodes?
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
          </span>
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

  // Selection state
  const [selectedNodeId, setSelectedNodeId] = useState<number | null>(null);

  // Compare state
  const [compareSet, setCompareSet] = useState<Set<number>>(new Set());
  const [compareOpen, setCompareOpen] = useState(false);

  // Busy / error state
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // Toolbar inline input
  const [activeInput, setActiveInput] = useState<
    "snapshot" | "branchFrom" | "restore" | null
  >(null);

  // Discard confirm
  const [discardPending, setDiscardPending] = useState(false);

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
      } else if (compareOpen) {
        setCompareOpen(false);
      } else {
        onClose();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose, compareOpen, activeInput, discardPending]);

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
    (action: "snapshot" | "branchFrom" | "restore" | "adopt" | "discard" | null) => {
      if (action === "adopt") {
        if (!selectedBranch) {
          setActionError("No branch selected — cannot adopt.");
          return;
        }
        void runBranchOp(
          () => actions.adoptBranch(selectedBranch.id),
          (branch) => branch.head_id,
        );
        return;
      }
      if (action === "discard") {
        setDiscardPending(true);
        return;
      }
      // snapshot / branchFrom / restore → show inline input
      setActiveInput(action as "snapshot" | "branchFrom" | "restore" | null);
    },
    [selectedBranch, actions, runBranchOp],
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
      }
    },
    [activeInput, aeroplaneId, selectedNode, actions, run, runBranchOp],
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

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  const headerTitle = aeroplaneLabel
    ? `Version graph — ${aeroplaneLabel}`
    : "Version graph";

  return (
    /* Backdrop */
    <div
      data-testid="version-graph-backdrop"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={onClose}
    >
      {/* Modal card — stop propagation so backdrop click doesn't fire on card */}
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Version graph"
        className="relative flex max-h-[80vh] w-[80vw] max-w-[1100px] flex-col rounded-xl border border-border bg-card shadow-2xl"
        onClick={(e) => e.stopPropagation()}
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
          activeInput={activeInput}
          onActionClick={handleToolbarActionClick}
          onNameConfirm={(name) => { void handleNameConfirm(name); }}
          onNameCancel={handleNameCancel}
          onConfirmDiscard={handleConfirmDiscard}
          onCancelDiscard={handleCancelDiscard}
          onOpenCompare={() => setCompareOpen(true)}
        />

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
            />
          </div>
        ) : (
          <div className="min-h-0 flex-1 overflow-y-auto">
            <OverlayContent
              rootId={rootId}
              isLoading={isLoading}
              tree={tree}
              currentHeadId={currentHeadId}
              selectedNodeId={selectedNodeId}
              compareSet={compareSet}
              onSelectNode={handleSelectNode}
              onCheckNode={handleCheckNode}
            />
          </div>
        )}
      </div>
    </div>
  );
}

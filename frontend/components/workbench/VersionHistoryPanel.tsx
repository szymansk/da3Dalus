"use client";

/**
 * History & Variants panel — shows the version lineage tree for the current
 * aeroplane and exposes per-node and per-branch actions.
 *
 * Per-node actions:
 *   - Select for compare (adds to compare set; max 2)
 *   - Branch from (fork a new editable branch)
 *   - Restore (fork editable branch from a frozen snapshot)
 *
 * Per-branch actions:
 *   - Adopt (promote to is_main=true)
 *   - Discard (delete branch + nodes; guarded)
 *
 * Props:
 *   rootId         — integer PK of the lineage root; null disables fetching
 *   currentHeadId  — integer PK of the currently-active head node
 *   aeroplaneId    — integer PK of the current head (for snapshot/branch)
 *   onClose        — called when the user closes the panel
 */

import { useState, useCallback } from "react";
import {
  X,
  GitBranch,
  RotateCcw,
  GitFork,
  Star,
  Trash2,
  ArrowLeftRight,
  Bot,
  User,
  Clock,
  Image as ImageIcon,
} from "lucide-react";
import { useLineageTree, useVersionActions, useCompareNodes } from "@/hooks/useVersioning";
import { VersionCompareView } from "@/components/workbench/VersionCompareView";
import type { BranchOut, TreeNodeOut, TreeOut } from "@/types/versioning";

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function PreviewThumbnail({ png }: { readonly png: string | null }) {
  if (!png) {
    return (
      <div
        className="flex h-[48px] w-[64px] shrink-0 items-center justify-center rounded border border-border bg-card-muted"
        aria-label="No preview available"
      >
        <ImageIcon size={16} className="text-muted-foreground/40" />
      </div>
    );
  }
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={`data:image/png;base64,${png}`}
      alt="Snapshot preview"
      className="h-[48px] w-[64px] shrink-0 rounded border border-border object-cover"
    />
  );
}

function CreatedByBadge({ createdBy }: { readonly createdBy: string | null }) {
  const isAi = createdBy === "ai";
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[9px] font-medium ${
        isAi
          ? "bg-violet-500/15 text-violet-400"
          : "bg-sidebar-accent text-muted-foreground"
      }`}
      aria-label={isAi ? "Created by AI" : "Created by human"}
      title={isAi ? "Created by AI" : "Created by human"}
    >
      {isAi ? <Bot size={9} /> : <User size={9} />}
      {isAi ? "ai" : "human"}
    </span>
  );
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

// ---------------------------------------------------------------------------
// Inline branch-name input
// ---------------------------------------------------------------------------

interface BranchNameInputProps {
  placeholder?: string;
  onConfirm: (name: string) => void;
  onCancel: () => void;
  busy: boolean;
}

function BranchNameInput({ placeholder, onConfirm, onCancel, busy }: BranchNameInputProps) {
  const [value, setValue] = useState("");

  return (
    <div className="mt-2 flex gap-2">
      <input
        autoFocus
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && value.trim()) onConfirm(value.trim());
          if (e.key === "Escape") onCancel();
        }}
        placeholder={placeholder ?? "branch name"}
        disabled={busy}
        className="min-w-0 flex-1 rounded border border-border bg-card-muted px-2 py-1 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-50"
        aria-label="Branch name"
      />
      <button
        type="button"
        onClick={() => { if (value.trim()) onConfirm(value.trim()); }}
        disabled={busy || !value.trim()}
        className="rounded bg-primary px-2 py-1 text-[11px] font-medium text-primary-foreground disabled:opacity-50"
        aria-label="Confirm branch name"
      >
        OK
      </button>
      <button
        type="button"
        onClick={onCancel}
        disabled={busy}
        className="rounded bg-sidebar-accent px-2 py-1 text-[11px] text-muted-foreground disabled:opacity-50"
        aria-label="Cancel"
      >
        ✕
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// NodeRow
// ---------------------------------------------------------------------------

interface NodeRowProps {
  node: TreeNodeOut;
  isCurrentHead: boolean;
  isSelectedForCompare: boolean;
  onSelectForCompare: (id: number) => void;
  onBranchFrom: (nodeId: number, name: string) => Promise<void>;
  onRestore: (snapshotId: number, name: string) => Promise<void>;
  busy: boolean;
}

function NodeRow({
  node,
  isCurrentHead,
  isSelectedForCompare,
  onSelectForCompare,
  onBranchFrom,
  onRestore,
  busy,
}: NodeRowProps) {
  const [showBranchInput, setShowBranchInput] = useState(false);
  const [showRestoreInput, setShowRestoreInput] = useState(false);

  const handleBranchConfirm = useCallback(async (name: string) => {
    await onBranchFrom(node.id, name);
    setShowBranchInput(false);
  }, [node.id, onBranchFrom]);

  const handleRestoreConfirm = useCallback(async (name: string) => {
    await onRestore(node.id, name);
    setShowRestoreInput(false);
  }, [node.id, onRestore]);

  return (
    <div
      className={`rounded-lg border p-3 transition-colors ${
        isCurrentHead
          ? "border-primary/40 bg-primary/5"
          : "border-border bg-card-muted"
      }`}
      aria-current={isCurrentHead ? "true" : undefined}
    >
      <div className="flex items-start gap-3">
        {/* Thumbnail placeholder — preview_png not in TreeNodeOut (bandwidth) */}
        <PreviewThumbnail png={null} />

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            {/* Label */}
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] font-semibold text-foreground truncate max-w-[180px]">
              {node.version_label ?? node.name}
            </span>

            {/* Badges */}
            {node.is_immutable && (
              <span className="rounded-full bg-amber-500/15 px-1.5 py-0.5 text-[9px] font-medium text-amber-400">
                snapshot
              </span>
            )}
            {isCurrentHead && (
              <span className="rounded-full bg-primary/20 px-1.5 py-0.5 text-[9px] font-medium text-primary">
                HEAD
              </span>
            )}
            <CreatedByBadge createdBy={node.created_by} />
          </div>

          {/* Note */}
          {node.version_note && (
            <p className="mt-0.5 text-[11px] text-muted-foreground line-clamp-2">
              {node.version_note}
            </p>
          )}

          {/* Timestamp */}
          <div className="mt-1 flex items-center gap-1 text-[10px] text-subtle-foreground">
            <Clock size={9} />
            <time dateTime={node.created_at}>{formatDate(node.created_at)}</time>
          </div>

          {/* Actions */}
          <div className="mt-2 flex flex-wrap gap-2">
            {/* Select for compare */}
            <button
              type="button"
              onClick={() => onSelectForCompare(node.id)}
              aria-label={
                isSelectedForCompare
                  ? "Remove from comparison"
                  : "Select for comparison"
              }
              aria-pressed={isSelectedForCompare}
              className={`flex items-center gap-1 rounded px-2 py-1 text-[11px] transition-colors ${
                isSelectedForCompare
                  ? "bg-primary text-primary-foreground"
                  : "bg-sidebar-accent text-muted-foreground hover:bg-sidebar-accent/80"
              }`}
            >
              <ArrowLeftRight size={10} />
              Compare
            </button>

            {/* Branch from */}
            <button
              type="button"
              onClick={() => setShowBranchInput(true)}
              disabled={busy || showBranchInput}
              aria-label="Fork a new branch from this node"
              className="flex items-center gap-1 rounded bg-sidebar-accent px-2 py-1 text-[11px] text-muted-foreground hover:bg-sidebar-accent/80 disabled:opacity-50"
            >
              <GitFork size={10} />
              Branch from
            </button>

            {/* Restore (only for immutable snapshots) */}
            {node.is_immutable && (
              <button
                type="button"
                onClick={() => setShowRestoreInput(true)}
                disabled={busy || showRestoreInput}
                aria-label="Restore this snapshot as a new editable branch"
                className="flex items-center gap-1 rounded bg-sidebar-accent px-2 py-1 text-[11px] text-muted-foreground hover:bg-sidebar-accent/80 disabled:opacity-50"
              >
                <RotateCcw size={10} />
                Restore
              </button>
            )}
          </div>

          {/* Inline inputs */}
          {showBranchInput && (
            <BranchNameInput
              placeholder="new-branch-name"
              onConfirm={(name) => { void handleBranchConfirm(name); }}
              onCancel={() => setShowBranchInput(false)}
              busy={busy}
            />
          )}
          {showRestoreInput && (
            <BranchNameInput
              placeholder={`restored-from-${node.version_label ?? node.id}`}
              onConfirm={(name) => { void handleRestoreConfirm(name); }}
              onCancel={() => setShowRestoreInput(false)}
              busy={busy}
            />
          )}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// BranchSection
// ---------------------------------------------------------------------------

interface BranchSectionProps {
  branch: BranchOut;
  nodes: TreeNodeOut[];
  currentHeadId: number | null;
  compareSet: Set<number>;
  onSelectForCompare: (id: number) => void;
  onBranchFrom: (nodeId: number, name: string) => Promise<void>;
  onRestore: (snapshotId: number, name: string) => Promise<void>;
  onAdopt: (branchId: number) => Promise<void>;
  onDiscard: (branchId: number) => Promise<void>;
  busy: boolean;
}

function BranchSection({
  branch,
  nodes,
  currentHeadId,
  compareSet,
  onSelectForCompare,
  onBranchFrom,
  onRestore,
  onAdopt,
  onDiscard,
  busy,
}: BranchSectionProps) {
  const isAiBranch = branch.name.startsWith("ai/");
  const [discardPending, setDiscardPending] = useState(false);

  return (
    <section aria-label={`Branch: ${branch.name}`} className="flex flex-col gap-2">
      {/* Branch header */}
      <div className="flex items-center gap-2 py-1">
        <GitBranch size={13} className={isAiBranch ? "text-violet-400" : "text-muted-foreground"} />
        <span
          className={`font-[family-name:var(--font-jetbrains-mono)] text-[12px] font-semibold ${
            isAiBranch ? "text-violet-400" : "text-foreground"
          }`}
        >
          {branch.name}
        </span>
        {branch.is_main && (
          <span className="rounded-full bg-primary/20 px-1.5 py-0.5 text-[9px] font-medium text-primary">
            main
          </span>
        )}
        {isAiBranch && (
          <span className="rounded-full bg-violet-500/15 px-1.5 py-0.5 text-[9px] font-medium text-violet-400">
            ai
          </span>
        )}

        {/* Branch actions */}
        <div className="ml-auto flex items-center gap-1">
          {!branch.is_main && (
            <button
              type="button"
              onClick={() => { void onAdopt(branch.id); }}
              disabled={busy}
              aria-label={`Promote branch '${branch.name}' to main`}
              title="Promote to main"
              className="flex items-center gap-1 rounded px-2 py-1 text-[10px] text-muted-foreground hover:bg-sidebar-accent disabled:opacity-50"
            >
              <Star size={10} />
              Adopt
            </button>
          )}
          {!branch.is_main && !discardPending && (
            <button
              type="button"
              onClick={() => setDiscardPending(true)}
              disabled={busy}
              aria-label={`Discard branch '${branch.name}'`}
              title="Discard branch and all its nodes"
              className="flex items-center gap-1 rounded px-2 py-1 text-[10px] text-destructive hover:bg-destructive/10 disabled:opacity-50"
            >
              <Trash2 size={10} />
              Discard
            </button>
          )}
          {!branch.is_main && discardPending && (
            <span className="flex items-center gap-1">
              <span className="text-[10px] font-medium text-destructive" aria-live="polite">
                Delete all nodes?
              </span>
              <button
                type="button"
                onClick={() => { setDiscardPending(false); void onDiscard(branch.id); }}
                disabled={busy}
                aria-label={`Confirm discard branch '${branch.name}'`}
                className="rounded bg-destructive px-2 py-1 text-[10px] font-medium text-white disabled:opacity-50"
              >
                Yes, delete
              </button>
              <button
                type="button"
                onClick={() => setDiscardPending(false)}
                disabled={busy}
                aria-label="Cancel discard"
                className="rounded bg-sidebar-accent px-2 py-1 text-[10px] text-muted-foreground disabled:opacity-50"
              >
                Cancel
              </button>
            </span>
          )}
        </div>
      </div>

      {/* Nodes belonging to this branch */}
      <ul role="list" className="flex flex-col gap-2 pl-4 border-l border-border">
        {nodes.length === 0 ? (
          <li className="text-[11px] text-muted-foreground italic">No nodes on this branch.</li>
        ) : (
          nodes.map((node) => (
            <li key={node.id} aria-current={node.id === currentHeadId ? "true" : undefined}>
              <NodeRow
                node={node}
                isCurrentHead={node.id === currentHeadId}
                isSelectedForCompare={compareSet.has(node.id)}
                onSelectForCompare={onSelectForCompare}
                onBranchFrom={onBranchFrom}
                onRestore={onRestore}
                busy={busy}
              />
            </li>
          ))
        )}
      </ul>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Panel content (extracted to avoid nested ternaries in JSX)
// ---------------------------------------------------------------------------

interface PanelContentProps {
  rootId: number | null;
  isLoading: boolean;
  tree: TreeOut | undefined;
  nodesByBranch: Map<number | null, TreeNodeOut[]>;
  currentHeadId: number | null;
  compareSet: Set<number>;
  onSelectForCompare: (id: number) => void;
  onBranchFrom: (nodeId: number, name: string) => Promise<void>;
  onRestore: (snapshotId: number, name: string) => Promise<void>;
  onAdopt: (branchId: number) => Promise<void>;
  onDiscard: (branchId: number) => Promise<void>;
  busy: boolean;
}

function PanelContent({
  rootId,
  isLoading,
  tree,
  nodesByBranch,
  currentHeadId,
  compareSet,
  onSelectForCompare,
  onBranchFrom,
  onRestore,
  onAdopt,
  onDiscard,
  busy,
}: PanelContentProps) {
  if (rootId === null) {
    return (
      <p className="text-[12px] text-muted-foreground">
        No aeroplane selected. Open an aeroplane to view its version history.
      </p>
    );
  }
  if (isLoading) {
    return <p className="text-[12px] text-muted-foreground">Loading history…</p>;
  }
  if (!tree || tree.nodes.length === 0) {
    return (
      <p className="text-[12px] text-muted-foreground">
        No version history yet. Use the Save button to create your first snapshot.
      </p>
    );
  }
  const legacyNodes = nodesByBranch.get(null) ?? [];
  return (
    <div className="flex flex-col gap-6">
      {/* Unassigned nodes (legacy / no branch) */}
      {legacyNodes.length > 0 && (
        <section aria-label="Legacy nodes" className="flex flex-col gap-2">
          <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">
            Legacy (pre-versioning)
          </p>
          <ul role="list" className="flex flex-col gap-2">
            {legacyNodes.map((node) => (
              <li key={node.id} aria-current={node.id === currentHeadId ? "true" : undefined}>
                <NodeRow
                  node={node}
                  isCurrentHead={node.id === currentHeadId}
                  isSelectedForCompare={compareSet.has(node.id)}
                  onSelectForCompare={onSelectForCompare}
                  onBranchFrom={onBranchFrom}
                  onRestore={onRestore}
                  busy={busy}
                />
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Branches */}
      {tree.branches.map((branch) => (
        <BranchSection
          key={branch.id}
          branch={branch}
          nodes={nodesByBranch.get(branch.id) ?? []}
          currentHeadId={currentHeadId}
          compareSet={compareSet}
          onSelectForCompare={onSelectForCompare}
          onBranchFrom={onBranchFrom}
          onRestore={onRestore}
          onAdopt={onAdopt}
          onDiscard={onDiscard}
          busy={busy}
        />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main panel
// ---------------------------------------------------------------------------

export interface VersionHistoryPanelProps {
  rootId: number | null;
  currentHeadId: number | null;
  aeroplaneId: number | null;
  onClose: () => void;
}

export function VersionHistoryPanel({
  rootId,
  currentHeadId,
  aeroplaneId,
  onClose,
}: VersionHistoryPanelProps) {
  const { tree, isLoading, error, mutate } = useLineageTree(rootId);
  const actions = useVersionActions(aeroplaneId, rootId);

  const [compareSet, setCompareSet] = useState<Set<number>>(new Set());
  const [compareOpen, setCompareOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // Derive the two compare IDs only when exactly 2 are selected.
  const compareIds = compareSet.size === 2 ? [...compareSet] : null;
  const compareIdA = compareIds?.[0] ?? null;
  const compareIdB = compareIds?.[1] ?? null;

  // Fetch comparison only when the panel is open and both IDs are known.
  const {
    compareOut,
    isLoading: compareLoading,
    error: compareError,
  } = useCompareNodes(
    compareOpen ? compareIdA : null,
    compareOpen ? compareIdB : null,
  );

  const run = useCallback(async (fn: () => Promise<unknown>) => {
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
  }, [mutate]);

  const handleSelectForCompare = useCallback((id: number) => {
    setCompareSet((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else if (next.size < 2) {
        next.add(id);
      }
      return next;
    });
  }, []);

  const handleBranchFrom = useCallback(
    async (nodeId: number, name: string) => {
      await run(() => actions.createBranch(nodeId, { name }));
    },
    [run, actions],
  );

  const handleRestore = useCallback(
    async (snapshotId: number, name: string) => {
      await run(() => actions.restore(snapshotId, { name }));
    },
    [run, actions],
  );

  const handleAdopt = useCallback(
    async (branchId: number) => {
      await run(() => actions.adoptBranch(branchId));
    },
    [run, actions],
  );

  const handleDiscard = useCallback(
    async (branchId: number) => {
      await run(() => actions.discardBranch(branchId));
    },
    [run, actions],
  );

  // Group nodes by branch_id.
  const nodesByBranch = (tree?.nodes ?? []).reduce<Map<number | null, TreeNodeOut[]>>(
    (acc, node) => {
      const key = node.branch_id;
      const arr = acc.get(key) ?? [];
      arr.push(node);
      acc.set(key, arr);
      return acc;
    },
    new Map(),
  );

  return (
    <aside
      aria-label="History and Variants"
      className="flex h-full w-[360px] shrink-0 flex-col border-l border-border bg-card"
    >
      {/* Panel header */}
      <div className="flex items-center gap-2 border-b border-border px-4 py-3">
        <GitBranch size={15} className="text-muted-foreground" />
        <span className="flex-1 text-[13px] font-semibold text-foreground">
          History &amp; Variants
        </span>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close History panel"
          className="flex h-6 w-6 items-center justify-center rounded hover:bg-sidebar-accent"
        >
          <X size={13} />
        </button>
      </div>

      {/* Compare bar */}
      {compareSet.size > 0 && !compareOpen && (
        <div className="flex items-center gap-2 border-b border-border bg-primary/5 px-4 py-2">
          <ArrowLeftRight size={12} className="text-primary" />
          <span className="flex-1 text-[11px] text-foreground">
            {compareSet.size === 1
              ? "Select one more node to compare"
              : "2 nodes selected"}
          </span>
          {compareSet.size === 2 && (
            <button
              type="button"
              onClick={() => setCompareOpen(true)}
              aria-label="Open compare view"
              className="rounded bg-primary px-2 py-0.5 text-[10px] font-medium text-primary-foreground"
            >
              Compare
            </button>
          )}
          <button
            type="button"
            onClick={() => { setCompareSet(new Set()); setCompareOpen(false); }}
            aria-label="Clear comparison selection"
            className="text-[10px] text-muted-foreground hover:text-foreground"
          >
            Clear
          </button>
        </div>
      )}

      {/* Error banner */}
      {(actionError ?? error) && (
        <div role="alert" className="border-b border-destructive/30 bg-destructive/10 px-4 py-2 text-[11px] text-destructive">
          {actionError ?? error?.message}
        </div>
      )}

      {/* Compare view (replaces content area when open) */}
      {compareOpen && (
        <div className="flex flex-1 flex-col overflow-hidden">
          <VersionCompareView
            compareOut={compareOut ?? null}
            isLoading={compareLoading}
            error={compareError?.message ?? null}
            onClose={() => setCompareOpen(false)}
          />
        </div>
      )}

      {/* Content */}
      {!compareOpen && <div className="flex-1 overflow-y-auto px-4 py-4">
        <PanelContent
          rootId={rootId}
          isLoading={isLoading}
          tree={tree}
          nodesByBranch={nodesByBranch}
          currentHeadId={currentHeadId}
          compareSet={compareSet}
          onSelectForCompare={handleSelectForCompare}
          onBranchFrom={handleBranchFrom}
          onRestore={handleRestore}
          onAdopt={handleAdopt}
          onDiscard={handleDiscard}
          busy={busy}
        />
      </div>}
    </aside>
  );
}

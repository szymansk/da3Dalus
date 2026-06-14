/**
 * versionGraphViewState — module-level view-state cache for the version graph
 * overlay (gh-981 §3).
 *
 * The overlay (`VersionGraphOverlay`) is rendered by the workbench layout only
 * while it is open, so it UNMOUNTS on close and loses all in-component state.
 * To preserve scroll position, the selected node, and the chosen branch filter
 * across a close→reopen within the same session, we stash that state OUTSIDE
 * the component — here, in a module-level Map keyed by the lineage `rootId`.
 *
 * This is intentionally a plain in-memory cache (not localStorage): it lives
 * for the lifetime of the page session and resets on reload, which matches the
 * "same session" expectation. Each aircraft (rootId) gets its own entry, so
 * switching aircraft does not bleed scroll/selection across lineages.
 */

export interface VersionGraphViewState {
  /** Saved scrollTop of the graph scroll container. */
  scrollTop: number;
  /** Last selected node id, or null if nothing was selected. */
  selectedNodeId: number | null;
  /**
   * Explicit list of HIDDEN branch ids (branches the user has unchecked).
   * Empty array means "show all" (default). Storing hidden ids (not visible
   * ids) means we can restore the filter state WITHOUT needing the tree to
   * be loaded first — the set of hidden ids is independent of allBranchIds.
   * New branches that appear after the filter was saved default to visible.
   */
  hiddenBranchIds: number[];
}

const cache = new Map<number, VersionGraphViewState>();

/** Read the cached view state for a lineage root, or undefined if none. */
export function getVersionGraphViewState(
  rootId: number,
): VersionGraphViewState | undefined {
  return cache.get(rootId);
}

/** Write (replace) the cached view state for a lineage root. */
export function setVersionGraphViewState(
  rootId: number,
  state: VersionGraphViewState,
): void {
  cache.set(rootId, state);
}

/**
 * Merge a partial update into the cached view state for a lineage root,
 * creating a default entry first if none exists. Keeps callers from having to
 * read-modify-write the whole object on each scroll / selection / filter change.
 */
export function patchVersionGraphViewState(
  rootId: number,
  patch: Partial<VersionGraphViewState>,
): void {
  const current: VersionGraphViewState = cache.get(rootId) ?? {
    scrollTop: 0,
    selectedNodeId: null,
    hiddenBranchIds: [],
  };
  cache.set(rootId, { ...current, ...patch });
}

/** Clear the entire cache (test helper / session reset). */
export function clearVersionGraphViewState(): void {
  cache.clear();
}

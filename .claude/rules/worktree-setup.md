# Worktree Setup

## Symlink gitignored assets after creating a worktree

The `exports/` directory is gitignored and contains the vendored AVL
binary (`exports/avl`). Git worktrees do not copy gitignored files, so
tests that depend on the binary fail with `FileNotFoundError`.

**After creating any worktree**, symlink the AVL binary from the main
checkout:

```bash
MAIN_ROOT=$(git worktree list --porcelain | head -1 | cut -d' ' -f2)
WORKTREE_ROOT=$(git rev-parse --show-toplevel)

if [ "$MAIN_ROOT" != "$WORKTREE_ROOT" ]; then
  mkdir -p "$WORKTREE_ROOT/exports"
  ln -sf "$MAIN_ROOT/exports/avl" "$WORKTREE_ROOT/exports/avl"
fi
```

The production code (`app/services/avl_runner._resolve_avl_path`) has
a fallback that searches the main worktree, but integration tests
reference the local path directly. The symlink keeps both paths
working.

## Also create the `tmp/` directory

The app mounts `tmp/` as a static-files directory at startup. Worktrees
don't have it:

```bash
mkdir -p "$WORKTREE_ROOT/tmp"
```

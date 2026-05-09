# Worktree Setup

## Create the `tmp/` directory

The app mounts `tmp/` as a static-files directory at startup. Worktrees
don't have it:

```bash
mkdir -p "$WORKTREE_ROOT/tmp"
```

## AVL binary

The AVL binary is delivered via the `avl-binary` Python wheel. After
`poetry install` in a worktree, `avl_path()` returns the correct path.
No manual symlinks needed.

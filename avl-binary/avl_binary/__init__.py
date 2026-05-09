from pathlib import Path


def avl_path() -> Path:
    p = Path(__file__).parent / "bin" / "avl"
    if not p.exists():
        raise FileNotFoundError(
            f"AVL binary not found at {p}. "
            f"Is the correct platform wheel installed?"
        )
    return p

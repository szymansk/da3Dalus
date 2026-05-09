#!/usr/bin/env python3
"""Build platform-specific wheels for the avl-binary package.

Usage:
    python build_wheels.py --platform macos_arm64 --binary ../exports/avl
    python build_wheels.py --platform linux_x86_64 --binary ./avl_linux_x86_64

The script:
1. Copies the provided binary to avl_binary/bin/avl
2. Sets executable permissions
3. Builds a wheel via `python -m build`
4. Renames the wheel to the correct platform tag
5. Outputs to dist/
"""

import argparse
import shutil
import stat
import subprocess
import sys
from pathlib import Path

PLATFORM_TAGS = {
    "macos_arm64": "macosx_11_0_arm64",
    "linux_x86_64": "manylinux_2_17_x86_64.manylinux2014_x86_64",
}

PACKAGE_DIR = Path(__file__).parent
BIN_DIR = PACKAGE_DIR / "avl_binary" / "bin"
DIST_DIR = PACKAGE_DIR / "dist"


def build_wheel(platform: str, binary_path: Path) -> Path:
    target = BIN_DIR / "avl"
    shutil.copy2(binary_path, target)
    target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    DIST_DIR.mkdir(exist_ok=True)

    subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(DIST_DIR)],
        cwd=str(PACKAGE_DIR),
        check=True,
    )

    generic_wheel = next(DIST_DIR.glob("avl_binary-*.whl"))
    platform_tag = PLATFORM_TAGS[platform]
    parts = generic_wheel.stem.split("-")
    # Replace: name-version-pythontag-abitag-platformtag
    final_name = f"{parts[0]}-{parts[1]}-py3-none-{platform_tag}.whl"
    final_path = DIST_DIR / final_name
    generic_wheel.rename(final_path)

    target.unlink()

    print(f"Built: {final_path}")
    return final_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build avl-binary platform wheel")
    parser.add_argument(
        "--platform",
        required=True,
        choices=list(PLATFORM_TAGS.keys()),
    )
    parser.add_argument(
        "--binary",
        required=True,
        type=Path,
        help="Path to the AVL binary for this platform",
    )
    args = parser.parse_args()

    if not args.binary.exists():
        print(f"Error: binary not found at {args.binary}", file=sys.stderr)
        sys.exit(1)

    build_wheel(args.platform, args.binary)


if __name__ == "__main__":
    main()

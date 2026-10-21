"""The committed JSON Schema of the canon model, generated from the types (ch. 8.9).

Run ``python -m aero_kernel.canon.schema_file [path]`` after changing :mod:`aero_kernel.canon.model`;
a test fails while the committed file differs from the generated text.
"""

import json
import sys
from pathlib import Path

from aero_kernel.canon.model import CanonModel

__all__ = ["SCHEMA_PATH", "schema_text", "write_schema"]

SCHEMA_PATH = Path(__file__).resolve().parent / "canon_model.schema.json"


def schema_text() -> str:
    """Generate the JSON Schema of :class:`CanonModel`.

    Returns:
        The schema as stable text: sorted keys, two-space indent, trailing newline.
    """
    return json.dumps(CanonModel.model_json_schema(), indent=2, sort_keys=True) + "\n"


def write_schema(path: Path = SCHEMA_PATH) -> None:
    """Write the generated schema.

    Args:
        path: Target file; defaults to the committed schema.
    """
    path.write_text(schema_text(), encoding="utf-8")


if __name__ == "__main__":
    write_schema(Path(sys.argv[1]) if len(sys.argv) > 1 else SCHEMA_PATH)

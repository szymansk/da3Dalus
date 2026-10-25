"""Read an evaluation rule table from its YAML file and write the shipped JSON (dev time, like the canon import).

The runtime evaluator (``aero_kernel.evaluation``) works on a validated ``RuleTable`` and never
reads YAML (Q12: the kernel runs without PyYAML); whoever calls it loads the table here.
"""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

import yaml
from aero_kernel.evaluation import rules as rules_module
from aero_kernel.evaluation.rules import RuleTable

__all__ = ["load_rule_table", "main", "render_rule_table"]

DEFAULT_YAML = Path("_reversa_sdd/calculations/evaluation/drela.yaml")


def load_rule_table(path: Path) -> RuleTable:
    """Read and validate a rule table.

    Args:
        path: A YAML file with ``source`` and ``rules``.

    Returns:
        The validated table.

    Raises:
        pydantic.ValidationError: If the file does not describe a valid table.
    """
    return RuleTable.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def render_rule_table(table: RuleTable) -> str:
    """Render a rule table as the shipped JSON text.

    Args:
        table: The validated table.

    Returns:
        Indented JSON with a trailing newline, stable across runs.
    """
    return table.model_dump_json(indent=2, exclude_none=True) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    """Write ``evaluation/rule_table.json`` from the YAML, or check that it is current.

    Args:
        argv: Command-line arguments; ``None`` means ``sys.argv[1:]``.

    Returns:
        ``0`` on success, ``1`` if ``--check`` finds the committed JSON stale.
    """
    parser = argparse.ArgumentParser(
        prog="python -m aero_kernel.importer.rule_table",
        description="Generate the shipped rule table JSON from the rule table YAML.",
    )
    parser.add_argument("yaml_file", type=Path, nargs="?", default=DEFAULT_YAML)
    parser.add_argument("--check", action="store_true", help="write nothing; fail if stale")
    arguments = parser.parse_args(argv)
    fresh = render_rule_table(load_rule_table(arguments.yaml_file))
    target = Path(rules_module.__file__).resolve().parent / "rule_table.json"
    if arguments.check:
        current = target.read_text(encoding="utf-8") if target.exists() else ""
        if current != fresh:
            print(f"{target.name} is stale: run `python -m aero_kernel.importer.rule_table`")
            return 1
        print("rule_table.json is current")
        return 0
    target.write_text(fresh, encoding="utf-8")
    print(f"wrote {target.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

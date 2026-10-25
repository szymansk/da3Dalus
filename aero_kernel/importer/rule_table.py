"""Read an evaluation rule table from its YAML file (dev time, like the canon import).

The runtime evaluator (``aero_kernel.evaluation``) works on a validated ``RuleTable`` and never
reads YAML (Q12: the kernel runs without PyYAML); whoever calls it loads the table here.
"""

from pathlib import Path

import yaml
from aero_kernel.evaluation.rules import RuleTable

__all__ = ["load_rule_table"]


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

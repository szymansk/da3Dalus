"""Narrowing of raw YAML values: the one place where untyped data is looked at (ARCHITECTURE ch. 8.9).

``yaml.safe_load`` returns ``object``; these helpers turn it into typed containers without
letting an ``Any`` leak into the stages.
"""

from typing import cast

import yaml

__all__ = ["as_list", "as_mapping", "compose_node", "is_number", "is_text", "scan_tokens"]


def as_mapping(value: object) -> dict[object, object] | None:
    """Return ``value`` as a mapping, or ``None`` if it is none."""
    if isinstance(value, dict):
        return cast(
            "dict[object, object]", value
        )  # safe_load builds dicts; keys are checked by callers
    return None


def as_list(value: object) -> list[object] | None:
    """Return ``value`` as a list, or ``None`` if it is none."""
    if isinstance(value, list):
        return cast("list[object]", value)  # safe_load builds lists of plain values
    return None


def is_text(value: object) -> bool:
    """Whether ``value`` is a string with some content."""
    return isinstance(value, str) and value.strip() != ""


def is_number(value: object) -> bool:
    """Whether ``value`` is a number; a YAML boolean is not one."""
    return isinstance(value, int | float) and not isinstance(value, bool)


def scan_tokens(raw: str) -> list[yaml.Token]:
    """Return the YAML tokens of ``raw``.

    Raises:
        yaml.YAMLError: If ``raw`` is not valid YAML.
    """
    # PyYAML's stub leaves the stream parameter untyped, which strict pyright reports.
    return list(yaml.scan(raw))  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]


def compose_node(text: str) -> yaml.Node | None:
    """Return the YAML node tree of ``text`` (keeps duplicate keys), or ``None`` if it is empty.

    Raises:
        yaml.YAMLError: If ``text`` is not valid YAML.
    """
    # Same untyped stub parameter as in scan_tokens.
    return yaml.compose(text)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

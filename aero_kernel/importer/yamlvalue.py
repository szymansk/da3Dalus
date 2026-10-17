"""Narrowing of raw YAML values: the one place where untyped data is looked at (ARCHITECTURE ch. 8.9).

``yaml.safe_load`` returns ``object``; these helpers turn it into typed containers without
letting an ``Any`` leak into the stages.
"""

from typing import cast

import yaml

__all__ = [
    "DuplicateKeyError",
    "as_list",
    "as_mapping",
    "is_number",
    "is_text",
    "load_unique",
    "scan_tokens",
]


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


class DuplicateKeyError(yaml.YAMLError):
    """A mapping repeats a key; YAML would silently keep the last value.

    Attributes:
        key: The repeated key.
        line: Its line within the parsed text, counted from 1.
    """

    def __init__(self, key: object, line: int) -> None:
        """Create the error.

        Args:
            key: The repeated key.
            line: Its line within the parsed text, counted from 1.
        """
        super().__init__(f"duplicate key {key!r}")
        self.key = key
        self.line = line


class _UniqueKeyLoader(yaml.SafeLoader):
    """A safe loader that rejects a repeated key at every depth."""

    def construct_mapping(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, node: yaml.MappingNode, deep: bool = False
    ) -> dict[object, object]:
        """Construct a mapping, raising :class:`DuplicateKeyError` on a repeated key."""
        seen: set[object] = set()
        for key_node, _ in node.value:
            key = cast("object", self.construct_object(key_node, deep=deep))  # pyright: ignore[reportUnknownMemberType]
            try:
                repeated = key in seen
                seen.add(key)
            except TypeError:  # an unhashable key is reported by the base class
                continue
            if repeated:
                raise DuplicateKeyError(key, key_node.start_mark.line + 1)
        # The base class returns dict[Hashable, Any]; the stages treat every value as ``object``.
        return cast("dict[object, object]", super().construct_mapping(node, deep))  # pyright: ignore[reportUnknownMemberType]


def load_unique(text: str) -> object:
    """Parse YAML safely, rejecting a repeated mapping key at every depth.

    Args:
        text: The YAML text.

    Returns:
        The parsed value.

    Raises:
        DuplicateKeyError: If a mapping repeats a key.
        yaml.YAMLError: If ``text`` is not valid YAML.
    """
    # Subclass of SafeLoader: no arbitrary object construction.
    return yaml.load(text, Loader=_UniqueKeyLoader)

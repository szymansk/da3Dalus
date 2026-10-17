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
        index: Character offset of the repeated key in the parsed text.
        path: The keys of the mappings that contain the repeated key, outermost first.
    """

    def __init__(self, key: object, line: int, index: int) -> None:
        """Create the error.

        Args:
            key: The repeated key.
            line: Its line within the parsed text, counted from 1.
            index: Character offset of the repeated key in the parsed text.
        """
        super().__init__(f"duplicate key {key!r}")
        self.key = key
        self.line = line
        self.index = index
        self.path: tuple[str, ...] = ()


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
                raise DuplicateKeyError(
                    key, key_node.start_mark.line + 1, key_node.start_mark.index
                )
        # The base class returns dict[Hashable, Any]; the stages treat every value as ``object``.
        return cast("dict[object, object]", super().construct_mapping(node, deep))  # pyright: ignore[reportUnknownMemberType]


def _trail_to(node: yaml.Node, index: int, trail: tuple[str, ...]) -> tuple[str, ...] | None:
    """Return the keys leading to the mapping that holds the key written at ``index``."""
    if isinstance(node, yaml.MappingNode):
        for key_node, value_node in node.value:
            if key_node.start_mark.index == index:
                return trail
            name = str(key_node.value) if isinstance(key_node, yaml.ScalarNode) else "?"
            found = _trail_to(value_node, index, (*trail, name))
            if found is not None:
                return found
    elif isinstance(node, yaml.SequenceNode):
        for item in node.value:
            found = _trail_to(item, index, trail)
            if found is not None:
                return found
    return None


def load_unique(text: str) -> object:
    """Parse YAML safely, rejecting a repeated mapping key at every depth.

    Args:
        text: The YAML text.

    Returns:
        The parsed value.

    Raises:
        DuplicateKeyError: If a mapping repeats a key; ``path`` names the mappings around it.
        yaml.YAMLError: If ``text`` is not valid YAML.
    """
    try:
        # Subclass of SafeLoader: no arbitrary object construction.
        return yaml.load(text, Loader=_UniqueKeyLoader)
    except DuplicateKeyError as error:
        # Composing builds the node tree only; it constructs nothing and so repeats no check.
        root = cast(
            "yaml.Node | None",
            yaml.compose(text, Loader=_UniqueKeyLoader),  # pyright: ignore[reportUnknownMemberType]
        )
        if root is not None:
            error.path = _trail_to(root, error.index, ()) or ()
        raise

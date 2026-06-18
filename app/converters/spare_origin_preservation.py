"""Pure helpers for preserving solver-supplied spare geometry on conversion.

gh-1053: A ``normal``-mode spare created by the spar-insert solver carries an
explicit, solved ``spare_origin`` + ``spare_vector``. The model→config converter
(:func:`app.converters.model_schema_converters._resolve_spare_vectors_and_origins`)
otherwise clears and recomputes every spare's geometry (the gh-352/gh-362
unit-leak guard), which collapses the solved front/rear couple onto the default
quarter-chord station. These helpers decide *when* a spare's explicit geometry
must be honoured verbatim and *how* its origin scales between the DB (mm) and a
``WingConfiguration`` built at an arbitrary geometry ``scale``.

This module deliberately has **no** CadQuery / AeroSandbox imports so the
decision logic is unit-testable in the CI fast tier (which excludes those
heavy dependencies).
"""

from __future__ import annotations

from typing import Sequence

# mm → m. The DB stores ``spare_origin`` in millimetres (gh-402); a
# ``WingConfiguration`` geometry is built from a metre base scaled by ``scale``.
_MM_TO_M = 0.001

# A 3-vector is "explicit" only when all three components are present.
_VECTOR_LEN = 3


def _is_explicit_triplet(value: object) -> bool:
    """True when ``value`` is a length-3 sequence of finite numbers."""
    if value is None:
        return False
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return False
    if len(value) != _VECTOR_LEN:
        return False
    try:
        return all(float(component) == float(component) for component in value)  # not-NaN
    except (TypeError, ValueError):
        return False


def should_preserve_normal_spare(
    spare_mode: object,
    spare_origin: object,
    spare_vector: object,
) -> bool:
    """Whether a spare's explicit origin + vector must be honoured verbatim.

    Only ``normal``-mode spares that already carry a fully explicit
    ``spare_origin`` AND ``spare_vector`` are preserved. ``standard`` /
    ``follow`` / ``*_backward`` spares always go through the recompute path so
    the gh-352/gh-362 unit-leak guard stays intact for them.
    """
    return (
        spare_mode == "normal"
        and _is_explicit_triplet(spare_origin)
        and _is_explicit_triplet(spare_vector)
    )


def scale_db_origin_to_config(
    spare_origin_mm: Sequence[float],
    scale: float,
) -> tuple[float, float, float]:
    """Scale a DB ``spare_origin`` (mm) into a config built at geometry ``scale``.

    The config geometry is a metre base multiplied by ``scale`` (``scale=1.0``
    → metres, ``scale=1000.0`` → millimetres). The DB origin is millimetres, so
    its metre value is ``mm * _MM_TO_M`` and its config value is that times
    ``scale``. Hence ``scale=1.0`` → mm→m, ``scale=1000.0`` → verbatim mm.
    """
    factor = _MM_TO_M * scale
    return (
        float(spare_origin_mm[0]) * factor,
        float(spare_origin_mm[1]) * factor,
        float(spare_origin_mm[2]) * factor,
    )

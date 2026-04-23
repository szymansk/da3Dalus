"""
Template for new AbstractShapeCreator subclasses.

Copy this file, rename the class, and implement _create_shape().
Follow the patterns below — they are consistent across all 29+
existing creators in this project.

Usage:
    1. Copy this file to the appropriate subdirectory:
       - cad_operations/  — boolean ops, transforms, offsets
       - wing/            — wing geometry, print orientation
       - fuselage/        — fuselage shells, mounts, reinforcements
       - export_import/   — file I/O (STEP, STL, 3MF, IGES)
       - components/      — component/servo import
    2. Rename the class and update the docstring
    3. Define your constructor parameters (domain params + shape keys)
    4. Implement _create_shape()
    5. Register in the subdirectory's __init__.py

Conventions:
    - creator_id is the unique key for this step in the construction tree
    - self.identifier (= creator_id) is the output dict key by convention
    - shapes_of_interest_keys: list of upstream shape keys this creator
      needs. Use [self.param] for named refs, [] for self-contained
      (config-driven) creators, None entries for positional pipeline slots.
    - loglevel default is logging.INFO (not the base class's FATAL)
    - Private fields (self._foo) are excluded from JSON serialization
    - Runtime-injected config (wing_config, servo_information, etc.) is
      passed as a constructor kwarg and stored as self._config (private)

Documentation (frontend integration):
    The Creator Catalog API (/construction-plans/creators) reflects
    class metadata into the frontend. The following are extracted and
    shown to the user as info tooltips:

    - **Class docstring** (first line): displayed as the creator's
      description in the Creator Gallery and Parameter Form header.
    - **Attributes section** in the docstring: parsed to extract
      per-parameter descriptions. Each line in the format
      ``param_name (type): Description text.`` becomes a tooltip
      next to the parameter input field.

    Best practice: always provide a clear one-line class docstring
    and an Attributes section documenting each constructor parameter.
    Parameters without descriptions show no info button in the UI.

    Example:
        class MyCreator(AbstractShapeCreator):
            \"\"\"Creates a reinforced shell from an input shape.

            Attributes:
                thickness (float): Wall thickness in mm.
                reinforce (bool): Whether to add internal ribs.
                input_shape (str): Key of the upstream shape to shell.
            \"\"\"
"""

from __future__ import annotations

import logging

from cadquery import Workplane

from cad_designer.airplane.AbstractShapeCreator import AbstractShapeCreator


class MyCreator(AbstractShapeCreator):
    """One-line description of what this creator produces or does.

    Attributes:
        input_shape (str): Key of the upstream shape to process.
    """

    suggested_creator_id = "{input_shape}.my_creator"

    def __init__(
        self,
        creator_id: str,
        # ── Domain parameters ──────────────────────────────────
        # Add your creator-specific parameters here.
        # Example: thickness: float, count: int, mode: str = "default"
        #
        # ── Shape references (upstream shapes this creator needs) ──
        # Use str keys that reference output of previous steps.
        # Default to None to allow positional pipeline resolution.
        input_shape: str | None = None,
        #
        # ── Runtime-injected config (optional) ─────────────────
        # These are passed by GeneralJSONDecoder at decode time.
        # Store as private (self._) to exclude from JSON serialization.
        # Example: wing_config: Optional[dict] = None,
        #
        # ── Base class ─────────────────────────────────────────
        loglevel: int = logging.INFO,
    ):
        # Store domain params BEFORE calling super().__init__
        self.input_shape = input_shape

        # Store runtime config as private (excluded from JSON)
        # self._wing_config = wing_config

        super().__init__(
            creator_id,
            shapes_of_interest_keys=[self.input_shape],
            #   [self.input_shape]       — single upstream shape
            #   [self.a, self.b]         — multiple named shapes
            #   [self.minuend] + self.subtrahends  — fixed + variable
            #   []                       — self-contained (config-driven)
            loglevel=loglevel,
        )

    def _create_shape(
        self,
        shapes_of_interest: dict[str, Workplane],
        input_shapes: dict[str, Workplane],
        **kwargs,
    ) -> dict[str, object | Workplane]:
        """
        Implement your shape creation logic here.

        Args:
            shapes_of_interest: Dict of upstream shapes this creator
                requested via shapes_of_interest_keys. Use this as
                your primary input — don't access input_shapes directly.
            input_shapes: All shapes from the previous step (rarely needed).
            **kwargs: All shapes from all previous steps (global registry).

        Returns:
            Dict mapping output key(s) to Workplane objects.
            Convention: {self.identifier: result} for single output.
            For multiple outputs: {f"{self.identifier}.name": shape, ...}
            For indexed outputs: {f"{self.identifier}[0]": shape, ...}
        """
        # 1. Log what this creator is doing
        keys = list(shapes_of_interest.keys())
        logging.info(
            f"processing '{keys}' --> '{self.identifier}'"
        )

        # 2. Get your input shape(s)
        shape = list(shapes_of_interest.values())[0]

        # 3. Do your CAD operation
        #    Example: result = shape.shell(-self.thickness)
        result = shape  # replace with actual operation

        # 4. Visual debug logging
        result.display(name=self.identifier, severity=logging.DEBUG)

        # 5. Return output dict
        return {self.identifier: result}

        # ── Variations ─────────────────────────────────────────
        #
        # Multiple outputs:
        #   return {
        #       f"{self.identifier}.outer": outer_shape,
        #       f"{self.identifier}.inner": inner_shape,
        #   }
        #
        # Pass-through (export creators):
        #   self._write_files(shapes_of_interest)
        #   return shapes_of_interest
        #
        # Config-driven (no upstream shapes):
        #   wing = self._wing_config[self.wing_index]
        #   shape = self._build_from_config(wing)
        #   return {self.identifier: shape}

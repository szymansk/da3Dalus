"""The AVL adapter: the neutral point of an airplane from the vortex lattice (ARCHITECTURE ch. 8.8).

One run of AVL at a lift coefficient on the aligned mesh of :mod:`aero_kernel.solvers.avl_mesh`, and a
second on a mesh refined by a fixed factor as the validity check: the adapter reports the declared
mesh's value and declares the disagreement as a ``defect`` warning (tool validity belongs to the
adapter). It adds no regime warning of its own: those come with the minimum-drag speed and are
inherited (#1203, M2).
"""

import asyncio
import logging
import time
from collections.abc import Mapping
from typing import ClassVar

from aero_kernel.errors import ErrorCategory, FormulaError, ToolRunTimeoutError
from aero_kernel.geometry import Airfoil, AirplaneGeometry, InlineAirfoil
from aero_kernel.geometry_properties import MainWingProperties, main_wing_properties
from aero_kernel.runtime import WorkerDiagnostics, WorkerOutcome
from aero_kernel.schema import KernelWarning
from aero_kernel.solvers.asb_airplane import load_aerosandbox
from aero_kernel.solvers.avl_contour import repanel
from aero_kernel.solvers.avl_mesh import MeshSurface, mesh_surfaces
from aero_kernel.solvers.avl_writer import (
    GEOMETRY_FILE,
    AvlOutput,
    airfoil_file,
    airfoil_file_name,
    avl_commands,
    avl_geometry,
    parse_avl_output,
)
from aero_kernel.solvers.base import SolverAdapter
from aero_kernel.solvers.devices import refuse_deflected_devices
from pydantic import BaseModel, ConfigDict, JsonValue

logger = logging.getLogger(__name__)

__all__ = ["AvlAdapter", "AvlNeutralPoint", "Contour"]

# Mesh and vortex core, from the BRYAN mesh study (scripts/sim_export/crrcsim/AVL_CONVERGENCE.md):
# aligned strips 10 chordwise / 24 spanwise converge to 0.3 % MAC against the next finer level;
# the core ratio 0.25 is AVL's default, set explicitly because it moves the neutral point by
# about 2.3 % MAC at 0.5.
N_CHORD = 10
N_SPAN = 24
CORE_RATIO = 0.25
# The check run uses this factor on both counts. 40/96 overflows AVL's vortex array on BRYAN.
REFINE_FACTOR = 2
# The disagreement of the two meshes above which the value is declared not converged, in mean
# chords (0.5 % MAC, AVL_CONVERGENCE.md).
REFINEMENT_TOLERANCE_MAC = 0.005
# Every airfoil is repanelled to this many points per side (cosine spaced), whatever it had: AVL stops
# at 399 contour points in total (its IBX limit; AeroSandbox's NACA 4-digit contour has 399 and a
# fine inline contour more), and a repanelling done only when a contour is too large would be an
# undeclared conditional substitution (ADR 0020). 80 per side give 159 points; BRYAN's own contours
# have 162. The same contour gives the thickness for CLAF.
AIRFOIL_POINTS_PER_SIDE = 80
# AVL's CLAF rule (avl_doc.txt): the lift-curve-slope factor 1 + 0.77 t/c.
CLAF_PER_THICKNESS = 0.77
# AVL reaches the requested lift coefficient exactly; a larger miss is a defect of ours.
CL_TOLERANCE = 1e-4
# AVL 3.40 prints the first on an overflow of its vortex arrays; on a mesh so fine that the influence
# matrix no longer fits LAPACK's integers it exits 0 with the second (BRYAN at 20/96).
# The longest one AVL run may take. The measured refined 20/48 run of BRYAN and JAGUAR takes 15 s and
# the 20/96 run 45 s; AVL can also spin forever on a geometry it cannot solve (a chain it reads tip
# first), so a run is never waited for longer than this. Expiry is a `timeout` error and the process
# group is killed (run_process).
AVL_MAX_RUN_S = 120.0
_OVERFLOW = ("Vortex array overflow", "DGETRF parameter number")


class AvlNeutralPoint(BaseModel):
    """The neutral point AVL found, and the caveats of the run.

    Attributes:
        x_np: x of the neutral point in m, in the geometry frame (aft positive).
        warnings: Tool validity warnings (mesh convergence), without origin.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    x_np: float
    warnings: tuple[KernelWarning, ...] = ()


class Contour(BaseModel):
    """An airfoil as AVL needs it.

    Attributes:
        coordinates: Selig order, chord 1, x in [0, 1].
        claf: ``CLAF = 1 + 0.77 t/c`` with the thickness from AeroSandbox.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    coordinates: tuple[tuple[float, float], ...]
    claf: float


def contour_worker(airfoils: tuple[Airfoil, ...]) -> WorkerOutcome[tuple[Contour, ...]]:
    """Resolve airfoils to unit-chord contours and their ``CLAF`` in a pool worker.

    Args:
        airfoils: Designations or inline coordinates.

    Returns:
        One :class:`Contour` per airfoil, in order.
    """
    started = time.perf_counter()
    import numpy as np

    asb = load_aerosandbox()  # heavy import, kept off the loop (ch. 8.10)

    contours: list[Contour] = []
    for airfoil in airfoils:
        if isinstance(airfoil, InlineAirfoil):
            raw = np.array(airfoil.coordinates, dtype=float)
        else:
            raw = np.asarray(asb.Airfoil(name=airfoil).coordinates, dtype=float)
        unit = np.array(repanel([(float(x), float(y)) for x, y in raw], AIRFOIL_POINTS_PER_SIDE))
        thickness = float(asb.Airfoil(name="contour", coordinates=unit).max_thickness())
        contours.append(
            Contour(
                coordinates=tuple((float(x), float(y)) for x, y in unit),
                claf=1.0 + CLAF_PER_THICKNESS * thickness,
            )
        )
    diagnostics = WorkerDiagnostics(duration_s=time.perf_counter() - started)
    return WorkerOutcome(value=tuple(contours), diagnostics=diagnostics)


class AvlAdapter(SolverAdapter):
    """AVL as a subprocess in the runtime.

    Attributes:
        tool: ``AVL``.
        requirements: The AVL binary and AeroSandbox (the thickness of the sections).
    """

    tool: ClassVar[str] = "AVL"
    requirements: ClassVar[Mapping[str, str]] = {
        "avl-binary": "avl_binary",
        "aerosandbox": "aerosandbox",
    }

    def settings(self) -> dict[str, JsonValue]:
        """The mesh, vortex core and refinement check the neutral point is computed with."""
        return {
            "avl_nchord": N_CHORD,
            "avl_nspan": N_SPAN,
            "avl_airfoil_points_per_side": AIRFOIL_POINTS_PER_SIDE,
            "avl_core_ratio": CORE_RATIO,
            "avl_refine_factor": REFINE_FACTOR,
            "avl_refinement_tolerance_mac": REFINEMENT_TOLERANCE_MAC,
        }

    async def _contours(self, airfoils: tuple[Airfoil, ...]) -> tuple[Contour, ...]:
        """The contours and ``CLAF`` of the airfoils, computed in a pool worker."""
        return await self.runtime.run_cpu(contour_worker, airfoils)

    async def _run(
        self,
        surfaces: tuple[MeshSurface, ...],
        contours: tuple[Contour, ...],
        n_chord: int,
        n_span: int,
        cl: float,
        reference: MainWingProperties,
    ) -> AvlOutput:
        """One AVL run on one mesh.

        Raises:
            FormulaError: ``tool_unavailable``; ``unsupported_configuration`` (``avl_array_limit``)
                if the mesh overflows AVL's vortex array.
            RuntimeError: If AVL fails or misses the lift coefficient (a defect of ours).
        """
        from avl_binary import avl_path  # the wheel is a declared requirement

        files: dict[str, str | bytes] = {
            GEOMETRY_FILE: avl_geometry(
                surfaces,
                [c.claf for c in contours],
                n_chord=n_chord,
                s_ref=reference.s_ref,
                c_ref=reference.c_mac,
                b_ref=reference.b_ref,
            ),
        }
        for index, contour in enumerate(contours):
            files[airfoil_file_name(index)] = airfoil_file(f"airfoil {index}", contour.coordinates)
        try:
            async with asyncio.timeout(AVL_MAX_RUN_S):
                run = await self.runtime.run_process(
                    files,
                    avl_commands(cl, CORE_RATIO),
                    executable=avl_path(),
                    args=(GEOMETRY_FILE,),
                )
        except TimeoutError as error:
            raise ToolRunTimeoutError("the vortex lattice run", AVL_MAX_RUN_S) from error
        if any(marker in run.stdout for marker in _OVERFLOW):
            raise FormulaError(
                ErrorCategory.UNSUPPORTED_CONFIGURATION,
                "avl_array_limit",
                "the vortex lattice is too fine for the solver's array limit",
                "the airplane has too many surfaces or sections for the neutral point by AVL",
                detail={"n_chord": n_chord, "n_span": n_span},
            )
        output = parse_avl_output(run.stdout)
        if run.returncode != 0 or output is None:
            msg = f"the vortex lattice run did not complete (exit {run.returncode})"
            logger.error("%s; stdout tail: %s", msg, run.stdout[-500:])
            raise RuntimeError(msg)
        if abs(output.cl - cl) > CL_TOLERANCE:
            msg = f"the vortex lattice trimmed to C_L {output.cl}, not the requested {cl}"
            raise RuntimeError(msg)
        return output

    async def neutral_point(self, airplane: AirplaneGeometry, cl: float) -> AvlNeutralPoint:
        """Find the neutral point of the airplane at a lift coefficient.

        Runs the declared mesh and the mesh refined by ``REFINE_FACTOR``; the declared mesh's
        value is returned. A disagreement above ``REFINEMENT_TOLERANCE_MAC`` is a
        ``avl_mesh_not_converged`` warning; a refined mesh that overflows AVL's array is
        ``avl_refinement_unchecked``.

        Args:
            airplane: The validated geometry, devices at rest, with one main wing.
            cl: The lift coefficient of the operating point.

        Returns:
            The neutral point and the adapter's warnings.

        Raises:
            FormulaError: ``tool_unavailable``; ``unsupported_configuration`` if the declared mesh
                overflows AVL's array.
            RuntimeError: If AVL fails (a defect, reported as ``internal``).
        """
        self.require_available()
        refuse_deflected_devices(airplane, "AVL")
        reference = main_wing_properties(airplane)
        numbers: dict[Airfoil, int] = {}

        def number(airfoil: Airfoil) -> int:
            return numbers.setdefault(airfoil, len(numbers))

        declared = mesh_surfaces(airplane, N_SPAN, number)
        refined = mesh_surfaces(airplane, N_SPAN * REFINE_FACTOR, number)
        contours = await self._contours(tuple(numbers))
        first = await self._run(declared, contours, N_CHORD, N_SPAN, cl, reference)
        warnings: list[KernelWarning] = []
        n_chord, n_span = N_CHORD * REFINE_FACTOR, N_SPAN * REFINE_FACTOR
        try:
            second = await self._run(refined, contours, n_chord, n_span, cl, reference)
        except FormulaError as error:
            if error.code != "avl_array_limit":
                raise
            warnings.append(
                KernelWarning.of(
                    "avl_refinement_unchecked",
                    "The refined mesh is beyond the solver's array limit, so the convergence "
                    "of the neutral point could not be checked.",
                    detail={"n_chord": n_chord, "n_span": n_span},
                )
            )
        else:
            delta = abs(second.x_np - first.x_np) / reference.c_mac
            if delta > REFINEMENT_TOLERANCE_MAC:
                warnings.append(
                    KernelWarning.of(
                        "avl_mesh_not_converged",
                        "The neutral point changes by more than the tolerance when the vortex "
                        "lattice is refined; the value is mesh-dependent.",
                        detail={
                            "x_np_declared": first.x_np,
                            "x_np_refined": second.x_np,
                            "delta_mac": delta,
                            "n_chord_declared": N_CHORD,
                            "n_span_declared": N_SPAN,
                            "n_chord_refined": n_chord,
                            "n_span_refined": n_span,
                        },
                    )
                )
        return AvlNeutralPoint(x_np=first.x_np, warnings=tuple(warnings))

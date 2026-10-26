"""The AVL adapter: the neutral point and the steady roll of an airplane (ARCHITECTURE ch. 8.8).

One run of AVL at a lift coefficient on the aligned mesh of :mod:`aero_kernel.solvers.avl_mesh`, and a
second on a mesh refined by a fixed factor as the validity check: the adapter reports the declared
mesh's value and declares the disagreement as a ``defect`` warning (tool validity belongs to the
adapter). It adds no regime warning of its own: those come with the minimum-drag speed and are
inherited (#1203, M2). The steady roll drives the devices acting as aileron on the same mesh with
their ends as stations, about the airplane's own reference point.
"""

import asyncio
import logging
import math
import time
from collections.abc import Mapping
from typing import ClassVar

from aero_kernel.config import config
from aero_kernel.errors import ErrorCategory, FormulaError, ToolRunTimeoutError
from aero_kernel.geometry import Airfoil, AirplaneGeometry, InlineAirfoil
from aero_kernel.geometry_properties import MainWingProperties
from aero_kernel.rules import Rules
from aero_kernel.runtime import SolverRuntime, WorkerDiagnostics, WorkerOutcome
from aero_kernel.schema import KernelWarning
from aero_kernel.solvers.asb_airplane import load_aerosandbox, main_wing_properties
from aero_kernel.solvers.avl_contour import repanel
from aero_kernel.solvers.avl_mesh import (
    MESH_DECIMALS,
    SLIVER_STEPS,
    MeshSurface,
    mesh_surfaces,
    split_at_hinge,
)
from aero_kernel.solvers.avl_writer import (
    CHORD_SPACING,
    GEOMETRY_FILE,
    AvlOutput,
    RollOutput,
    airfoil_file,
    airfoil_file_name,
    avl_commands,
    avl_geometry,
    avl_roll_commands,
    parse_avl_output,
    parse_roll_output,
)
from aero_kernel.solvers.base import SolverAdapter
from aero_kernel.solvers.devices import refuse_deflected_devices, roll_segments
from pydantic import BaseModel, ConfigDict, JsonValue

logger = logging.getLogger(__name__)

__all__ = ["AvlAdapter", "AvlNeutralPoint", "AvlRoll", "Contour"]

# Mesh and vortex core, from the BRYAN mesh study (scripts/sim_export/crrcsim/AVL_CONVERGENCE.md):
# aligned strips 10 chordwise / 24 spanwise converge to 0.3 % MAC against the next finer level;
# the core ratio 0.25 is AVL's default, set explicitly because it moves the neutral point by
# about 2.3 % MAC at 0.5.
N_CHORD = 10
N_SPAN = 24
CORE_RATIO = 0.25
# A steady roll splits the controlled wing at the hinge into a front and an aft surface (Drela's rule 3,
# avl_doc.txt:1110-1117): the discretisation error of the control derivative at the hinge falls like
# 1/N_chord otherwise (BRYAN and JAGUAR: 4.5 % and 7.5 % between the declared and the refined mesh), and
# aligning the hinge with a panel edge does not cure it. Chordwise vortices of the front and the aft piece.
SPLIT_N_CHORD = (12, 8)
# AVL's chordwise limit per surface (KCMAX, amake.f:55): above it AVL prints "MAKESURF: Array overflow"
# and returns zero without an error.
AVL_MAX_CHORD_VORTICES = 50
# AVL's fixed arrays (AVL.INC:22-24): strips including the mirror images (NSMAX), vortices (NVMAX) and
# surfaces including the mirror images (NFMAX). Above them AVL stops with a message and no result, or
# worse, goes on with a corrupted lattice, so the adapter counts before it writes.
AVL_MAX_STRIPS = 500
AVL_MAX_VORTICES = 6000
AVL_MAX_SURFACES = 100
# The check run uses this factor on both counts. 40/96 overflows AVL's vortex array on BRYAN.
REFINE_FACTOR = 2
# Every airfoil is repanelled to this many points per side (cosine spaced), whatever it had: AVL stops
# at 399 contour points in total (its IBX limit; AeroSandbox's NACA 4-digit contour has 399 and a
# fine inline contour more), and a repanelling done only when a contour is too large would be an
# undeclared conditional substitution (ADR 0020). 80 per side give 159 points; BRYAN's own contours
# have 162. The same contour gives the thickness for CLAF.
AIRFOIL_POINTS_PER_SIDE = 80
# AVL's CLAF rule (avl_doc.txt): the lift-curve-slope factor 1 + 0.77 t/c.
CLAF_PER_THICKNESS = 0.77
# The longest one AVL run may take. The measured refined 20/48 run of BRYAN and JAGUAR takes 15 s and
# the 20/96 run 45 s; AVL can also spin forever on a geometry it cannot solve (a chain it reads tip
# first), so a run is never waited for longer than this. Expiry is a `timeout` error and the process
# group is killed (run_process).
AVL_MAX_RUN_S = 120.0
# AVL 3.40 prints the first on an overflow of its vortex arrays; on a mesh so fine that the influence
# matrix no longer fits LAPACK's integers it exits 0 with the second (BRYAN at 20/96).
# the log line of a run whose output was not understood
_FAILED_RUN_LOG = "%s; stdout tail: %s"
_OVERFLOW = (
    "Vortex array overflow",
    "Strip array overflow",
    "Surface array overflow",
    "DGETRF parameter number",
)


class AvlNeutralPoint(BaseModel):
    """The neutral point AVL found, and the caveats of the run.

    Attributes:
        x_np: x of the neutral point in m, in the geometry frame (aft positive).
        warnings: Tool validity warnings (mesh convergence), without origin.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    x_np: float
    warnings: tuple[KernelWarning, ...] = ()


class AvlRoll(BaseModel):
    """The steady roll AVL found, and the caveats of the run.

    Attributes:
        p_hat: ``p'b/2V`` in stability axes, positive for a roll to the right.
        warnings: Tool validity warnings (range, mesh convergence), without origin.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    p_hat: float
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


_ORIGIN = (0.0, 0.0, 0.0)


def _unchecked_warning(what: str, n_chord: int, n_span: int, reason: str) -> KernelWarning:
    """The refinement could not be run: the solver refused or did not solve the refined mesh.

    Args:
        what: The checked quantity, for the message.
        n_chord: Chordwise count of the refined mesh.
        n_span: Spanwise count of the refined mesh.
        reason: The error code of the refined run: ``avl_array_limit`` (beyond the solver's fixed
            arrays) or ``avl_roll_branch_inconsistent`` (the lattice left the linear branch).
    """
    cause = (
        "is beyond the solver's array limit"
        if reason == "avl_array_limit"
        else "gave no consistent solution"
    )
    return KernelWarning.of(
        "avl_refinement_unchecked",
        f"The refined mesh {cause}, so the convergence of the {what} could not be checked.",
        detail={"n_chord": n_chord, "n_span": n_span, "reason": reason},
    )


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

    def __init__(self, runtime: SolverRuntime, rules: Rules | None = None) -> None:
        """Create the adapter.

        Args:
            runtime: The runtime of the owning ``compute()`` call.
            rules: The rule parameters of the call (the canon's, with the caller's overrides). If
                omitted, those of the shipped canon without overrides.
        """
        super().__init__(runtime)
        if rules is None:
            from aero_kernel.build import (
                shipped_build,  # build imports this module
            )

            rules = Rules(shipped_build().model)
        self.rules = rules

    def roll_rate_limit(self) -> float:
        """The largest ``|p b / 2V|`` for which AVL is used: the canon rule ``avl-roll-rate-validity``."""
        return self.rules.value("avl-roll-rate-validity", "max_roll_rate_coefficient")

    def join_tolerance_m(self) -> float:
        """The distance in m under which two hinge-line ends are one: the canon rule ``hinge-line-continuity``."""
        return self.rules.value("hinge-line-continuity", "join_tolerance")

    def settings(self) -> dict[str, JsonValue]:
        """Every constant that shapes an AVL result or decides value versus error: mesh, core, checks.

        Not listed: the AVL compile limits (``AVL_MAX_*``). They only gate a refusal before the run.
        The tolerances of the self-checks are the kernel configuration (``config.yaml``); the roll-rate
        limit and the join tolerance are rule parameters of the canon, with the caller's overrides.
        """
        cfg = config()
        return {
            "avl_nchord": N_CHORD,
            "avl_nspan": N_SPAN,
            "avl_airfoil_points_per_side": AIRFOIL_POINTS_PER_SIDE,
            "avl_core_ratio": CORE_RATIO,
            "avl_refine_factor": REFINE_FACTOR,
            "avl_refinement_tolerance_mac": cfg.avl_refinement_tolerance_mac.value,
            "avl_roll_refinement_tolerance": cfg.avl_roll_refinement_tolerance.value,
            "avl_roll_nchord_front": SPLIT_N_CHORD[0],
            "avl_roll_nchord_aft": SPLIT_N_CHORD[1],
            "avl_roll_branch_tolerance": cfg.avl_roll_branch_tolerance.value,
            "avl_chord_spacing": CHORD_SPACING,
            "avl_sliver_steps": SLIVER_STEPS,
            "avl_claf_per_thickness": CLAF_PER_THICKNESS,
            "avl_roll_rate_limit": self.roll_rate_limit(),
            "avl_roll_print_floor": cfg.avl_roll_print_floor.value,
            "avl_roll_moment_tolerance": cfg.avl_roll_moment_tolerance.value,
            "avl_control_echo_tolerance": cfg.avl_control_echo_tolerance.value,
            "avl_cl_tolerance": cfg.avl_cl_tolerance.value,
            "avl_contour_margin": cfg.avl_contour_margin.value,
            "avl_max_run_s": AVL_MAX_RUN_S,
            "avl_mesh_decimals": MESH_DECIMALS,
            "avl_join_tolerance_m": self.join_tolerance_m(),
        }

    async def _contours(self, airfoils: tuple[Airfoil, ...]) -> tuple[Contour, ...]:
        """The contours and ``CLAF`` of the airfoils, computed in a pool worker."""
        return await self.runtime.run_cpu(contour_worker, airfoils)

    async def _execute(
        self,
        surfaces: tuple[MeshSurface, ...],
        contours: tuple[Contour, ...],
        mesh: tuple[int, int],
        commands: str,
        reference: MainWingProperties,
        xyz_ref: tuple[float, float, float],
    ) -> str:
        """One AVL run on one mesh; returns the output text.

        Raises:
            FormulaError: ``tool_unavailable``; ``unsupported_configuration`` (``avl_array_limit``)
                if the mesh overflows AVL's vortex array.
            RuntimeError: If AVL exits with an error (a defect of ours).
        """
        from avl_binary import avl_path  # the wheel is a declared requirement

        n_chord, n_span = mesh
        widest = max(surface.n_chord or n_chord for surface in surfaces)
        if widest > AVL_MAX_CHORD_VORTICES:
            raise FormulaError(
                ErrorCategory.UNSUPPORTED_CONFIGURATION,
                "avl_array_limit",
                f"{widest} chordwise vortices on one surface are beyond the solver's limit of "
                f"{AVL_MAX_CHORD_VORTICES}",
                "the chordwise resolution of the vortex lattice is limited by the solver",
                detail={"n_chord": widest, "n_span": n_span},
            )
        strips = sum((len(s.sections) - 1) * (2 if s.symmetric else 1) for s in surfaces)
        vortices = sum(
            (len(s.sections) - 1) * (2 if s.symmetric else 1) * (s.n_chord or n_chord)
            for s in surfaces
        )
        surface_count = sum(2 if s.symmetric else 1 for s in surfaces)
        if (
            strips > AVL_MAX_STRIPS
            or vortices > AVL_MAX_VORTICES
            or surface_count > AVL_MAX_SURFACES
        ):
            raise FormulaError(
                ErrorCategory.UNSUPPORTED_CONFIGURATION,
                "avl_array_limit",
                f"the vortex lattice has {strips} strips, {vortices} vortices and "
                f"{surface_count} surfaces, beyond the solver's limits of {AVL_MAX_STRIPS}, "
                f"{AVL_MAX_VORTICES} and {AVL_MAX_SURFACES}",
                "the airplane has too many surfaces or sections for the vortex lattice solver",
                detail={
                    "n_chord": n_chord,
                    "n_span": n_span,
                    "strips": strips,
                    "vortices": vortices,
                },
            )
        files: dict[str, str | bytes] = {
            GEOMETRY_FILE: avl_geometry(
                surfaces,
                [c.claf for c in contours],
                n_chord=n_chord,
                s_ref=reference.s_ref,
                c_ref=reference.c_mac,
                b_ref=reference.b_ref,
                xyz_ref=xyz_ref,
            ),
        }
        for index, contour in enumerate(contours):
            files[airfoil_file_name(index)] = airfoil_file(f"airfoil {index}", contour.coordinates)
        try:
            async with asyncio.timeout(AVL_MAX_RUN_S):
                run = await self.runtime.run_process(
                    files, commands, executable=avl_path(), args=(GEOMETRY_FILE,)
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
        if run.returncode != 0:
            msg = f"the vortex lattice run did not complete (exit {run.returncode})"
            logger.error(_FAILED_RUN_LOG, msg, run.stdout[-500:])
            raise RuntimeError(msg)
        return run.stdout

    async def _run(
        self,
        surfaces: tuple[MeshSurface, ...],
        contours: tuple[Contour, ...],
        n_chord: int,
        n_span: int,
        cl: float,
        reference: MainWingProperties,
    ) -> AvlOutput:
        """One neutral-point run on one mesh.

        Raises:
            FormulaError: As :meth:`_execute`.
            RuntimeError: If AVL fails or misses the lift coefficient (a defect of ours).
        """
        stdout = await self._execute(
            surfaces,
            contours,
            (n_chord, n_span),
            avl_commands(cl, CORE_RATIO),
            reference,
            _ORIGIN,
        )
        output = parse_avl_output(stdout)
        if output is None:
            msg = "the vortex lattice run did not complete (no neutral point in the output)"
            logger.error(_FAILED_RUN_LOG, msg, stdout[-500:])
            raise RuntimeError(msg)
        if abs(output.cl - cl) > config().avl_cl_tolerance.value:
            msg = f"the vortex lattice trimmed to C_L {output.cl}, not the requested {cl}"
            raise RuntimeError(msg)
        return output

    async def _run_roll(
        self,
        surfaces: tuple[MeshSurface, ...],
        contours: tuple[Contour, ...],
        mesh: tuple[int, int],
        run: tuple[float, float],
        reference: MainWingProperties,
        xyz_ref: tuple[float, float, float],
    ) -> RollOutput:
        """One steady-roll run on one mesh, and the checks of the run itself.

        Args:
            surfaces: The mesh with the roll devices driven.
            contours: The airfoil contours.
            mesh: Chordwise and spanwise strip counts.
            run: The lift coefficient and the aileron command in degrees.
            reference: The kernel's reference values.
            xyz_ref: The airplane's reference point.

        Raises:
            FormulaError: As :meth:`_execute`.
            RuntimeError: If AVL fails, misses the lift coefficient, leaves a rolling moment or
                echoes another control value (a defect of ours, reported as ``internal``).
        """
        cl, delta = run
        stdout = await self._execute(
            surfaces,
            contours,
            mesh,
            avl_roll_commands(cl, CORE_RATIO, delta),
            reference,
            xyz_ref,
        )
        output = parse_roll_output(stdout)
        if output is None:
            msg = "the vortex lattice run did not complete (no steady roll in the output)"
            logger.error(_FAILED_RUN_LOG, msg, stdout[-500:])
            raise RuntimeError(msg)
        if abs(output.cl - cl) > config().avl_cl_tolerance.value:
            msg = f"the vortex lattice trimmed to C_L {output.cl}, not the requested {cl}"
            raise RuntimeError(msg)
        if abs(output.cl_stability) > config().avl_roll_moment_tolerance.value:
            msg = (
                f"the steady roll left a rolling moment of {output.cl_stability} in stability axes"
            )
            raise RuntimeError(msg)
        if abs(output.control - delta) > config().avl_control_echo_tolerance.value:
            msg = f"the vortex lattice echoed the control at {output.control}, not the commanded {delta}"
            raise RuntimeError(msg)
        linear = -output.cl_delta * delta / output.cl_p
        cfg = config()
        if abs(output.p_hat - linear) > (
            cfg.avl_roll_branch_tolerance.value * abs(linear) + cfg.avl_roll_print_floor.value
        ):
            raise FormulaError(
                ErrorCategory.NOT_CONVERGED,
                "avl_roll_branch_inconsistent",
                f"the vortex lattice gave p'b/2V = {output.p_hat:.5f} while its derivatives at the "
                f"state without roll give {linear:.5f}: the solution is not on the branch of the "
                "linear response",
                "the mesh is not usable for this airplane; the result is discarded",
                detail={"p_hat": output.p_hat, "p_hat_linear": linear},
            )
        return output

    async def neutral_point(self, airplane: AirplaneGeometry, cl: float) -> AvlNeutralPoint:
        """Find the neutral point of the airplane at a lift coefficient.

        Runs the declared mesh and the mesh refined by ``REFINE_FACTOR``; the declared mesh's
        value is returned. A disagreement above ``avl_refinement_tolerance_mac`` (``config.yaml``) is a
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

        join = self.join_tolerance_m()
        declared = mesh_surfaces(airplane, N_SPAN, number, join_tolerance_m=join)
        refined = mesh_surfaces(airplane, N_SPAN * REFINE_FACTOR, number, join_tolerance_m=join)
        contours = await self._contours(tuple(numbers))
        first = await self._run(declared, contours, N_CHORD, N_SPAN, cl, reference)
        warnings: list[KernelWarning] = []
        n_chord, n_span = N_CHORD * REFINE_FACTOR, N_SPAN * REFINE_FACTOR
        try:
            second = await self._run(refined, contours, n_chord, n_span, cl, reference)
        except FormulaError as error:
            if error.code != "avl_array_limit":
                raise
            warnings.append(_unchecked_warning("neutral point", n_chord, n_span, error.code))
        else:
            delta = abs(second.x_np - first.x_np) / reference.c_mac
            if delta > config().avl_refinement_tolerance_mac.value:
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

    async def steady_roll(
        self, airplane: AirplaneGeometry, cl: float, delta_a_deg: float
    ) -> AvlRoll:
        """Find the steady roll at an aileron command and a lift coefficient (canon ``roll-rate``).

        AVL's default axes are the stability axes, the rotation is about the airplane's reference
        point. Runs the declared mesh and the mesh refined by ``REFINE_FACTOR`` with the ends of
        the driven devices as stations; the declared mesh's value is returned. The result is
        reported against the primer's range, and a disagreement of the meshes above
        ``avl_roll_refinement_tolerance`` (``config.yaml``) is declared.

        Args:
            airplane: The validated geometry, devices at rest, with one main wing and at least one
                device acting as aileron.
            cl: The lift coefficient of the operating point.
            delta_a_deg: The aileron command in degrees, positive = roll to the right.

        Returns:
            ``p'b/2V`` and the adapter's warnings.

        Raises:
            FormulaError: ``tool_unavailable``; ``invalid_input`` for a non-finite command or a
                device without a hinge; ``unsupported_configuration`` for a deflected geometry
                state, a roll device on an unmirrored wing or off the main wing, a discontinuous
                hinge line, or a declared mesh that overflows AVL's array.
            RuntimeError: If AVL fails or breaks its own checks (a defect, reported as
                ``internal``).
            ValueError: If the airplane has no device acting as aileron (a defect of the caller;
                the canon's ``has_aileron`` condition prevents it).
        """
        self.require_available()
        refuse_deflected_devices(airplane, "AVL")
        if not math.isfinite(delta_a_deg):
            raise FormulaError(
                ErrorCategory.INVALID_INPUT,
                "invalid_input",
                f"delta_a = {delta_a_deg} is not admissible",
                "give a finite aileron deflection",
                parameter="delta_a",
            )
        if not roll_segments(airplane):
            msg = "the steady roll needs a device acting as aileron"
            raise ValueError(msg)
        reference = main_wing_properties(airplane)
        numbers: dict[Airfoil, int] = {}

        def number(airfoil: Airfoil) -> int:
            return numbers.setdefault(airfoil, len(numbers))

        join = self.join_tolerance_m()
        refined_split = (SPLIT_N_CHORD[0] * REFINE_FACTOR, SPLIT_N_CHORD[1] * REFINE_FACTOR)

        def driven(n_span: int, split: tuple[int, int]) -> tuple[MeshSurface, ...]:
            main, *others = mesh_surfaces(
                airplane, n_span, number, drive_roll=True, join_tolerance_m=join
            )
            return (*split_at_hinge(main, split), *others)

        declared = driven(N_SPAN, SPLIT_N_CHORD)
        refined = driven(N_SPAN * REFINE_FACTOR, refined_split)
        contours = await self._contours(tuple(numbers))
        xyz_ref = airplane.xyz_ref
        first = await self._run_roll(
            declared, contours, (N_CHORD, N_SPAN), (cl, delta_a_deg), reference, xyz_ref
        )
        warnings: list[KernelWarning] = []
        roll_limit = self.roll_rate_limit()
        if abs(first.p_hat) > roll_limit:
            warnings.append(
                KernelWarning.of(
                    "avl_roll_rate_beyond_range",
                    "AVL's primer gives -0.10 < pb/2V < 0.10 as the practical limit for roll "
                    "rates, beyond which results should be interpreted with caution.",
                    detail={"p_hat": first.p_hat, "limit": roll_limit},
                )
            )
        n_chord, n_span = N_CHORD * REFINE_FACTOR, N_SPAN * REFINE_FACTOR
        try:
            second = await self._run_roll(
                refined, contours, (n_chord, n_span), (cl, delta_a_deg), reference, xyz_ref
            )
        except FormulaError as error:
            # the declared run passed every check: a refined run that is beyond the arrays or off the
            # linear branch leaves the value standing and the refinement unchecked, declared
            if error.code not in ("avl_array_limit", "avl_roll_branch_inconsistent"):
                raise
            warnings.append(_unchecked_warning("roll rate", n_chord, n_span, error.code))
        else:
            if abs(second.p_hat - first.p_hat) > (
                config().avl_roll_refinement_tolerance.value * abs(first.p_hat)
            ):
                warnings.append(
                    KernelWarning.of(
                        "avl_mesh_not_converged",
                        "The roll rate changes by more than the tolerance when the vortex "
                        "lattice is refined; the value is mesh-dependent.",
                        detail={
                            "p_hat_declared": first.p_hat,
                            "p_hat_refined": second.p_hat,
                            "n_chord_declared": N_CHORD,
                            "n_span_declared": N_SPAN,
                            "n_chord_refined": n_chord,
                            "n_span_refined": n_span,
                        },
                    )
                )
        return AvlRoll(p_hat=first.p_hat, warnings=tuple(warnings))

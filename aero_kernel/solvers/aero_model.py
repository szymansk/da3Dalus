"""Reusable AeroBuildup model functions and the pool worker's cache of them (ch. 8.4, 8.8, 8.10).

Building AeroBuildup symbolically costs more than solving through it (BRYAN, NeuralFoil
``xlarge``: 3.3 s to build, 0.9 s for the zero-lift angle through the built function). So the
Opti problems call one CasADi ``Function`` per converted airplane, built once:
``f(V, alpha, p, q, r, rho, mu, a) -> (L, D_profile, D_induced, CL, Cl, Cn)``. It offers the two
parts of AeroBuildup's drag, never its total: a problem that needs drag forms the kernel's drag from
them (``aerobuildup.kernel_drag``, #1346), so there is one producer of drag. The function is a
mechanism, never a value: a problem solved through a cached function gives the same numbers as one
solved through a function built for it.

The cache is process-local and lives only in a pool worker: the runtime installs it there
(:func:`install_model_cache`), bounded to ``max_models`` functions, least recently used out. Where
none is installed (a worker function called in the parent process, e.g. by a unit test), the
function is built for the call. A function is never shipped between processes (433 MB serialised).
The key (:func:`model_key`) is computed in the parent, so the runtime can route a job to the worker
that holds its function.

AeroSandbox and CasADi are imported only when a function is built, never at import.
"""

import importlib
import time
from collections import OrderedDict
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from aero_kernel.canonical import sha256_of, spell_non_finite
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.solvers.air import GAMMA, GAS_CONSTANT, AirState
from aero_kernel.solvers.asb_airplane import load_aerosandbox

__all__ = [
    "MAX_MODELS_PER_WORKER",
    "MODEL_INPUTS",
    "MODEL_OUTPUTS",
    "AeroModel",
    "ModelCache",
    "aero_model",
    "build_aero_model",
    "install_model_cache",
    "installed_model_cache",
    "model_key",
]

# Functions one pool worker keeps. Measured on BRYAN and CHEKKER (NeuralFoil xlarge, 2026-10-31):
# about 280 MB RSS per built function, plus 200-300 MB while an IPOPT solve through it lives. Two
# cover the clean and the configured airplane of one aircraft; the bound of the whole runtime is
# workers x this x ~280 MB.
MAX_MODELS_PER_WORKER = 2

# The inputs of the function, in order: true airspeed (m/s), angle of attack (deg), the body rates
# p, q, r (rad/s), density (kg/m^3), dynamic viscosity (Pa s), speed of sound (m/s).
MODEL_INPUTS = ("v", "alpha", "p", "q", "r", "density", "dynamic_viscosity", "speed_of_sound")
# The AeroBuildup outputs the Opti problems read: lift, the profile and the induced drag (N), the lift
# coefficient, and the rolling and yawing moment coefficients (body axes, as AeroBuildup returns
# them). AeroBuildup's total drag and its coefficient are left out: they hold the viscous factor the
# kernel removes (``aerobuildup.kernel_drag``, #1346); its pitching moment is left out because no
# problem reads it (#1347).
MODEL_OUTPUTS = ("L", "D_profile", "D_induced", "CL", "Cl", "Cn")


def model_key(
    airplane: AirplaneGeometry,
    *,
    roll_deg: float,
    model_size: str,
    tool_versions: Mapping[str, str],
) -> str:
    """The key of an airplane's model function: what changes the converted airplane or its model.

    SHA-256 over the canonical JSON of the geometry the worker converts (its flaps included), the
    aileron command that ``to_asb_airplane`` builds in, the NeuralFoil model size and the versions
    of AeroSandbox and NeuralFoil. The air state and the operating point are inputs of the
    function, not part of the key. Exact values, never rounded (ch. 8.4).

    Args:
        airplane: The geometry as the worker converts it (devices as configured).
        roll_deg: The aileron command in degrees, 0 for the airplane without one.
        model_size: The NeuralFoil model size the function evaluates its sections with.
        tool_versions: Distribution -> version of the tools the function is built with.

    Returns:
        ``"sha256:"`` plus the hex digest.
    """
    return sha256_of(
        {
            "airplane": spell_non_finite(airplane.model_dump(mode="json")),
            "roll_deg": roll_deg,
            "model_size": model_size,
            "tool_versions": dict(tool_versions),
        }
    )


class _SymbolicAtmosphere:
    """A duck-typed ``asb.Atmosphere`` whose state is three CasADi symbols.

    It answers the methods AeroBuildup calls as :class:`~aero_kernel.solvers.air.FixedAtmosphere`
    does, with temperature and pressure derived the same way, so the function's air is an input.
    The symbols are ``casadi.MX`` (untyped boundary).
    """

    def __init__(
        self,
        density: Any,  # noqa: ANN401  # untyped casadi boundary
        dynamic_viscosity: Any,  # noqa: ANN401  # untyped casadi boundary
        speed_of_sound: Any,  # noqa: ANN401  # untyped casadi boundary
    ) -> None:
        self._density = density
        self._dynamic_viscosity = dynamic_viscosity
        self._speed_of_sound = speed_of_sound

    def density(self) -> Any:  # noqa: ANN401  # untyped casadi boundary
        """Density in kg/m^3."""
        return self._density

    def dynamic_viscosity(self) -> Any:  # noqa: ANN401  # untyped casadi boundary
        """Dynamic viscosity in Pa s."""
        return self._dynamic_viscosity

    def speed_of_sound(self) -> Any:  # noqa: ANN401  # untyped casadi boundary
        """Speed of sound in m/s."""
        return self._speed_of_sound

    def ratio_of_specific_heats(self) -> float:
        """Ratio of specific heats of air."""
        return GAMMA

    def temperature(self) -> Any:  # noqa: ANN401  # untyped casadi boundary
        """Temperature in K implied by the speed of sound."""
        return self._speed_of_sound**2 / (GAMMA * GAS_CONSTANT)

    def pressure(self) -> Any:  # noqa: ANN401  # untyped casadi boundary
        """Pressure in Pa implied by density and temperature."""
        return self._density * GAS_CONSTANT * self.temperature()


def load_casadi() -> Any:  # noqa: ANN401  # untyped casadi boundary
    """Return the ``casadi`` module (installed with AeroSandbox), typed as the untyped boundary."""
    return importlib.import_module("casadi")


class AeroModel:
    """One converted airplane's AeroBuildup as a CasADi function of the operating point and air."""

    def __init__(self, function: Any) -> None:  # noqa: ANN401  # untyped casadi boundary
        """Wrap a built function.

        Args:
            function: The ``casadi.Function`` of :data:`MODEL_INPUTS` to :data:`MODEL_OUTPUTS`.
        """
        self._function = function

    def __call__(
        self,
        v: object,
        alpha: object,
        air: AirState,
        *,
        p: object = 0.0,
        q: object = 0.0,
        r: object = 0.0,
    ) -> dict[str, Any]:
        """Evaluate the model: numbers give numbers, Opti variables give expressions.

        Args:
            v: True airspeed in m/s.
            alpha: Angle of attack in degrees.
            air: The air state.
            p: Body roll rate in rad/s.
            q: Body pitch rate in rad/s.
            r: Body yaw rate in rad/s.

        Returns:
            Output name (:data:`MODEL_OUTPUTS`) -> its value or expression.
        """
        values = self._function(
            v, alpha, p, q, r, air.density, air.dynamic_viscosity, air.speed_of_sound
        )
        return dict(zip(MODEL_OUTPUTS, values, strict=True))


def build_aero_model(asb_airplane: object, model_size: str) -> AeroModel:
    """Build the model function of a converted airplane: AeroBuildup over symbolic inputs.

    Args:
        asb_airplane: The ``asb.Airplane`` (from ``to_asb_airplane``).
        model_size: The NeuralFoil model size AeroBuildup evaluates its sections with.

    Returns:
        The model. A failure to build it propagates: there is no other route (ADR 0020).
    """
    asb, casadi = load_aerosandbox(), load_casadi()
    symbols = {name: casadi.MX.sym(name) for name in MODEL_INPUTS}
    atmosphere = _SymbolicAtmosphere(
        symbols["density"], symbols["dynamic_viscosity"], symbols["speed_of_sound"]
    )
    result = asb.AeroBuildup(
        asb_airplane,
        asb.OperatingPoint(
            atmosphere=atmosphere,
            velocity=symbols["v"],
            alpha=symbols["alpha"],
            p=symbols["p"],
            q=symbols["q"],
            r=symbols["r"],
        ),
        model_size=model_size,
    ).run()
    function = casadi.Function(
        "aero_model",
        [symbols[name] for name in MODEL_INPUTS],
        [result[name] for name in MODEL_OUTPUTS],
        list(MODEL_INPUTS),
        list(MODEL_OUTPUTS),
    )
    return AeroModel(function)


class ModelCache:
    """A bounded LRU of model functions by key, local to one pool worker process."""

    def __init__(self, max_models: int) -> None:
        """Create an empty cache.

        Args:
            max_models: Functions kept; the least recently used one is dropped.

        Raises:
            ValueError: If the bound is below 1.
        """
        if max_models < 1:
            msg = f"max_models must be >= 1, got {max_models}"
            raise ValueError(msg)
        self.max_models = max_models
        self._models: OrderedDict[str, AeroModel] = OrderedDict()

    def keys(self) -> tuple[str, ...]:
        """The keys held, least recently used first."""
        return tuple(self._models)

    def get(self, key: str, build: Callable[[], AeroModel]) -> tuple[AeroModel, bool]:
        """Return the function of ``key``, building and keeping it on a miss.

        Args:
            key: The model key.
            build: Builds the function; called only on a miss. A failure keeps nothing.

        Returns:
            The function and whether it was held (a hit).
        """
        found = self._models.get(key)
        if found is not None:
            self._models.move_to_end(key)
            return found, True
        built = build()
        self._models[key] = built
        while len(self._models) > self.max_models:
            self._models.popitem(last=False)
        return built, False


@dataclass
class _Installed:
    """The cache of this process; set only in a pool worker (by the runtime), never in the parent."""

    cache: ModelCache | None = None


_INSTALLED = _Installed()


def install_model_cache(max_models: int) -> None:
    """Install this worker process's model cache; idempotent for the same bound.

    Called by the runtime in its pool worker processes only, so the parent process holds no
    model and no state of this module.

    Args:
        max_models: Functions the worker keeps.
    """
    current = _INSTALLED.cache
    if current is None or current.max_models != max_models:
        _INSTALLED.cache = ModelCache(max_models)


def installed_model_cache() -> ModelCache | None:
    """The cache installed in this process, ``None`` outside a pool worker."""
    return _INSTALLED.cache


def aero_model(key: str | None, asb_airplane: object, model_size: str) -> tuple[AeroModel, str]:
    """The model function of a converted airplane: from this worker's cache, or built.

    Args:
        key: The model key the parent computed (:func:`model_key`); ``None`` builds without caching.
        asb_airplane: The ``asb.Airplane`` the key stands for.
        model_size: The NeuralFoil model size.

    Returns:
        The model and one diagnostics note (built or reused, the build time), for the parent's log.
    """
    started = time.perf_counter()
    cache = _INSTALLED.cache

    def build() -> AeroModel:
        return build_aero_model(asb_airplane, model_size)

    if key is None or cache is None:
        model, held = build(), False
    else:
        model, held = cache.get(key, build)
    if held:
        return model, "aero model reused from the worker's cache"
    return model, f"aero model built in {time.perf_counter() - started:.3f} s"

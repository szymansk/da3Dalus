"""The rpm search finds a balance between a covered and an uncovered table block (gh-1417).

At a given flight speed the low-rpm blocks of an APC table do not reach the advance ratio
``J = V / (n D)``, so the lowest covered block has an uncovered neighbour; a balance below the lowest
covered block speed but above the coverage edge exists inside the table. The drags are those measured
with the real AeroBuildup on the Avistar Elite (3.70 kg, sea level, gh-1415); the drive train is the
Avistar's (AXI 4120/14 + APC 13x8E + 4S). Before gh-1417 the speeds 17.0 to 17.75, 22, 26, 30 and 34 m/s
ended as ``outside_propeller_table``. The independent check reads the published table with a plain
piecewise-linear interpolation (``powertrain_reference``) and tests thrust = drag at the found speed.
"""

import math

import pytest
from aero_kernel.components import Components
from aero_kernel.errors import FormulaError
from aero_kernel.formulas.motor_propeller_equilibrium import equilibrium
from aero_kernel.formulas.motor_propeller_part_load import demand_within_full_throttle, part_load
from aero_kernel.tests import powertrain_reference as reference
from aero_kernel.tests.components_builders import apc_13x8e_table, components_of
from aero_kernel.tests.formula_builders import close
from aero_kernel.tests.test_powertrain_chain import context_for
from aero_kernel.tests.test_powertrain_edges import small_table

RHO, D_PROP, U_BAT = 1.225, 13 * 0.0254, 14.8

# the drag in N of the level-flight point of the Avistar at 3.70 kg, measured with the real AeroBuildup
AVISTAR_DRAG_N = {
    16.75: 2.213591167719497,  # worked before
    17.0: 2.2097443439386915,
    17.25: 2.2073249349152047,
    17.58: 2.206194234279141,  # the minimum-drag speed
    17.75: 2.206481838220401,
    22.0: 2.3660607575224635,
    26.0: 2.7346176244044735,
    30.0: 3.2749161760431096,
    34.0: 3.9383640343642004,
    36.0: 4.317298919173118,  # worked before; the thrust demand ratio is above 1
}


def avistar_components() -> Components:
    document = components_of(
        "axi_4120_14", "thunder_power_prolitex_4s_6000", "apc_13x8e"
    ).model_dump()
    document["propeller"]["table"] = apc_13x8e_table()
    return Components.model_validate(document)


def motor() -> tuple[float, float, float]:
    found = avistar_components().motor
    assert found is not None
    assert found.io_no_load_a is not None
    assert found.rm_ohm is not None
    return found.kv_rpm_per_volt, found.io_no_load_a, found.rm_ohm


@pytest.mark.parametrize("v", sorted(AVISTAR_DRAG_N))
def test_the_part_load_speed_is_found_where_the_table_covers_the_balance(v: float) -> None:
    k_v, i_0, r_m = motor()
    drag = AVISTAR_DRAG_N[v]
    ctx = context_for("motor-propeller-part-load")
    got = part_load(ctx, avistar_components(), v, RHO, k_v, i_0, r_m, U_BAT, D_PROP, drag)
    rpm = got.n_pl * 60.0
    c_t, _ = reference.coefficients(rpm, v / (got.n_pl * D_PROP))
    assert close(RHO * got.n_pl**2 * D_PROP**4 * c_t, drag, 1e-6)
    assert got.p_bat > 0.0


def test_a_table_that_truly_lacks_the_balance_still_fails_truthfully() -> None:
    # the drag is far above the thrust the whole table gives at this speed
    k_v, i_0, r_m = motor()
    ctx = context_for("motor-propeller-part-load")
    with pytest.raises(FormulaError) as caught:
        part_load(ctx, avistar_components(), 17.58, RHO, k_v, i_0, r_m, U_BAT, D_PROP, 1000.0)
    assert caught.value.code == "outside_propeller_table"
    assert "coverage edge" in caught.value.message
    assert int(str(caught.value.detail["covered_grid_points"])) >= 1


def test_the_demand_above_full_throttle_at_36_m_s_fires_the_postcondition() -> None:
    k_v, i_0, r_m = motor()
    ctx = context_for("motor-propeller-part-load")
    got = part_load(
        ctx, avistar_components(), 36.0, RHO, k_v, i_0, r_m, U_BAT, D_PROP, AVISTAR_DRAG_N[36.0]
    )
    assert got.r_t > 1.0
    verdict = demand_within_full_throttle({}, {"r_t": got.r_t})
    assert verdict.state == "violated"


def test_the_equilibrium_finds_a_balance_below_the_lowest_covered_block() -> None:
    """Three blocks (1000, 2000, 3000 rpm), flat ``C_T`` 0.1 and ``C_P`` 3.0; the 1000 rpm block covers J up
    to 0.5 only, so at 5 m/s its grid point (J = 0.91) is uncovered, the coverage edge lies at J = 0.5
    (1817 rpm) and the balance at about 1880 rpm lies between the edge and the 2000 rpm block, where the
    search used to look no further. The independent value is a plain bisection of the motor torque
    ``(I - I_0) / K_v'`` against the propeller torque ``C_P rho n^2 D^5 / 2 pi`` on rpm."""
    components = small_table((3.0, 3.0), (0.5, 0.8, 0.8))
    got = equilibrium(
        context_for("motor-propeller-equilibrium"),
        components, 5.0, RHO, 162.0, 1.2, 0.082, U_BAT, D_PROP,
    )  # fmt: skip
    k_v_rad = 2.0 * math.pi * 162.0 / 60.0

    def residual(rpm: float) -> float:
        n = rpm / 60.0
        current = (U_BAT - 2.0 * math.pi * n / k_v_rad) / 0.082
        return (current - 1.2) / k_v_rad - 3.0 * RHO * n**2 * D_PROP**5 / (2.0 * math.pi)

    low, high = 1817.0, 2000.0
    for _ in range(100):
        middle = 0.5 * (low + high)
        low, high = (middle, high) if residual(middle) > 0.0 else (low, middle)
    assert close(got.n_prop * 60.0, 0.5 * (low + high), 1e-6)
    assert 1817.0 < got.n_prop * 60.0 < 2000.0

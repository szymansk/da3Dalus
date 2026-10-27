"""The MVP chain on the reference fleet through the public compute(), real AVL and real AeroSandbox.

Aero tier. The goldens are **regression, not validation** (aero_kernel/CLAUDE.md): they pin what this
build computes, written by running the kernel at SM_target = 0.10 and the fleet masses of the README.
Per quantity the three values are the neutral-point worlds textbook / Pappas / AVL. The aircraft the
kernel cannot compute record the error it gives: BELEMNITOS' V-tail has no neutral point (#1208), and
RV-7's flaps need a landing deflection for the approach speed of ``lateral-static-stability-app``.
CHEKKER and WIESEL compute since #1307 (asymmetric fuselage sections).
"""

from typing import Any

import pytest
from aero_kernel import compute
from aero_kernel.schema import AircraftInput, ComputeResult, QuantityStatus
from aero_kernel.tests.engine_builders import request
from aero_kernel.tests.reference_fleet import FleetMember, flap_values, reference_document

pytestmark = [pytest.mark.aero]

SM_TARGET = 0.10
WORLDS = ("textbook", "pappas", "avl")
REL = 2e-3  # the regression tolerance
SLUGS = (
    "vertical-tail-volume",
    "spiral-parameter-md",
    "spiral-parameter-mp",
    "pitching-moment-slope",
    "static-margin-probe",
    "dihedral-effect-md",
    "weathercock-stability-md",
    "spiral-criterion-md",
    "spiral-doubling-time-md",
    "dihedral-effect-app",
    "weathercock-stability-app",
    "spiral-criterion-app",
    "spiral-doubling-time-app",
    "dihedral-effect-mp",
    "roll-due-to-yaw-rate-mp",
    "weathercock-stability-mp",
    "spiral-criterion-mp",
    "spiral-doubling-time-mp",
)

GOLDEN = {
    FleetMember.BRYAN: {
        "vertical-tail-volume": (0.055889564925848935, 0.05583702833957879, 0.05515425431836371),
        "spiral-parameter-md": (1.7135753862157608, 1.7119646132346549, 1.6910307455501599),
        "spiral-parameter-mp": (1.167204513905726, 1.1661073334084173, 1.1518481971886754),
        "pitching-moment-slope": (-1.3115618905556574, -1.2968088122754111, -1.1050754071108644),
        "static-margin-probe": (0.19954525497087794, 0.1973006740721528, 0.16812973559376723),
        "dihedral-effect-md": (-0.052987, -0.052994, -0.053084),
        "weathercock-stability-md": (0.075545, 0.075403, 0.07356),
        "spiral-criterion-md": (-0.003884704058, -0.0038680910759999994, -0.0036519060599999997),
        "spiral-doubling-time-md": (3.9379928970024514, 3.947696723079849, 4.082343249552841),
        "dihedral-effect-app": (-0.065496, -0.065506, -0.065641),
        "weathercock-stability-app": (0.07712, 0.07698, 0.075153),
        "spiral-criterion-app": (-0.003915086872, -0.0038964298600000034, -0.003653030627999999),
        "spiral-doubling-time-app": (3.7592825330560475, 3.7706870314356933, 3.9301895864856635),
        "dihedral-effect-mp": (-0.083425, -0.08344, -0.08364),
        "weathercock-stability-mp": (0.080515, 0.080376, 0.078577),
        "spiral-criterion-mp": (
            -0.004186289479999999,
            -0.004164419495999999,
            -0.003881071616999998,
        ),
        "spiral-doubling-time-mp": (3.4677179965108755, 3.4801930056930392, 3.654574190584924),
        "roll-due-to-yaw-rate-mp": (0.198492, 0.198411, 0.197361),
    },
    FleetMember.JAGUAR: {
        "vertical-tail-volume": (0.02241860994257862, 0.021857472431766837, 0.021616158168489292),
        "spiral-parameter-md": (
            0.0007303477167890575,
            0.0007120671230824995,
            0.0007042056489917863,
        ),
        "spiral-parameter-mp": (
            0.0004490689478745131,
            0.0004378287580394342,
            0.0004329949729566515,
        ),
        "pitching-moment-slope": (-1.5960540933191, -1.2201297183921038, -1.0584653993321353),
        "static-margin-probe": (0.23525456859109092, 0.1798442118766681, 0.15601527663178882),
        "dihedral-effect-md": (-0.030767, -0.030826, -0.030851),
        "weathercock-stability-md": (0.030626, 0.02956, 0.029101),
        "spiral-criterion-md": (-0.0023671478850000004, -0.002262971888, -0.0022180813279999998),
        "spiral-doubling-time-md": (4.083530498610765, 4.125962242847995, 4.145533509220245),
        "dihedral-effect-app": (-0.039633, -0.039715, -0.03975),
        "weathercock-stability-app": (0.032849, 0.031775, 0.031314),
        "spiral-criterion-app": (-0.0029734095239999994, -0.00284744017, -0.002793358038),
        "spiral-doubling-time-app": (3.2272734763561552, 3.262813460933183, 3.279058022228713),
        "dihedral-effect-mp": (-0.055154, -0.055278, -0.055332),
        "weathercock-stability-mp": (0.03773, 0.036645, 0.036179),
        "spiral-criterion-mp": (-0.004331298048000001, -0.004164590823, -0.004092960631000002),
        "spiral-doubling-time-mp": (2.3096629279775573, 2.3350676133483383, 2.346627634877029),
        "roll-due-to-yaw-rate-mp": (0.176848, 0.175885, 0.175469),
    },
    FleetMember.RV7: {
        "vertical-tail-volume": (0.08299981005376741, 0.08260137411188775, 0.08222818779390684),
        "spiral-parameter-md": (3.6146224130288553, 3.5972706204796734, 3.5810184431754646),
        "spiral-parameter-mp": (2.2546181173979285, 2.2437949493376346, 2.2336576654915663),
        "pitching-moment-slope": (-0.4505140970124621, -0.4065268549318808, -0.3653271658861832),
        "static-margin-probe": (0.10973313432856603, 0.09901902354717118, 0.08898388581823653),
        "dihedral-effect-md": (-0.112096, -0.112185, -0.112267),
        "weathercock-stability-md": (0.114502, 0.113536, 0.112631),
        "spiral-criterion-md": (0.006020090312000003, 0.006082540443000002, 0.0061408189810000045),
        "spiral-doubling-time-md": (-5.937876581993306, -5.830019976816344, -5.731169242376445),
        "dihedral-effect-mp": (-0.151054, -0.151205, -0.151346),
        "weathercock-stability-mp": (0.132902, 0.131928, 0.131016),
        "spiral-criterion-mp": (0.005651143291999998, 0.005747741324000001, 0.005838151786000001),
        "spiral-doubling-time-mp": (-6.3565948508987455, -6.2057826369791815, -6.0691432369182),
        "roll-due-to-yaw-rate-mp": (0.187581, 0.186972, 0.186401),
        "dihedral-effect-app": (-0.11211, -0.112147, -0.112181),
        "weathercock-stability-app": (0.104331, 0.103376, 0.102481),
        "spiral-criterion-app": (
            0.0031651667940000017,
            0.0032547406920000015,
            0.003338640119000001,
        ),
        "spiral-doubling-time-app": (-8.06557909709055, -7.776385503427931, -7.51954205227241),
    },
    FleetMember.CHEKKER: {
        "vertical-tail-volume": (0.042546551629209804, 0.04191818550080524, 0.04137168394275927),
        "spiral-parameter-md": (1.2845980820454492, 1.2656259705003, 1.2491255767805247),
        "spiral-parameter-mp": (0.8554188074942738, 0.8427852053891246, 0.831797529698),
        "pitching-moment-slope": (-1.5595587307566676, -1.392390174606797, -1.2470006122770396),
        "static-margin-probe": (0.3171375216474266, 0.28314366136553354, 0.2535785769853561),
        "dihedral-effect-md": (-0.124651, -0.124693, -0.12473),
        "weathercock-stability-md": (0.005753, 0.004657, 0.003705),
        "spiral-criterion-md": (0.006432202177, 0.006583627014, 0.0067152360949999995),
        "spiral-doubling-time-md": (-0.676009157397108, -0.6056980924994139, -0.5471834026151904),
        "dihedral-effect-app": (-0.135866, -0.13593, -0.135985),
        "weathercock-stability-app": (0.008742, 0.007634, 0.006671),
        "spiral-criterion-app": (0.006900898919999999, 0.007074727484, 0.007225877743999999),
        "spiral-doubling-time-app": (-0.8173664987185193, -0.7471403993758698, -0.6888284003262578),
        "dihedral-effect-mp": (-0.161403, -0.161519, -0.16162),
        "weathercock-stability-mp": (0.01732, 0.016187, 0.015202),
        "spiral-criterion-mp": (0.007542825768999999, 0.007773946279999999, 0.007974946856),
        "spiral-doubling-time-mp": (-1.173657637682534, -1.0931877655930589, -1.0270137560432142),
        "roll-due-to-yaw-rate-mp": (0.23288, 0.230876, 0.229132),
    },
    FleetMember.WIESEL: {
        "vertical-tail-volume": (0.03972881444148937, 0.03888724528575182, 0.039253299538574225),
        "spiral-parameter-md": (4.028012641050421, 3.9426878901036906, 3.9798012844600827),
        "spiral-parameter-mp": (2.463369991980496, 2.4111888173453107, 2.433885871725516),
        "pitching-moment-slope": (-1.3243032159540764, -1.0700535061683092, -1.1806435710670928),
        "static-margin-probe": (0.26732632326361927, 0.21600300146763238, 0.23832691874180295),
        "dihedral-effect-md": (-0.083991, -0.084106, -0.084056),
        "weathercock-stability-md": (0.043255, 0.041521, 0.042275),
        "spiral-criterion-md": (
            0.0011887518259999993,
            0.0012746439350000008,
            0.0012373301410000008,
        ),
        "spiral-doubling-time-md": (-16.053050533818052, -14.453128455749342, -15.121128081003977),
        "dihedral-effect-app": (-0.101737, -0.101908, -0.101834),
        "weathercock-stability-app": (0.045006, 0.043302, 0.044043),
        "spiral-criterion-app": (
            0.0007094788889999998,
            0.0008373537819999994,
            0.0007817986109999982,
        ),
        "spiral-doubling-time-app": (-25.435770361130125, -20.866202192095763, -22.668109206889252),
        "dihedral-effect-mp": (-0.111077, -0.111277, -0.11119),
        "weathercock-stability-mp": (0.046421, 0.044734, 0.045468),
        "spiral-criterion-mp": (0.0003720830140000004, 0.000522801388, 0.0004572379739999988),
        "spiral-doubling-time-mp": (-48.488364341622756, -33.4652578906001, -38.783355437738635),
        "roll-due-to-yaw-rate-mp": (0.15037, 0.14847, 0.149297),
    },
}

# Quantity -> the cause the kernel names, for the aircraft it cannot compute.
UPSTREAM = {
    FleetMember.BELEMNITOS: {"neutral-point": "unsupported_layout"},
}
# The approach point of RV-7 binds the landing configuration, which needs the landing flap deflection.
RV7_NEEDS_LANDING_DEFLECTION = tuple(s for s in SLUGS if s.endswith("-app"))


async def run(member: FleetMember, *, flaps: bool = True) -> ComputeResult:
    aircraft = AircraftInput.model_validate(
        {
            "airplane": reference_document(member),
            "values": {
                "aircraft-mass": member.mass_kg,
                "altitude": 0.0,
                "static-margin-target": SM_TARGET,
                **(flap_values(member) if flaps else {}),
            },
        }
    )
    return await compute(aircraft, request(*SLUGS))


@pytest.mark.parametrize("member", list(GOLDEN))
@pytest.mark.asyncio
async def test_the_chain_per_world_is_the_regression_golden(member: FleetMember) -> None:
    result = await run(member)
    by_slug = {q.slug: q for q in result.quantities}
    for slug, golden in GOLDEN[member].items():
        quantity = by_slug[slug]
        assert quantity.status is QuantityStatus.OK, (slug, quantity.error)
        assert quantity.interval is not None, slug
        worlds = quantity.interval.worlds
        assert set(worlds) == {f"neutral-point={w}" for w in WORLDS}, slug
        for name, value in zip(WORLDS, golden, strict=True):
            assert abs(worlds[f"neutral-point={name}"] - value) <= REL * abs(value), (slug, name)


@pytest.mark.parametrize("member", [FleetMember.BRYAN, FleetMember.JAGUAR, FleetMember.RV7])
@pytest.mark.asyncio
async def test_the_declared_caveats_travel_with_the_values(member: FleetMember) -> None:
    by_slug = {q.slug: q for q in (await run(member)).quantities}
    assert "avl_body_equivalent_round" in {w.code for w in by_slug["dihedral-effect-md"].warnings}
    assert "aerobuildup_no_downwash" in {w.code for w in by_slug["static-margin-probe"].warnings}


@pytest.mark.asyncio
async def test_a_stable_spiral_of_the_rv7_reports_a_negative_halving_time() -> None:
    by_slug = {q.slug: q for q in (await run(FleetMember.RV7)).quantities}
    criterion, time = by_slug["spiral-criterion-md"], by_slug["spiral-doubling-time-md"]
    assert criterion.interval is not None
    assert time.interval is not None
    assert criterion.interval.min > 0.0
    assert time.interval.max < 0.0
    assert "spiral_halving_time_reported" in {w.code for w in time.warnings}


@pytest.mark.asyncio
async def test_the_unstable_spirals_of_bryan_and_jaguar_have_a_positive_doubling_time() -> None:
    for member in (FleetMember.BRYAN, FleetMember.JAGUAR):
        by_slug = {q.slug: q for q in (await run(member)).quantities}
        assert by_slug["spiral-criterion-md"].interval is not None
        assert by_slug["spiral-criterion-md"].interval.max < 0.0  # type: ignore[union-attr]
        assert by_slug["spiral-doubling-time-md"].interval.min > 0.0  # type: ignore[union-attr]


@pytest.mark.parametrize("member", list(UPSTREAM))
@pytest.mark.asyncio
async def test_the_aircraft_the_kernel_cannot_compute_name_their_cause(member: FleetMember) -> None:
    causes = UPSTREAM[member]
    for quantity in (await run(member)).quantities:
        assert quantity.status is QuantityStatus.ERROR, quantity.slug
        assert quantity.error is not None
        assert quantity.error.code == "upstream_failed", quantity.slug
        listed: Any = quantity.error.detail["causes"]
        named: dict[str, str] = {c["quantity"]: c["code"] for c in listed}
        assert set(named) & set(causes), (quantity.slug, named)
        for cause, code in causes.items():
            if cause in named:
                assert named[cause] == code


@pytest.mark.asyncio
async def test_the_rv7_approach_point_needs_the_landing_deflection() -> None:
    by_slug = {q.slug: q for q in (await run(FleetMember.RV7, flaps=False)).quantities}
    for slug in RV7_NEEDS_LANDING_DEFLECTION:
        error = by_slug[slug].error
        assert error is not None
        assert error.code == "upstream_failed"
        assert error.detail["causes"] == [{"quantity": "airplane-landing", "code": "missing_input"}]

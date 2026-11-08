"""The MVP chain of the plan batch (#1372): one compute per aircraft through the public compute().

Aero tier, real AVL and real AeroSandbox. The goldens are **regression, not validated**
(aero_kernel/CLAUDE.md): they pin what this build computes (NeuralFoil xlarge, AVL 3.40) for the 28 plan
models of the reference fleet, written by running the kernel at SM_target = 0.10, an aileron
deflection of 20 deg, sea level and the masses of the README. Per quantity the golden is a value, the
three neutral-point worlds textbook / Pappas / AVL, the worlds by name, or what the kernel answers
instead of a value: ``not_applicable`` or the error with the causes upstream. A quantity that does not
compute is recorded, never repaired by editing a copy (reference README).
"""

from dataclasses import dataclass
from typing import Any, cast

import pytest
from aero_kernel import compute
from aero_kernel.schema import ComputeResult, QuantityResult, QuantityStatus
from aero_kernel.tests.engine_builders import request
from aero_kernel.tests.reference_fleet import PLAN_BATCH, FleetMember, aircraft_input
from aero_kernel.tests.test_mvp_chain_fleet import SLUGS as LATERAL_SLUGS

pytestmark = [pytest.mark.aero]

SM_TARGET = 0.10
AILERON_DEFLECTION_DEG = 20.0  # the roll-rate fleet test's command
REL = 2e-3  # the regression tolerance of the fleet tests
WORLDS = ("textbook", "pappas", "avl")
CORE_SLUGS = (
    "stall-speed",
    "max-lift-coefficient",
    "minimum-drag-speed",
    "max-lift-to-drag-ratio",
    "minimum-sink-speed",
    "neutral-point",
    "centre-of-gravity-design",
    "roll-rate-approach",
)
SLUGS = CORE_SLUGS + LATERAL_SLUGS
NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class Failed:
    """The error the kernel gives instead of a value, with the causes of an ``upstream_failed``."""

    code: str
    causes: tuple[tuple[str, str], ...] = ()


Golden = float | tuple[float, float, float] | dict[str, float] | str | Failed

# Regression goldens per member, recorded for #1372.
GOLDEN: dict[FleetMember, dict[str, Golden]] = {
    FleetMember.A6M2_ZERO: {
        "stall-speed": 6.8172879410350316,
        "max-lift-coefficient": 1.308261607596656,
        "minimum-drag-speed": 10.769740793993797,
        "max-lift-to-drag-ratio": 11.241855721961663,
        "minimum-sink-speed": 7.786654368127998,
        "neutral-point": (0.17902112270045786, 0.18428609578122332, 0.182214),
        "centre-of-gravity-design": (0.16561333063009467, 0.17087830371086013, 0.1688062079296368),
        "roll-rate-approach": {"roll-rate=aerobuildup": 274.55807405126234},
        "horizontal-tail-volume": (0.37205623864068527, 0.36552095112965804, 0.36809299498875264),
        "turn-sideslip": NOT_APPLICABLE,
        "turn-sideslip-gain": NOT_APPLICABLE,
        "rudder-roll-authority-md": NOT_APPLICABLE,
        "rudder-roll-authority-mp": NOT_APPLICABLE,
        "vertical-tail-volume": (0.036428454333094634, 0.03585956394061605, 0.03608345784551365),
        "spiral-parameter-md": (2.6335677977732135, 2.592440293312145, 2.6086265353268208),
        "spiral-parameter-mp": (1.376688856562345, 1.3551895896220196, 1.3636508941041245),
        "dihedral-effect-md": (-0.039235, -0.039226, -0.03923),
        "weathercock-stability-md": (0.020517, 0.019345, 0.019806),
        "spiral-criterion-md": (
            -0.00016501468900000007,
            -3.743801099999984e-05,
            -8.759905000000007e-05,
        ),
        "spiral-doubling-time-md": (47.6593492666797, 199.60639643757065, 87.06610116789169),
        "dihedral-effect-app": (-0.058695, -0.058739, -0.058721),
        "weathercock-stability-app": (0.021617, 0.02045, 0.020909),
        "spiral-criterion-app": (
            0.0001424078349999999,
            0.00031409573100000003,
            0.00024651504100000037,
        ),
        "spiral-doubling-time-app": (-54.381256478637454, -23.61905326620964, -30.61351961432831),
        "dihedral-effect-mp": (-0.076578, -0.07667, -0.076634),
        "roll-due-to-yaw-rate-mp": (0.215168, 0.214136, 0.214542),
        "weathercock-stability-mp": (0.024196, 0.023036, 0.023493),
        "spiral-criterion-mp": (
            0.0002070938920000001,
            0.00041903578400000023,
            0.0003355632599999995,
        ),
        "spiral-doubling-time-mp": (-41.07589079773987, -19.60452926018001, -24.823477662246262),
    },
    FleetMember.AERONCA_CHAMP: {
        "stall-speed": Failed("not_converged"),
        "max-lift-coefficient": Failed("not_converged"),
        "minimum-drag-speed": 6.995921888883736,
        "max-lift-to-drag-ratio": 10.514759606017298,
        "minimum-sink-speed": 6.716799268910961,
        "neutral-point": (0.15279815198459995, 0.1596476642966776, 0.179001),
        "centre-of-gravity-design": (0.13822453812664923, 0.14507405043872687, 0.16442738614204927),
        "roll-rate-approach": NOT_APPLICABLE,
        "horizontal-tail-volume": (0.405745440245864, 0.39720143472964636, 0.3730602989125999),
        "turn-sideslip": (6.453012150533729, 6.407514692740901, 6.27897861858383),
        "turn-sideslip-gain": (2.288487962729586, 2.2723528025803725, 2.22676893389656),
        "rudder-roll-authority-md": (
            0.04592933898305125,
            0.04401378353044662,
            0.038821879513095306,
        ),
        "rudder-roll-authority-mp": (
            0.042337482552232346,
            0.04057173113172073,
            0.035785854595840466,
        ),
        "vertical-tail-volume": (0.019832795463061086, 0.01941481189055722, 0.018233796946927235),
        "spiral-parameter-md": (2.315827794856021, 2.267020859051104, 2.129116586418803),
        "spiral-parameter-mp": (2.1347208784100364, 2.089730838517864, 1.9626112268334275),
        "dihedral-effect-md": (-0.117556, -0.117621, -0.117805),
        "weathercock-stability-md": (0.016582, 0.01519, 0.011256),
        "spiral-criterion-md": (
            0.0019553629519999992,
            0.0021867736099999997,
            0.0028408649190000005,
        ),
        "spiral-doubling-time-md": (-3.7114370931085405, -3.182096479474585, -2.1522768356658464),
        "dihedral-effect-app": Failed(
            "upstream_failed", (("stall-speed-landing", "not_converged"),)
        ),
        "weathercock-stability-app": Failed(
            "upstream_failed", (("stall-speed-landing", "not_converged"),)
        ),
        "spiral-criterion-app": Failed(
            "upstream_failed", (("stall-speed-landing", "not_converged"),)
        ),
        "spiral-doubling-time-app": Failed(
            "upstream_failed", (("stall-speed-landing", "not_converged"),)
        ),
        "dihedral-effect-mp": (-0.122993, -0.123083, -0.123337),
        "roll-due-to-yaw-rate-mp": (0.281468, 0.279688, 0.274643),
        "weathercock-stability-mp": (0.017347, 0.015948, 0.011993),
        "spiral-criterion-mp": (0.0021696702310000007, 0.002418275397, 0.003121333881999999),
        "spiral-doubling-time-mp": (-3.4947005667824587, -3.0161552117156227, -2.0755231109267074),
    },
    FleetMember.ALBATROS_4: {
        "stall-speed": 7.303938072489423,
        "max-lift-coefficient": 1.3266096278339128,
        "minimum-drag-speed": 11.13550205226123,
        "max-lift-to-drag-ratio": 28.38645829464224,
        "minimum-sink-speed": 9.085192613967894,
        "neutral-point": (0.5906281445820271, 0.6062989298538811, 0.594349),
        "centre-of-gravity-design": (0.5612106733674225, 0.5768814586392765, 0.5649315287853954),
        "roll-rate-approach": Failed("upstream_failed", (("airplane-landing", "missing_input"),)),
        "horizontal-tail-volume": (0.24250689210040904, 0.23900509201425954, 0.2416754282268909),
        "turn-sideslip": NOT_APPLICABLE,
        "turn-sideslip-gain": NOT_APPLICABLE,
        "rudder-roll-authority-md": NOT_APPLICABLE,
        "rudder-roll-authority-mp": NOT_APPLICABLE,
        "vertical-tail-volume": NOT_APPLICABLE,
        "spiral-parameter-md": NOT_APPLICABLE,
        "spiral-parameter-mp": NOT_APPLICABLE,
        "dihedral-effect-md": (-0.058299, -0.05829, -0.058297),
        "weathercock-stability-md": (0.023168, 0.022765, 0.023072),
        "spiral-criterion-md": (-0.0024224427840000002, -0.002375275885, -0.0024111722740000003),
        "spiral-doubling-time-md": (5.778164569401125, 5.805967445694296, 5.784776531744912),
        "dihedral-effect-app": Failed("upstream_failed", (("airplane-landing", "missing_input"),)),
        "weathercock-stability-app": Failed(
            "upstream_failed", (("airplane-landing", "missing_input"),)
        ),
        "spiral-criterion-app": Failed("upstream_failed", (("airplane-landing", "missing_input"),)),
        "spiral-doubling-time-app": Failed(
            "upstream_failed", (("airplane-landing", "missing_input"),)
        ),
        "dihedral-effect-mp": (-0.072435, -0.072445, -0.072438),
        "roll-due-to-yaw-rate-mp": (0.217079, 0.216526, 0.216948),
        "weathercock-stability-mp": (0.024128, 0.023726, 0.024033),
        "spiral-criterion-mp": (-0.003662148427, -0.0035920440260000003, -0.0036456285839999996),
        "spiral-doubling-time-mp": (3.6609271746691663, 3.684101249478073, 3.6662732043121475),
    },
    FleetMember.BARRACUDA: {
        "stall-speed": 6.654436151345649,
        "max-lift-coefficient": 1.3840291689322524,
        "minimum-drag-speed": 7.683638661764813,
        "max-lift-to-drag-ratio": 18.423876568192068,
        "minimum-sink-speed": 7.659394666663513,
        "neutral-point": (0.3233724791517571, 0.3360690659751089, 0.343987),
        "centre-of-gravity-design": (0.30695610742188484, 0.3196526942452366, 0.32757062827012773),
        "roll-rate-approach": NOT_APPLICABLE,
        "horizontal-tail-volume": (0.35210780489140453, 0.3456392931957352, 0.3416053548185844),
        "turn-sideslip": (10.303868336392854, 10.23897937977017, 10.198512499576704),
        "turn-sideslip-gain": (1.7514511840798475, 1.7404213614734094, 1.7335428025752397),
        "rudder-roll-authority-md": NOT_APPLICABLE,
        "rudder-roll-authority-mp": NOT_APPLICABLE,
        "vertical-tail-volume": NOT_APPLICABLE,
        "spiral-parameter-md": NOT_APPLICABLE,
        "spiral-parameter-mp": NOT_APPLICABLE,
        "dihedral-effect-md": (-0.161939, -0.162064, -0.162142),
        "weathercock-stability-md": (0.041872, 0.04057, 0.039758),
        "spiral-criterion-md": (-0.004203611765, -0.0040033920719999986, -0.0038786097600000003),
        "spiral-doubling-time-md": (5.70432348211378, 5.883835678242321, 6.0050657265693435),
        "dihedral-effect-app": (-0.156314, -0.156391, -0.156438),
        "weathercock-stability-app": (0.042624, 0.041326, 0.040517),
        "spiral-criterion-app": (-0.0030088932200000003, -0.002863014168, -0.00277229156),
        "spiral-doubling-time-app": (8.413999436755917, 8.675921892575758, 8.852453085160809),
        "dihedral-effect-mp": (-0.162109, -0.162236, -0.162315),
        "roll-due-to-yaw-rate-mp": (0.283926, 0.282359, 0.28138),
        "weathercock-stability-mp": (0.041855, 0.040554, 0.039742),
        "spiral-criterion-mp": (
            -0.004237041200000001,
            -0.004035628270000003,
            -0.003909755755000001,
        ),
        "spiral-doubling-time-mp": (5.652939178969017, 5.830607797523347, 5.951033446249415),
    },
    FleetMember.BF109_E: {
        "stall-speed": 6.843045695823234,
        "max-lift-coefficient": 1.2858849539528456,
        "minimum-drag-speed": 10.160000043988687,
        "max-lift-to-drag-ratio": 10.505908251323739,
        "minimum-sink-speed": 7.723453163020594,
        "neutral-point": (0.20712454311260511, 0.2125368153548087, 0.211291),
        "centre-of-gravity-design": (0.19371080089450216, 0.19912307313670574, 0.19787725778189705),
        "roll-rate-approach": {"roll-rate=aerobuildup": 302.84144223171677},
        "horizontal-tail-volume": (0.40284067252978883, 0.3972597486851551, 0.39854438484322685),
        "turn-sideslip": NOT_APPLICABLE,
        "turn-sideslip-gain": NOT_APPLICABLE,
        "rudder-roll-authority-md": NOT_APPLICABLE,
        "rudder-roll-authority-mp": NOT_APPLICABLE,
        "vertical-tail-volume": (0.04281955752077564, 0.042223490567127916, 0.04236069529928419),
        "spiral-parameter-md": (2.753554082541157, 2.7152234063568406, 2.724046492634404),
        "spiral-parameter-mp": (1.5912163246249666, 1.5690658979944827, 1.57416455903312),
        "dihedral-effect-md": (-0.051688, -0.051698, -0.051696),
        "weathercock-stability-md": (0.036695, 0.035252, 0.035584),
        "spiral-criterion-md": (
            -0.0009344817309999993,
            -0.0007627488080000008,
            -0.0008021848640000001,
        ),
        "spiral-doubling-time-md": (13.649597598542023, 16.1319676027203, 15.468169643405078),
        "dihedral-effect-app": (-0.065526, -0.065586, -0.065572),
        "weathercock-stability-app": (0.038313, 0.03687, 0.037202),
        "spiral-criterion-app": (
            -0.0009917706390000008,
            -0.0007813783019999998,
            -0.0008297859579999992,
        ),
        "spiral-doubling-time-app": (12.445224396153693, 15.287193598577899, 14.50560440802741),
        "dihedral-effect-mp": (-0.084901, -0.085031, -0.085001),
        "roll-due-to-yaw-rate-mp": (0.227192, 0.226045, 0.226309),
        "weathercock-stability-mp": (0.042232, 0.040794, 0.041125),
        "spiral-criterion-mp": (
            -0.0013620074749999996,
            -0.0010977581139999994,
            -0.0011585917630000005,
        ),
        "spiral-doubling-time-mp": (9.42064506031885, 11.368379417145281, 10.841250166946029),
    },
    FleetMember.D520_DEWOITINE: {
        "stall-speed": 6.765163889454842,
        "max-lift-coefficient": 1.3289362585060194,
        "minimum-drag-speed": 9.753921487467574,
        "max-lift-to-drag-ratio": 9.728638055189545,
        "minimum-sink-speed": 7.674137783482635,
        "neutral-point": (0.24423028424520912, 0.25066110352931265, 0.247102),
        "centre-of-gravity-design": (0.23082562178560986, 0.2372564410697134, 0.23369733754040073),
        "roll-rate-approach": {"roll-rate=aerobuildup": 280.95209167599967},
        "horizontal-tail-volume": (0.44533991407867124, 0.43663043599306395, 0.44145065140007755),
        "turn-sideslip": NOT_APPLICABLE,
        "turn-sideslip-gain": NOT_APPLICABLE,
        "rudder-roll-authority-md": NOT_APPLICABLE,
        "rudder-roll-authority-mp": NOT_APPLICABLE,
        "vertical-tail-volume": (0.040896118512460444, 0.04011016711242576, 0.040545147832323505),
        "spiral-parameter-md": (2.1467064770906874, 2.1054505578860594, 2.1282834320750745),
        "spiral-parameter-mp": (1.3288419823766515, 1.3033039789068213, 1.3174378542756642),
        "dihedral-effect-md": (-0.044722, -0.044769, -0.044743),
        "weathercock-stability-md": (0.042121, 0.039927, 0.041142),
        "spiral-criterion-md": (-0.002306103314, -0.002015993468999999, -0.002176686538),
        "spiral-doubling-time-md": (6.013580637682904, 6.552390190713209, 6.236158229154348),
        "dihedral-effect-app": (-0.055318, -0.055426, -0.055367),
        "weathercock-stability-app": (0.043123, 0.04094, 0.042148),
        "spiral-criterion-app": (-0.0025142033210000005, -0.0021740693180000003, -0.00236223845),
        "spiral-doubling-time-app": (5.296941337889683, 5.853697750138209, 5.525927238067355),
        "dihedral-effect-mp": (-0.073122, -0.073332, -0.073216),
        "roll-due-to-yaw-rate-mp": (0.223751, 0.222597, 0.223236),
        "weathercock-stability-mp": (0.046185, 0.04403, 0.045222),
        "spiral-criterion-mp": (
            -0.0031086819929999994,
            -0.0026866419299999998,
            -0.002920010391999999,
        ),
        "spiral-doubling-time-mp": (4.301531001610061, 4.7865924638288835, 4.501080259675114),
    },
    FleetMember.DARDO: {
        "stall-speed": 6.887458490162249,
        "max-lift-coefficient": 1.2332810837100099,
        "minimum-drag-speed": 10.369581487148654,
        "max-lift-to-drag-ratio": 20.40328526800063,
        "minimum-sink-speed": 8.436373630769891,
        "neutral-point": (0.4389129818522856, 0.45677169973887405, 0.450004),
        "centre-of-gravity-design": (0.41933262980526087, 0.4371913476918493, 0.4304236479529753),
        "roll-rate-approach": {"roll-rate=aerobuildup": 166.09886545077975},
        "horizontal-tail-volume": (0.49125924068546045, 0.4769681500891164, 0.4823838697791472),
        "turn-sideslip": NOT_APPLICABLE,
        "turn-sideslip-gain": NOT_APPLICABLE,
        "rudder-roll-authority-md": NOT_APPLICABLE,
        "rudder-roll-authority-mp": NOT_APPLICABLE,
        "vertical-tail-volume": (0.029370357737493778, 0.028445506641711645, 0.028795986141929436),
        "spiral-parameter-md": (0.809671033500381, 0.7841750845150564, 0.7938369722488846),
        "spiral-parameter-mp": (0.5359172743515055, 0.5190416311311361, 0.5254367870959209),
        "dihedral-effect-md": (-0.078655, -0.078707, -0.078687),
        "weathercock-stability-md": (0.040391, 0.038955, 0.039499),
        "spiral-criterion-md": (
            -0.0027036051700000006,
            -0.0025779935969999996,
            -0.0026255868959999995,
        ),
        "spiral-doubling-time-md": (7.405994620149918, 7.518440344547677, 7.474537887125269),
        "dihedral-effect-app": (-0.093403, -0.093499, -0.093463),
        "weathercock-stability-app": (0.04216, 0.040737, 0.041276),
        "spiral-criterion-app": (
            -0.003910029163000001,
            -0.003740149847000001,
            -0.003804445224999999,
        ),
        "spiral-doubling-time-app": (4.9191695910699735, 4.990413759962477, 4.962755808127431),
        "dihedral-effect-mp": (-0.100714, -0.100831, -0.100787),
        "roll-due-to-yaw-rate-mp": (0.202277, 0.200494, 0.201171),
        "weathercock-stability-mp": (0.043387, 0.04197, 0.042507),
        "spiral-criterion-mp": (
            -0.004592230497000001,
            -0.004399441097999999,
            -0.004472527381000001,
        ),
        "spiral-doubling-time-mp": (4.192030312598677, 4.251597336617843, 4.2283942647088),
    },
    FleetMember.ESTRELA: {
        "stall-speed": 10.669975972903739,
        "max-lift-coefficient": 1.0326563202767058,
        "minimum-drag-speed": 16.708469017700008,
        "max-lift-to-drag-ratio": 14.020180017807263,
        "minimum-sink-speed": 13.533345658346642,
        "neutral-point": (0.36560578438393637, 0.3679511346645267, 0.377691),
        "centre-of-gravity-design": (0.34287278438393637, 0.3452181346645267, 0.354958),
        "roll-rate-approach": {"roll-rate=aerobuildup": 310.6114952023161},
        "horizontal-tail-volume": (0.42668683237758076, 0.424938697120339, 0.4176789704455492),
        "turn-sideslip": NOT_APPLICABLE,
        "turn-sideslip-gain": NOT_APPLICABLE,
        "rudder-roll-authority-md": NOT_APPLICABLE,
        "rudder-roll-authority-mp": NOT_APPLICABLE,
        "vertical-tail-volume": (0.0518515742196652, 0.051646337255828255, 0.050794020906250806),
        "spiral-parameter-md": (0.0, 0.0, 0.0),
        "spiral-parameter-mp": (0.0, 0.0, 0.0),
        "dihedral-effect-md": (-0.057596, -0.057613, -0.057684),
        "weathercock-stability-md": (0.090787, 0.090257, 0.088057),
        "spiral-criterion-md": (
            -0.00037666443300000095,
            -0.00034406352699999955,
            -0.0002088813849999982,
        ),
        "spiral-doubling-time-md": (117.42250041918523, 127.77814113808168, 205.2059205347492),
        "dihedral-effect-app": (-0.085731, -0.085768, -0.085924),
        "weathercock-stability-app": (0.095813, 0.095284, 0.093087),
        "spiral-criterion-app": (
            0.0005185894150000012,
            0.0005609852280000008,
            0.0007377783469999996,
        ),
        "spiral-doubling-time-app": (-79.32073210813192, -72.89535331173555, -54.067256584892974),
        "dihedral-effect-mp": (-0.090285, -0.090326, -0.090495),
        "roll-due-to-yaw-rate-mp": (0.147542, 0.147159, 0.145564),
        "weathercock-stability-mp": (0.096838, 0.096309, 0.094113),
        "spiral-criterion-mp": (
            0.0006162144640000002,
            0.0006606899149999984,
            0.0008449821630000017,
        ),
        "spiral-doubling-time-mp": (-66.5392869887222, -61.6966690933062, -47.061013324555475),
    },
    FleetMember.EXTRA_300_EP: {
        "stall-speed": 7.438358759582281,
        "max-lift-coefficient": 1.1305431223321876,
        "minimum-drag-speed": 10.852394821506946,
        "max-lift-to-drag-ratio": 10.681996803329998,
        "minimum-sink-speed": 8.915164166646617,
        "neutral-point": (0.25944732644978885, 0.26976868096608064, 0.262058),
        "centre-of-gravity-design": (0.24046136778511942, 0.2507827223014112, 0.24307204133533059),
        "roll-rate-approach": {"roll-rate=aerobuildup": 371.10816259093366},
        "horizontal-tail-volume": (0.6108176111399876, 0.597353883260113, 0.6074121086734511),
        "turn-sideslip": NOT_APPLICABLE,
        "turn-sideslip-gain": NOT_APPLICABLE,
        "rudder-roll-authority-md": NOT_APPLICABLE,
        "rudder-roll-authority-mp": NOT_APPLICABLE,
        "vertical-tail-volume": (0.05870598043473505, 0.05752557647871669, 0.05840741018587116),
        "spiral-parameter-md": (0.0, 0.0, 0.0),
        "spiral-parameter-mp": (0.0, 0.0, 0.0),
        "dihedral-effect-md": (-0.046177, -0.046487, -0.046256),
        "weathercock-stability-md": (0.116651, 0.113522, 0.11586),
        "spiral-criterion-md": (
            -0.0061910457540000005,
            -0.005929650997999999,
            -0.0061249034760000026,
        ),
        "spiral-doubling-time-md": (6.608956546497889, 6.715701257456158, 6.63515534562295),
        "dihedral-effect-app": (-0.056972, -0.057357, -0.05707),
        "weathercock-stability-app": (0.119227, 0.116146, 0.118448),
        "spiral-criterion-app": (
            -0.007742702143999998,
            -0.0074276498860000005,
            -0.007662959455999999,
        ),
        "spiral-doubling-time-app": (4.882659744127933, 4.9583992255903375, 4.901277984796734),
        "dihedral-effect-mp": (-0.066161, -0.066607, -0.066273),
        "roll-due-to-yaw-rate-mp": (0.156235, 0.155242, 0.155986),
        "weathercock-stability-mp": (0.121886, 0.118851, 0.121118),
        "spiral-criterion-mp": (-0.009236806595000003, -0.008876043906, -0.009145677146000002),
        "spiral-doubling-time-mp": (3.9111481853070176, 3.9685985858878605, 3.9251920428867204),
    },
    FleetMember.F3A_COMPETICION: {
        "stall-speed": 9.4273490728853,
        "max-lift-coefficient": 1.252534220359849,
        "minimum-drag-speed": 14.855334169451703,
        "max-lift-to-drag-ratio": 13.42886400643957,
        "minimum-sink-speed": 12.014427563889276,
        "neutral-point": (0.709721191154154, 0.730534364957508, 0.731815),
        "centre-of-gravity-design": (0.6723783436115894, 0.6931915174149434, 0.6944721524574354),
        "roll-rate-approach": {"roll-rate=aerobuildup": 213.70622810002564},
        "horizontal-tail-volume": (0.5899244549987915, 0.5779997587526879, 0.5772660319300458),
        "turn-sideslip": NOT_APPLICABLE,
        "turn-sideslip-gain": NOT_APPLICABLE,
        "rudder-roll-authority-md": NOT_APPLICABLE,
        "rudder-roll-authority-mp": NOT_APPLICABLE,
        "vertical-tail-volume": (0.07539714038303016, 0.07393050692828093, 0.07384026493951033),
        "spiral-parameter-md": (0.9948237500461687, 0.9754723292099855, 0.9742816358597561),
        "spiral-parameter-mp": (0.6507099690417316, 0.6380522872637866, 0.6372734598252278),
        "dihedral-effect-md": (-0.064445, -0.064691, -0.064706),
        "weathercock-stability-md": (0.101632, 0.098471, 0.098277),
        "spiral-criterion-md": (0.004059605900999999, 0.004213303953999997, 0.004222707450999999),
        "spiral-doubling-time-md": (-11.927815501112669, -11.138855608075218, -11.09234986283521),
        "dihedral-effect-app": (-0.090134, -0.090501, -0.090524),
        "weathercock-stability-app": (0.10542, 0.1023, 0.102108),
        "spiral-criterion-app": (0.004786558078, 0.005023754192999998, 0.0050383331879999965),
        "spiral-doubling-time-app": (-9.255507317158576, -8.558041612659443, -8.517323662050588),
        "dihedral-effect-mp": (-0.093386, -0.093768, -0.093792),
        "roll-due-to-yaw-rate-mp": (0.127026, 0.125294, 0.125187),
        "weathercock-stability-mp": (0.106049, 0.102936, 0.102744),
        "spiral-criterion-mp": (0.004826792407999998, 0.005075343144000002, 0.005090794967999999),
        "spiral-doubling-time-mp": (-9.13461501269663, -8.43227573921247, -8.391022587446828),
    },
    FleetMember.FORCE_5: {
        "stall-speed": 5.125843977604058,
        "max-lift-coefficient": 1.298745662507848,
        "minimum-drag-speed": 7.450972493194853,
        "max-lift-to-drag-ratio": 20.194569311906303,
        "minimum-sink-speed": 6.262107724857891,
        "neutral-point": (0.3948732789626659, 0.4136087564098914, 0.409641),
        "centre-of-gravity-design": (0.3718779577654948, 0.39061343521272035, 0.3866456788028289),
        "roll-rate-approach": NOT_APPLICABLE,
        "horizontal-tail-volume": (0.4330900526424989, 0.42159871683181016, 0.4240323255535258),
        "turn-sideslip": (8.885015544630763, 8.750655369327486, 8.779120962133218),
        "turn-sideslip-gain": (0.9812314228727431, 0.9663931341462887, 0.9695367790832482),
        "rudder-roll-authority-md": (0.0565187489216417, 0.05326747487672587, 0.053947984129191995),
        "rudder-roll-authority-mp": (
            0.03992157697685694,
            0.03762506494264835,
            0.038105737339403874,
        ),
        "vertical-tail-volume": (0.01372938724373693, 0.01332864311638652, 0.013413511787841509),
        "spiral-parameter-md": (4.11662573997426, 3.9964664378505037, 4.021913499050442),
        "spiral-parameter-mp": (2.9077464469558434, 2.822872862158886, 2.840847195135303),
        "dihedral-effect-md": (-0.214558, -0.214534, -0.214539),
        "weathercock-stability-md": (0.011973, 0.010456, 0.010777),
        "spiral-criterion-md": (0.0027188151909999995, 0.002739322554, 0.0027350965200000008),
        "spiral-doubling-time-md": (-3.4451165725345474, -3.3151685676453146, -3.342320440892972),
        "dihedral-effect-app": (-0.224491, -0.224507, -0.224504),
        "weathercock-stability-app": (0.00999, 0.008487, 0.008806),
        "spiral-criterion-app": (0.0033965100760000003, 0.003431631498, 0.0034240755919999998),
        "spiral-doubling-time-app": (-2.7177394281784477, -2.613855942479592, -2.635838824122973),
        "dihedral-effect-mp": (-0.231131, -0.231173, -0.231164),
        "roll-due-to-yaw-rate-mp": (0.226793, 0.223404, 0.224122),
        "weathercock-stability-mp": (0.008966, 0.007474, 0.00779),
        "spiral-criterion-mp": (0.003938074478, 0.003982227180999999, 0.003972855816),
        "spiral-doubling-time-mp": (-2.3745512154738613, -2.2855752779969607, -2.304264884478818),
    },
    FleetMember.FORCE_FOUR: {
        "stall-speed": 6.39550098640449,
        "max-lift-coefficient": 1.480490297794477,
        "minimum-drag-speed": 9.36807864510023,
        "max-lift-to-drag-ratio": 15.311278650172873,
        "minimum-sink-speed": 6.997529221303774,
        "neutral-point": (0.2507272288643489, 0.26662007590717535, 0.266398),
        "centre-of-gravity-design": (0.23896585169960238, 0.25485869874242884, 0.2546366228352535),
        "roll-rate-approach": NOT_APPLICABLE,
        "horizontal-tail-volume": (0.6671657608314654, 0.6420471238221231, 0.6423981146852344),
        "turn-sideslip": (8.836203125806225, 8.738171656641601, 8.739547736612556),
        "turn-sideslip-gain": (1.983686676328828, 1.9616790655401086, 1.9619879891201897),
        "rudder-roll-authority-md": (
            0.035148107931325945,
            0.03245997904036142,
            0.032496804537401426,
        ),
        "rudder-roll-authority-mp": (
            0.019610575409645108,
            0.018110757711631207,
            0.01813130417143245,
        ),
        "vertical-tail-volume": (0.019157680370627258, 0.018410520415881204, 0.018420960724298455),
        "spiral-parameter-md": (1.8346745144164407, 1.7631212104336245, 1.7641210479611964),
        "spiral-parameter-mp": (1.023640390185872, 0.9837178581876797, 0.9842757086776733),
        "dihedral-effect-md": (-0.125134, -0.12517, -0.12517),
        "weathercock-stability-md": (0.010784, 0.00903, 0.009055),
        "spiral-criterion-md": (0.001244930234, 0.0014246110699999998, 0.001422030415),
        "spiral-doubling-time-md": (-7.708175211013613, -6.262133284437034, -6.280303368709638),
        "dihedral-effect-app": (-0.132968, -0.133056, -0.133055),
        "weathercock-stability-app": (0.010164, 0.008408, 0.008432),
        "spiral-criterion-app": (
            0.0014385681200000003,
            0.0016733723280000004,
            0.0016702033150000001,
        ),
        "spiral-doubling-time-app": (-6.7226742059771585, -5.417470054415533, -5.432691520887015),
        "dihedral-effect-mp": (-0.148345, -0.148535, -0.148532),
        "roll-due-to-yaw-rate-mp": (0.29427, 0.291378, 0.291418),
        "weathercock-stability-mp": (0.010291, 0.00854, 0.008564),
        "spiral-criterion-mp": (0.0018749147149999998, 0.00221662654, 0.002212017988),
        "spiral-doubling-time-mp": (-5.7726118263415875, -4.648544842886345, -4.661445717565414),
    },
    FleetMember.FW190_A8: {
        "stall-speed": 6.706278696123697,
        "max-lift-coefficient": 1.300948280555578,
        "minimum-drag-speed": 10.17029541668154,
        "max-lift-to-drag-ratio": 10.600751844333422,
        "minimum-sink-speed": 7.5623763779515185,
        "neutral-point": (0.20681329780192595, 0.21270994548851588, 0.210758),
        "centre-of-gravity-design": (0.19339657790569878, 0.1992932255922887, 0.19734128010377283),
        "roll-rate-approach": {"roll-rate=aerobuildup": 300.7813651300473},
        "horizontal-tail-volume": (0.4196355922799753, 0.41224127495951013, 0.4146889884912445),
        "turn-sideslip": NOT_APPLICABLE,
        "turn-sideslip-gain": NOT_APPLICABLE,
        "rudder-roll-authority-md": NOT_APPLICABLE,
        "rudder-roll-authority-mp": NOT_APPLICABLE,
        "vertical-tail-volume": (0.034852801889184326, 0.0342530448546372, 0.03445158020896272),
        "spiral-parameter-md": (2.512633090224307, 2.4693949776648236, 2.4837079302487743),
        "spiral-parameter-mp": (1.3892439540859225, 1.3653374447379993, 1.3732511281642559),
        "dihedral-effect-md": (-0.05767, -0.057673, -0.057672),
        "weathercock-stability-md": (0.068132, 0.066687, 0.067165),
        "spiral-criterion-md": (-0.0043990305559999995, -0.004280394258, -0.004319626273000001),
        "spiral-doubling-time-md": (5.197285371435456, 5.234564184963967, 5.222012052628208),
        "dihedral-effect-app": (-0.07216, -0.072222, -0.072202),
        "weathercock-stability-app": (0.069502, 0.068066, 0.068541),
        "spiral-criterion-app": (-0.005783157843999998, -0.005630073962, -0.005680626861999999),
        "spiral-doubling-time-app": (3.5874856938373925, 3.6144770182551897, 3.605445371423596),
        "dihedral-effect-mp": (-0.0902, -0.090336, -0.090291),
        "roll-due-to-yaw-rate-mp": (0.226725, 0.225448, 0.225872),
        "weathercock-stability-mp": (0.072927, 0.071511, 0.071979),
        "spiral-criterion-mp": (
            -0.007757463075000004,
            -0.007562675928000001,
            -0.0076270337069999986,
        ),
        "spiral-doubling-time-mp": (2.5633589708718842, 2.582715646150461, 2.576215013026955),
    },
    FleetMember.GEE_BEE_R3: {
        "stall-speed": 11.119308378946085,
        "max-lift-coefficient": 1.207374272879881,
        "minimum-drag-speed": 18.31963706867325,
        "max-lift-to-drag-ratio": 14.774752998226868,
        "minimum-sink-speed": 14.357825821497428,
        "neutral-point": (0.8789389065677747, 0.9000691490442492, 0.884585),
        "centre-of-gravity-design": (0.8272692728665344, 0.8483995153430088, 0.8329153662987596),
        "roll-rate-approach": Failed("upstream_failed", (("airplane-landing", "missing_input"),)),
        "horizontal-tail-volume": (0.5077486914550469, 0.498955783210295, 0.5053991878208068),
        "turn-sideslip": NOT_APPLICABLE,
        "turn-sideslip-gain": NOT_APPLICABLE,
        "rudder-roll-authority-md": NOT_APPLICABLE,
        "rudder-roll-authority-mp": NOT_APPLICABLE,
        "vertical-tail-volume": (0.05637335488345333, 0.055507104927640195, 0.05614188909731163),
        "spiral-parameter-md": (
            -0.00036310344272409885,
            -0.0003575238858241126,
            -0.0003616125606576572,
        ),
        "spiral-parameter-mp": (
            -0.00022303550120409768,
            -0.0002196082704944434,
            -0.00022211973013227761,
        ),
        "dihedral-effect-md": (-0.036873, -0.037035, -0.036916),
        "weathercock-stability-md": (0.040677, 0.038859, 0.040191),
        "spiral-criterion-md": (
            0.0014780083500000002,
            0.0015967823850000003,
            0.0015097473149999997,
        ),
        "spiral-doubling-time-md": (-16.41777873589153, -14.555944807138706, -15.89150151282882),
        "dihedral-effect-app": Failed("upstream_failed", (("airplane-landing", "missing_input"),)),
        "weathercock-stability-app": Failed(
            "upstream_failed", (("airplane-landing", "missing_input"),)
        ),
        "spiral-criterion-app": Failed("upstream_failed", (("airplane-landing", "missing_input"),)),
        "spiral-doubling-time-app": Failed(
            "upstream_failed", (("airplane-landing", "missing_input"),)
        ),
        "dihedral-effect-mp": (-0.059173, -0.059421, -0.059239),
        "roll-due-to-yaw-rate-mp": (0.11566, 0.114784, 0.115427),
        "weathercock-stability-mp": (0.04619, 0.044407, 0.045714),
        "spiral-criterion-mp": (
            0.0014503699619999996,
            0.0016539038269999997,
            0.0015046361690000008,
        ),
        "spiral-doubling-time-mp": (-16.11777646894122, -13.644108457429407, -15.39259599315846),
    },
    FleetMember.KASTAWAY: {
        "stall-speed": 5.819460951340531,
        "max-lift-coefficient": 1.258606806334081,
        "minimum-drag-speed": 8.96078664592611,
        "max-lift-to-drag-ratio": 16.22824235372535,
        "minimum-sink-speed": 6.634625250035501,
        "neutral-point": (0.271027631998723, 0.2823534117052573, 0.279787),
        "centre-of-gravity-design": (0.2543178346645118, 0.2656436143710461, 0.2630772026657888),
        "roll-rate-approach": NOT_APPLICABLE,
        "horizontal-tail-volume": (0.4158660657340806, 0.40638338661953916, 0.4085321533541346),
        "turn-sideslip": (3.8082816044502485, 3.7368107942792896, 3.7530168597315985),
        "turn-sideslip-gain": (0.7957181233903793, 0.7807847164490522, 0.7841708788521117),
        "rudder-roll-authority-md": (0.3590275742489033, 0.34311474294812105, 0.34668897131238985),
        "rudder-roll-authority-mp": (0.19681959110832406, 0.18809614707607153, 0.19005554578424833),
        "vertical-tail-volume": (0.03786496088285491, 0.037016325011567416, 0.03720862515248547),
        "spiral-parameter-md": (9.481789123185637, 9.269281670746608, 9.317435672283409),
        "spiral-parameter-mp": (5.197934621330696, 5.081437636429127, 5.10783575059217),
        "dihedral-effect-md": (-0.273865, -0.273998, -0.273968),
        "weathercock-stability-md": (0.045765, 0.042784, 0.043459),
        "spiral-criterion-md": (0.009044896785000003, 0.00894632177, 0.008968808529000002),
        "spiral-doubling-time-md": (-2.509211561335999, -2.475504365075181, -2.483138244308111),
        "dihedral-effect-app": (-0.289622, -0.289874, -0.289817),
        "weathercock-stability-app": (0.043311, 0.040348, 0.04102),
        "spiral-criterion-app": (0.009343021287, 0.009281131338000001, 0.009295145113999998),
        "spiral-doubling-time-app": (-2.2820396385060056, -2.245238904852004, -2.2536383579351575),
        "dihedral-effect-mp": (-0.306361, -0.306735, -0.30665),
        "roll-due-to-yaw-rate-mp": (0.243777, 0.239494, 0.240466),
        "weathercock-stability-mp": (0.042101, 0.039169, 0.039834),
        "spiral-criterion-mp": (0.009938495224, 0.009912891013999997, 0.009918391005999998),
        "spiral-doubling-time-mp": (-2.1449304764798875, -2.105698607707738, -2.1146941350873183),
    },
    FleetMember.MILES_MAGISTER: {
        "stall-speed": 6.945716327962192,
        "max-lift-coefficient": 1.464253888326677,
        "minimum-drag-speed": 12.010762255670143,
        "max-lift-to-drag-ratio": 9.78843347760925,
        "minimum-sink-speed": 7.275913706065835,
        "neutral-point": (0.1689013139066721, 0.1777610970278877, 0.170622),
        "centre-of-gravity-design": (0.15766880401634378, 0.1665285871375594, 0.15938949010967168),
        "roll-rate-approach": {"roll-rate=aerobuildup": 287.2007038164642},
        "horizontal-tail-volume": (0.7079557002763134, 0.686578993715531, 0.7038040634701922),
        "turn-sideslip": NOT_APPLICABLE,
        "turn-sideslip-gain": NOT_APPLICABLE,
        "rudder-roll-authority-md": NOT_APPLICABLE,
        "rudder-roll-authority-mp": NOT_APPLICABLE,
        "vertical-tail-volume": (0.04875436012616885, 0.04743890642732929, 0.0484988817634322),
        "spiral-parameter-md": (5.549596115396304, 5.399861061584259, 5.520515603915032),
        "spiral-parameter-mp": (2.036551118888933, 1.9816024190129533, 2.0258793606269685),
        "dihedral-effect-md": (-0.088017, -0.088049, -0.088023),
        "weathercock-stability-md": (0.066262, 0.062934, 0.065616),
        "spiral-criterion-md": (
            0.0006673207380000004,
            0.0008782018600000004,
            0.0007082246040000014,
        ),
        "spiral-doubling-time-md": (-44.74590542250437, -32.556467217800574, -41.81392549996266),
        "dihedral-effect-app": (-0.110284, -0.110542, -0.110334),
        "weathercock-stability-app": (0.066748, 0.063434, 0.066104),
        "spiral-criterion-app": (
            -0.0010965856560000015,
            -0.0007225521939999997,
            -0.001023888165999999,
        ),
        "spiral-doubling-time-app": (22.696109236857147, 33.12387091156692, 24.12641049243606),
        "dihedral-effect-mp": (-0.138192, -0.138731, -0.138297),
        "roll-due-to-yaw-rate-mp": (0.283478, 0.280703, 0.282941),
        "weathercock-stability-mp": (0.071725, 0.068475, 0.071093),
        "spiral-criterion-mp": (-0.003860249534, -0.0032944029319999964, -0.0037500256120000033),
        "spiral-doubling-time-mp": (6.320951688313078, 7.173200178457541, 6.466868384288015),
    },
    # AVL's lateral run gives no derivatives: recorded as the kernel answers it, bug #1373
    FleetMember.MINI_FUNTANA: {
        "stall-speed": 6.851323641723553,
        "max-lift-coefficient": 0.876770973456084,
        "minimum-drag-speed": 10.691969869913397,
        "max-lift-to-drag-ratio": 11.623539431736907,
        "minimum-sink-speed": 8.698673476187055,
        "neutral-point": (0.2537205182389136, 0.2536662142967273, 0.263728),
        "centre-of-gravity-design": (0.230905646574542, 0.23085134263235568, 0.2409131283356284),
        "roll-rate-approach": {"roll-rate=aerobuildup": 569.8456283312153},
        "horizontal-tail-volume": (0.4278343824233866, 0.4278798041199412, 0.41946377834702775),
        "turn-sideslip": NOT_APPLICABLE,
        "turn-sideslip-gain": NOT_APPLICABLE,
        "rudder-roll-authority-md": NOT_APPLICABLE,
        "rudder-roll-authority-mp": NOT_APPLICABLE,
        "vertical-tail-volume": (0.0587571745599855, 0.05876303165069862, 0.057677791993548416),
        "spiral-parameter-md": (0.0, 0.0, 0.0),
        "spiral-parameter-mp": (0.0, 0.0, 0.0),
        "dihedral-effect-md": Failed("internal"),
        "weathercock-stability-md": Failed("internal"),
        "spiral-criterion-md": Failed("internal"),
        "spiral-doubling-time-md": Failed("internal"),
        "dihedral-effect-app": Failed("internal"),
        "weathercock-stability-app": Failed("internal"),
        "spiral-criterion-app": Failed("internal"),
        "spiral-doubling-time-app": Failed("internal"),
        "dihedral-effect-mp": Failed("internal"),
        "roll-due-to-yaw-rate-mp": Failed("internal"),
        "weathercock-stability-mp": Failed("internal"),
        "spiral-criterion-mp": Failed("internal"),
        "spiral-doubling-time-mp": Failed("internal"),
    },
    FleetMember.P36_HAWK: {
        "stall-speed": 6.764139338031463,
        "max-lift-coefficient": 1.3215257702325125,
        "minimum-drag-speed": 9.830725209958148,
        "max-lift-to-drag-ratio": 10.231859699516258,
        "minimum-sink-speed": 7.69584837704675,
        "neutral-point": (0.1278891346585562, 0.1335959282659489, 0.12963),
        "centre-of-gravity-design": (0.11455555667852042, 0.12026235028591313, 0.11629642201996422),
        "roll-rate-approach": {"roll-rate=aerobuildup": 247.17676107153682},
        "horizontal-tail-volume": (0.4028603545084523, 0.39529812252346014, 0.40055348510466365),
        "turn-sideslip": NOT_APPLICABLE,
        "turn-sideslip-gain": NOT_APPLICABLE,
        "rudder-roll-authority-md": NOT_APPLICABLE,
        "rudder-roll-authority-mp": NOT_APPLICABLE,
        "vertical-tail-volume": (0.03817509308150271, 0.037485135874813474, 0.0379646206742566),
        "spiral-parameter-md": (2.0224059747330414, 1.9858540382612864, 2.011255755583026),
        "spiral-parameter-mp": (1.239396402968796, 1.216996183057155, 1.2325631846736085),
        "dihedral-effect-md": (-0.039801, -0.039835, -0.039812),
        "weathercock-stability-md": (0.038046, 0.035967, 0.037412),
        "spiral-criterion-md": (-0.00271947072, -0.0024406655249999995, -0.002634407048),
        "spiral-doubling-time-md": (4.709588547216386, 4.986472804930732, 4.787899231542698),
        "dihedral-effect-app": (-0.050389, -0.050482, -0.050417),
        "weathercock-stability-app": (0.039011, 0.036935, 0.038377),
        "spiral-criterion-app": (-0.0030487890660000003, -0.0027175744439999995, -0.00294761852),
        "spiral-doubling-time-app": (4.018404423682317, 4.299119450933909, 4.097467681192911),
        "dihedral-effect-mp": (-0.066612, -0.066795, -0.066668),
        "roll-due-to-yaw-rate-mp": (0.220562, 0.219644, 0.220282),
        "weathercock-stability-mp": (0.041684, 0.03962, 0.041054),
        "spiral-criterion-mp": (-0.003757168192, -0.003347006155000002, -0.0036319490000000006),
        "spiral-doubling-time-mp": (3.2705329945682595, 3.52377845476269, 3.341790247505626),
    },
    FleetMember.P39: {
        "stall-speed": 10.744129359778434,
        "max-lift-coefficient": 1.3092053546930804,
        "minimum-drag-speed": 19.10612027984956,
        "max-lift-to-drag-ratio": 15.32728431151209,
        "minimum-sink-speed": 13.563358500119465,
        "neutral-point": (0.8217208481002621, 0.8394672325170343, 0.833715),
        "centre-of-gravity-design": (0.7757717103184598, 0.7935180947352319, 0.7877658622181977),
        "roll-rate-approach": Failed("upstream_failed", (("airplane-landing", "missing_input"),)),
        "horizontal-tail-volume": (0.46021469183662295, 0.45216936053209594, 0.45477713771382283),
        "turn-sideslip": NOT_APPLICABLE,
        "turn-sideslip-gain": NOT_APPLICABLE,
        "rudder-roll-authority-md": NOT_APPLICABLE,
        "rudder-roll-authority-mp": NOT_APPLICABLE,
        "vertical-tail-volume": (0.03956285778382288, 0.038908502447652746, 0.03912060221704889),
        "spiral-parameter-md": (7.2554415783784965, 7.135439202942818, 7.174336228381424),
        "spiral-parameter-mp": (3.6563967688921286, 3.595921290857826, 3.615523537888119),
        "dihedral-effect-md": (-0.086479, -0.086513, -0.086502),
        "weathercock-stability-md": (0.038102, 0.036307, 0.036889),
        "spiral-criterion-md": (0.0043323837370000005, 0.004433161756000002, 0.004400442576),
        "spiral-doubling-time-md": (-5.596312846916985, -5.263048640913244, -5.369499095752046),
        "dihedral-effect-app": Failed("upstream_failed", (("airplane-landing", "missing_input"),)),
        "weathercock-stability-app": Failed(
            "upstream_failed", (("airplane-landing", "missing_input"),)
        ),
        "spiral-criterion-app": Failed("upstream_failed", (("airplane-landing", "missing_input"),)),
        "spiral-doubling-time-app": Failed(
            "upstream_failed", (("airplane-landing", "missing_input"),)
        ),
        "dihedral-effect-mp": (-0.117776, -0.117952, -0.117895),
        "roll-due-to-yaw-rate-mp": (0.176519, 0.174849, 0.175391),
        "weathercock-stability-mp": (0.040336, 0.038561, 0.039137),
        "spiral-criterion-mp": (0.004865168704000001, 0.005056032415000001, 0.004994073113000002),
        "spiral-doubling-time-mp": (-4.481004391715403, -4.182579447171285, -4.2769399828164545),
    },
    FleetMember.SNOOPY: {
        "stall-speed": 5.548502615869733,
        "max-lift-coefficient": 1.283481289912637,
        "minimum-drag-speed": 7.557084154315299,
        "max-lift-to-drag-ratio": 19.445833668433202,
        "minimum-sink-speed": 6.469668761096849,
        "neutral-point": (0.4225483986455356, 0.45084094155486115, 0.438166),
        "centre-of-gravity-design": (0.4034921608883401, 0.43178470379766565, 0.4191097622428045),
        "roll-rate-approach": NOT_APPLICABLE,
        "horizontal-tail-volume": (0.6953283143851352, 0.6712311988825295, 0.6820266064079377),
        "turn-sideslip": (18.56286986281394, 18.37454266379648, 18.458779757349863),
        "turn-sideslip-gain": (1.727296612829065, 1.7097725481035941, 1.7176109075514943),
        "rudder-roll-authority-md": (0.03567979189416162, 0.03327522761954342, 0.03434209130211978),
        "rudder-roll-authority-mp": (
            0.026150372978696462,
            0.024388023780611483,
            0.02516994771389997,
        ),
        "vertical-tail-volume": (0.01596401228346573, 0.01541669975372445, 0.015661893490779007),
        "spiral-parameter-md": (2.2350140591608008, 2.1583885105827925, 2.1927164376605424),
        "spiral-parameter-mp": (1.638082739749641, 1.5819224717481892, 1.6070820382426212),
        "dihedral-effect-md": (-0.130439, -0.130353, -0.130392),
        "weathercock-stability-md": (0.018539, 0.016832, 0.017597),
        "spiral-criterion-md": (
            -0.0002496296659999994,
            -9.78111919999994e-05,
            -0.00016582399299999977,
        ),
        "spiral-doubling-time-md": (46.80594949105642, 113.95223013091322, 68.66994633401812),
        "dihedral-effect-app": (-0.132173, -0.132105, -0.132136),
        "weathercock-stability-app": (0.017573, 0.015866, 0.016631),
        "spiral-criterion-app": (-0.0002235926369999995, -5.352610700000036e-05, -0.000129787903),
        "spiral-doubling-time-app": (50.24774429838122, 200.30385099846814, 84.3813439589615),
        "dihedral-effect-mp": (-0.137017, -0.136996, -0.137006),
        "roll-due-to-yaw-rate-mp": (0.236669, 0.234232, 0.235323),
        "weathercock-stability-mp": (0.015112, 0.013407, 0.014171),
        "spiral-criterion-mp": (
            3.986315999999698e-06,
            0.00022345136000000024,
            0.00012505028499999954,
        ),
        "spiral-doubling-time-mp": (-2607.0673672687585, -44.45557571558753, -81.08227531913921),
    },
    FleetMember.SONAS_40: {
        "stall-speed": 8.906442661471099,
        "max-lift-coefficient": 1.1652994397451586,
        "minimum-drag-speed": 12.958124084182552,
        "max-lift-to-drag-ratio": 13.142882152343914,
        "minimum-sink-speed": 11.717711470345185,
        "neutral-point": (0.37326483386892706, 0.38514532950110025, 0.376339),
        "centre-of-gravity-design": (0.34732646810732837, 0.35920696373950156, 0.3504006342384013),
        "roll-rate-approach": {"roll-rate=aerobuildup": 223.96291633478552},
        "horizontal-tail-volume": (0.5221401445723637, 0.5133096507281724, 0.5198551889663916),
        "turn-sideslip": NOT_APPLICABLE,
        "turn-sideslip-gain": NOT_APPLICABLE,
        "rudder-roll-authority-md": NOT_APPLICABLE,
        "rudder-roll-authority-mp": NOT_APPLICABLE,
        "vertical-tail-volume": (0.05347695358066641, 0.05254584864744729, 0.05323602329132515),
        "spiral-parameter-md": (1.1770245433981845, 1.15653097961982, 1.171721682168909),
        "spiral-parameter-mp": (0.9624692214414837, 0.9457113513656588, 0.9581329985926229),
        "dihedral-effect-md": (-0.063208, -0.063386, -0.063254),
        "weathercock-stability-md": (0.082989, 0.081121, 0.082506),
        "spiral-criterion-md": (
            -0.002521657850999999,
            -0.0023955863870000005,
            -0.0024890404439999987,
        ),
        "spiral-doubling-time-md": (14.473815294717634, 14.898257546197089, 14.57953185539588),
        "dihedral-effect-app": (-0.07629, -0.076518, -0.076349),
        "weathercock-stability-app": (0.085935, 0.084085, 0.085456),
        "spiral-criterion-app": (
            -0.0036665703899999985,
            -0.0035049137409999993,
            -0.003624728645999999,
        ),
        "spiral-doubling-time-app": (9.47748773329821, 9.703614775504418, 9.534049027791989),
        "dihedral-effect-mp": (-0.074759, -0.074981, -0.074816),
        "roll-due-to-yaw-rate-mp": (0.137968, 0.136893, 0.137691),
        "weathercock-stability-mp": (0.08555, 0.083698, 0.085071),
        "spiral-criterion-mp": (-0.003520837067, -0.003363546344999996, -0.003480234709),
        "spiral-doubling-time-mp": (9.909658985124464, 10.151266322664487, 9.969816227652593),
    },
    FleetMember.SPIRIT_100: {
        "stall-speed": 4.890025401038546,
        "max-lift-coefficient": 1.3722670566981743,
        "minimum-drag-speed": 7.655121194331461,
        "max-lift-to-drag-ratio": 19.94119588564243,
        "minimum-sink-speed": 6.056373887548118,
        "neutral-point": (0.4737961308511267, 0.4953150187510106, 0.493284),
        "centre-of-gravity-design": (0.4492896996778477, 0.4708085875777316, 0.468777568826721),
        "roll-rate-approach": Failed("upstream_failed", (("airplane-landing", "missing_input"),)),
        "horizontal-tail-volume": (0.4656077380373866, 0.4523128538459529, 0.4535676658609112),
        "turn-sideslip": NOT_APPLICABLE,
        "turn-sideslip-gain": NOT_APPLICABLE,
        "rudder-roll-authority-md": NOT_APPLICABLE,
        "rudder-roll-authority-mp": NOT_APPLICABLE,
        "vertical-tail-volume": (0.017760832298518565, 0.0172248225201557, 0.017275412769784067),
        "spiral-parameter-md": (3.8861588666251574, 3.7688772484120077, 3.7799466478553243),
        "spiral-parameter-mp": (2.4324379232829867, 2.3590286094498114, 2.3659572060198415),
        "dihedral-effect-md": (-0.17065, -0.170677, -0.170674),
        "weathercock-stability-md": (0.019926, 0.018453, 0.018592),
        "spiral-criterion-md": (0.0013107346279999997, 0.001357425482, 0.0013531077419999993),
        "spiral-doubling-time-md": (-8.299779997241108, -7.754848023186222, -7.804142004505676),
        "dihedral-effect-app": Failed("upstream_failed", (("airplane-landing", "missing_input"),)),
        "weathercock-stability-app": Failed(
            "upstream_failed", (("airplane-landing", "missing_input"),)
        ),
        "spiral-criterion-app": Failed("upstream_failed", (("airplane-landing", "missing_input"),)),
        "spiral-doubling-time-app": Failed(
            "upstream_failed", (("airplane-landing", "missing_input"),)
        ),
        "dihedral-effect-mp": (-0.193397, -0.193506, -0.193496),
        "roll-due-to-yaw-rate-mp": (0.234311, 0.231156, 0.231454),
        "weathercock-stability-mp": (0.018233, 0.016801, 0.016936),
        "spiral-criterion-mp": (0.001718086215000001, 0.0018112296240000007, 0.001802352264),
        "spiral-doubling-time-mp": (-6.261366004792846, -5.778125825277631, -5.821863672306091),
    },
    FleetMember.SPRITE: {
        "stall-speed": 8.905219013863126,
        "max-lift-coefficient": 1.0637115442374978,
        "minimum-drag-speed": 13.814605398407654,
        "max-lift-to-drag-ratio": 14.501883402147183,
        "minimum-sink-speed": 10.724574615169617,
        "neutral-point": (0.2641482570045175, 0.26809136033731945, 0.265268),
        "centre-of-gravity-design": (0.2448208660631007, 0.24876396939590265, 0.2459406090585832),
        "roll-rate-approach": {"roll-rate=aerobuildup": 389.93808907966087},
        "horizontal-tail-volume": (0.32622685506123644, 0.32265149795782977, 0.3252115428223753),
        "turn-sideslip": NOT_APPLICABLE,
        "turn-sideslip-gain": NOT_APPLICABLE,
        "rudder-roll-authority-md": NOT_APPLICABLE,
        "rudder-roll-authority-mp": NOT_APPLICABLE,
        "vertical-tail-volume": (0.029640556750800216, 0.02935345260729525, 0.029559026335152894),
        "spiral-parameter-md": (0.014275007405838126, 0.01413673693375364, 0.014235742040583638),
        "spiral-parameter-mp": (0.008603190193102, 0.00851985803532348, 0.008579525938809016),
        "dihedral-effect-md": (-0.044794, -0.044819, -0.044801),
        "weathercock-stability-md": (0.058965, 0.058238, 0.058759),
        "spiral-criterion-md": (
            -0.003487187190999999,
            -0.0034292420880000004,
            -0.0034707370849999994,
        ),
        "spiral-doubling-time-md": (7.270912480067985, 7.302593382124019, 7.27983789071139),
        "dihedral-effect-app": (-0.064477, -0.064528, -0.064492),
        "weathercock-stability-app": (0.061291, 0.060575, 0.061088),
        "spiral-criterion-app": (
            -0.004575862725999998,
            -0.004499492204999998,
            -0.004554188692000001,
        ),
        "spiral-doubling-time-app": (5.054565793418105, 5.079928081407567, 5.061700084949214),
        "dihedral-effect-mp": (-0.075384, -0.075448, -0.075402),
        "roll-due-to-yaw-rate-mp": (0.167434, 0.166876, 0.167275),
        "weathercock-stability-mp": (0.063211, 0.062503, 0.06301),
        "spiral-criterion-mp": (-0.005301965998, -0.005214907627999999, -0.005277239758000001),
        "spiral-doubling-time-mp": (4.290027766203655, 4.312094923302701, 4.296218866798318),
    },
    FleetMember.SUPER_TRIDENT: {
        "stall-speed": 6.0843250484296245,
        "max-lift-coefficient": 1.0769457250640162,
        "minimum-drag-speed": 7.440306961004602,
        "max-lift-to-drag-ratio": 16.769462847003364,
        "minimum-sink-speed": 6.7431548042373795,
        "neutral-point": (0.37249216648298167, 0.40097934077937253, 0.394857),
        "centre-of-gravity-design": (0.3557280275213087, 0.3842152018176996, 0.37809286103832707),
        "roll-rate-approach": NOT_APPLICABLE,
        "horizontal-tail-volume": (0.8512957512318106, 0.8116705003589153, 0.8201865885741908),
        "turn-sideslip": (8.591229767974621, 8.414922201841689, 8.452809355077585),
        "turn-sideslip-gain": (1.0977907625644223, 1.0752621115216534, 1.080103347056672),
        "rudder-roll-authority-md": (
            0.03963934717983071,
            0.03573403837606309,
            0.036556268511937016,
        ),
        "rudder-roll-authority-mp": (
            0.03255899917302405,
            0.029351253456743158,
            0.030026617513383723,
        ),
        "vertical-tail-volume": (0.013026485254353834, 0.012368158871192534, 0.012509643541445556),
        "spiral-parameter-md": (3.042981004149379, 2.889196261805265, 2.922247016137819),
        "spiral-parameter-mp": (2.499446208035424, 2.373130371498302, 2.4002776269286077),
        "dihedral-effect-md": (-0.20712, -0.207091, -0.207097),
        "weathercock-stability-md": (0.000609, -0.001782, -0.001268),
        "spiral-criterion-md": (0.0033038992769999997, 0.00343856052, 0.0034094853410000002),
        "spiral-doubling-time-md": (-2.345396437323966, -2.0958217307687925, -2.1479038046699883),
        "dihedral-effect-app": (-0.203934, -0.203875, -0.203887),
        "weathercock-stability-app": (0.002003, -0.000393, 0.000122),
        "spiral-criterion-app": (0.0028365590710000004, 0.002951718621, 0.002927018427),
        "spiral-doubling-time-app": (-2.8129897631752336, -2.507840883535837, -2.5713662175563274),
        "dihedral-effect-mp": (-0.213241, -0.213268, -0.213262),
        "roll-due-to-yaw-rate-mp": (0.234094, 0.229319, 0.230345),
        "weathercock-stability-mp": (-0.001809, -0.004186, -0.003675),
        "spiral-criterion-mp": (0.004356493049999999, 0.004525983562, 0.004489672621000001),
        "spiral-doubling-time-mp": (-1.7384913389914587, -1.5650943433000453, -1.6012223240782708),
    },
    FleetMember.ULTRA_MINI_STICK: {
        "stall-speed": 5.745696698625537,
        "max-lift-coefficient": 1.128645933661611,
        "minimum-drag-speed": 8.754454902828886,
        "max-lift-to-drag-ratio": 10.65731613566995,
        "minimum-sink-speed": 7.513860168166943,
        "neutral-point": (0.16062716617452535, 0.16328408629716154, 0.172644),
        "centre-of-gravity-design": (0.1420350726028904, 0.14469199272552657, 0.15405190642836503),
        "roll-rate-approach": {"roll-rate=aerobuildup": 286.0757286478424},
        "horizontal-tail-volume": (0.4811607935457315, 0.4778312256448729, 0.4661016791092939),
        "turn-sideslip": NOT_APPLICABLE,
        "turn-sideslip-gain": NOT_APPLICABLE,
        "rudder-roll-authority-md": NOT_APPLICABLE,
        "rudder-roll-authority-mp": NOT_APPLICABLE,
        "vertical-tail-volume": (0.03730341479532069, 0.03704882359133097, 0.03615193863098029),
        "spiral-parameter-md": (0.0, 0.0, 0.0),
        "spiral-parameter-mp": (0.0, 0.0, 0.0),
        "dihedral-effect-md": (-0.088102, -0.088143, -0.088289),
        "weathercock-stability-md": (0.046346, 0.045948, 0.044546),
        "spiral-criterion-md": (
            -0.00019575040599999986,
            -0.00017147343299999968,
            -8.613443599999986e-05,
        ),
        "spiral-doubling-time-md": (66.6787820831519, 75.36586640296348, 144.7543995198698),
        "dihedral-effect-app": (-0.115621, -0.11568, -0.115884),
        "weathercock-stability-app": (0.055201, 0.054799, 0.053386),
        "spiral-criterion-app": (
            -0.001267327464999999,
            -0.0012265544060000005,
            -0.0010835615740000006,
        ),
        "spiral-doubling-time-app": (11.335597737937311, 11.6017807859594, 12.692220023877438),
        "dihedral-effect-mp": (-0.114435, -0.114493, -0.114695),
        "roll-due-to-yaw-rate-mp": (0.15051, 0.149814, 0.147355),
        "weathercock-stability-mp": (0.054768, 0.054367, 0.052954),
        "spiral-criterion-mp": (
            -0.0012058369199999999,
            -0.001166016922999999,
            -0.0010259385100000002,
        ),
        "spiral-doubling-time-mp": (11.852089605210747, 12.141009523793288, 13.334853471941752),
    },
    FleetMember.VOODOO: {
        "stall-speed": 5.426031949602609,
        "max-lift-coefficient": 1.1663474930260136,
        "minimum-drag-speed": 9.636279208498136,
        "max-lift-to-drag-ratio": 18.0069237238447,
        "minimum-sink-speed": 6.932242140699631,
        "neutral-point": Failed("unsupported_layout"),
        "centre-of-gravity-design": Failed(
            "upstream_failed", (("neutral-point", "unsupported_layout"),)
        ),
        "roll-rate-approach": NOT_APPLICABLE,
        "horizontal-tail-volume": NOT_APPLICABLE,
        "turn-sideslip": Failed("upstream_failed", (("neutral-point", "unsupported_layout"),)),
        "turn-sideslip-gain": Failed("upstream_failed", (("neutral-point", "unsupported_layout"),)),
        "rudder-roll-authority-md": NOT_APPLICABLE,
        "rudder-roll-authority-mp": NOT_APPLICABLE,
        "vertical-tail-volume": NOT_APPLICABLE,
        "spiral-parameter-md": NOT_APPLICABLE,
        "spiral-parameter-mp": NOT_APPLICABLE,
        "dihedral-effect-md": Failed("upstream_failed", (("neutral-point", "unsupported_layout"),)),
        "weathercock-stability-md": Failed(
            "upstream_failed", (("neutral-point", "unsupported_layout"),)
        ),
        "spiral-criterion-md": Failed(
            "upstream_failed", (("neutral-point", "unsupported_layout"),)
        ),
        "spiral-doubling-time-md": Failed(
            "upstream_failed", (("neutral-point", "unsupported_layout"),)
        ),
        "dihedral-effect-app": Failed(
            "upstream_failed", (("neutral-point", "unsupported_layout"),)
        ),
        "weathercock-stability-app": Failed(
            "upstream_failed", (("neutral-point", "unsupported_layout"),)
        ),
        "spiral-criterion-app": Failed(
            "upstream_failed", (("neutral-point", "unsupported_layout"),)
        ),
        "spiral-doubling-time-app": Failed(
            "upstream_failed", (("neutral-point", "unsupported_layout"),)
        ),
        "dihedral-effect-mp": Failed("upstream_failed", (("neutral-point", "unsupported_layout"),)),
        "roll-due-to-yaw-rate-mp": Failed(
            "upstream_failed", (("neutral-point", "unsupported_layout"),)
        ),
        "weathercock-stability-mp": Failed(
            "upstream_failed", (("neutral-point", "unsupported_layout"),)
        ),
        "spiral-criterion-mp": Failed(
            "upstream_failed", (("neutral-point", "unsupported_layout"),)
        ),
        "spiral-doubling-time-mp": Failed(
            "upstream_failed", (("neutral-point", "unsupported_layout"),)
        ),
    },
    FleetMember.WINDFREAK: {
        "stall-speed": 7.301711605466716,
        "max-lift-coefficient": 0.8605660827418935,
        "minimum-drag-speed": 10.70300036194253,
        "max-lift-to-drag-ratio": 20.091103979236742,
        "minimum-sink-speed": 9.325518655580813,
        "neutral-point": Failed("unsupported_layout"),
        "centre-of-gravity-design": Failed(
            "upstream_failed", (("neutral-point", "unsupported_layout"),)
        ),
        "roll-rate-approach": NOT_APPLICABLE,
        "horizontal-tail-volume": NOT_APPLICABLE,
        "turn-sideslip": Failed("upstream_failed", (("neutral-point", "unsupported_layout"),)),
        "turn-sideslip-gain": Failed("upstream_failed", (("neutral-point", "unsupported_layout"),)),
        "rudder-roll-authority-md": Failed(
            "upstream_failed", (("neutral-point", "unsupported_layout"),)
        ),
        "rudder-roll-authority-mp": Failed(
            "upstream_failed", (("neutral-point", "unsupported_layout"),)
        ),
        "vertical-tail-volume": Failed(
            "upstream_failed", (("neutral-point", "unsupported_layout"),)
        ),
        "spiral-parameter-md": Failed(
            "upstream_failed", (("neutral-point", "unsupported_layout"),)
        ),
        "spiral-parameter-mp": Failed(
            "upstream_failed", (("neutral-point", "unsupported_layout"),)
        ),
        "dihedral-effect-md": Failed("upstream_failed", (("neutral-point", "unsupported_layout"),)),
        "weathercock-stability-md": Failed(
            "upstream_failed", (("neutral-point", "unsupported_layout"),)
        ),
        "spiral-criterion-md": Failed(
            "upstream_failed", (("neutral-point", "unsupported_layout"),)
        ),
        "spiral-doubling-time-md": Failed(
            "upstream_failed", (("neutral-point", "unsupported_layout"),)
        ),
        "dihedral-effect-app": Failed(
            "upstream_failed", (("neutral-point", "unsupported_layout"),)
        ),
        "weathercock-stability-app": Failed(
            "upstream_failed", (("neutral-point", "unsupported_layout"),)
        ),
        "spiral-criterion-app": Failed(
            "upstream_failed", (("neutral-point", "unsupported_layout"),)
        ),
        "spiral-doubling-time-app": Failed(
            "upstream_failed", (("neutral-point", "unsupported_layout"),)
        ),
        "dihedral-effect-mp": Failed("upstream_failed", (("neutral-point", "unsupported_layout"),)),
        "roll-due-to-yaw-rate-mp": Failed(
            "upstream_failed", (("neutral-point", "unsupported_layout"),)
        ),
        "weathercock-stability-mp": Failed(
            "upstream_failed", (("neutral-point", "unsupported_layout"),)
        ),
        "spiral-criterion-mp": Failed(
            "upstream_failed", (("neutral-point", "unsupported_layout"),)
        ),
        "spiral-doubling-time-mp": Failed(
            "upstream_failed", (("neutral-point", "unsupported_layout"),)
        ),
    },
    FleetMember.WRISTOCRAT: {
        "stall-speed": 5.127034527483944,
        "max-lift-coefficient": 0.973267748566667,
        "minimum-drag-speed": 6.631941748504025,
        "max-lift-to-drag-ratio": 16.00120553018703,
        "minimum-sink-speed": 5.790569859985646,
        "neutral-point": (0.23785454793893585, 0.24872662015474406, 0.24841),
        "centre-of-gravity-design": (0.22309964752227657, 0.23397171973808478, 0.23365509958334071),
        "roll-rate-approach": NOT_APPLICABLE,
        "horizontal-tail-volume": (0.39752390334014776, 0.38798345167250614, 0.3882612919244266),
        "turn-sideslip": (5.14923614167325, 5.058256952285788, 5.060905198840768),
        "turn-sideslip-gain": (0.8444147498184852, 0.8294952224688736, 0.8299295040575705),
        "rudder-roll-authority-md": (0.13953478806931563, 0.13320319053600083, 0.1333855031935305),
        "rudder-roll-authority-mp": (0.10637601137980994, 0.1015490424169038, 0.10168803064772712),
        "vertical-tail-volume": (0.020132539950847867, 0.01967046536957725, 0.019683922061413096),
        "spiral-parameter-md": (6.930808949590051, 6.771735596149934, 6.776368184011945),
        "spiral-parameter-mp": (5.28378493918399, 5.162513469252317, 5.166045177910393),
        "dihedral-effect-md": (-0.246036, -0.246065, -0.246064),
        "weathercock-stability-md": (0.023812, 0.021815, 0.021873),
        "spiral-criterion-md": (0.005435053380000001, 0.005416902265000001, 0.005417495531),
        "spiral-doubling-time-md": (-2.2337882487942515, -2.186305612938788, -2.1876632508392237),
        "dihedral-effect-app": (-0.245628, -0.245655, -0.245654),
        "weathercock-stability-app": (0.023898, 0.0219, 0.021958),
        "spiral-criterion-app": (0.005414017722000002, 0.005395527675, 0.005395942946000001),
        "spiral-doubling-time-app": (-2.247322398980169, -2.199603097963278, -2.201024859222071),
        "dihedral-effect-mp": (-0.258932, -0.259025, -0.259022),
        "roll-due-to-yaw-rate-mp": (0.218646, 0.21486, 0.21497),
        "weathercock-stability-mp": (0.021548, 0.019577, 0.019634),
        "spiral-criterion-mp": (0.006234966291999999, 0.006234206455, 0.006234443027999998),
        "spiral-doubling-time-mp": (-1.8818103228471703, -1.8388365535069366, -1.8400046291518222),
    },
}


def close(actual: float | None, expected: float) -> bool:
    return actual is not None and abs(actual - expected) <= REL * abs(expected)


def check(quantity: QuantityResult, golden: Golden) -> None:
    slug = quantity.slug
    if isinstance(golden, Failed):
        assert quantity.status is QuantityStatus.ERROR, (slug, quantity.status)
        assert quantity.error is not None, slug
        assert quantity.error.code == golden.code, (slug, quantity.error)
        causes = cast("list[dict[str, Any]]", quantity.error.detail.get("causes", []))
        assert tuple((c["quantity"], c["code"]) for c in causes) == golden.causes, slug
        return
    if golden == NOT_APPLICABLE:
        assert quantity.status is QuantityStatus.NOT_APPLICABLE, (slug, quantity.status)
        assert quantity.interval is None, slug
        return
    assert quantity.status is QuantityStatus.OK, (slug, quantity.error)
    if isinstance(golden, float):
        assert close(quantity.value, golden), (slug, quantity.value, golden)
        return
    assert quantity.interval is not None, slug
    worlds = quantity.interval.worlds
    if isinstance(golden, dict):
        expected = golden
    else:
        assert isinstance(golden, tuple), slug
        expected = {f"neutral-point={w}": v for w, v in zip(WORLDS, golden, strict=True)}
    assert set(worlds) == set(expected), slug
    for name, value in expected.items():
        assert close(worlds[name], value), (slug, name, worlds[name], value)


async def run(member: FleetMember) -> ComputeResult:
    values = {
        "altitude": 0.0,
        "static-margin-target": SM_TARGET,
        "aileron-deflection": AILERON_DEFLECTION_DEG,
    }
    return await compute(aircraft_input(member, values), request(*SLUGS))


def test_every_member_of_the_batch_has_its_golden() -> None:
    assert set(GOLDEN) == set(PLAN_BATCH)
    assert all(tuple(golden) == SLUGS for golden in GOLDEN.values())


@pytest.mark.parametrize("member", PLAN_BATCH, ids=lambda m: m.name)
@pytest.mark.asyncio
async def test_the_chain_of_the_plan_batch_is_the_regression_golden(member: FleetMember) -> None:
    by_slug = {q.slug: q for q in (await run(member)).quantities}
    for slug, golden in GOLDEN[member].items():
        check(by_slug[slug], golden)

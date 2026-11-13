"""The MVP chain on the reference fleet through the public compute(), real AVL and real AeroSandbox.

Aero tier. The goldens are **regression, not validation** (aero_kernel/CLAUDE.md): they pin what this
build computes, written by running the kernel at SM_target = 0.10 and the fleet masses of the README.
Per quantity the three values are the neutral-point worlds textbook / Pappas / AVL. Re-recorded for #1346:
the kernel's drag (AeroBuildup's viscous factor k_e,D0 removed) moves V_md and V_mp, at which the lateral
derivatives and the spiral parameter are evaluated, and the AVL world's neutral point. The aircraft the
kernel cannot compute record the error it gives: RV-7's flaps need a landing deflection for the
approach speed of ``lateral-static-stability-app``. CHEKKER and WIESEL compute since #1307
(asymmetric fuselage sections), BELEMNITOS since #1208 (V-tail neutral point).
"""

import math
from typing import cast

import pytest
from aero_kernel import compute
from aero_kernel.evaluation import RuleStatus, evaluate_rules, shipped_rule_table
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.graph import facts_from_geometry
from aero_kernel.schema import AircraftInput, ComputeResult, QuantityStatus
from aero_kernel.tests.engine_builders import request
from aero_kernel.tests.reference_fleet import FleetMember, flap_values, reference_document

pytestmark = [pytest.mark.aero]

SM_TARGET = 0.10
STANDARD_GRAVITY = 9.80665  # the kernel's default gravity (a canon input, so not echoed as a value)
WORLDS = ("textbook", "pappas", "avl")
REL = 2e-3  # the regression tolerance
SLUGS = (
    "horizontal-tail-volume",
    "turn-sideslip",
    "turn-sideslip-gain",
    "rudder-roll-authority-md",
    "rudder-roll-authority-mp",
    "vertical-tail-volume",
    "spiral-parameter-md",
    "spiral-parameter-mp",
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
    # #1355 slice 2: BRYAN's canopy merged into the fuselage moves V_md, V_mp and the AVL body;
    # the values before are those of #1346 (git history of this file).
    FleetMember.BRYAN: {
        "vertical-tail-volume": (
            0.055889564925848935,
            0.05583702833957879,
            0.055117972548860625,
        ),  # #1358: was (0.055889564925848935, 0.05583702833957879, 0.05512381302882941)
        "spiral-parameter-md": (
            1.8375299198920345,
            1.8358026287726912,
            1.812161605063359,
        ),  # #1358: was (1.8153973103358465, 1.8136908240260032, 1.7905242604905278)
        "spiral-parameter-mp": (
            1.287376107326161,
            1.2861659646812074,
            1.269603029435008,
        ),  # #1358: was (1.2706540457318949, 1.2694596219430951, 1.2532446107637456)
        "dihedral-effect-md": (
            -0.047848,
            -0.047852,
            -0.047904,
        ),  # #1358: was (-0.048605, -0.048609, -0.048663)
        "weathercock-stability-md": (
            0.065055,
            0.064938,
            0.063339,
        ),  # #1358: was (0.065118, 0.065001, 0.063415)
        "spiral-criterion-md": (  # #1358: was (-0.0026123705619999996, -0.0026000706179999996, -0.0024324532389999997)
            -0.0026248712689999993,
            -0.002612605379999999,
            -0.0024450336720000026,
        ),
        "spiral-doubling-time-md": (
            5.222243606023033,
            5.237558363019721,
            5.462144818364262,
        ),  # #1358: was (5.229827362476103, 5.245372880306831, 5.473475700059018)
        "dihedral-effect-app": (
            -0.064498,
            -0.064505,
            -0.064609,
        ),  # #1358: was (-0.064632, -0.06464, -0.064743)
        "weathercock-stability-app": (
            0.066953,
            0.066837,
            0.065256,
        ),  # #1358: was (0.066973, 0.066857, 0.065289)
        "spiral-criterion-app": (
            -0.0024226886419999993,
            -0.0024082258199999984,
            -0.0022114622520000016,
        ),  # #1358: was (-0.0024218580859999995, -0.002407320789, -0.0022119411719999996)
        "spiral-doubling-time-app": (
            5.399408928067232,
            5.422728666041908,
            5.770107916442872,
        ),  # #1358: was (5.400309753056281, 5.423828452605851, 5.768996776931942)
        "dihedral-effect-mp": (
            -0.07444,
            -0.07445,
            -0.074584,
        ),  # #1358: was (-0.075611, -0.075621, -0.075758)
        "weathercock-stability-mp": (
            0.068619,
            0.068504,
            0.066935,
        ),  # #1358: was (0.068842, 0.068727, 0.067172)
        "spiral-criterion-mp": (
            -0.002395387889999998,
            -0.002379578904,
            -0.0021648752239999992,
        ),  # #1358: was (-0.002397831730000001, -0.0023818921020000005, -0.002166706858)
        "spiral-doubling-time-mp": (
            5.4290555845809445,
            5.456280457004085,
            5.864845830110837,
        ),  # #1358: was (5.424605747906527, 5.45210492011868, 5.862701314743131)
        "roll-due-to-yaw-rate-mp": (
            0.18015,
            0.180076,
            0.179064,
        ),  # #1358: was (0.182077, 0.182002, 0.180983)
        "horizontal-tail-volume": (
            0.47784453880864197,
            0.47736734162563543,
            0.47083605700826675,
        ),  # #1358: was (0.47784453880864197, 0.47736734162563543, 0.4708891069071349)
    },
    FleetMember.JAGUAR: {
        "vertical-tail-volume": (
            0.02241860994257862,
            0.021857472431766837,
            0.02161084476647386,
        ),  # #1358: was (0.02241860994257862, 0.021857472431766837, 0.021604275469436614)
        "spiral-parameter-md": (  # #1358: was (0.0007009632400524788, 0.0006834181394105982, 0.0006755014236311173)
            0.0007168347572718028,
            0.0006988923927635152,
            0.0006910064764181386,
        ),
        "spiral-parameter-mp": (  # #1358: was (0.00044786087284640747, 0.00043665092111332875, 0.00043159275680957753)
            0.0004486906740102111,
            0.0004374599523649604,
            0.00043252389550624775,
        ),
        "dihedral-effect-md": (
            -0.031506,
            -0.031567,
            -0.031594,
        ),  # #1358: was (-0.032411, -0.032474, -0.032502)
        "weathercock-stability-md": (
            0.030797,
            0.029729,
            0.02926,
        ),  # #1358: was (0.031008, 0.02994, 0.029459)
        "spiral-criterion-md": (
            -0.002413886917,
            -0.002307771912,
            -0.0022611246900000005,
        ),  # #1358: was (-0.0024717262300000004, -0.002363510886, -0.0023148166369999995)
        "spiral-doubling-time-md": (
            3.997370967434639,
            4.039328385731496,
            4.059076950852463,
        ),  # #1358: was (3.8964376579165627, 3.9376241881010157, 3.9573378150728695)
        "dihedral-effect-app": (
            -0.039611,
            -0.039693,
            -0.039729,
        ),  # #1358: was (-0.039633, -0.039715, -0.039752)
        "weathercock-stability-app": (
            0.032843,
            0.031769,
            0.031297,
        ),  # #1358: was (0.032849, 0.031775, 0.031291)
        "spiral-criterion-app": (
            -0.00297175944,
            -0.0028458317780000004,
            -0.0027904928799999994,
        ),  # #1358: was (-0.0029734095239999994, -0.00284744017, -0.002790657778)
        "spiral-doubling-time-app": (
            3.229016625787197,
            3.2645923196333984,
            3.2812362457101854,
        ),  # #1358: was (3.2272734763561552, 3.262813460933183, 3.2798952877938663)
        "dihedral-effect-mp": (
            -0.055207,
            -0.055331,
            -0.055386,
        ),  # #1358: was (-0.055323, -0.055448, -0.055504)
        "weathercock-stability-mp": (
            0.037749,
            0.036664,
            0.036187,
        ),  # #1358: was (0.03779, 0.036706, 0.036216)
        "spiral-criterion-mp": (
            -0.004336717008,
            -0.004169828252000001,
            -0.0040964629629999996,
        ),  # #1358: was (-0.004348526534, -0.004181498932, -0.0041060071519999995)
        "spiral-doubling-time-mp": (
            2.3073010767103233,
            2.3326968167822693,
            2.344517742600123,
        ),  # #1358: was (2.302151031594126, 2.327441132903775, 2.3395474249407746)
        "roll-due-to-yaw-rate-mp": (
            0.176987,
            0.176022,
            0.175597,
        ),  # #1358: was (0.177292, 0.176326, 0.175888)
        "horizontal-tail-volume": (
            0.4961653106252867,
            0.4843902684658993,
            0.4792149752435751,
        ),  # #1358: was (0.4961653106252867, 0.4843902684658993, 0.4790771235618024)
    },
    FleetMember.RV7: {
        "vertical-tail-volume": (
            0.08299981005376741,
            0.08260137411188775,
            0.0823223209528384,
        ),  # #1358: was (0.08299981005376741, 0.08260137411188775, 0.08232598055728932)
        "spiral-parameter-md": (
            3.4201582053710453,
            3.4037399273647253,
            3.3922410341619686,
        ),  # #1358: was (3.4131676914627334, 3.3967829710271054, 3.3854580730257293)
        "spiral-parameter-mp": (
            2.1761853549019405,
            2.165738698927386,
            2.1584221593164044,
        ),  # #1358: was (2.1774822888254683, 2.1670294069922154, 2.1598045159086534)
        "dihedral-effect-md": (
            -0.115828,
            -0.115922,
            -0.115988,
        ),  # #1358: was (-0.11597, -0.116064, -0.116129)
        "weathercock-stability-md": (
            0.116011,
            0.115044,
            0.114367,
        ),  # #1358: was (0.116069, 0.115102, 0.114434)
        "spiral-criterion-md": (
            0.006070540842000004,
            0.006135726507999997,
            0.006181417922999997,
        ),  # #1358: was (0.006072173627000001, 0.0061375107559999975, 0.006182598777999999)
        "spiral-doubling-time-md": (
            -5.852893368438802,
            -5.745070884877815,
            -5.670879939543939,
        ),  # #1358: was (-5.850162486576177, -5.742275251299046, -5.669132348351651)
        "dihedral-effect-mp": (
            -0.154706,
            -0.154864,
            -0.154974,
        ),  # #1358: was (-0.154644, -0.154801, -0.15491)
        "weathercock-stability-mp": (
            0.134946,
            0.133972,
            0.133289,
        ),  # #1358: was (0.134911, 0.133936, 0.133263)
        "spiral-criterion-mp": (
            0.0054938676240000005,
            0.005594275483999999,
            0.005664784249999999,
        ),  # #1358: was (0.005496696330999997, 0.005597223511000001, 0.005666504381999997)
        "spiral-doubling-time-mp": (
            -6.579493193229386,
            -6.416475523175471,
            -6.305492332587719,
        ),  # #1358: was (-6.575390944435995, -6.412336326639169, -6.303269402027587)
        "roll-due-to-yaw-rate-mp": (
            0.192503,
            0.191881,
            0.191444,
        ),  # #1358: was (0.192419, 0.191797, 0.191366)
        "dihedral-effect-app": (
            -0.111985,
            -0.112021,
            -0.112047,
        ),  # #1358: was (-0.11211, -0.112147, -0.112172)
        "weathercock-stability-app": (
            0.104274,
            0.103318,
            0.102649,
        ),  # #1358: was (0.104331, 0.103376, 0.102715)
        "spiral-criterion-app": (  # #1358: was (0.0031651667940000017, 0.0032547406920000015, 0.0033166535509999984)
            0.0031673059359999985,
            0.0032567782080000045,
            0.003319585471999998,
        ),
        "spiral-doubling-time-app": (
            -8.059780722239793,
            -7.771066176279423,
            -7.577848406844959,
        ),  # #1358: was (-8.06557909709055, -7.776385503427931, -7.585566120295225)
        "horizontal-tail-volume": (
            0.46242042634810815,
            0.4601217478084075,
            0.4585118189824178,
        ),  # #1358: was (0.46242042634810815, 0.4601217478084075, 0.45853293217360086)
    },
    FleetMember.CHEKKER: {
        "vertical-tail-volume": (
            0.042546551629209804,
            0.04191818550080524,
            0.041501123399267585,
        ),  # #1358: was (0.042546551629209804, 0.04191818550080524, 0.04131168576051653)
        "spiral-parameter-md": (
            1.4570448636852895,
            1.4355259013993515,
            1.4212432352463078,
        ),  # #1358: was (1.2155634727111202, 1.1976109269952153, 1.1802831083525032)
        "spiral-parameter-mp": (
            0.9337255560510549,
            0.9199354487407978,
            0.9107826143099407,
        ),  # #1358: was (0.8255425979642333, 0.8133502348642426, 0.8015821513865011)
        "dihedral-effect-md": (
            -0.115884,
            -0.11591,
            -0.115927,
        ),  # #1358: was (-0.128846, -0.128896, -0.128945)
        "weathercock-stability-md": (
            0.003732,
            0.002647,
            0.001927,
        ),  # #1358: was (0.006817, 0.005717, 0.004655)
        "spiral-criterion-md": (
            0.006008104992,
            0.006142809783999999,
            0.006232134556999999,
        ),  # #1358: was (0.006618280529999999, 0.006777835579, 0.0069319636)
        "spiral-doubling-time-md": (
            -0.5634124644165173,
            -0.4911344894935163,
            -0.4448904607837116,
        ),  # #1358: was (-0.7288070099238422, -0.6588721566396655, -0.5944025558380204)
        "dihedral-effect-app": (
            -0.135759,
            -0.135823,
            -0.135865,
        ),  # #1358: was (-0.135866, -0.13593, -0.135991)
        "weathercock-stability-app": (
            0.008711,
            0.007604,
            0.006869,
        ),  # #1358: was (0.008742, 0.007634, 0.006565)
        "spiral-criterion-app": (
            0.006897012362999999,
            0.007070425725000001,
            0.007185693217000001,
        ),  # #1358: was (0.006900898919999999, 0.007074727484, 0.007242424199)
        "spiral-doubling-time-app": (
            -0.815983288818358,
            -0.7458175821072754,
            -0.7010923499581307,
        ),  # #1358: was (-0.8173664987185193, -0.7471403993758698, -0.6825732601780217)
        "dihedral-effect-mp": (
            -0.152248,
            -0.152345,
            -0.152409,
        ),  # #1358: was (-0.165338, -0.165462, -0.165583)
        "weathercock-stability-mp": (
            0.013953,
            0.012828,
            0.012082,
        ),  # #1358: was (0.018871, 0.017734, 0.016637)
        "spiral-criterion-mp": (
            0.0073925310939999996,
            0.007602163141000001,
            0.007741049533999999,
        ),  # #1358: was (0.007575420761000002, 0.007816410005999998, 0.008048947340000001)
        "spiral-doubling-time-mp": (
            -1.0357729454209064,
            -0.9607788103585708,
            -0.9132985087462556,
        ),  # #1358: was (-1.2384981148179042, -1.154838679755825, -1.0788587624008696)
        "roll-due-to-yaw-rate-mp": (
            0.216802,
            0.214908,
            0.213649,
        ),  # #1358: was (0.239795, 0.237744, 0.235762)
        "horizontal-tail-volume": (
            0.424137752916356,
            0.41757506031430747,
            0.4132192393293262,
        ),  # #1358: was (0.424137752916356, 0.41757506031430747, 0.41124074154884005)
        "turn-sideslip": (
            2.843528757647932,
            2.816892763733877,
            2.7992145547866074,
        ),  # #1358: was (3.2756171636177362, 3.2451665480341023, 3.2157609335062465)
        "rudder-roll-authority-md": (
            0.061992234518861135,
            0.06017464102606867,
            0.05898319088633131,
        ),  # #1358: was (0.05171803405028524, 0.05020167699557676, 0.0487594848807043)
        "rudder-roll-authority-mp": (  # #1358: was (0.035123990766397245, 0.034094166022162836, 0.03311470994931793)
            0.03972680257803884,
            0.03856202478908327,
            0.03779850166638438,
        ),
        "turn-sideslip-gain": (
            1.4240055698597025,
            1.4106665791460171,
            1.4018135411950738,
        ),  # #1358: was (1.4503320470793162, 1.4368495485368242, 1.4238297409758247)
    },
    # V-tail (#1208, root carried to the centreline): S_h,eff = sum S_i cos^2(nu_i) and the fin share sum S_i sin^2(nu_i); the aircraft
    # has ailerons, so the turn sideslip and the rudder roll authority do not apply. The AVL mesh is
    # declared not converged (1.27 % MAC).
    FleetMember.BELEMNITOS: {
        "horizontal-tail-volume": (0.45950560635266013, 0.4488237381988041, 0.45656878152972113),
        "vertical-tail-volume": (0.025408286952336757, 0.024817634809059307, 0.025245895706618834),
        "spiral-parameter-md": (
            0.848701185329157,
            0.8289719066470822,
            0.8432769061171653,
        ),  # #1358: was (0.8486991754892165, 0.8289699435287594, 0.8432749091226565)
        "spiral-parameter-mp": (
            0.7345469434191771,
            0.7174713441360647,
            0.7298522548947639,
        ),  # #1358: was (0.7345125179051271, 0.7174377188925601, 0.729818049403501)
        "dihedral-effect-md": (-0.094868, -0.095005, -0.094905),
        "weathercock-stability-md": (0.016994, 0.015078, 0.016467),
        "spiral-criterion-md": (
            -0.001804905128,
            -0.0014463230339999999,
            -0.0017061973919999995,
        ),  # #1358: was (-0.00180481026, -0.0014463230339999999, -0.0017061973919999995)
        "spiral-doubling-time-md": (
            3.216952137734797,
            3.721672852501508,
            3.334774984068144,
        ),  # #1358: was (3.217117424231301, 3.7216684457849256, 3.3347710354652436)
        "dihedral-effect-app": (
            -0.086639,
            -0.086727,
            -0.086663,
        ),  # #1358: was (-0.08664, -0.086727, -0.086664)
        "weathercock-stability-app": (0.015794, 0.01388, 0.015268),
        "spiral-criterion-app": (  # #1358: was (-0.0014056698020000003, -0.0011063984559999999, -0.0013233878399999998)
            -0.0014056386830000002,
            -0.0011063568160000002,
            -0.001323429481,
        ),
        "spiral-doubling-time-app": (
            3.9331974751193175,
            4.576096811664044,
            4.0807987270445985,
        ),  # #1358: was (3.933100758994933, 4.575932122424116, 4.080918092210947)
        "dihedral-effect-mp": (
            -0.101673,
            -0.101851,
            -0.101722,
        ),  # #1358: was (-0.101675, -0.101854, -0.101724)
        "roll-due-to-yaw-rate-mp": (
            0.238573,
            0.236747,
            0.238072,
        ),  # #1358: was (0.238582, 0.236757, 0.238081)
        "weathercock-stability-mp": (
            0.018314,
            0.016398,
            0.017787,
        ),  # #1358: was (0.018315, 0.016399, 0.017788)
        "spiral-criterion-mp": (
            -0.0022166051659999997,
            -0.0018084909460000004,
            -0.0021043245400000003,
        ),  # #1358: was (-0.002216864555, -0.001808728749, -0.002104579096)
        "spiral-doubling-time-mp": (
            2.7758109685231074,
            3.1829028079758097,
            2.872077667754676,
        ),  # #1358: was (2.7755913269260257, 3.1826161075699564, 2.8718424189669736)
    },
    FleetMember.WIESEL: {
        "vertical-tail-volume": (
            0.03972881444148937,
            0.03888724528575182,
            0.03927838087725308,
        ),  # #1358: was (0.03972881444148937, 0.03888724528575182, 0.039284726758123625)
        "spiral-parameter-md": (
            3.744330980637661,
            3.665015413171686,
            3.7018788618669665,
        ),  # #1358: was (3.680333345186025, 3.602373429450246, 3.6391946721031836)
        "spiral-parameter-mp": (
            2.442491379585694,
            2.390752473275227,
            2.4147991337135326,
        ),  # #1358: was (2.437042082476476, 2.385418607759728, 2.409800887694143)
        "dihedral-effect-md": (
            -0.087225,
            -0.087349,
            -0.087291,
        ),  # #1358: was (-0.088023, -0.08815, -0.08809)
        "weathercock-stability-md": (
            0.043483,
            0.041755,
            0.042558,
        ),  # #1358: was (0.043546, 0.041818, 0.042634)
        "spiral-criterion-md": (  # #1358: was (0.0010945545549999993, 0.0011898834120000002, 0.0011448860140000012)
            0.0011137906549999995,
            0.001207167951999999,
            0.0011637696509999998,
        ),
        "spiral-doubling-time-md": (
            -16.842047218003884,
            -15.00926521614503,
            -15.824485091352422,
        ),  # #1358: was (-17.075220297174752, -15.173067737886583, -16.03158193366587)
        "dihedral-effect-app": (
            -0.101679,
            -0.10185,
            -0.10177,
        ),  # #1358: was (-0.101737, -0.101908, -0.101828)
        "weathercock-stability-app": (
            0.044998,
            0.043294,
            0.044086,
        ),  # #1358: was (0.045006, 0.043302, 0.044106)
        "spiral-criterion-app": (  # #1358: was (0.0007094788889999998, 0.0008373537819999994, 0.0007770614419999999)
            0.0007113175819999989,
            0.0008391484880000003,
            0.0007797137939999999,
        ),
        "spiral-doubling-time-app": (
            -25.371225958017973,
            -20.822459405018424,
            -22.751766127189764,
        ),  # #1358: was (-25.435770361130125, -20.866202192095763, -22.833650307591267)
        "dihedral-effect-mp": (
            -0.111672,
            -0.111874,
            -0.11178,
        ),  # #1358: was (-0.111829, -0.112031, -0.111936)
        "weathercock-stability-mp": (
            0.046523,
            0.044837,
            0.045621,
        ),  # #1358: was (0.04655, 0.044865, 0.045661)
        "spiral-criterion-mp": (  # #1358: was (0.00034163753999999925, 0.0004941471570000001, 0.00042210263699999934)
            0.00034805355299999917,
            0.0005002903609999986,
            0.00042937264799999906,
        ),
        "spiral-doubling-time-mp": (
            -51.86149153524717,
            -34.99161293464704,
            -41.36074222804993,
        ),  # #1358: was (-52.842709852951444, -35.432743338948264, -42.08935925997173)
        "roll-due-to-yaw-rate-mp": (
            0.151533,
            0.149623,
            0.150512,
        ),  # #1358: was (0.15184, 0.149927, 0.150831)
        "horizontal-tail-volume": (
            0.5417262125334599,
            0.5298328066511209,
            0.5353604977660313,
        ),  # #1358: was (0.5417262125334599, 0.5298328066511209, 0.5354501803980052)
    },
}

# The turn sideslip applies only without ailerons. Which members have a roll device is read from the
# reference documents themselves (#1383): the fleet grows, a named list goes stale.
TURN_SIDESLIP = ("turn-sideslip", "turn-sideslip-gain")
# The rudder roll authority has the same applicability (`has_no_aileron`).
WITHOUT_AILERON_ONLY = (*TURN_SIDESLIP, "rudder-roll-authority-md", "rudder-roll-authority-mp")
ROLL_ROLES = frozenset({"aileron", "flaperon", "elevon"})


def _device_roles(node: object) -> set[str]:
    """Every ``role`` named anywhere in a geometry document."""
    if isinstance(node, dict):
        document = cast("dict[str, object]", node)
        role = document.get("role")
        found = {role} if isinstance(role, str) else set[str]()
        return found.union(*(_device_roles(value) for value in document.values()))
    if isinstance(node, list):
        return set[str]().union(*(_device_roles(item) for item in cast("list[object]", node)))
    return set()


def _has_roll_device(member: FleetMember) -> bool:
    return bool(_device_roles(reference_document(member)) & ROLL_ROLES)


WITHOUT_TURN_SIDESLIP = tuple(m for m in FleetMember if _has_roll_device(m))
RUDDER_ONLY = tuple(m for m in FleetMember if not _has_roll_device(m))
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


@pytest.mark.asyncio
async def test_the_rv7_approach_point_needs_the_landing_deflection() -> None:
    by_slug = {q.slug: q for q in (await run(FleetMember.RV7, flaps=False)).quantities}
    for slug in RV7_NEEDS_LANDING_DEFLECTION:
        error = by_slug[slug].error
        assert error is not None
        assert error.code == "upstream_failed"
        assert error.detail["causes"] == [{"quantity": "airplane-landing", "code": "missing_input"}]


@pytest.mark.parametrize("member", WITHOUT_TURN_SIDESLIP)
@pytest.mark.asyncio
async def test_with_ailerons_the_turn_sideslip_and_rudder_roll_authority_are_not_applicable(
    member: FleetMember,
) -> None:
    by_slug = {q.slug: q for q in (await run(member)).quantities}
    for slug in WITHOUT_AILERON_ONLY:
        assert by_slug[slug].status is QuantityStatus.NOT_APPLICABLE, slug
        assert by_slug[slug].interval is None


def test_the_fleet_has_members_with_and_without_a_roll_device() -> None:
    assert FleetMember.CHEKKER in RUDDER_ONLY
    assert FleetMember.BRYAN in WITHOUT_TURN_SIDESLIP
    assert len(WITHOUT_TURN_SIDESLIP) + len(RUDDER_ONLY) == len(FleetMember)


@pytest.mark.parametrize("member", RUDDER_ONLY)
@pytest.mark.asyncio
async def test_without_a_roll_device_the_turn_sideslip_and_rudder_roll_authority_apply(
    member: FleetMember,
) -> None:
    """The turn sideslip applies; the rudder roll authority applies exactly where its input
    vertical-tail-volume does (BARRACUDA and VOODOO have none)."""
    by_slug = {q.slug: q for q in (await run(member)).quantities}
    for slug in TURN_SIDESLIP:
        assert by_slug[slug].status is not QuantityStatus.NOT_APPLICABLE, slug
    no_fin_volume = by_slug["vertical-tail-volume"].status is QuantityStatus.NOT_APPLICABLE
    for slug in ("rudder-roll-authority-md", "rudder-roll-authority-mp"):
        assert (by_slug[slug].status is QuantityStatus.NOT_APPLICABLE) is no_fin_volume, slug


@pytest.mark.asyncio
async def test_the_belemnitos_v_tail_volumes_are_the_shares_of_its_two_roles() -> None:
    """V_H uses S_h,eff = sum S_i cos^2(nu_i) and V_V the fin share sum S_i sin^2(nu_i) of the one
    surface; both Drela bands hold, and the unstable spiral is judged (B < 5), not hidden (#1208)."""
    airplane = AirplaneGeometry.model_validate(reference_document(FleetMember.BELEMNITOS))
    result = await run(FleetMember.BELEMNITOS)
    verdicts = {
        v.rule_id: v
        for v in evaluate_rules(shipped_rule_table(), result, facts_from_geometry(airplane))
    }
    assert verdicts["horizontal-tail-volume"].status is RuleStatus.INSIDE
    assert verdicts["vertical-tail-volume"].status is RuleStatus.INSIDE
    assert verdicts["spiral-stability"].status is RuleStatus.BELOW
    assert verdicts["spiral-stability-circling-aileron"].status is RuleStatus.BELOW
    assert verdicts["spiral-stability-circling-rudder-only"].status is RuleStatus.NOT_APPLICABLE


@pytest.mark.parametrize("member", list(GOLDEN))
@pytest.mark.asyncio
async def test_the_drela_rules_judge_the_new_values_on_the_fleet(member: FleetMember) -> None:
    """Both rules evaluate end to end: the volume inside Drela's band, the sideslip only for CHEKKER."""
    airplane = AirplaneGeometry.model_validate(reference_document(member))
    result = await run(member)
    judged = evaluate_rules(shipped_rule_table(), result, facts_from_geometry(airplane))
    verdicts = {v.rule_id: v for v in judged}
    assert verdicts["horizontal-tail-volume"].status is RuleStatus.INSIDE
    expected = RuleStatus.INSIDE if member is FleetMember.CHEKKER else RuleStatus.NOT_APPLICABLE
    assert verdicts["turn-sideslip"].status is expected
    assert verdicts["rudder-roll-authority"].status is (
        RuleStatus.BELOW if member is FleetMember.CHEKKER else RuleStatus.NOT_APPLICABLE
    )
    if member is FleetMember.CHEKKER:
        assert verdicts["turn-sideslip"].level == "below-typical-limit"


@pytest.mark.asyncio
async def test_the_chekker_sideslip_is_the_gain_times_the_worst_turn_yaw_rate() -> None:
    """beta = kappa r_hat_max with r_hat_max = rho g b C_L,mp / (8 W/S), rebuilt from the canon's own outputs."""
    aircraft = AircraftInput.model_validate(
        {
            "airplane": reference_document(FleetMember.CHEKKER),
            "values": {
                "aircraft-mass": FleetMember.CHEKKER.mass_kg,
                "altitude": 0.0,
                "static-margin-target": SM_TARGET,
            },
        }
    )
    slugs = ("air-density", "wing-span", "wing-loading", "lift-coefficient-minimum-sink")
    result = await compute(aircraft, request(*slugs, *TURN_SIDESLIP))
    by_slug = {q.slug: q for q in result.quantities}
    values: dict[str, float] = {}
    for slug in slugs:
        value = by_slug[slug].value
        assert value is not None, slug
        values[slug] = value
    r_hat = (
        values["air-density"]
        * STANDARD_GRAVITY
        * values["wing-span"]
        * values["lift-coefficient-minimum-sink"]
        / (8.0 * values["wing-loading"])
    )
    beta, kappa = by_slug["turn-sideslip"], by_slug["turn-sideslip-gain"]
    assert beta.interval is not None
    assert kappa.interval is not None
    for world, gain in kappa.interval.worlds.items():
        assert abs(beta.interval.worlds[world] - math.degrees(gain * r_hat)) <= 1e-9

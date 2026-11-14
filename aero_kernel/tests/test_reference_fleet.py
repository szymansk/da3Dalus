"""The reference fleet copies equal their sources except for the recorded additions."""

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest
from aero_kernel.schema import AircraftInput
from aero_kernel.tests.reference_fleet import (
    FLAP_DEFLECTIONS_DEG,
    PLAN_BATCH,
    REFERENCE_DIR,
    FleetMember,
    reference_document,
)
from aero_kernel.validate import validate_aircraft

# Recorded in reference/README.md: the SHA-256 of each source as canonical JSON.
SOURCE_CANONICAL_SHA256 = {
    FleetMember.BRYAN: "09952f107c1204abdd160fb59e668c0bc13131b2a4112a270d77470c9c15d4e1",
    FleetMember.JAGUAR: "92e8ad7c5b29df99175b1c2306b5a4b5509bf753736e853b12114660c2f1bed6",
    FleetMember.CHEKKER: "01779a0cc90e44b98ea4a49ab8fd949472f0305f1701f60b39b0e8aaf755e3c4",
    FleetMember.BELEMNITOS: "747c570e5527ccfc604a7e466ed2049d96b04b29b05550d07940230241a5754e",
    # WIESEL and RV-7 have no source file: the source is the null-stripped export of the app's
    # GET /aeroplanes/{id} from a copy of db/test.db (README).
    FleetMember.WIESEL: "f8528c5a688219caa834ac73eb190f1d7aa3cd04045d6abfaaed48b77f423e06",
    FleetMember.RV7: "72e8f9e0c5307a001b89b841d6f486eb23624c2ce71f54503dad56350abd06b2",
    # The 28 plan models of #1372, exported as WIESEL and RV-7 were; the export already states
    # every surface_type and body role, so their copies carry no addition.
    FleetMember.A6M2_ZERO: "68bff8aa9958e8ee5c0f936cc78576ac6a4a430d3746c9cb560bc37468832123",
    FleetMember.AERONCA_CHAMP: "fb26cd7b3b16b837bd6ad5e35c3b26cee78e3e90225e9329fa4d66f40d315fca",
    FleetMember.ALBATROS_4: "c6e29d57f6d2c8ab1da3916323d29b0a725f2e8456811d34af6c52f338375026",
    FleetMember.BARRACUDA: "6938594724c24320375b7bd388d99b3ae842159e5d2bc47c7a79f303bfe42d58",
    FleetMember.BF109_E: "a285c94a9f1ad455a949f2056dad1fdcc765fad42b0afd16d4a92e78e36bb886",
    FleetMember.D520_DEWOITINE: "6ade3b0b673d3501abf5f92d2155e1ddcfd8c94aaccec82f6a473086c9fd102f",
    FleetMember.DARDO: "17e4f522c175448470d843aea3c0039d6e7680ed6d729d2696f882831f206431",
    FleetMember.ESTRELA: "f82a8550724dc81c91ac7c0c845cc13f427a584010b098e54631f918d3c03477",
    FleetMember.EXTRA_300_EP: "cda24eeb81ecc7c84ee8a5a8a8db63366fd5b9fde3ef4727ef1d5a3e55a79e85",
    FleetMember.F3A_COMPETICION: "7c44d960180bc82cf87fc823a4950172ea23fb314e3951a9d8ec64b716a2e275",
    FleetMember.FORCE_5: "5a4cda0c4023db7481a24381a21a8fc4e55b7416848d303018ac1f639cc6b0df",
    FleetMember.FORCE_FOUR: "2bf10ca4b23c32b3564645415ad3d2dc9a53af3726643b8286ace55f8e052d0f",
    FleetMember.FW190_A8: "1e14ba92cac62d4c5912d5b831e287b6e1d7b86aabf7515407a7644f8f902da9",
    FleetMember.GEE_BEE_R3: "4d6fa0e7d4c1f1eae7d4d8a565f0c4419b9a7d08323fc602d3652c7ed396ce5f",
    FleetMember.KASTAWAY: "44f36fc31904967273527e86ad316b5c4820533cd16d4ce4acbd5e6cf3ac17d3",
    FleetMember.MILES_MAGISTER: "8e5c45ee9484cb18244e7bf8ad4cb20afc1650956d2a68203ace8de733cce329",
    FleetMember.MINI_FUNTANA: "0c1f02282c382b4b4b76abea1c30a195ada281e6a4656e12e6ec6b4d91462ed5",
    FleetMember.P36_HAWK: "45b0854f9d56d8cb11e1664b8e10518061b7a7526ef5e3be87de1069ab7464b5",
    FleetMember.P39: "bc099584d33f10b6f3d0c939d73ddc4dbd21de3afea8bb78ac97c434a72a594e",
    FleetMember.SNOOPY: "c02bd4b1f6b082670d8fb08f62aae1fefee6564e868691ba4e3c6de85fece627",
    FleetMember.SONAS_40: "73a4af4ecf0ca96849a40d0d01c16459d76b9d6aca44fe03932f043c51e15842",
    FleetMember.SPIRIT_100: "2a78862b02e9d495c4fd75c5c4207c7a7822ad096ec1041aa33adb9111731a37",
    FleetMember.SPRITE: "93f4f22972e2379e129b88e5af90f79a6ca4d7f94a371c3eff600a21963512da",
    FleetMember.SUPER_TRIDENT: "58687c7004680f61099811430075d27a4e5d275d2386fbb95ad137274c26b6d0",
    FleetMember.ULTRA_MINI_STICK: "8fd656a65a27e34fbaacdea5c5bb7c29cb43749e53b523f2c362bc0670d0b057",
    FleetMember.VOODOO: "b10bb0ef0b2b9b0290254e341f8c675062a5789f1e92c7851d31e025224c5945",
    FleetMember.WINDFREAK: "42ffcf810fd42b1f560db9b4920945772e3ea79fb0a15f348bc850df614feb31",
    FleetMember.WRISTOCRAT: "f51ea5f344750d13d4f216075c7abfe1b2a6656ca93326f67576c64680fa5fce",
    # The validation aircraft of #1388 has no source file: its source is the generator
    # scripts/canon_checks/reference_fleet/avistar_elite/build_document.py (README).
    FleetMember.AVISTAR_ELITE: "f09c30fc970e25dc180ab0f0524f1daddee21057967c25f54b74708ef3c48b61",
}
AIRFOIL_SHA256 = {
    "bryan/bryan_profil.dat": "75fc1827fb3059c6525464032b3a9c95f48c1205ef513750fd34532ebb69eb62",
    "bryan/bryan_platte.dat": "d221c31868aa05d295488b2286f66352406fe6b8649084bc98fb8737bd414595",
    "jaguar/jaguar_test_da3dalus_export__tragflaeche_kulfan.dat": "51eadb6d6121bd31cacfb08dead004223142b4f665eedc90e273953af4b92755",
    "jaguar/jaguar_test_da3dalus_export__hoehenleitwerk_kulfan.dat": "b902ac2c03d07c19921cbdaf522a4bd47aacf2c6d7f7c7365b8065856ba06003",
    "jaguar/jaguar_test_da3dalus_export__seitenleitwerk_kulfan.dat": "9a24aa95dc458b6c5a67965ad97a3797dc638ad06ec76250f8b4dbae651d8cb6",
    "chekker/chekker_test_da3dalus_export__tragflaeche_kulfan.dat": "67fd4dedb24e60450644ac2820fc6ac999b54802af4c253b5e27c9785d516e5b",
    "chekker/chekker_test_da3dalus_export__hoehenleitwerk_kulfan.dat": "7b3d6d3664542a344b0485c6ba3f54978dfdcf580acb5e50b56a17fe63da8b47",
    "chekker/chekker_test_da3dalus_export__seitenleitwerk_kulfan.dat": "a246dcdebed289a8acb57ac88afd05e48c0d3df6085c5cc8d866fb4ad09f41bd",
    "belemnitos/mh32.dat": "ad0928ce919261d66d0f58fa22bb450c5cb7f5f5710f8c5bd334005c5e48af4c",
    "belemnitos/belemnitos_vlw_00.dat": "55a9987860ab6f75de8c1c3c94f109eabf77d4a389cb8ba54a5e3258c63c0afb",
    "belemnitos/belemnitos_vlw_01.dat": "10c7e2d9c33fe6e8ef0dbafd3c9182886864b53e3f43a2cfd4c6165a1afdfec6",
    "belemnitos/belemnitos_vlw_02.dat": "ce30712593da820c9a1cbc3de18e92217325c4d92837289404753cbdf536659e",
    "belemnitos/belemnitos_vlw_03.dat": "1b1984d95564d7b828c96045c45e2dd86749d74b6df4dcd8fa02c53c12187dd3",
    "belemnitos/belemnitos_vlw_04.dat": "fe7f88c0651a1e4bf83e14719b53873b937cb4c07b32cfd2d9944892c3fe5c42",
    "belemnitos/belemnitos_vlw_05.dat": "15e69a3bd5289e786682db8fae5ecece396b43eac50b59dbba29604863d455c2",
    "belemnitos/belemnitos_vlw_06.dat": "5991bde121db4dd967c47580e74242b4a5b30a545ca07ee3b5844f541a185e8e",
    "belemnitos/belemnitos_vlw_07.dat": "c4fc111644816911b722c3ce0b1756311a0d16afa8e37f89f7e94f985614b84d",
    "belemnitos/belemnitos_vlw_08.dat": "32299353ef395127caf81fee23404854f110e872ec3e57e464b4b7e0fe79cb11",
    "belemnitos/belemnitos_vlw_09.dat": "93171808ee6f7171b6df2a60beb656095296ea1f2ae78ef3906e764164eed109",
    "wiesel/wiesel_main_wing_kulfan.dat": "3d9c5083d2b78957c9dbd9d1d062d5705106502fd0e4547238991e7ab7549f4a",
    "wiesel/wiesel_horizontal_tail_kulfan.dat": "433c17dc888ef530cccb0485ff2d691e23545c963f39cd99825f719c90cb2917",
    "wiesel/wiesel_vertical_tail_kulfan.dat": "43f596a38e6291726dee681c7b3b50e45faa2f60014f4e1fc1aed48778cebfcf",
    "rv7/naca23013.5.dat": "54262966a988b6e3839e035a860e7030fd41b8a4a1bb554ca0a1e93d98baa882",
    "rv7/naca0015.dat": "645e867c98ddbc808b315c0c0a672cf390aac23fe32112f83b560efb1b0e7bf9",
    "rv7/n12.dat": "82c981d6576fe7793e6657774b2d12ed36c14ec69237a9b72e99dbdbf9d8ddc0",
    "a6m2_zero/a6m2_zero_main_wing_kulfan.dat": "ef3def7c95da5cacac76714c3997e3e3c90ba4e1799057beb9386d2cd5228f3b",
    "a6m2_zero/a6m2_zero_horizontal_tail_kulfan.dat": "59f3e2994f5edcd758e606735aaf560af8bc867c8a316c15da69374b7e42ae8e",
    "a6m2_zero/a6m2_zero_vertical_tail_kulfan.dat": "52a2cf69950a36fe06879bc3d1f50c9450702994debb558bc24b9788bb4e399e",
    "aeronca_champ/aeronca_champ_main_wing_kulfan.dat": "a04ad110eb8205f034f273a05e1049c552bd4a7e56d25c48cddcb14e7860697e",
    "aeronca_champ/aeronca_champ_horizontal_tail_kulfan.dat": "c5e1bd2672b27fee18476eda3dc905e0f302021e46aae18967a0dbaa48314f72",
    "aeronca_champ/aeronca_champ_vertical_tail_kulfan.dat": "ecddd48808e3027a34fd63aa5777bae6c7aa9e1806a90e55fcd6391513decbda",
    "albatros_4/sd7037.dat": "58dc2b375e8c96c4b2ad7acd2968de9d69334ec80c656da10a022981e470784f",
    "albatros_4/albatros_4_v_tail_kulfan.dat": "f2d83d6cb4907b688acafd5d1e9e7f569f49697effb18e0f64e395d6da1cad01",
    "barracuda/barracuda_main_wing_kulfan.dat": "99daaf9a65e34c4aa416de90a42cd73e00a32ad367cc661f1f4f9467f8234b25",
    "barracuda/barracuda_v_tail_kulfan.dat": "56737465686a728ac459688eaa652ee80f3d8807c516ac2ad42abb0804052aa1",
    "bf109_e/bf109_e_main_wing_kulfan.dat": "5f4b6d902b4495b6ed1d5afa1cfbcec1d23d66d9269d657f709acf4dd78549a3",
    "bf109_e/bf109_e_horizontal_tail_kulfan.dat": "d2ea328bc26738140d555155807f52d8cc25ce3f0093858f8f1e3b08d439bb7e",
    "bf109_e/bf109_e_vertical_tail_kulfan.dat": "2edb28ddf0cb1894cf1879937f175957a63d9084c71a4983709aed3294149abe",
    "d520_dewoitine/d520_dewoitine_main_wing_kulfan.dat": "48645ca42c612c0fd153c2d4aa02fd9d188b3b1b886ba48fee3adf9de246b85f",
    "d520_dewoitine/d520_dewoitine_horizontal_tail_kulfan.dat": "235e3dce2f7e70458886081e3ec7f4f1a85e7360b04317149d890ace502ad08f",
    "d520_dewoitine/d520_dewoitine_vertical_tail_kulfan.dat": "0a659002364927c8b720db9bc2d5038677391bef620a6d401307b63742d65c24",
    "dardo/naca2410.dat": "3f523e19178b501a0a19b07871299277a2fd9f39e47d8f08ce955949ec3c5c2d",
    "dardo/naca0006.dat": "b4393d8fc137a5915778896ba5111c7672afd12c84058d62361f79e4a645cd4d",
    "dardo/dardo_vertical_tail_kulfan.dat": "f7b5444985f1257584f3e6300b01dcbba270ef367b62229299b7183c169f6f4c",
    "estrela/estrela_main_wing_kulfan.dat": "354876e2c46083b09268fcd837a1d429dd40d91ecaec3a62515970c4fff4a125",
    "estrela/estrela_horizontal_tail_kulfan.dat": "6c2eb133fb1255cc00eff99c179888d564b8e282a469bc48e3aba541cda7a86a",
    "estrela/estrela_vertical_tail_kulfan.dat": "7a34c2eb2f6bf9a47f438009f2da843110ae2f155f390cc9589fe700243139ac",
    "extra_300_ep/extra_300_ep_main_wing_kulfan.dat": "414a36af9620cfc9fa081fd0f07c5384cfaaafbfe7a578c65231de7d59efb88b",
    "extra_300_ep/extra_300_ep_horizontal_tail_kulfan.dat": "a2d03425322374516e901410ee7ff833eea3f399cd93c6dc399bdaba85435fba",
    "extra_300_ep/extra_300_ep_vertical_tail_kulfan.dat": "88031b4d388269ea9a114a58a268c99d2995334f961a95fe35fb840a00455c4f",
    "f3a_competicion/f3a_competicion_main_wing_kulfan.dat": "a3e6a0e0ed3a36743d037731439bfb37f87f13ca23027e3fedafed91d852a1d2",
    "f3a_competicion/f3a_competicion_horizontal_tail_kulfan.dat": "11560244f92b1b77ede210d9030c17a8ee29f957408595973678f63d83e3a8cf",
    "f3a_competicion/f3a_competicion_vertical_tail_kulfan.dat": "4cfcbbd58657e5c6d3215c3aa51bb8d650326221b7f72db03698ed4b5dc458fe",
    "force_5/force_5_main_wing_kulfan.dat": "9c4641c18aae7022ef8e3b3958d84b6732184825564cb43456f12bae8f9a3729",
    "force_5/force_5_horizontal_tail_kulfan.dat": "8619716d5b5d5a977c149754d3d871785fde48180ba4dc8b3fc58365e99310e6",
    "force_5/force_5_vertical_tail_kulfan.dat": "16f9d8279f1d519f6c604cb4182108d2ec081d274a983cc067d1dfb19ca6670c",
    "force_four/force_four_main_wing_kulfan.dat": "fea8bc0d0afd08faf247b28dcacd57f4d808b30cf3d18a1337fae44c4bfb1bbd",
    "force_four/force_four_horizontal_tail_kulfan.dat": "0cb52bf19c7e8989bd7ed7d75ee9b6028ce47bccff0830a4d702027c69373bcb",
    "force_four/bryan_platte.dat": "d221c31868aa05d295488b2286f66352406fe6b8649084bc98fb8737bd414595",
    "fw190_a8/fw190_a8_main_wing_kulfan.dat": "80a570b28d44422200b18855c77033a3a0d018091f6fc217ec24dceb0a96cb18",
    "fw190_a8/fw190_a8_horizontal_tail_kulfan.dat": "1a684258caeac32caa56ef8c27fdff231349ab958f52ce8e5a9abbd8bc719476",
    "fw190_a8/fw190_a8_vertical_tail_kulfan.dat": "6dbe0ff203b1b540e4b70dadff1b95f020eba3017a3193b4ea6c59e51a81f6e6",
    "gee_bee_r3/gee_bee_r3_main_wing_kulfan.dat": "737ea33e71f217056f6d38db2e5e0872f3463bd9c7848c0eac671e9b12a5b84f",
    "gee_bee_r3/gee_bee_r3_horizontal_tail_kulfan.dat": "547def8bcc18fb3e1f80eff92efd25f47d0d21ac61c0a5a435c0b2a843cb4409",
    "gee_bee_r3/gee_bee_r3_vertical_tail_kulfan.dat": "52b984b883089760a823ffac2c37a26665ecf9af86d3d4066a6d11f7ea92038b",
    "kastaway/kastaway_main_wing_kulfan.dat": "016c8743003ea2fefce2f831b4071de53d79b576588f956928b2c21093549ccc",
    "kastaway/kastaway_horizontal_tail_kulfan.dat": "3f99d4fc4b51534f008928bf7c75e5b78ecf03947f71053379251adb2f536b00",
    "kastaway/kastaway_vertical_tail_kulfan.dat": "a9acf1c0c67c6605a312eaa90313972cf45eb2a1b1089afc1c28ce65edf7063e",
    "miles_magister/miles_magister_main_wing_kulfan.dat": "bbe7f91f9e0b6929ff7d27a2cd5f24c615e9d77bfc7087a9753a3642f34f4eef",
    "miles_magister/bryan_platte.dat": "d221c31868aa05d295488b2286f66352406fe6b8649084bc98fb8737bd414595",
    "miles_magister/miles_magister_vertical_tail_kulfan.dat": "f19a080a6a946da400db3bfc088c6f913e033d071af071fd71b15aa517788d67",
    "mini_funtana/mini_funtana_main_wing_kulfan.dat": "5bcf54cb7549ee6521ecf9121d8804fbb73508dae6e60a409a13fe8d6ce19794",
    "mini_funtana/mini_funtana_horizontal_tail_kulfan.dat": "c23a38823b551ac620ae10375974daec2f504cdf61963fe4be563c03c495f51f",
    "mini_funtana/bryan_platte.dat": "d221c31868aa05d295488b2286f66352406fe6b8649084bc98fb8737bd414595",
    "p36_hawk/p36_hawk_main_wing_kulfan.dat": "9dff6c273fddb0adb104ec7954c3a2a3f993549e7ca731ded8dfa48d52fce483",
    "p36_hawk/p36_hawk_horizontal_tail_kulfan.dat": "3a90eab9ecfcd36c13c6c7945c284eda9c36557480fcfa292595e7ce16765867",
    "p36_hawk/bryan_platte.dat": "d221c31868aa05d295488b2286f66352406fe6b8649084bc98fb8737bd414595",
    "p39/p39_main_wing_kulfan.dat": "a607da7ce2b6c2f45c2ca4a5b33e22626302a75dc2f3d1b2afb9f30bf9ec0e5a",
    "p39/naca0210.dat": "b2d9e2c90465517cfec859a5b6aceac28ce5cb22280f15aa51725bc6f56e7695",
    "snoopy/snoopy_main_wing_kulfan.dat": "55d83bcc143f19334c8cd57eee403d2c818f5caf149ee0dd499ebf6d6f5e1cb9",
    "snoopy/naca0008.dat": "e1fc6db22dd2d270076bc625274608aee674fae367f537d4f47019742c1ff276",
    "snoopy/snoopy_vertical_tail_kulfan.dat": "0d230f5b0e6a376b521452708398557ed700d4348266c964582e50bfc444b9f7",
    "sonas_40/sonas_40_main_wing_kulfan.dat": "9c4084c87f2b7df9a5062287701069329e6bcbe4f72f2d259ebbd547faa30a2a",
    "sonas_40/sonas_40_horizontal_tail_kulfan.dat": "1c5b71c917763b81a078746f9328cc6cbb61c79f93140e9ffbf397eb9c8b065c",
    "sonas_40/sonas_40_vertical_tail_kulfan.dat": "4c824abf832f736bd9d53108f3739f95ab60674eeb291af16a0395f750a15142",
    "spirit_100/spirit_100_main_wing_kulfan.dat": "39a88d985a692acfe9b84cce5470ed8521bb737e6ecaee7fe5c4185f6c4301aa",
    "spirit_100/spirit_100_horizontal_tail_kulfan.dat": "d134507b09ef64c97a38cbdfd682c4c27c82673cf55c173e546e17525ad3d045",
    "spirit_100/spirit_100_vertical_tail_kulfan.dat": "6ac6d51b39a9842f37471f55e98f15337944af2c21216602a655bc8c95d999bc",
    "sprite/sprite_main_wing_kulfan.dat": "e0767394202405d782f3848f6b590a40db0d719fd831ec11ca376e7fc4b5305c",
    "sprite/sprite_horizontal_tail_kulfan.dat": "3b2fd6af37c100a79f0ca985fef53779a928d2b98353ee03ae29291aed32d39e",
    "sprite/sprite_vertical_tail_kulfan.dat": "f222fe14f364432adcd10a9178ad62ce0267c5ad85d945d69c175df6d6c759a3",
    "super_trident/super_trident_main_wing_kulfan.dat": "a545907391d544c56d71980b30a953b2e0f307d0baeab1b148defdb2fdd4093e",
    "super_trident/super_trident_horizontal_tail_kulfan.dat": "9e980a193e51791966d02e04e48e3ffe7b5ca66414b43e186ea7099a99aac98d",
    "super_trident/super_trident_vertical_tail_kulfan.dat": "91dcd89a35b7742486f28c08cbabb18c397ebeed6dd698c732f71e148637c4c9",
    "ultra_mini_stick/e168_15.dat": "48f7e73386ab23a1e6b0e939e1dd02db5109851452dbe54e9270ce460031ba26",
    "ultra_mini_stick/ultra_mini_stick_horizontal_tail_kulfan.dat": "31ba99893f126a27c0db01d9fc53b14df1c20c5f87785618df09cd78fcf8d63b",
    "ultra_mini_stick/ultra_mini_stick_vertical_tail_kulfan.dat": "b3c696002c0058d9808fe5b73b53d9beb2ef2557dbb619549ba8ca1fdae06a05",
    "voodoo/voodoo_main_wing_kulfan.dat": "5d8eb98e2d854f630e7eb2c1f1fa4aa63b8da42d53aae311c1c63ca28be00e9b",
    "voodoo/voodoo_vertical_tail_kulfan.dat": "05a7348f12f0793b6aa9bb5292c80aeb4192f4111d6df7ddcfdf0504d334ec14",
    "windfreak/windfreak_main_wing_kulfan.dat": "62915d86a07f05ee990e52e0aa7ae6e853a80b41789a3c2114cd8da51b72ce7f",
    "windfreak/windfreak_vertical_tail_kulfan.dat": "201c0c7336bb29f14ae46cdd39041f9b5722d21a6dd04792d122ee7dc89718ac",
    "windfreak/windfreak_tip_plate_kulfan.dat": "94a0e79400b95365a6bfc4ffb6278e48931916d3a136e4526c7613e987a09275",
    "wristocrat/wristocrat_main_wing_kulfan.dat": "17668189add6b04dcb08b9689f6005b6d7bcf2a153b1393b8c0c8cf5f2901081",
    "wristocrat/wristocrat_horizontal_tail_kulfan.dat": "7e1ed736e3cb914e6af2079157a3b1202260d47e600c570a3652a378b44a88d2",
    "wristocrat/wristocrat_vertical_tail_kulfan.dat": "285c7673e2e8e19fad721c09abb99a26ae47ac2f9388c23bdc72ad56cca9993f",
    # AVISTAR of the UIUC Airfoil Database and the repository's NACA 0006 (README, #1388).
    "avistar_elite/avistar.dat": "b71d63826ada136382d26bb4df7954cefce0b2f49ca5910c16c13d6ddb48dce5",
    "avistar_elite/naca0006.dat": "b4393d8fc137a5915778896ba5111c7672afd12c84058d62361f79e4a645cd4d",
}
CONVENTIONAL = {
    "Tragflaeche": "main_wing",
    "Hoehenleitwerk": "horizontal_tail",
    "Seitenleitwerk": "vertical_tail",
}
# The role follows the function, per aircraft (README), keyed by the wing name of the copy.
SURFACE_TYPES = {
    FleetMember.BRYAN: CONVENTIONAL,
    FleetMember.JAGUAR: CONVENTIONAL,
    FleetMember.CHEKKER: CONVENTIONAL,
    FleetMember.BELEMNITOS: {"Tragflaeche": "main_wing", "V-Leitwerk": "v_tail"},
    FleetMember.WIESEL: {
        "main_wing": "main_wing",
        "horizontal_tail": "horizontal_tail",
        "vertical_tail": "vertical_tail",
    },
    # the DB names the surfaces "rudder" and "elevator"; the function decides, not the name
    FleetMember.RV7: {
        "main_wing": "main_wing",
        "rudder": "vertical_tail",
        "elevator": "horizontal_tail",
    },
}
# RV-7's root rib of the main wing is a bare designation in the export; the copy gives it the path
# its other five ribs have (an addition: the kernel resolves airfoil files by their path).
# BELEMNITOS' source carries a provenance note the format has no field for; the copy omits it.
BELEMNITOS_NOTE = ("quelle", "e-Hawk_Segler.airplane.json (aiHawk), umgewandelt 2026-10-13")
RV7_ROOT_AIRFOIL = ("naca23013.5", "./components/airfoils/naca23013.5.dat")
# BRYAN's `Haube` is the canopy on `Rumpf` (#1355 slice 2, README): role and attached_to are
# additions; every other body of the fleet is a fuselage without attachment.
BODY_ROLES = {FleetMember.BRYAN: {"Haube": ("canopy", "Rumpf")}}


def canonical_sha256(document: object) -> str:
    """SHA-256 of the document as canonical JSON (sorted keys, compact)."""
    text = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode()).hexdigest()


@pytest.mark.parametrize("member", list(FleetMember))
def test_a_copy_without_its_additions_is_the_source(member: FleetMember) -> None:
    document = json.loads(member.json_path.read_text())
    if member in SURFACE_TYPES:  # the first six; the plan batch's export states types and roles
        added = {name: wing.pop("surface_type") for name, wing in document["wings"].items()}
        assert added == SURFACE_TYPES[member]
        roles = {
            name: (body.pop("role"), body.pop("attached_to"))
            for name, body in document["fuselages"].items()
            if "role" in body
        }
        assert roles == BODY_ROLES.get(member, {})
    if member is FleetMember.BELEMNITOS:
        assert BELEMNITOS_NOTE[0] not in document
        document[BELEMNITOS_NOTE[0]] = BELEMNITOS_NOTE[1]
    if member is FleetMember.RV7:
        root = document["wings"]["main_wing"]["x_secs"][0]
        assert root["airfoil"] == RV7_ROOT_AIRFOIL[1]
        root["airfoil"] = RV7_ROOT_AIRFOIL[0]
    assert canonical_sha256(document) == SOURCE_CANONICAL_SHA256[member]


def test_the_avistar_copy_is_what_its_generator_builds() -> None:
    """The validation aircraft's source is a script that names the origin of every number."""
    path = (
        REFERENCE_DIR.parents[1]
        / "scripts/canon_checks/reference_fleet/avistar_elite/build_document.py"
    )
    spec = importlib.util.spec_from_file_location("build_avistar_elite", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.document() == json.loads(FleetMember.AVISTAR_ELITE.json_path.read_text())


@pytest.mark.parametrize(("name", "digest"), sorted(AIRFOIL_SHA256.items()))
def test_the_airfoil_files_are_byte_identical_copies(name: str, digest: str) -> None:
    assert hashlib.sha256((REFERENCE_DIR / name).read_bytes()).hexdigest() == digest


@pytest.mark.parametrize("member", list(FleetMember))
def test_every_airfoil_path_resolves_into_inline_selig_coordinates(member: FleetMember) -> None:
    document = reference_document(member)
    for wing in document["wings"].values():
        for section in wing["x_secs"]:
            coordinates = section["airfoil"]["coordinates"]
            assert len(coordinates) > 20
            xs = [x for x, _ in coordinates]
            assert abs(xs[0] - 1.0) < 1e-3  # Selig order starts at the trailing edge
            assert abs(min(xs)) < 1e-3
            assert max(xs) <= 1.0 + 1e-6


def test_the_masses_are_the_recorded_ones() -> None:
    assert FleetMember.BRYAN.mass_kg == 0.151  # total_mass_kg of the source
    assert FleetMember.JAGUAR.mass_kg == 0.160  # approx., maintainer 2026-10-14
    assert json.loads(FleetMember.JAGUAR.json_path.read_text())["total_mass_kg"] is None
    assert FleetMember.CHEKKER.mass_kg == 0.439  # total_mass_kg of the source
    assert json.loads(FleetMember.CHEKKER.json_path.read_text())["total_mass_kg"] == 0.439
    # estimated total mass, maintainer 2026-10-26; exact value after the build: equal to the source's
    assert FleetMember.BELEMNITOS.mass_kg == 0.280
    assert json.loads(FleetMember.BELEMNITOS.json_path.read_text())["total_mass_kg"] == 0.28
    assert FleetMember.WIESEL.mass_kg == 0.625  # aeroplanes.total_mass_kg of the app DB
    assert "total_mass_kg" not in json.loads(FleetMember.WIESEL.json_path.read_text())

    assert FleetMember.RV7.mass_kg == 0.500  # approx., maintainer 2026-10-25
    # the export carries no mass, so there is nothing to conflict with
    assert "total_mass_kg" not in json.loads(FleetMember.RV7.json_path.read_text())
    # flaps without a deflection in the DB: the maintainer's guess, 2026-10-26
    assert FLAP_DEFLECTIONS_DEG == {
        FleetMember.RV7: {"flap-deflection-takeoff": 15.0, "flap-deflection-landing": 30.0}
    }


# The plan batch's masses (maintainer, 2026-11-07; each source in the README). They equal the DB's
# total_mass_kg, which the export serves as null (#1147), so the copies carry none.
PLAN_BATCH_MASS_KG = {
    FleetMember.A6M2_ZERO: 0.36,
    FleetMember.AERONCA_CHAMP: 0.39,
    FleetMember.ALBATROS_4: 5.0,
    FleetMember.BARRACUDA: 1.54,
    FleetMember.BF109_E: 0.36,
    FleetMember.D520_DEWOITINE: 0.36,
    FleetMember.DARDO: 1.35,
    FleetMember.ESTRELA: 1.7,
    FleetMember.EXTRA_300_EP: 0.75,
    FleetMember.F3A_COMPETICION: 4.7,
    FleetMember.FORCE_5: 1.22,
    FleetMember.FORCE_FOUR: 0.68,
    FleetMember.FW190_A8: 0.35,
    FleetMember.GEE_BEE_R3: 12.0,
    FleetMember.KASTAWAY: 0.65,
    FleetMember.MILES_MAGISTER: 0.36,
    FleetMember.MINI_FUNTANA: 0.539,
    FleetMember.P36_HAWK: 0.36,
    FleetMember.P39: 9.5,
    FleetMember.SNOOPY: 1.474,
    FleetMember.SONAS_40: 2.1,
    FleetMember.SPIRIT_100: 1.26,
    FleetMember.SPRITE: 1.0,
    FleetMember.SUPER_TRIDENT: 1.05,
    FleetMember.ULTRA_MINI_STICK: 0.35,
    FleetMember.VOODOO: 1.16,
    FleetMember.WINDFREAK: 2.6,
    FleetMember.WRISTOCRAT: 0.34,
}


@pytest.mark.parametrize("member", PLAN_BATCH)
def test_the_plan_batch_masses_are_the_settled_ones(member: FleetMember) -> None:
    assert member.mass_kg == PLAN_BATCH_MASS_KG[member]
    assert "total_mass_kg" not in json.loads(member.json_path.read_text())


def test_the_readme_records_every_hash_the_tests_check() -> None:
    readme = Path(REFERENCE_DIR / "README.md").read_text()
    for digest in (*SOURCE_CANONICAL_SHA256.values(), *AIRFOIL_SHA256.values()):
        assert digest in readme


@pytest.mark.parametrize("member", list(FleetMember))
def test_a_reference_aircraft_parses_and_is_admissible(member: FleetMember) -> None:
    aircraft = AircraftInput.model_validate(
        {"airplane": reference_document(member), "values": {"aircraft-mass": member.mass_kg}}
    )
    assert validate_aircraft(aircraft).errors == ()

"""Repro without DB: e-Hawk WingConfiguration -> app import converters -> ASB control surfaces."""

import json
from app.schemas.wing import Wing as WingConfigurationSchema
from app.services.create_wing_configuration import create_wing_configuration
from app.converters.model_schema_converters import (
    wing_config_to_asb_wing_schema,
    _asb_wing_xsecs_from_schema,
)

wc = WingConfigurationSchema(
    **json.load(open(__import__("pathlib").Path(__file__).with_name("e-Hawk_wingconfig.json")))
)
cfg = create_wing_configuration(wc)
schema = (
    wing_config_to_asb_wing_schema(cfg, wing_name="main", scale=0.001)
    if "wing_name" in wing_config_to_asb_wing_schema.__code__.co_varnames
    else wing_config_to_asb_wing_schema(cfg)
)
for i, x in enumerate(schema.x_secs):
    cs = x.control_surface
    if cs:
        print(i, "schema:", cs.name, "symmetric", cs.symmetric)
for i, xs in enumerate(_asb_wing_xsecs_from_schema(schema)):
    for c in xs.control_surfaces:
        print(i, "ASB:", c.name, "symmetric", c.symmetric)

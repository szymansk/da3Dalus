from typing import Annotated, Literal

from pydantic import confloat, Field, BeforeValidator

Factor = confloat(ge=0, le=1.0)

CoordinateSystemBase = Annotated[
    Literal["world","wing","root_airfoil","tip_airfoil"],
    Field(description="Allowed values are 'world','wing','root_airfoil' or 'tip_airfoil'"),
    BeforeValidator(lambda x: x.lower() if isinstance(x, str) else x)
]

WingSegmentType = Annotated[
    Literal['root','segment','tip'],
    Field(description="Allowed values are 'ROOT', 'SEGMENT' or 'TIP'"),
    BeforeValidator(lambda x: x.lower() if isinstance(x, str) else x)
]

TipType = Annotated[
    Literal["flat", "round"],
    Field(description="Allowed values are 'flat' or 'round'"),
    BeforeValidator(lambda x: x.lower() if isinstance(x, str) else x)
]

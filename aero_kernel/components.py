"""The fitted components: motor, battery and propeller, pushed by the caller (ARCHITECTURE ch. 8.11).

A contract of its own, separate from the geometry format. Field names and units are the
catalogue's (the component types ``brushless_motor``, ``battery`` and ``propeller``), so the
caller pushes what the catalogue holds. A value the catalogue does not have arrives **absent**
(``None``): the kernel never fills, estimates or defaults it (ARCHITECTURE "Components", rule 3).
Types and structure only; physical admissibility is ``validate.py``'s.

The propeller's measured table (``C_T(J)``, ``C_P(J)`` per rpm block) is added with
``propeller-table-lookup`` and a new ``schema_version``.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["Battery", "Chemistry", "Components", "Motor", "Propeller"]

Number = Annotated[float, Field(strict=True)]

# The closed list of the catalogue's ``battery.chemistry`` enumeration.
Chemistry = Literal["lipo", "lihv", "life", "li_ion", "nimh"]


class Motor(BaseModel):
    """The brushless motor (catalogue type ``brushless_motor``).

    Attributes:
        kv_rpm_per_volt: Voltage constant ``K_v`` in rpm/V (required by the catalogue).
        max_power_w: The manufacturer's power rating in W.
        io_no_load_a: No-load current ``I_0`` in A.
        rm_ohm: Winding resistance ``R_m`` in ohm.
        efficiency_pct: The efficiency the manufacturer publishes, in percent (0 to 100).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    kv_rpm_per_volt: Number
    max_power_w: Number | None = None
    io_no_load_a: Number | None = None
    rm_ohm: Number | None = None
    efficiency_pct: Number | None = None


class Battery(BaseModel):
    """The battery pack (catalogue type ``battery``).

    Attributes:
        capacity_mah: Charge in mAh (required by the catalogue).
        cells: Number of cells in series (required by the catalogue).
        mass_g: Mass in g.
        c_rate: Continuous C-rate in 1/h.
        cell_voltage_v: Nominal voltage of one cell in V, from the datasheet.
        chemistry: The cell chemistry.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    capacity_mah: Number
    cells: Number
    mass_g: Number | None = None
    c_rate: Number | None = None
    cell_voltage_v: Number | None = None
    chemistry: Chemistry | None = None


class Propeller(BaseModel):
    """The propeller (catalogue type ``propeller``).

    Attributes:
        diameter_in: Diameter in inches (required by the catalogue).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    diameter_in: Number


class Components(BaseModel):
    """The fitted components of one aircraft; ``AircraftInput.components`` (canon type ``components``).

    Attributes:
        schema_version: Version of this contract; the kernel accepts only ``1``.
        motor: The motor, or ``None`` if the aircraft has none pushed.
        battery: The battery, or ``None``.
        propeller: The propeller, or ``None``.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1]
    motor: Motor | None = None
    battery: Battery | None = None
    propeller: Propeller | None = None

"""The fitted components: motor, battery and propeller, pushed by the caller (ARCHITECTURE ch. 8.11).

A contract of its own, separate from the geometry format. Field names and units are the
catalogue's (the component types ``brushless_motor``, ``battery`` and ``propeller``), so the
caller pushes what the catalogue holds. A value the catalogue does not have arrives **absent**
(``None``): the kernel never fills, estimates or defaults it (ARCHITECTURE "Components", rule 3).
Types and structure only; physical admissibility is ``validate.py``'s.

The propeller's performance table (``C_T(J)``, ``C_P(J)`` per rpm block, APC's PER3 data) came
with ``propeller-table-lookup`` and ``schema_version`` 2. The caller pushes the table; the kernel
reads no file.

The materials table (``materials``, ``schema_version`` 3, gh-1427) holds what the spar capacity
reads of a material: its published breaking strength in bending, with its source. It is pushed
like the motor: a value the catalogue lacks is absent, never defaulted. The key of a material is a
plain name that the geometry's spars refer to, not a storage id.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = [
    "Battery",
    "Chemistry",
    "Components",
    "Material",
    "Motor",
    "Propeller",
    "PropellerTable",
    "RpmBlock",
]

SCHEMA_VERSION = 3  # the version of this contract

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


class RpmBlock(BaseModel):
    """One rpm block of the propeller table: the coefficients over the advance ratio at one speed.

    The three lists have one entry per tabulated point and the same length (checked by
    ``validate.py``). Names follow the catalogue's propeller polars (``J``, ``Ct``, ``Cp``).

    Attributes:
        rpm: The propeller speed of the block in rpm.
        j: Advance ratio ``J = V / (n D)`` of each point (1), increasing.
        ct: Thrust coefficient ``C_T = T / (rho n^2 D^4)`` of each point (1).
        cp: Power coefficient ``C_P = P / (rho n^3 D^5)`` of each point (1).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    rpm: Number
    j: tuple[Number, ...]
    ct: tuple[Number, ...]
    cp: tuple[Number, ...]


class PropellerTable(BaseModel):
    """The propeller's performance table: every rpm block of the data, never a reduced curve.

    Attributes:
        blocks: The rpm blocks, increasing in ``rpm``.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    blocks: tuple[RpmBlock, ...]


class Propeller(BaseModel):
    """The propeller (catalogue type ``propeller``).

    Attributes:
        diameter_in: Diameter in inches (required by the catalogue).
        table: The performance table, or ``None`` if none is pushed (``propeller-table-lookup`` is
            then ``missing_input``).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    diameter_in: Number
    table: PropellerTable | None = None


class Material(BaseModel):
    """A structural material (catalogue type ``material``), as the spar capacity reads it.

    The strength is the **published breaking strength in bending**, as the source states it: no
    safety, resistance or knock-down factor is folded into it, and the kernel applies none
    (maintainer, 2026-11-19, gh-1427). An already reduced allowable must not be pushed here.

    Attributes:
        name: Display name of the material.
        bending_strength_pa: Breaking strength in bending in Pa, or ``None`` if the catalogue has
            none (a spar of this material then has no capacity: ``spar_material_without_strength``).
        density_kg_m3: Density in kg/m^3.
        source: Where the strength and the density come from, as free text.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    bending_strength_pa: Number | None = None
    density_kg_m3: Number | None = None
    source: str | None = None


class Components(BaseModel):
    """The fitted components of one aircraft; ``AircraftInput.components`` (canon type ``components``).

    Attributes:
        schema_version: Version of this contract; the kernel accepts only ``3``.
        motor: The motor, or ``None`` if the aircraft has none pushed.
        battery: The battery, or ``None``.
        propeller: The propeller, or ``None``.
        materials: The materials by key (the name the geometry's spars refer to), or ``None`` if
            none are pushed.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[3]

    @field_validator("schema_version", mode="before")
    @classmethod
    def _supported_version(cls, value: object) -> object:
        """Refuse another version with a message that names the contract."""
        if value != SCHEMA_VERSION:
            msg = (
                f"components schema_version {value!r} is not supported: this kernel accepts "
                f"version {SCHEMA_VERSION} (version 2 added the propeller performance table "
                "`propeller.table`, version 3 the materials table `materials`; an older document "
                "is re-pushed with its schema_version raised, nothing else changes)"
            )
            raise ValueError(msg)
        return value

    motor: Motor | None = None
    battery: Battery | None = None
    propeller: Propeller | None = None
    materials: dict[str, Material] | None = None

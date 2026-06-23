"""Carbon-fibre tube stock validator for the COTS import pipeline (gh-1081).

Validates ``spar_tube`` component records before they reach ``import_snapshot``.
A ``spar_tube`` is a purchasable carbon-fibre tube or rod that the spar-build
workflow (#1080) can snap to.

Key domain rules (spec validation comment in gh-1081):
- Properties are keyed on **fiber orientation** (UD-axial / 0/90 / ±45), not
  on process name.  Process is metadata only.
- σ_allow must be an **allowable** (≤ R_m / SF, SF ≥ 1.5), not the ultimate.
  Woven 0/90 tubes have materially lower σ_allow than UD pultruded.
- **Physical-bounds guard:** σ_allow ∈ [10, 1500] MPa, E ∈ [3, 250] GPa,
  ρ ∈ [100, 2800] kg/m³  (Sadraey Table 10.6 + RC practice).
- **Conical tubes** (outer_d_mm=None, inner_d_mm=None) are geometry-incomplete
  and must NOT emit a bending allowable (geometry_complete=False).
- **role_use** (spar | boom | pushrod | shaft) lets #1080 filter non-spar parts.
- Every σ_allow / E value must carry a citation in ``sigma_allow_basis`` /
  ``e_basis`` (provenance requirement).
- E is currently **dead data** in the sizing path (spar_sizing.py only reads
  allowable_bending_stress_mpa + density_kg_m3); stored for future
  buckling/deflection consumers.  Scope is data-only for this ticket.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_VALID_ROLE_USE = {"spar", "boom", "pushrod", "shaft"}

# Physical-bounds guard (Sadraey Table 10.6 + RC materials practice)
_SIGMA_ALLOW_MIN_MPA = 10.0
_SIGMA_ALLOW_MAX_MPA = 1500.0
_E_MIN_GPA = 3.0
_E_MAX_GPA = 250.0
_RHO_MIN_KGM3 = 100.0
_RHO_MAX_KGM3 = 2800.0


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


def validate_spar_tube_record(record: dict[str, Any]) -> str | None:
    """Validate a spar_tube snapshot record.

    Returns an error string if the record is invalid, else ``None``.

    Parameters
    ----------
    record:
        Dict in the spar_tube snapshot format (see data/cots/carbon_tubes.json).

    Returns
    -------
    str | None
        Human-readable error description, or ``None`` if the record is valid.
    """
    specs = record.get("specs") or {}
    name = record.get("name", "?")

    # --- required top-level fields ---
    for key in ("manufacturer", "name", "component_type"):
        if not record.get(key):
            return f"'{name}': missing required field '{key}'"

    # --- fiber_orientation required (the primary load-bearing parameter) ---
    fo = specs.get("fiber_orientation")
    if not fo:
        return f"'{name}': missing required specs.fiber_orientation"

    # --- role_use required and must be a known value ---
    role = specs.get("role_use")
    if not role:
        return f"'{name}': missing required specs.role_use"
    if role not in _VALID_ROLE_USE:
        return (
            f"'{name}': invalid specs.role_use={role!r}; must be one of {sorted(_VALID_ROLE_USE)}"
        )

    # --- geometry completeness ---
    geometry_complete = specs.get("geometry_complete", True)
    if geometry_complete:
        # Sizing-usable tubes must declare their cross-section
        if specs.get("outer_d_mm") is None:
            return f"'{name}': specs.outer_d_mm required when geometry_complete=True"
        # Provenance required for σ_allow when geometry is known
        sigma = specs.get("allowable_bending_stress_mpa")
        if sigma is not None:
            basis = specs.get("sigma_allow_basis")
            if not basis:
                return (
                    f"'{name}': specs.sigma_allow_basis (provenance citation) required "
                    "when allowable_bending_stress_mpa is set"
                )

    # --- physical-bounds guard ---
    sigma = specs.get("allowable_bending_stress_mpa")
    if sigma is not None:
        if sigma < _SIGMA_ALLOW_MIN_MPA or sigma > _SIGMA_ALLOW_MAX_MPA:
            return (
                f"'{name}': specs.allowable_bending_stress_mpa={sigma} MPa out of valid "
                f"range [{_SIGMA_ALLOW_MIN_MPA}, {_SIGMA_ALLOW_MAX_MPA}] MPa"
            )

    e_gpa = specs.get("youngs_modulus_gpa")
    if e_gpa is not None:
        if e_gpa < _E_MIN_GPA or e_gpa > _E_MAX_GPA:
            return (
                f"'{name}': specs.youngs_modulus_gpa={e_gpa} GPa out of valid "
                f"range [{_E_MIN_GPA}, {_E_MAX_GPA}] GPa"
            )

    rho = specs.get("density_kg_m3")
    if rho is not None:
        if rho < _RHO_MIN_KGM3 or rho > _RHO_MAX_KGM3:
            return (
                f"'{name}': specs.density_kg_m3={rho} kg/m³ out of valid "
                f"range [{_RHO_MIN_KGM3}, {_RHO_MAX_KGM3}] kg/m³"
            )

    return None

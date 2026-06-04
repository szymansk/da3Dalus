"""Regression test for gh-624: ``trim_with_aerobuildup`` must validate
``operating_point.control_deflections`` against the actual airplane's
``ControlSurface.name`` set, otherwise stale keys (e.g. ``elevator``
after a rename to ``elev_pitch``) get silently dropped by AeroSandbox
and the OP is marked ``TRIMMED`` on a deflection set that no longer
applies.

The fix puts the guard inside ``trim_with_aerobuildup`` so both call
sites — endpoint handlers AND the background ``retrim_dirty_ops`` —
benefit. We test by injecting an OP with a known-stale deflection
key and asserting a ``ValidationDomainError`` with the expected list
of unknown surfaces.
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

from app.core.exceptions import ValidationDomainError
from app.tests.conftest import make_aeroplane


def _run(coro):
    return asyncio.run(coro)


def _build_aeroplane_with_elevator(db, name: str = "trim-validate"):
    """Build a minimal aeroplane with a wing + a TED named ``elevator``
    so that the airplane has exactly one control surface."""
    from app.models.aeroplanemodel import (
        WingModel,
        WingXSecModel,
        WingXSecDetailModel,
        WingXSecTrailingEdgeDeviceModel,
    )

    aeroplane = make_aeroplane(db, name=name)
    wing = WingModel(name="h-stab", aeroplane_id=aeroplane.id, symmetric=True)
    db.add(wing)
    db.flush()
    for i, x in enumerate([0.0, 0.5]):
        xsec = WingXSecModel(
            wing_id=wing.id,
            xyz_le=[0, x, 0],
            chord=0.2,
            twist=0.0,
            airfoil="naca0012",
            sort_index=i,
        )
        db.add(xsec)
        db.flush()
        if i == 0:  # The TED lives on the root xsec.
            detail = WingXSecDetailModel(wing_xsec_id=xsec.id)
            db.add(detail)
            db.flush()
            ted = WingXSecTrailingEdgeDeviceModel(
                wing_xsec_detail_id=detail.id,
                name="elevator",
                role="elevator",
            )
            db.add(ted)
    db.commit()
    return aeroplane


def test_trim_raises_when_op_has_unknown_deflection_keys(client_and_db):
    """The fix: ``trim_with_aerobuildup`` rejects an OP whose stored
    ``control_deflections`` reference surfaces that don't exist."""
    _, SessionLocal = client_and_db
    db = SessionLocal()
    aeroplane = _build_aeroplane_with_elevator(db, name="stale-deflections")

    from app.schemas.aeroanalysisschema import (
        AeroBuildupTrimRequest,
        OperatingPointSchema,
    )

    op_schema = OperatingPointSchema(
        velocity=30.0,
        alpha=2.0,
        beta=0.0,
        p=0.0,
        q=0.0,
        r=0.0,
        altitude=500.0,
        xyz_ref=[0.0, 0.0, 0.0],
        # Stale name — geometry has "elevator" but the OP was trimmed
        # before a rename and still references "elev_pitch".
        control_deflections={"elev_pitch": -2.5},
    )
    request = AeroBuildupTrimRequest(
        operating_point=op_schema,
        trim_variable="elevator",
        target_coefficient="Cm",
        target_value=0.0,
    )

    from app.services.aerobuildup_trim_service import trim_with_aerobuildup

    with pytest.raises(ValidationDomainError) as exc_info:
        _run(trim_with_aerobuildup(db, aeroplane.uuid, request))

    msg = str(exc_info.value)
    assert "elev_pitch" in msg
    # Validator lists the surfaces available on the airplane so the
    # user sees what's expected.
    assert "elevator" in msg
    db.close()


def test_trim_passes_when_op_has_no_deflections(client_and_db):
    """No-op when ``control_deflections`` is empty — the validator must
    not error out. We mock the aero solver so the test stays fast and
    doesn't depend on a working AeroBuildup compute."""
    _, SessionLocal = client_and_db
    db = SessionLocal()
    aeroplane = _build_aeroplane_with_elevator(db, name="empty-deflections")

    from app.schemas.aeroanalysisschema import (
        AeroBuildupTrimRequest,
        OperatingPointSchema,
    )

    op_schema = OperatingPointSchema(
        velocity=30.0,
        alpha=2.0,
        beta=0.0,
        p=0.0,
        q=0.0,
        r=0.0,
        altitude=500.0,
        xyz_ref=[0.0, 0.0, 0.0],
        control_deflections=None,
    )
    request = AeroBuildupTrimRequest(
        operating_point=op_schema,
        trim_variable="elevator",
        target_coefficient="Cm",
        target_value=0.0,
    )

    # Mock the inner aero call so the test stays quick. We only care
    # that the validator doesn't reject an empty dict.
    with patch(
        "app.services.aerobuildup_trim_service._run_single_aerobuildup",
        return_value={"Cm": 0.0, "CL": 0.4, "CD": 0.03},
    ):
        from app.services.aerobuildup_trim_service import trim_with_aerobuildup

        result = _run(trim_with_aerobuildup(db, aeroplane.uuid, request))
        assert result is not None  # got past the validator + ran the mocked solver
    db.close()

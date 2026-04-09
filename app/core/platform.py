"""Platform capability probes and dependency guards.

CadQuery and Aerosandbox are intentionally excluded on linux/aarch64 via
environment markers in pyproject.toml. Any endpoint that transitively
imports them would 500 with an opaque ``ModuleNotFoundError`` when
called on such a platform. Use the helpers in this module to detect
capability at module import time and to return a clean HTTP 503 from
affected endpoints.

Typical use in an endpoint::

    from fastapi import Depends
    from app.core.platform import require_cad

    @router.post("/aeroplanes/{id}/wings/{name}/stl", dependencies=[Depends(require_cad)])
    async def export_wing_stl(...): ...

The probes are cached at module-load time — they do not retry — so a
broken install detected once stays broken for the life of the process.
"""

from __future__ import annotations

from functools import lru_cache

from fastapi import HTTPException, status


@lru_cache(maxsize=1)
def cad_available() -> bool:
    """Return True if CadQuery can be imported on this interpreter."""
    try:
        import cadquery  # noqa: F401
    except ImportError:
        return False
    return True


@lru_cache(maxsize=1)
def aerosandbox_available() -> bool:
    """Return True if Aerosandbox can be imported on this interpreter."""
    try:
        import aerosandbox  # noqa: F401
    except ImportError:
        return False
    return True


def require_cad() -> None:
    """FastAPI dependency that gates endpoints on CadQuery availability.

    Raises HTTPException 503 with a clear message if CadQuery is missing.
    """
    if not cad_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CAD backend (CadQuery) is not available on this platform.",
        )


def require_aerosandbox() -> None:
    """FastAPI dependency that gates endpoints on Aerosandbox availability."""
    if not aerosandbox_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Aerodynamic backend (Aerosandbox) is not available on this platform.",
        )

import logging
import os

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.docs import get_swagger_ui_html, get_swagger_ui_oauth2_redirect_html
from fastapi.responses import JSONResponse

from app.api.v2.endpoints import aeroplane as aeroplane_v2
from app.api.v2.endpoints import flight_profiles
from app.api.v2.endpoints import health
from app.core.platform import aerosandbox_available, cad_available

# Heavy routers that transitively import CadQuery / Aerosandbox are loaded
# behind capability probes. On platforms where those libraries are excluded
# (linux/aarch64 per pyproject.toml markers) the affected routers are not
# registered; the service still starts and /health still answers.
_cad_router = None
_aeroanalysis_router = None
_operating_points_router = None
_airfoils_router = None

if cad_available():
    try:
        from app.api.v2.endpoints import cad as _cad_module
        _cad_router = _cad_module.router
    except ImportError as exc:
        logging.getLogger(__name__).warning("cad router unavailable: %s", exc)

if aerosandbox_available():
    try:
        from app.api.v2.endpoints import aeroanalysis as _aeroanalysis_module
        _aeroanalysis_router = _aeroanalysis_module.router
    except ImportError as exc:
        logging.getLogger(__name__).warning("aeroanalysis router unavailable: %s", exc)

    try:
        from app.api.v2.endpoints import operating_points as _operating_points_module
        _operating_points_router = _operating_points_module.router
    except ImportError as exc:
        logging.getLogger(__name__).warning("operating_points router unavailable: %s", exc)

    try:
        from app.api.v2.endpoints import airfoils as _airfoils_module
        _airfoils_router = _airfoils_module.router
    except ImportError as exc:
        logging.getLogger(__name__).warning("airfoils router unavailable: %s", exc)
from app.mcp_server import create_mcp_http_app
from app.core.exceptions import (
    ServiceException,
    NotFoundError,
    ValidationError,
    ValidationDomainError,
    ConflictError,
    InternalError,
)
from sqlalchemy.exc import IntegrityError
from app.logging_config import setup_logging

from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles


setup_logging()


def create_app() -> FastAPI:
    mcp_app = create_mcp_http_app(path="/")

    app = FastAPI(
        title="da3dalus Model Context Protocol (v2)",
        version="2.0.0",
        openapi_url="/openapi.json",   # served at /api/v2/openapi.json
        docs_url=None,                 # custom route below with custom favicon
        redoc_url="/redoc",            # served at /api/v2/redoc
        lifespan=mcp_app.lifespan,
    )
    app.include_router(health.router, prefix="", tags=["health"])
    app.include_router(aeroplane_v2.router, prefix="", tags=[])
    app.include_router(flight_profiles.router, prefix="", tags=["flight-profiles"])
    if _cad_router is not None:
        app.include_router(_cad_router, prefix="", tags=["cad"])
    if _aeroanalysis_router is not None:
        app.include_router(_aeroanalysis_router, prefix="", tags=[])
    if _operating_points_router is not None:
        app.include_router(_operating_points_router, prefix="", tags=["operating_points"])
    if _airfoils_router is not None:
        app.include_router(_airfoils_router, prefix="", tags=["airfoils"])

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], # copied from other python backends to resolve the cors origin problem
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Ensure tmp directory exists
    os.makedirs("tmp", exist_ok=True)

    # Mount static files
    app.mount("/static", StaticFiles(directory="tmp"), name="static")
    app.mount("/assets", StaticFiles(directory="app/static"), name="assets")
    app.mount("/mcp", mcp_app)

    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=f"{app.title} - Swagger UI",
            swagger_favicon_url="/assets/swagger-favicon.svg",
            oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
            swagger_ui_parameters=app.swagger_ui_parameters,
        )

    @app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
    async def swagger_ui_redirect():
        return get_swagger_ui_oauth2_redirect_html()

    return app


app = create_app()


def _safe_json(value):
    return jsonable_encoder(value, custom_encoder={BaseException: lambda e: str(e)})


# Global exception handler for ServiceException hierarchy
@app.exception_handler(ServiceException)
async def service_exception_handler(request: Request, exc: ServiceException):
    """Translate service exceptions to HTTP responses."""
    if isinstance(exc, NotFoundError):
        status_code = 404
        error_code = "not_found"
        logging.getLogger(__name__).info("4xx NotFound: %s", exc.details)
    elif isinstance(exc, (ValidationError, ValidationDomainError)):
        status_code = 422
        error_code = "validation_error"
        logging.getLogger(__name__).info("4xx Validation: %s", exc.details)
    elif isinstance(exc, ConflictError):
        status_code = 409
        error_code = "conflict"
        logging.getLogger(__name__).info("4xx Conflict: %s", exc.details)
    elif isinstance(exc, InternalError):
        status_code = 500
        error_code = "internal_error"
        logging.getLogger(__name__).exception("5xx InternalError")
    else:
        status_code = 500
        error_code = "service_error"
        logging.getLogger(__name__).exception("5xx ServiceException")

    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": error_code,
                "message": exc.message,
                "details": _safe_json(exc.details) if exc.details else None,
            }
        },
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=409,
        content={
            "error": {
                "code": "conflict",
                "message": "name existiert bereits",
                "details": None,
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    details = _safe_json(exc.errors())
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": "Ungültige Eingabedaten",
                "details": details,
            }
        },
    )


import uvicorn
def run_app(entry_point:str = "app.main:app", port:int = 8000):
    uvicorn.run(entry_point, host="0.0.0.0", port=port, reload=True)

if __name__ == "__main__":
    run_app()

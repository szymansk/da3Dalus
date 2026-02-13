import os

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.v1.endpoints import aeroplane as health
from app.api.v2.endpoints import aeroplane as aeroplane_v2
from app.api.v2.endpoints import cad, aeroanalysis, operating_points
from app.api.v2.endpoints import flight_profiles
from app.core.exceptions import (
    ServiceException,
    NotFoundError,
    ValidationError,
    ValidationDomainError,
    ConflictError,
    InternalError,
)
from sqlalchemy.exc import IntegrityError
import logging
from app.logging_config import setup_logging

from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles


setup_logging()

app = FastAPI(
    title="da3dalus Model Context Protocol (v2)",
    version="2.0.0",
    openapi_url="/openapi.json",   # served at /api/v2/openapi.json
    docs_url="/docs",              # served at /api/v2/docs
    redoc_url="/redoc",            # served at /api/v2/redoc
)
app.include_router(aeroplane_v2.router, prefix="", tags=[])
app.include_router(cad.router, prefix="", tags=["cad"])
app.include_router(aeroanalysis.router, prefix="", tags=["aeroanalysis"])
app.include_router(operating_points.router, prefix="", tags=["operating_points"])
app.include_router(flight_profiles.router, prefix="", tags=["flight-profiles"])

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

app.include_router(health.router, tags=["health"])


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

import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.v1.endpoints import aeroplane as health
from app.api.v2.endpoints import aeroplane as aeroplane_v2
from app.api.v2.endpoints import cad, aeroanalysis, operating_points
from app.core.exceptions import (
    ServiceException,
    NotFoundError,
    ValidationError,
    ConflictError,
    InternalError,
)
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


# Global exception handler for ServiceException hierarchy
@app.exception_handler(ServiceException)
async def service_exception_handler(request: Request, exc: ServiceException):
    """Translate service exceptions to HTTP responses."""
    if isinstance(exc, NotFoundError):
        status_code = 404
        error_type = "not_found"
    elif isinstance(exc, ValidationError):
        status_code = 422
        error_type = "validation_error"
    elif isinstance(exc, ConflictError):
        status_code = 409
        error_type = "conflict"
    elif isinstance(exc, InternalError):
        status_code = 500
        error_type = "internal_error"
    else:
        status_code = 500
        error_type = "service_error"
    
    return JSONResponse(
        status_code=status_code,
        content={
            "error": error_type,
            "message": exc.message,
            "details": exc.details,
        },
    )


import uvicorn
def run_app(entry_point:str = "app.main:app", port:int = 8000):
    uvicorn.run(entry_point, host="0.0.0.0", port=port, reload=True)

if __name__ == "__main__":
    run_app()

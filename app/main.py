import os

from fastapi import FastAPI

from app.api.v1.endpoints import aeroplane as health
from app.api.v2.endpoints import aeroplane as aeroplane_v2
from app.api.v2.endpoints import cad, aeroanalysis, operating_points
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

import uvicorn
def run_app(entry_point:str = "app.main:app", port:int = 8000):
    uvicorn.run(entry_point, host="0.0.0.0", port=port, reload=True)

if __name__ == "__main__":
    run_app()

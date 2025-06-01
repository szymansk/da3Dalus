
from fastapi import FastAPI
from app.api.v1.endpoints import aeroplane as aeroplane_v1, health
from app.api.v2.endpoints import aeroplane as aeroplane_v2
from app.api.v2.endpoints import cad, aeroanalysis, operating_points

import uvicorn

from fastapi.middleware.cors import CORSMiddleware

# 1️⃣ Create a “root” app with docs disabled
app = FastAPI(
    title="da3dalus CAD-Service (root)",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# 2️⃣ Create the v1 sub-app
app_v1 = FastAPI(
    title="da3dalus CAD-Service (v1)",
    version="1.0.0",
    openapi_url="/openapi.json",   # served at /api/v1/openapi.json
    docs_url="/docs",              # served at /api/v1/docs
    redoc_url="/redoc",            # served at /api/v1/redoc
)
app_v1.include_router(aeroplane_v1.router, prefix="", tags=["aeroplane"])

# 3️⃣ Create the v2 sub-app
app_v2 = FastAPI(
    title="da3dalus Model Context Protocol (v2)",
    version="2.0.0",
    openapi_url="/openapi.json",   # served at /api/v2/openapi.json
    docs_url="/docs",              # served at /api/v2/docs
    redoc_url="/redoc",            # served at /api/v2/redoc
)
app_v2.include_router(aeroplane_v2.router, prefix="", tags=["aeroplane"])
app_v2.include_router(cad.router, prefix="", tags=["cad"])
app_v2.include_router(aeroanalysis.router, prefix="", tags=["aeroanalysis"])

app_v2.include_router(operating_points.router, prefix="", tags=["operating_points"])

# 4️⃣ Mount both under your root
app.mount("/api/v1", app_v1)
app.mount("/api/v2", app_v2)

# cors-origin problem with configurator

# origins = [
#     "http://localhost",
#     "http://localhost:8085",
# ]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # copied from other python backends to resolve the cors origin problem
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
#app.include_router(aeroplane.router, prefix="/api/v1", tags=["aeroplane"])

#app.include_router(aeroplane_v2.router, prefix="/api/v2", tags=["v2", "aeroplane"])

if __name__ == '__main__':
    uvicorn.run("main:app", host='0.0.0.0', port=8000, reload=True)

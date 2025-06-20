
from fastapi import FastAPI
from fastapi_mcp import FastApiMCP
from sqlalchemy.testing.plugin.plugin_base import include_tags

from app.api.v1.endpoints import aeroplane as aeroplane_v1, health
from app.api.v2.endpoints import aeroplane as aeroplane_v2
from app.api.v2.endpoints import cad, aeroanalysis, operating_points

from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

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

# Add the MCP server to your FastAPI app
mcp = FastApiMCP(
    app,
    name="My API MCP",  # Name for your MCP server
    description="MCP server for my API",  # Description
    describe_all_responses = True,  # Include all possible response schemas
    describe_full_response_schema = True,  # Include full JSON schema in descriptions
)

# Mount the MCP server to your FastAPI app
mcp.mount()

app_analysis_tools = FastAPI()
mcp_analysis_tools = FastApiMCP(
    app,
    name="My API MCP",  # Name for your MCP server
    description="MCP server for my API",  # Description
    describe_all_responses = True,  # Include all possible response schemas
    describe_full_response_schema = True,  # Include full JSON schema in descriptions
    #include_tags=["analysis"]
)

#mcp_analysis_tools.mount(app_analysis_tools)

def run_app(entry_point:str = "main:app", port:int = 8000):
    uvicorn.run(entry_point, host="0.0.0.0", port=port, reload=True)

import multiprocessing
import uvicorn
if __name__ == "__main__":
    process_app = multiprocessing.Process(target=run_app, args=("app.main:app", 8000))
 #   process_analysis_tools = multiprocessing.Process(target=run_app, args=("app.main:app_analysis_tools", 8001))

    process_app.start()
#    process_analysis_tools.start()

    process_app.join()
#    process_analysis_tools.join()

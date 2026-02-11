"""
FastMCP 2.x Server for da3Dalus CAD Modelling Service.
"""

from fastmcp import FastMCP


def create_mcp_server() -> FastMCP:
    """Create MCP server from FastAPI app."""
    from app.main import app as fastapi_app
    mcp = FastMCP.from_fastapi(app=fastapi_app, name="da3dalus-cad-tools")

    
    return mcp


mcp: FastMCP | None = None

def get_mcp() -> FastMCP:
    global mcp
    if mcp is None:
        mcp = create_mcp_server()
    return mcp

def run_mcp_server():
    """Start the FastMCP server as a separate process."""
    mcp = get_mcp()
    mcp.run(transport="http", host="0.0.0.0", port=8001, path="/mcp")

mcp = get_mcp()
if __name__ == "__main__":
    run_mcp_server()
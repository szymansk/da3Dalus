"""gh-1187: the MCP wing tools carry the wing role."""

import asyncio

import app.mcp_server as mcp_server


def _tools() -> dict:
    server = mcp_server.create_mcp_server()
    return {tool.name: tool for tool in asyncio.run(server.list_tools())}


def test_set_surface_type_tool_is_registered() -> None:
    assert "set_aeroplane_wing_surface_type" in mcp_server.MCP_TOOL_NAMES


def test_create_wing_tool_requires_surface_type_in_its_request_schema() -> None:
    request = _tools()["create_aeroplane_wing"].parameters["properties"]["request"]
    assert "surface_type" in request["required"]
    assert "main_wing" in str(request["properties"]["surface_type"])


def test_update_wing_tool_requires_surface_type_in_its_request_schema() -> None:
    request = _tools()["update_aeroplane_wing"].parameters["properties"]["request"]
    assert "surface_type" in request["required"]
    assert "main_wing" in str(request["properties"]["surface_type"])


def test_set_surface_type_tool_forwards_to_the_endpoint(monkeypatch) -> None:
    captured: dict = {}

    async def fake_call(endpoint, **kwargs):
        captured["endpoint"] = endpoint.__name__
        captured["kwargs"] = kwargs
        return {"status": "ok"}

    monkeypatch.setattr(mcp_server, "_call_endpoint", fake_call)
    request = mcp_server.schemas.WingSurfaceTypeUpdateSchema(surface_type="canard")
    result = asyncio.run(
        mcp_server.set_aeroplane_wing_surface_type_tool(
            aeroplane_id="00000000-0000-0000-0000-000000000001",
            wing_name="w",
            request=request,
        )
    )
    assert result == {"status": "ok"}
    assert captured["endpoint"] == "set_aeroplane_wing_surface_type"
    assert captured["kwargs"]["wing_name"] == "w"
    assert captured["kwargs"]["request"].surface_type.value == "canard"

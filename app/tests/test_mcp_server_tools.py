import asyncio
import inspect
import re
from typing import Any

import app.mcp_server as mcp_server


def _run(coro):
    return asyncio.run(coro)


def _build_required_kwargs(handler) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    signature = inspect.signature(handler)

    for name, parameter in signature.parameters.items():
        if parameter.default is not inspect._empty:
            continue

        if name in {"op_id", "opset_id", "profile_id", "cross_section_index", "skip", "limit"}:
            kwargs[name] = 1
        elif name.endswith("_id"):
            kwargs[name] = "00000000-0000-0000-0000-000000000001"
        elif name.endswith("_name") or name == "name":
            kwargs[name] = "demo"
        else:
            kwargs[name] = object()

    return kwargs


def test_create_mcp_server_does_not_use_from_fastapi(monkeypatch):
    def _forbidden(*args, **kwargs):
        raise AssertionError("FastMCP.from_fastapi must not be used.")

    monkeypatch.setattr(mcp_server.FastMCP, "from_fastapi", _forbidden)

    server = mcp_server.create_mcp_server()
    assert server is not None


def test_all_native_tool_names_are_registered():
    server = mcp_server.create_mcp_server()
    tools = _run(server.list_tools())

    listed_names = {tool.name for tool in tools}
    expected_names = set(mcp_server.MCP_TOOL_NAMES)

    assert listed_names == expected_names
    assert len(listed_names) == 63
    assert "get_aeroplane_three_view_url" not in listed_names
    assert "get_streamlines_three_view_url" not in listed_names


def test_stub_endpoints_are_not_registered_as_tools():
    names = set(mcp_server.MCP_TOOL_NAMES)

    assert "get_aeroplane_stability_summary" not in names
    assert "get_wing_lift_distribution" not in names
    assert "get_aeroplane_moment_distribution" not in names


def test_tool_naming_and_descriptions_follow_basic_conventions():
    for spec in mcp_server.TOOL_SPECS:
        assert re.fullmatch(r"[a-z][a-z0-9_]*", spec.name)
        assert spec.description
        assert spec.description[0].isupper()
        assert spec.description.endswith(".")


def test_all_tool_handlers_delegate_through_call_endpoint(monkeypatch):
    captured_calls: list[tuple[Any, dict[str, Any]]] = []

    async def _fake_call(endpoint_fn, **kwargs):
        captured_calls.append((endpoint_fn, kwargs))
        if endpoint_fn.__name__ == "download_aeroplane_zip":
            return {
                "url": "http://unit.test/static/fake.zip",
                "filename": "fake.zip",
                "mime_type": "application/zip",
            }
        if endpoint_fn.__name__ == "calculate_streamlines":
            return {"url": "http://unit.test/static/fake.html"}
        if endpoint_fn.__name__ == "analyze_airplane_alpha_sweep_diagram":
            return {"url": "http://unit.test/static/fake.png"}
        if endpoint_fn.__name__ in {"get_streamlines_three_view", "get_aeroplane_three_view"}:
            return {"url": "http://unit.test/static/fake.png", "mime_type": "image/png"}
        return {"endpoint": endpoint_fn.__name__, "kwargs": kwargs}

    monkeypatch.setattr(mcp_server, "_call_endpoint", _fake_call)
    monkeypatch.setattr(
        mcp_server,
        "register_file_asset",
        lambda *args, **kwargs: mcp_server.AssetEntry(
            asset_id="asset",
            kind="data",
            file_path=mcp_server.Path("tmp/fake"),
            mime_type="application/octet-stream",
            public_url="http://unit.test/static/fake",
            filename="fake",
        ),
    )
    monkeypatch.setattr(
        mcp_server,
        "register_bytes_asset",
        lambda *args, **kwargs: mcp_server.AssetEntry(
            asset_id="asset",
            kind="img",
            file_path=mcp_server.Path("tmp/fake"),
            mime_type="image/png",
            public_url="http://unit.test/static/fake.png",
            filename="fake.png",
        ),
    )

    for spec in mcp_server.TOOL_SPECS:
        handler = spec.handler
        required_kwargs = _build_required_kwargs(handler)

        call_count_before = len(captured_calls)
        result = _run(handler(**required_kwargs))

        assert len(captured_calls) == call_count_before + 1

        endpoint_fn, forwarded_kwargs = captured_calls[-1]
        assert callable(endpoint_fn)
        assert result is not None

        for key, expected_value in required_kwargs.items():
            assert key in forwarded_kwargs
            assert forwarded_kwargs[key] is expected_value

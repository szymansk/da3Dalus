import asyncio
from pathlib import Path
from urllib.parse import urlparse
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient
from fastmcp.exceptions import ResourceError

import app.mcp_server as mcp_server
from app.main import create_app


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def clear_asset_registry():
    with mcp_server.ASSET_REGISTRY_LOCK:
        mcp_server.ASSET_REGISTRY.clear()
    yield
    with mcp_server.ASSET_REGISTRY_LOCK:
        mcp_server.ASSET_REGISTRY.clear()


@pytest.fixture(autouse=True)
def stable_base_url(monkeypatch):
    class DummySettings:
        base_url = "http://unit.test"

    monkeypatch.setattr(mcp_server, "get_settings", lambda: DummySettings())


@pytest.fixture(scope="module")
def fastapi_client():
    with TestClient(create_app()) as client:
        yield client


def test_resource_templates_are_registered():
    server = mcp_server.create_mcp_server()
    templates = _run(server.list_resource_templates())
    template_uris = {template.uri_template for template in templates}

    assert "img://{asset_id}" in template_uris
    assert "data://{asset_id}" in template_uris


def test_image_resource_and_public_url(monkeypatch, fastapi_client):
    image_bytes = b"\x89PNG\r\n\x1a\nunit-test-image"
    image_path = Path("tmp/test_assets/three_view.png")
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(image_bytes)

    async def fake_three_view(*, aeroplane_id, db, request=None, settings=None):
        return {"url": "http://unit.test/static/test_assets/three_view.png"}

    monkeypatch.setattr(mcp_server.aeroanalysis, "get_aeroplane_three_view_url", fake_three_view)

    server = mcp_server.create_mcp_server()
    payload = _run(mcp_server.get_aeroplane_three_view_tool("00000000-0000-0000-0000-000000000001"))

    assert payload["resource_uri"].startswith("img://")
    assert payload["url_from_docker_container"].startswith("http://unit.test/static/")
    assert payload["url_for_webui"].startswith("http://unit.test/static/")
    assert payload["mime_type"] == "image/png"

    resource = _run(server.read_resource(payload["resource_uri"]))
    assert resource.contents[0].mime_type == "image/png"
    assert resource.contents[0].content == image_bytes

    path = urlparse(payload["url_from_docker_container"]).path
    response = fastapi_client.get(path)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/png")
    assert response.content == image_bytes


def test_image_public_url_uses_mcp_request_port_when_context_is_available(monkeypatch):
    image_bytes = b"\x89PNG\r\n\x1a\nctx-based-image"
    image_path = Path("tmp/test_assets/ctx_three_view.png")
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(image_bytes)

    async def fake_three_view(*, aeroplane_id, db, request=None, settings=None):
        return {"url": "http://unit.test/static/test_assets/ctx_three_view.png"}

    monkeypatch.setattr(mcp_server.aeroanalysis, "get_aeroplane_three_view_url", fake_three_view)

    class DummyRequest:
        def __init__(self, url: str) -> None:
            self.url = url

    class DummyRequestContext:
        def __init__(self, url: str) -> None:
            self.request = DummyRequest(url)

    class DummyCtx:
        def __init__(self, url: str) -> None:
            self.request_context = DummyRequestContext(url)

    ctx = DummyCtx("http://agent-zero.internal:8090/mcp")
    payload = _run(mcp_server.get_aeroplane_three_view_tool("00000000-0000-0000-0000-000000000001", ctx=ctx))

    assert payload["url_from_docker_container"].startswith("http://agent-zero.internal:8090/static/")
    assert payload["url_for_webui"].startswith("http://unit.test/static/")


def test_alpha_sweep_diagram_resource_and_public_url(monkeypatch, fastapi_client):
    png_path = Path("tmp/test_assets/alpha_sweep.png")
    png_path.parent.mkdir(parents=True, exist_ok=True)
    png_bytes = b"\x89PNG\r\n\x1a\nalpha-sweep"
    png_path.write_bytes(png_bytes)

    async def fake_alpha_sweep_diagram(*, aeroplane_id, sweep_request, db, request=None, settings=None):
        return {"url": f"{settings.base_url}/static/test_assets/alpha_sweep.png"}

    monkeypatch.setattr(mcp_server.aeroanalysis, "analyze_airplane_alpha_sweep_diagram", fake_alpha_sweep_diagram)

    server = mcp_server.create_mcp_server()
    payload = _run(mcp_server.analyze_alpha_sweep_diagram_tool("00000000-0000-0000-0000-000000000001", object()))

    assert payload["resource_uri"].startswith("img://")
    assert payload["url_from_docker_container"].endswith("/static/test_assets/alpha_sweep.png")
    assert payload["url_for_webui"].endswith("/static/test_assets/alpha_sweep.png")
    assert payload["mime_type"] == "image/png"

    resource = _run(server.read_resource(payload["resource_uri"]))
    assert resource.contents[0].mime_type == "image/png"
    assert resource.contents[0].content == png_bytes

    path = urlparse(payload["url_from_docker_container"]).path
    response = fastapi_client.get(path)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/png")
    assert response.content == png_bytes


def test_zip_resource_and_public_url(monkeypatch, fastapi_client):
    zip_path = Path("tmp/test_assets/export.zip")
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    with ZipFile(zip_path, "w") as archive:
        archive.writestr("readme.txt", "zip-content")

    zip_bytes = zip_path.read_bytes()

    async def fake_download(*, aeroplane_id, request=None, settings=None):
        return {
            "url": "http://unit.test/static/test_assets/export.zip",
            "filename": zip_path.name,
            "mime_type": "application/zip",
        }

    monkeypatch.setattr(mcp_server.cad, "download_aeroplane_zip", fake_download)

    server = mcp_server.create_mcp_server()
    payload = _run(mcp_server.download_export_zip_tool("task-1"))

    assert payload["resource_uri"].startswith("data://")
    assert payload["url_from_docker_container"].endswith("/static/test_assets/export.zip")
    assert payload["url_for_webui"].endswith("/static/test_assets/export.zip")
    assert payload["mime_type"] == "application/zip"

    resource = _run(server.read_resource(payload["resource_uri"]))
    assert resource.contents[0].mime_type == "application/zip"
    assert resource.contents[0].content == zip_bytes

    path = urlparse(payload["url_from_docker_container"]).path
    response = fastapi_client.get(path)
    assert response.status_code == 200
    assert "zip" in response.headers["content-type"]
    assert response.content == zip_bytes


def test_unknown_asset_resource_raises_resource_error():
    server = mcp_server.create_mcp_server()

    with pytest.raises(ResourceError):
        _run(server.read_resource("img://does-not-exist"))


def test_resolve_public_base_url_from_context():
    class DummyRequest:
        def __init__(self, url: str) -> None:
            self.url = url

    class DummyRequestContext:
        def __init__(self, url: str) -> None:
            self.request = DummyRequest(url)

    class DummyCtx:
        def __init__(self, url: str) -> None:
            self.request_context = DummyRequestContext(url)

    ctx = DummyCtx("http://example.com:1234/mcp")
    assert mcp_server.resolve_public_base_url(ctx) == "http://example.com:1234"

    ctx = DummyCtx("http://example.com:1234/api/mcp")
    assert mcp_server.resolve_public_base_url(ctx) == "http://example.com:1234/api"

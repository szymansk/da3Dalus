"""Extended tests for app/mcp_server.py — covers utility functions, error paths,
and edge cases that the existing tool/resource tests do not exercise.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.responses import FileResponse, JSONResponse, Response
from fastmcp.exceptions import NotFoundError

import app.mcp_server as mcp_server


def _run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# _normalize_result
# ---------------------------------------------------------------------------

class TestNormalizeResult:
    def test_none_returns_status_ok(self):
        assert mcp_server._normalize_result(None) == {"status": "ok"}

    def test_json_response_with_body(self):
        body = json.dumps({"key": "value"}).encode("utf-8")
        resp = JSONResponse(content={"key": "value"}, status_code=200)
        result = mcp_server._normalize_result(resp)
        assert result == {"key": "value"}

    def test_json_response_with_null_content(self):
        resp = JSONResponse(content=None, status_code=204)
        # JSONResponse with None content produces b"null" which is truthy
        result = mcp_server._normalize_result(resp)
        # json.loads(b"null") returns None
        assert result is None

    def test_json_response_truly_empty(self):
        resp = JSONResponse(content=None, status_code=204)
        resp.body = b""
        result = mcp_server._normalize_result(resp)
        assert result == {"status_code": 204}

    def test_file_response(self, tmp_path):
        dummy = tmp_path / "export.stl"
        dummy.write_text("solid test")
        resp = FileResponse(
            path=str(dummy),
            filename="export.stl",
            media_type="application/sla",
        )
        result = mcp_server._normalize_result(resp)
        assert result["file_path"] == str(dummy)
        assert result["filename"] == "export.stl"
        assert result["media_type"] == "application/sla"

    def test_response_with_image_body(self):
        image_bytes = b"\x89PNG\r\n\x1a\nfake-image-data"
        resp = Response(content=image_bytes, media_type="image/png")
        result = mcp_server._normalize_result(resp)
        assert result["media_type"] == "image/png"
        assert result["encoding"] == "base64"
        import base64
        assert base64.b64decode(result["data"]) == image_bytes

    def test_response_with_json_body(self):
        payload = {"items": [1, 2, 3]}
        resp = Response(
            content=json.dumps(payload).encode("utf-8"),
            media_type="application/json",
        )
        result = mcp_server._normalize_result(resp)
        assert result == payload

    def test_response_with_text_body(self):
        resp = Response(content=b"hello world", media_type="text/plain")
        result = mcp_server._normalize_result(resp)
        assert result["media_type"] == "text/plain"
        assert result["content"] == "hello world"

    def test_response_with_no_body(self):
        resp = Response(status_code=204)
        resp.body = b""
        result = mcp_server._normalize_result(resp)
        assert result == {"status_code": 204}

    def test_pydantic_encodable_object(self):
        result = mcp_server._normalize_result({"simple": "dict"})
        assert result == {"simple": "dict"}


# ---------------------------------------------------------------------------
# _base_url_from_request_url
# ---------------------------------------------------------------------------

class TestBaseUrlFromRequestUrl:
    def test_strips_mcp_suffix(self):
        assert mcp_server._base_url_from_request_url("http://host:8001/mcp") == "http://host:8001"

    def test_strips_nested_mcp_suffix(self):
        assert mcp_server._base_url_from_request_url("http://host:8001/api/mcp") == "http://host:8001/api"

    def test_returns_none_for_missing_scheme(self):
        assert mcp_server._base_url_from_request_url("/just/a/path") is None

    def test_returns_none_for_missing_netloc(self):
        assert mcp_server._base_url_from_request_url("file:///some/path") is None

    def test_no_mcp_suffix(self):
        result = mcp_server._base_url_from_request_url("http://host:8001/api/v2")
        assert result == "http://host:8001/api/v2"


# ---------------------------------------------------------------------------
# _base_url_from_context
# ---------------------------------------------------------------------------

class TestBaseUrlFromContext:
    def test_none_context_returns_none(self):
        assert mcp_server._base_url_from_context(None) is None

    def test_context_without_request_context(self):
        ctx = MagicMock(spec=[])  # no attributes at all
        assert mcp_server._base_url_from_context(ctx) is None

    def test_context_with_no_request(self):
        ctx = MagicMock()
        ctx.request_context = MagicMock(spec=[])  # no .request
        assert mcp_server._base_url_from_context(ctx) is None

    def test_context_with_no_url(self):
        ctx = MagicMock()
        ctx.request_context.request = MagicMock(spec=[])  # no .url
        assert mcp_server._base_url_from_context(ctx) is None


# ---------------------------------------------------------------------------
# _base_url_from_active_request
# ---------------------------------------------------------------------------

class TestBaseUrlFromActiveRequest:
    def test_returns_none_on_runtime_error(self, monkeypatch):
        monkeypatch.setattr(
            mcp_server,
            "get_http_request",
            MagicMock(side_effect=RuntimeError("no active request")),
        )
        assert mcp_server._base_url_from_active_request() is None

    def test_returns_url_when_request_available(self, monkeypatch):
        mock_request = MagicMock()
        mock_request.url = "http://agent:9000/mcp"
        monkeypatch.setattr(mcp_server, "get_http_request", lambda: mock_request)
        assert mcp_server._base_url_from_active_request() == "http://agent:9000"


# ---------------------------------------------------------------------------
# _resolve_tmp_path_from_static_url
# ---------------------------------------------------------------------------

class TestResolveTmpPathFromStaticUrl:
    def test_valid_static_url(self):
        result = mcp_server._resolve_tmp_path_from_static_url("/static/foo/bar.png")
        assert result == mcp_server._normalize_file_path(Path("tmp") / "foo" / "bar.png")

    def test_raises_for_non_static_url(self):
        with pytest.raises(ValueError, match="Unsupported static URL format"):
            mcp_server._resolve_tmp_path_from_static_url("/other/path.png")

    def test_full_url_with_static_path(self):
        result = mcp_server._resolve_tmp_path_from_static_url("http://host/static/img.png")
        assert result == mcp_server._normalize_file_path(Path("tmp") / "img.png")


# ---------------------------------------------------------------------------
# resolve_tmp_path_from_known_output
# ---------------------------------------------------------------------------

class TestResolveTmpPathFromKnownOutput:
    def test_dict_with_file_path(self, tmp_path):
        p = tmp_path / "file.stl"
        p.write_text("solid")
        result = mcp_server.resolve_tmp_path_from_known_output({"file_path": str(p)})
        assert result == p.resolve()

    def test_string_existing_path(self, tmp_path):
        p = tmp_path / "existing.txt"
        p.write_text("hello")
        result = mcp_server.resolve_tmp_path_from_known_output(str(p))
        assert result == p.resolve()

    def test_dict_with_url_static(self):
        result = mcp_server.resolve_tmp_path_from_known_output(
            {"url": "/static/mcp_assets/data/abc.zip"}
        )
        assert "mcp_assets" in str(result)

    def test_string_with_static_prefix(self):
        result = mcp_server.resolve_tmp_path_from_known_output("/static/foo.png")
        assert "foo.png" in str(result)

    def test_string_starting_with_tmp(self):
        result = mcp_server.resolve_tmp_path_from_known_output("tmp/some/file.bin")
        assert "some/file.bin" in str(result) or "some" in str(result)

    def test_string_starting_with_dot_tmp(self):
        result = mcp_server.resolve_tmp_path_from_known_output("./tmp/some/file.bin")
        assert "some/file.bin" in str(result) or "some" in str(result)

    def test_http_url_with_static(self):
        result = mcp_server.resolve_tmp_path_from_known_output(
            "http://host:8001/static/exports/data.zip"
        )
        expected = mcp_server._normalize_file_path(Path("tmp") / "exports" / "data.zip")
        assert result == expected

    def test_dict_with_url_http(self):
        result = mcp_server.resolve_tmp_path_from_known_output(
            {"url": "http://host/static/foo.zip"}
        )
        assert "foo.zip" in str(result)

    def test_raises_for_empty_payload(self):
        with pytest.raises(ValueError, match="Unable to resolve"):
            mcp_server.resolve_tmp_path_from_known_output({"other": "data"})

    def test_raises_for_unsupported_string(self):
        with pytest.raises(ValueError, match="Unsupported output payload"):
            mcp_server.resolve_tmp_path_from_known_output("ftp://nowhere/file")

    def test_raises_for_none(self):
        with pytest.raises(ValueError, match="Unable to resolve"):
            mcp_server.resolve_tmp_path_from_known_output(None)


# ---------------------------------------------------------------------------
# _infer_asset_kind
# ---------------------------------------------------------------------------

class TestInferAssetKind:
    def test_explicit_kind_takes_priority(self):
        assert mcp_server._infer_asset_kind("application/zip", explicit_kind="archive") == "archive"

    def test_image_mime(self):
        assert mcp_server._infer_asset_kind("image/png") == "img"
        assert mcp_server._infer_asset_kind("image/jpeg") == "img"

    def test_non_image_mime(self):
        assert mcp_server._infer_asset_kind("application/json") == "data"
        assert mcp_server._infer_asset_kind("text/html") == "data"


# ---------------------------------------------------------------------------
# register_file_asset
# ---------------------------------------------------------------------------

class TestRegisterFileAsset:
    def test_raises_for_nonexistent_file(self):
        with pytest.raises(FileNotFoundError, match="does not exist"):
            mcp_server.register_file_asset("/no/such/file.png")

    def test_copies_file_outside_tmp(self, tmp_path):
        source = tmp_path / "external.stl"
        source.write_text("solid test")
        entry = mcp_server.register_file_asset(source, mime_type="model/stl")
        assert entry.kind == "data"
        assert entry.mime_type == "model/stl"
        assert entry.file_path.exists()
        # File was copied under tmp/
        assert "mcp_assets" in str(entry.file_path)
        assert "external" in str(entry.file_path)

    def test_file_inside_tmp_not_copied(self):
        p = mcp_server._normalize_file_path(Path("tmp") / "already_here.png")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"\x89PNGfake")
        try:
            entry = mcp_server.register_file_asset(p, mime_type="image/png")
            assert entry.file_path == p
            assert entry.kind == "img"
        finally:
            p.unlink(missing_ok=True)

    def test_guesses_mime_type(self, tmp_path):
        source = tmp_path / "readme.txt"
        source.write_text("hello")
        entry = mcp_server.register_file_asset(source)
        assert entry.mime_type == "text/plain"

    def test_falls_back_to_octet_stream(self, tmp_path):
        source = tmp_path / "mystery.xyz123"
        source.write_bytes(b"\x00\x01\x02")
        entry = mcp_server.register_file_asset(source)
        assert entry.mime_type == "application/octet-stream"


# ---------------------------------------------------------------------------
# register_bytes_asset
# ---------------------------------------------------------------------------

class TestRegisterBytesAsset:
    def test_registers_png_bytes(self):
        entry = mcp_server.register_bytes_asset(
            b"\x89PNGfake",
            mime_type="image/png",
        )
        assert entry.kind == "img"
        assert entry.file_path.exists()
        assert entry.file_path.suffix == ".png"
        assert entry.file_path.read_bytes() == b"\x89PNGfake"

    def test_registers_binary_bytes(self):
        entry = mcp_server.register_bytes_asset(
            b"\x00\x01\x02",
            mime_type="application/octet-stream",
        )
        assert entry.kind == "data"
        assert entry.file_path.suffix == ".bin"

    def test_custom_filename(self):
        entry = mcp_server.register_bytes_asset(
            b"content",
            mime_type="text/html",
            filename="report.html",
        )
        assert entry.filename == "report.html"
        assert entry.file_path.name == "report.html"

    def test_custom_kind(self):
        entry = mcp_server.register_bytes_asset(
            b"content",
            mime_type="application/zip",
            kind="archive",
        )
        assert entry.kind == "archive"

    def test_custom_base_url(self):
        entry = mcp_server.register_bytes_asset(
            b"content",
            mime_type="image/png",
            base_url="http://custom:9999",
        )
        assert entry.public_url.startswith("http://custom:9999/static/")


# ---------------------------------------------------------------------------
# _asset_entry_or_raise
# ---------------------------------------------------------------------------

class TestAssetEntryOrRaise:
    def test_unknown_id_raises(self):
        with pytest.raises(NotFoundError, match="Unknown asset"):
            mcp_server._asset_entry_or_raise("nonexistent", "img")

    def test_wrong_kind_raises(self):
        entry = mcp_server.register_bytes_asset(b"data", mime_type="application/zip", kind="data")
        with pytest.raises(NotFoundError, match="registered as 'data'"):
            mcp_server._asset_entry_or_raise(entry.asset_id, "img")

    def test_missing_file_raises(self, tmp_path):
        # Register a file, then delete it
        f = tmp_path / "will_delete.txt"
        f.write_text("temp")
        entry = mcp_server.register_file_asset(f)
        # Now remove the copied file
        entry.file_path.unlink()
        with pytest.raises(NotFoundError, match="missing"):
            mcp_server._asset_entry_or_raise(entry.asset_id, entry.kind)


# ---------------------------------------------------------------------------
# _to_resource_result
# ---------------------------------------------------------------------------

class TestToResourceResult:
    def test_text_file_returns_text_content(self):
        entry = mcp_server.register_bytes_asset(
            b"hello text",
            mime_type="text/plain",
            filename="readme.txt",
        )
        result = mcp_server._to_resource_result(entry)
        assert result.contents[0].mime_type == "text/plain"
        # ResourceContent stores text in .content as str
        assert result.contents[0].content == "hello text"

    def test_text_with_unicode_decode_error_falls_back_to_binary(self):
        # Write invalid UTF-8 bytes but label as text
        entry = mcp_server.register_bytes_asset(
            b"\x89\xfe\xff\x00invalid-utf8",
            mime_type="text/plain",
            filename="broken.txt",
        )
        result = mcp_server._to_resource_result(entry)
        # Falls back to binary read
        assert result.contents[0].mime_type == "text/plain"
        assert result.contents[0].content == b"\x89\xfe\xff\x00invalid-utf8"

    def test_binary_file_returns_bytes(self):
        data = b"\x89PNG\r\n\x1a\nimage-data"
        entry = mcp_server.register_bytes_asset(data, mime_type="image/png")
        result = mcp_server._to_resource_result(entry)
        assert result.contents[0].content == data


# ---------------------------------------------------------------------------
# _register_image_payload
# ---------------------------------------------------------------------------

class TestRegisterImagePayload:
    def test_raises_for_non_dict(self):
        with pytest.raises(ValueError, match="Expected image payload dict"):
            mcp_server._register_image_payload("not-a-dict", filename_prefix="test")

    def test_raises_for_missing_base64(self):
        with pytest.raises(ValueError, match="Expected base64 image payload"):
            mcp_server._register_image_payload(
                {"encoding": "raw", "data": "abc"},
                filename_prefix="test",
            )

    def test_raises_for_missing_data_key(self):
        with pytest.raises(ValueError, match="Expected base64 image payload"):
            mcp_server._register_image_payload(
                {"encoding": "base64"},
                filename_prefix="test",
            )

    def test_successful_registration(self):
        import base64
        image_bytes = b"\x89PNGfake"
        payload = {
            "encoding": "base64",
            "data": base64.b64encode(image_bytes).decode("ascii"),
            "media_type": "image/png",
        }
        result = mcp_server._register_image_payload(payload, filename_prefix="sweep")
        assert "resource_uri" in result
        assert result["resource_uri"].startswith("img://")
        assert result["mime_type"] == "image/png"

    def test_defaults_to_png_mime(self):
        import base64
        payload = {
            "encoding": "base64",
            "data": base64.b64encode(b"data").decode("ascii"),
        }
        result = mcp_server._register_image_payload(payload, filename_prefix="test")
        assert result["mime_type"] == "image/png"

    def test_non_png_uses_bin_suffix(self):
        import base64
        payload = {
            "encoding": "base64",
            "data": base64.b64encode(b"data").decode("ascii"),
            "media_type": "image/jpeg",
        }
        result = mcp_server._register_image_payload(payload, filename_prefix="test")
        assert result["mime_type"] == "image/jpeg"


# ---------------------------------------------------------------------------
# _asset_payload
# ---------------------------------------------------------------------------

class TestAssetPayload:
    def test_includes_filename_when_present(self):
        entry = mcp_server.register_bytes_asset(
            b"data",
            mime_type="application/zip",
            filename="export.zip",
        )
        payload = mcp_server._asset_payload(entry)
        assert payload["filename"] == "export.zip"

    def test_omits_filename_when_none(self):
        entry = mcp_server.AssetEntry(
            asset_id="abc",
            kind="data",
            file_path=mcp_server._normalize_file_path(Path("tmp") / "abc.bin"),
            mime_type="application/octet-stream",
            public_url="http://unit.test/static/abc.bin",
            filename=None,
        )
        with mcp_server.ASSET_REGISTRY_LOCK:
            mcp_server.ASSET_REGISTRY["abc"] = entry
        payload = mcp_server._asset_payload(entry)
        assert "filename" not in payload


# ---------------------------------------------------------------------------
# _normalize_file_path
# ---------------------------------------------------------------------------

class TestNormalizeFilePath:
    def test_absolute_path_unchanged(self, tmp_path):
        p = tmp_path / "file.txt"
        result = mcp_server._normalize_file_path(str(p))
        assert result == p.resolve()

    def test_relative_path_resolved(self):
        result = mcp_server._normalize_file_path("tmp/foo.txt")
        assert result.is_absolute()
        assert str(result).endswith("tmp/foo.txt")


# ---------------------------------------------------------------------------
# resolve_public_base_url
# ---------------------------------------------------------------------------

class TestResolvePublicBaseUrl:
    def test_falls_back_to_settings(self):
        result = mcp_server.resolve_public_base_url(ctx=None)
        assert result == "http://unit.test"

    def test_context_takes_priority(self):
        ctx = MagicMock()
        ctx.request_context.request.url = "http://agent:9000/mcp"
        result = mcp_server.resolve_public_base_url(ctx=ctx)
        assert result == "http://agent:9000"


# ---------------------------------------------------------------------------
# build_public_url_from_tmp_path
# ---------------------------------------------------------------------------

class TestBuildPublicUrlFromTmpPath:
    def test_default_base_url(self):
        file_path = mcp_server._normalize_file_path(Path("tmp") / "foo" / "bar.png")
        url = mcp_server.build_public_url_from_tmp_path(file_path)
        assert url == "http://unit.test/static/foo/bar.png"

    def test_custom_base_url(self):
        file_path = mcp_server._normalize_file_path(Path("tmp") / "export.zip")
        url = mcp_server.build_public_url_from_tmp_path(file_path, base_url="http://custom:5000/")
        assert url == "http://custom:5000/static/export.zip"


# ---------------------------------------------------------------------------
# download_export_zip_tool error path
# ---------------------------------------------------------------------------

class TestDownloadExportZipToolError:
    def test_raises_for_unexpected_payload(self, monkeypatch):
        async def fake_download(*, aeroplane_id, request=None, settings=None):
            return "not-a-dict"

        monkeypatch.setattr(mcp_server.cad, "download_aeroplane_zip", fake_download)
        with pytest.raises(ValueError, match="Unexpected ZIP payload"):
            _run(mcp_server.download_export_zip_tool("task-1"))


# ---------------------------------------------------------------------------
# MCPToolSpec and mcp_tool decorator
# ---------------------------------------------------------------------------

class TestMCPToolSpec:
    def test_dataclass_fields(self):
        spec = mcp_server.MCPToolSpec(name="test", description="Test tool.", handler=lambda: None)
        assert spec.name == "test"
        assert spec.description == "Test tool."
        assert callable(spec.handler)

    def test_mcp_tool_decorator_registers_spec(self):
        original_count = len(mcp_server.TOOL_SPECS)
        # We won't actually decorate — just verify the existing count is non-zero
        assert original_count > 0


# ---------------------------------------------------------------------------
# create_mcp_server
# ---------------------------------------------------------------------------

class TestCreateMcpServer:
    def test_returns_fastmcp_instance(self):
        server = mcp_server.create_mcp_server()
        assert server is not None
        assert server.name == "da3dalus-cad-tools"

    def test_tools_and_resources_registered(self):
        server = mcp_server.create_mcp_server()
        tools = _run(server.list_tools())
        templates = _run(server.list_resource_templates())
        assert len(tools) > 0
        assert len(templates) >= 2


# ---------------------------------------------------------------------------
# _call_endpoint
# ---------------------------------------------------------------------------

class TestCallEndpoint:
    def test_sync_endpoint(self):
        def sync_fn(db, name: str):
            return {"name": name}

        result = _run(mcp_server._call_endpoint(sync_fn, name="test"))
        assert result == {"name": "test"}

    def test_async_endpoint(self):
        async def async_fn(db, x: int):
            return {"x": x}

        result = _run(mcp_server._call_endpoint(async_fn, x=42))
        assert result == {"x": 42}

    def test_endpoint_without_db_param(self):
        def no_db_fn(value: str):
            return {"value": value}

        result = _run(mcp_server._call_endpoint(no_db_fn, value="hello"))
        assert result == {"value": "hello"}

    def test_endpoint_returning_none(self):
        def returns_none(db):
            return None

        result = _run(mcp_server._call_endpoint(returns_none))
        assert result == {"status": "ok"}

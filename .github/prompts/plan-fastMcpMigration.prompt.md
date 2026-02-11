## Plan: FastMCP 3.0 Migration (FastAPI Integration)

Migration von `fastapi-mcp` (lokale Wheel) zu **FastMCP 3.0.0** mit `FastMCP.from_fastapi()`. Separater MCP-Server-Prozess auf Port 8001 mit Streamable HTTP Transport.

### TL;DR

FastMCP 3.0 bietet `FastMCP.from_fastapi(app)` — alle 58 FastAPI-Endpoints werden automatisch als MCP-Tools exponiert. Die FastAPI-App bleibt unverändert auf Port 8000, der MCP-Server läuft als separater Prozess auf Port 8001.

**Steps**

1. **Dependency aktualisieren** in [pyproject.toml](pyproject.toml#L14):
   - `fastapi_mcp @ external/...` entfernen  
   - `"fastmcp>=3.0.0b2"` hinzufügen (Poetry erkennt Beta-Versionen mit `>=`)

2. **Neues MCP-Server Modul erstellen** — `app/mcp_server.py`:
   ```python
   from fastmcp import FastMCP
   from app.main import app as fastapi_app
   
   mcp = FastMCP.from_fastapi(app=fastapi_app, name="da3dalus-cad-tools")
   
   if __name__ == "__main__":
       mcp.run(transport="http", host="0.0.0.0", port=8001, path="/mcp")
   ```

3. **main.py bereinigen** — [app/main.py](app/main.py):
   - Import `from fastapi_mcp import FastApiMCP` entfernen (Zeile 3)
   - Ungenutzten Import `from sqlalchemy.testing.plugin.plugin_base import include_tags` entfernen (Zeile 4)
   - Gesamten MCP-Konfigurationsblock entfernen (Zeilen 44-66: `mcp = FastApiMCP(...)`, `mcp.mount()`, `app_analysis_tools`, `mcp_analysis_tools`)
   - Multiprocessing erweitern: zweiten Prozess für `app.mcp_server` auf Port 8001 hinzufügen

4. **Docker Smoke Test anpassen** — [docker_smoke_test.py](docker_smoke_test.py#L25-L26):
   - `import fastapi_mcp as mcp` → `import fastmcp`
   - Print-Statement entsprechend anpassen

5. **Readme aktualisieren** — [Readme.md](Readme.md):
   - MCP-Endpoint ändern: `http://localhost:8001/mcp` (Streamable HTTP)
   - Notiz zu FastMCP 3.0 statt fastapi-mcp

6. **Aufräumen** (optional):
   - `external/fastapi_mcp-0.4.0-py3-none-any.whl` löschen
   - `external/fastapi_mcp-0.3.4-py3-none-any.whl` löschen

**Verification**

```bash
# Dependencies neu installieren
poetry install

# Terminal 1: FastAPI starten
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal 2: MCP-Server starten  
python -m app.mcp_server

# Test FastAPI
curl http://localhost:8000/docs

# Test MCP (Streamable HTTP)
curl http://localhost:8001/mcp

# Docker Smoke Test
python docker_smoke_test.py
```

**Decisions**

- **FastMCP 3.0.0 Beta**: Version `>=3.0.0b2` — moderne Provider-Architektur, `from_fastapi()` generiert Tools automatisch aus OpenAPI-Spec
- **Separater Prozess**: MCP-Server auf Port 8001, FastAPI bleibt auf Port 8000 (wie gewünscht)
- **Streamable HTTP Transport**: `mcp.run(transport="http")` — der Standard für Remote-MCP in FastMCP 3.0
- **Poetry bleibt**: Dependency-Syntax in `[project].dependencies` mit Poetry-Backend

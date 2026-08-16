# Flowcharts — mcp-server

## 1. Where the MCP server sits

```mermaid
flowchart LR
    subgraph PROC["one uvicorn process"]
        FA["FastAPI app (app.main:app)"]
        subgraph MOUNTS
            REST["/aeroplanes, /wings, … ~230 v2 routes"]
            STATIC["/static → tmp/<br/>/assets → app/static"]
            MCPMOUNT["/mcp → FastMCP http_app"]
        end
        EP["app/api/v2/endpoints/*<br/>endpoint FUNCTIONS"]
        SVC["app/services/*"]
    end

    HTTPCLI["Browser / REST client"] --> REST
    AGENT["MCP client<br/>(Claude Desktop, IDE, agent)"] --> MCPMOUNT
    REST --> EP
    MCPMOUNT -->|"_call_endpoint(fn, **kwargs)"| EP
    EP --> SVC
```

The MCP surface is a **second front door onto the same endpoint functions** —
not a second implementation. `_call_endpoint` imports the FastAPI handler and
calls it as a plain Python callable, bypassing routing, dependency injection
and middleware.

## 2. Registration — decorator collects, factory installs

```mermaid
flowchart TD
    A["@mcp_tool(name=…, description=…)"] --> B["TOOL_SPECS.append(MCPToolSpec(name, description, handler))"]
    B --> C["… 76 decorated coroutines at import time …"]
    C --> D["MCP_TOOL_NAMES = tuple(spec.name for spec in TOOL_SPECS)"]
    D --> E["create_mcp_server()"]
    E --> F["mcp = FastMCP(name='da3dalus-cad-tools')"]
    F --> G["for spec in TOOL_SPECS:<br/>mcp.tool(name, description)(spec.handler)"]
    G --> H["mcp.resource('img://{asset_id}') → read_image_asset"]
    G --> I["mcp.resource('data://{asset_id}') → read_data_asset"]
    H --> J["get_mcp() memoises into the module global 'mcp'"]
    I --> J
    J --> K["create_mcp_http_app(path='/') → mcp.http_app()"]
    K --> L["app.mount('/mcp', mcp_app) in create_app()"]
    L --> M["_combined_lifespan wraps mcp_app.lifespan(app)"]
```

The decorator only *records* metadata; the signature of the decorated
coroutine is what FastMCP introspects for the tool's input schema, so the
Pydantic types in the handler signature (`UUID4`, `OperatingPointSchema`,
`AlphaSweepRequest`, …) become the MCP JSON schema.

## 3. One tool invocation, end to end

```mermaid
sequenceDiagram
    autonumber
    participant C as MCP client
    participant F as FastMCP (/mcp)
    participant T as *_tool coroutine
    participant CE as _call_endpoint
    participant DB as SessionLocal()
    participant EP as endpoint function
    participant S as service layer

    C->>F: tools/call {name, arguments}
    F->>F: validate arguments against the handler signature
    F->>T: await handler(**kwargs)
    T->>CE: _call_endpoint(endpoint_fn, **kwargs)
    CE->>DB: with SessionLocal() as db
    CE->>CE: inspect.signature(endpoint_fn).parameters
    alt endpoint declares a 'db' parameter
        CE->>CE: call_kwargs['db'] = db
    end
    CE->>EP: endpoint_fn(**call_kwargs)
    EP->>S: business logic
    S-->>EP: model / schema
    EP-->>CE: Pydantic model | JSONResponse | FileResponse | Response | None
    CE->>CE: _normalize_result(...)
    CE-->>T: JSON-safe value
    T-->>F: value (or an asset payload)
    F-->>C: tool result
```

**Transaction semantics differ from REST.** `get_db()` commits on success;
`_call_endpoint` uses a bare `with SessionLocal() as db:` which **never
commits**. Any MCP tool whose endpoint relies on the dependency's commit
persists nothing unless the service itself commits.

## 4. `_normalize_result` — FastAPI return types → MCP JSON

```mermaid
flowchart TD
    A["result"] --> B{"None?"}
    B -- yes --> B1["{'status': 'ok'}"]
    A --> C{"JSONResponse?"}
    C -- yes --> C1{"body empty?"}
    C1 -- yes --> C2["{'status_code': …}"]
    C1 -- no --> C3["json.loads(body)"]
    A --> D{"FileResponse?"}
    D -- yes --> D1["{'file_path', 'filename', 'media_type'}"]
    A --> E{"Response?"}
    E -- yes --> E1{"media_type startswith 'image/'?"}
    E1 -- yes --> E2["{'media_type', 'encoding': 'base64', 'data': b64}"]
    E1 -- no --> E3{"media_type == 'application/json'?"}
    E3 -- yes --> E4["json.loads(body)"]
    E3 -- no --> E5["{'media_type', 'content': utf-8 with errors='replace'}"]
    A --> F["else → jsonable_encoder(result)"]
```

## 5. The asset registry — binary results become URLs + resources

```mermaid
flowchart TD
    subgraph PRODUCERS["asset-producing tools"]
        TV["get_aeroplane_three_view"]
        ZIP["download_export_zip"]
        SW["analyze_alpha_sweep_diagram"]
    end

    TV --> R1["resolve_tmp_path_from_known_output(payload)"]
    ZIP --> R1
    SW --> R2["_register_image_payload(base64 payload)"]

    R1 --> RF["register_file_asset(path, mime, kind, base_url)"]
    R2 --> RB["register_bytes_asset(bytes, mime, kind, filename)"]

    RF --> OUT{"file already under tmp/?"}
    OUT -- no --> COPY["shutil.copy2 → tmp/mcp_assets/external/&lt;uuid4&gt;_&lt;name&gt;"]
    OUT -- yes --> KEEP["keep in place"]
    RB --> WRITE["write to tmp/mcp_assets/&lt;kind&gt;/&lt;id[:2]&gt;/&lt;name&gt;"]

    COPY --> STORE
    KEEP --> STORE
    WRITE --> STORE["_store_asset_entry → ASSET_REGISTRY[asset_id]<br/>(guarded by ASSET_REGISTRY_LOCK)"]

    STORE --> PAY["_asset_payload(entry)"]
    PAY --> P1["resource_uri: 'img://&lt;id&gt;' | 'data://&lt;id&gt;'"]
    PAY --> P2["url_from_docker_container: request-derived base URL"]
    PAY --> P3["url_for_webui / url: settings.base_url (host)"]
    PAY --> P4["mime_type, filename"]
```

### Reading an asset back

```mermaid
flowchart LR
    A["MCP resources/read img://&lt;id&gt;"] --> B["read_image_asset(asset_id)"]
    B --> C["_asset_entry_or_raise(id, expected_kind='img')"]
    C -- "unknown id" --> E1["NotFoundError"]
    C -- "kind mismatch" --> E2["NotFoundError: registered as 'data'"]
    C -- "file gone" --> E3["NotFoundError: Asset file is missing"]
    C --> D["_to_resource_result"]
    D --> F{"mime startswith 'text/'?"}
    F -- yes --> G["read_text; on UnicodeDecodeError fall through"]
    F -- no --> H["read_bytes"]
    G --> I["ResourceResult([ResourceContent(...)])"]
    H --> I
```

`ASSET_REGISTRY` is a **process-local dict**. It does not survive a restart and
is not shared across workers, so an `img://…` URI issued by one process is a
404 in any other.

## 6. Public base-URL resolution (the dual-URL problem)

```mermaid
flowchart TD
    A["resolve_public_base_url(ctx)"] --> B["_base_url_from_context(ctx)<br/>ctx.request_context.request.url"]
    B -- None --> C["_base_url_from_active_request()<br/>fastmcp get_http_request()"]
    C -- "RuntimeError (no active request)" --> D["settings.base_url<br/>(app/settings.py, default http://localhost:8000)"]
    B --> E["_base_url_from_request_url"]
    C --> E
    E --> F["strip a trailing '/mcp' from the path prefix"]
    F --> G["'&lt;scheme&gt;://&lt;netloc&gt;&lt;prefix&gt;'"]
    D --> G
```

Both URLs are then emitted side by side, because the caller's network view and
the browser's view differ when the service runs in a container:
`url_from_docker_container` (request-derived) vs `url_for_webui` /
`url` (from `settings.base_url`).

## 7. Tool coverage vs the REST surface

```mermaid
pie showData
    title 76 MCP tools by domain
    "wings + cross-sections + control surfaces / servos" : 20
    "fuselages + fuselage cross-sections" : 11
    "operating points + point sets" : 10
    "flight profiles + assignment" : 7
    "aeroplane base + mass + airfoil upload" : 8
    "aero analysis + three-view + sweeps" : 6
    "design assumptions" : 4
    "stability + flight envelope" : 4
    "CAD export + task status + zip" : 3
    "trim (ASB + AVL)" : 2
    "aeroplane delete/get variants" : 1
```

Domains **absent** from MCP although they exist in REST: versioning
(`/branches`, `/lineages`), copilot history and stream, component tree,
components / component types (COTS), construction plans and parts,
construction templates, mass & CG, loading scenarios, mission objectives,
weight items, endurance, matching chart, tail sizing, field lengths, forward
CG, speed polar, turbulator optimizer, powertrain (all five routers),
OpenVSP import, fuselage slice, health.

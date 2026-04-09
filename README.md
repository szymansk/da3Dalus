# da3Dalus CAD Modelling Service

## Introduction

### Purpose

The **da3Dalus CAD Modelling Service** is a RESTful API service that provides parametric CAD modelling and aerodynamic analysis capabilities for aircraft design. It combines CAD generation using CadQuery with aerodynamic simulation using Aerosandbox, enabling automated aircraft design workflows.

### What It Provides

- **Parametric Aircraft Modelling**: Create and manage aircraft configurations including wings, fuselages, and complete assemblies
- **CAD Generation**: Generate 3D CAD models (STEP files) from parametric definitions
- **Aerodynamic Analysis**: Perform vortex lattice method (VLM) analysis, stability analysis, and parameter sweeps
- **Operating Point Analysis**: Calculate aerodynamic performance at specific flight conditions
- **3D Visualization**: Generate streamline plots and three-view diagrams
- **Model Context Protocol (MCP) Server**: Exposes all API endpoints as MCP tools for AI agent integration

### Technology Stack

- **FastAPI**: Modern web framework for building APIs
- **CadQuery**: Parametric CAD scripting in Python
- **Aerosandbox**: Aerodynamic analysis toolkit
- **SQLAlchemy**: Database ORM for persistence
- **FastMCP 3.0**: Model Context Protocol server integration

---

## Launching the Application

### Option 1: Using Poetry (Local Development)

Poetry is the recommended way for local development with hot-reload capabilities.

#### Prerequisites

- Python 3.11 or 3.12
- Poetry installed (`curl -sSL https://install.python-poetry.org | python3 -`)

#### Steps

1. **Install dependencies:**
   ```bash
   poetry install
   ```

2. **Activate the virtual environment:**
   ```bash
   poetry shell
   ```

3. **Run the application:**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

4. **Alternative: Using VS Code debugger:**
   - Open the project in VS Code
   - Press `F5` or select "FastAPI: app.main" from the Run and Debug panel
   - The application will start with debugging enabled

### Option 2: Using Docker Compose (Production)

Docker Compose provides a containerized environment with all dependencies pre-installed.

#### Prerequisites

- Docker and Docker Compose installed

#### Steps

1. **Build the image:**
   ```bash
   docker compose build
   ```

2. **Start the service:**
   ```bash
   docker compose up -d
   ```

3. **View logs:**
   ```bash
   docker compose logs -f aero-cad-service
   ```

4. **Stop the service:**
   ```bash
   docker compose down
   ```

The service will be available at `http://localhost:8086` (mapped to internal port 8000).

---

## Testing and Documentation

### API Documentation

Once the application is running, you can access the interactive API documentation:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
  - Interactive API documentation with "Try it out" functionality
  - Complete endpoint descriptions and request/response schemas

- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
  - Alternative, more detailed API documentation

- **OpenAPI Schema**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)
  - Machine-readable API specification

### Testing MCP with MCP Inspector

The application exposes a Model Context Protocol (MCP) server that can be tested using the MCP Inspector.

#### Install MCP Inspector

```bash
npm install -g @modelcontextprotocol/inspector
```

#### Launch MCP Inspector

1. **Start the application** (using Poetry or Docker)

2. **Run MCP Inspector:**
   ```bash
   mcp-inspector http://localhost:8000/mcp
   ```

3. **Access the Inspector UI:**
   - Open your browser to the URL shown in the terminal (typically `http://localhost:5173`)
   - The inspector will connect to your MCP server via Streamable HTTP

4. **Test MCP Tools:**
   - Browse available tools (all API endpoints are exposed as MCP tools)
   - Test tool invocations with different parameters
   - View responses and schemas

#### MCP Endpoints

- **Streamable HTTP**: `http://localhost:8000/mcp`
- MCP is mounted into the same FastAPI app as the REST API, so both run on one host/port.

#### MCP Client Configuration Example

For Claude Desktop or other MCP clients:

```json
{
  "mcpServers": {
    "da3dalus-cad": {
      "type":"streamable-http",
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

---

## Architecture

### API Versioning

The service uses API versioning with both v1 and v2 endpoints:

- **v2** (current): Main API with full MCP support
  - `/aeroplanes/` - Aircraft management
  - `/operating_points/` - Flight condition definitions
  - `/aeroplanes/{id}/wings/` - Wing analysis
  - CAD generation and aerodynamic analysis endpoints

### Key API Endpoints

- **Health Check**: `GET /health`
- **Aeroplane CRUD**: `POST|GET|PUT|DELETE /aeroplanes/`
- **Wing Analysis**: `POST /aeroplanes/{id}/wings/{name}/{analysis_tool}`
- **Operating Point Analysis**: `POST /aeroplanes/{id}/operating_point/{tool}`
- **Stability Analysis**: `GET /aeroplanes/{id}/stability_summary`
- **CAD Export**: Various endpoints for STEP file generation

---

## Development

### Running Tests

```bash
poetry run pytest
```

Or use the included shell script:

```bash
./run_all_tests.sh
```

### Project Structure

```
app/
├── api/           # API endpoints (v1 and v2)
├── converters/    # Data converters between formats
├── core/          # Core business logic
├── db/            # Database configuration
├── models/        # SQLAlchemy models
├── schemas/       # Pydantic schemas
└── services/      # Business logic services

cad_designer/      # CAD generation modules
components/        # Reusable aircraft components
Avl/              # AVL analysis integration
docs/             # Documentation (asciidoctor)
```

### Building Documentation

The project documentation is written in AsciiDoctor format:

```bash
make doc
```

Generated documentation will be available in the `docs/html/` directory.

### Environment Variables

- `BROWSER_PATH`: Path to Chromium browser for rendering (default: `/usr/bin/chromium-browser`)
- `QT_QPA_PLATFORM`: Set to `offscreen` for headless rendering

---

## Platform Support

The application supports multiple platforms with conditional dependencies:

- **macOS (arm64/x86_64)**: Full support including CadQuery, Aerosandbox, and visualization
- **Linux (amd64)**: Full support
- **Linux (aarch64)**: Full support in Docker (CadQuery and visualization tools excluded in poetry.toml due to availability)

Platform-specific dependencies are handled via environment markers in [pyproject.toml](pyproject.toml).

---

## License

[Your License Here]

## Contributors

Marc Szymanski (marc.szymanski@mac.com)


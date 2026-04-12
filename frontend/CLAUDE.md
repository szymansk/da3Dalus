@AGENTS.md

## da3Dalus Construction Workbench Frontend

- Backend API: http://localhost:8000 (FastAPI)
- Swagger UI: http://localhost:8000/docs
- OpenAPI schema: http://localhost:8000/openapi.json
- MCP endpoint: http://localhost:8000/mcp
- This frontend connects to the cad-modelling-service backend
- Use App Router (not Pages Router)
- All API calls go through server-side route handlers or
  server actions to avoid CORS
- Dark theme with orange accent (#FF8400), fonts: JetBrains Mono + Geist

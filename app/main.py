from fastapi import FastAPI
from app.mcp_server.server import mcp
from app.observability.health import router as health_router
from app.auth.router import router as auth_router


def create_app() -> FastAPI:
    app = FastAPI(title="Weather MCP Server")
    app.include_router(health_router, prefix="/v1")
    app.mount("/mcp", mcp.http_app(path="/mcp"))

    return app


app = create_app()

app.include_router(auth_router)

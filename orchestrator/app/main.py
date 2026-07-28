"""Entry point: FastAPI + grafo del agente + métricas Prometheus."""
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.application.agent.builder import build_graph
from app.application.services.agent_service import AgentService
from app.config import get_settings
from app.infrastructure.api.routers import agent, health, insights
from app.infrastructure.persistence.checkpointer import lifespan_checkpointer
from app.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with lifespan_checkpointer() as (checkpointer, kind):
        graph = build_graph(checkpointer=checkpointer)
        app.state.agent_service = AgentService(graph)
        app.state.checkpointer_kind = kind
        yield


def create_app() -> FastAPI:
    setup_logging()
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        lifespan=lifespan,
        # /api/docs lo usa el frontend para el listado de documentos del RAG;
        # el Swagger UI del template se mueve a /api/swagger para no chocar.
        docs_url="/api/swagger" if settings.app_env != "production" else None,
    )
    app.include_router(agent.router)
    app.include_router(health.router)
    app.include_router(insights.router)
    Instrumentator().instrument(app).expose(app, endpoint="/metrics", tags=["ops"])
    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=get_settings().app_port)

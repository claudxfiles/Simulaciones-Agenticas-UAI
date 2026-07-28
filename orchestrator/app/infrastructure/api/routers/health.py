"""Health check para orquestadores (Swarm healthcheck, k8s probes)."""
from fastapi import APIRouter, Request

from app.config import get_settings
from app.domain.models import HealthResponse

router = APIRouter(tags=["ops"])


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        app=settings.app_name,
        env=settings.app_env,
        checkpointer=request.app.state.checkpointer_kind,
    )

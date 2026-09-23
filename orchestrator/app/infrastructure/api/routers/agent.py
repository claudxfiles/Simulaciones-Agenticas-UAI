"""Endpoints del agente."""
from fastapi import APIRouter, Depends, Request

from app.domain.models import InvokeRequest, InvokeResponse
from app.infrastructure.api.auth import require_auth

router = APIRouter(prefix="/api/agent", tags=["agent"], dependencies=[Depends(require_auth)])


@router.post("/invoke", response_model=InvokeResponse)
async def invoke(payload: InvokeRequest, request: Request) -> InvokeResponse:
    service = request.app.state.agent_service
    return await service.invoke(payload)

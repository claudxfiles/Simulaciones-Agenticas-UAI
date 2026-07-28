"""Endpoints del agente."""
from fastapi import APIRouter, Request

from app.domain.models import InvokeRequest, InvokeResponse

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/invoke", response_model=InvokeResponse)
async def invoke(payload: InvokeRequest, request: Request) -> InvokeResponse:
    service = request.app.state.agent_service
    return await service.invoke(payload)

"""Capa de dominio: contratos de datos de la API.

Puro Pydantic, sin dependencias de frameworks ni de infraestructura.
"""
from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class InvokeRequest(BaseModel):
    """Una vuelta de conversación con el agente."""

    session_id: str = Field(..., min_length=1, max_length=128,
                            description="Identificador de la conversación (thread)")
    message: str = Field(..., min_length=1, description="Mensaje del usuario")


class InvokeResponse(BaseModel):
    session_id: str
    reply: str
    blocked: bool = False
    tool_calls: list[str] = Field(default_factory=list,
                                  description="Nombres de tools ejecutadas en esta vuelta")
    fiscal_issues: list[str] = Field(default_factory=list,
                                     description="Hallazgos del agente fiscalizador (paso 05)")
    latency_ms: float = 0.0


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    app: str
    env: str
    checkpointer: Literal["postgres", "memory"]

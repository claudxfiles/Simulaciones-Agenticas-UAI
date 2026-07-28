"""Guardrail de entrada: valida el mensaje ANTES de gastar tokens en el LLM.

Base: reglas determinísticas (rápidas, gratis). Si el caso lo amerita,
agregar aquí una segunda pasada con un modelo chico como clasificador.
"""
import logging
import re

from langchain_core.messages import AIMessage

from app.application.agent.prompts.loader import get_prompt
from app.application.agent.state import AgentState
from app.config import get_settings

logger = logging.getLogger(__name__)

# Patrones de inyección de prompt / abuso. Ampliar según el dominio.
_BLOCK_PATTERNS = [
    re.compile(r"ignora (todas )?(tus|las) instrucciones", re.IGNORECASE),
    re.compile(r"(revela|muestra|imprime).{0,30}(system prompt|instrucciones internas)", re.IGNORECASE),
    re.compile(r"act(úa|ua) como si no tuvieras (reglas|restricciones)", re.IGNORECASE),
]


def _violates(text: str) -> str | None:
    settings = get_settings()
    if len(text) > settings.guardrail_max_input_chars:
        return f"input demasiado largo ({len(text)} chars)"
    for pattern in _BLOCK_PATTERNS:
        if pattern.search(text):
            return f"patrón bloqueado: {pattern.pattern}"
    return None


def guardrail_node(state: AgentState) -> dict:
    last = state["messages"][-1]
    reason = _violates(str(last.content))
    if reason:
        logger.warning("guardrail bloqueó input: %s", reason)
        return {
            "blocked": True,
            "messages": [AIMessage(content=get_prompt("guardrail_rejection"))],
        }
    return {"blocked": False}

"""Nodo Fiscalizador (paso 05 del roadmap): valida la respuesta final antes
de entregarla al usuario.

Corre después de que el LLM produce una respuesta sin más tool_calls
pendientes (justo antes de END). Chequea:

1. Fuentes: si el agente usó tools, la respuesta debería reflejarlo
   (heurística simple — no bloquea, solo marca).
2. PII: emails, teléfonos, tarjetas de crédito vía regex.
3. Relevancia: un LLM-judge ligero confirma que la respuesta atiende la
   pregunta original.

No corrige automáticamente (mantenerlo simple): expone los issues en el
estado (`fiscal_issues`) para que el servicio de aplicación decida — se
loguean siempre y se pueden anexar a la respuesta cuando hay hallazgos.
"""
from __future__ import annotations

import logging
import re

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.application.agent.state import AgentState

logger = logging.getLogger(__name__)

_PII_PATTERNS = {
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "telefono": re.compile(r"\b(?:\+?56)?[\s.-]?9\d{8}\b|\b\d{3}[\s.-]\d{3}[\s.-]\d{4}\b"),
    "tarjeta": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
}

_JUDGE_PROMPT = """Evalúa en una sola palabra si la RESPUESTA atiende la PREGUNTA.
Responde únicamente "SI" o "NO", sin explicación.

PREGUNTA: {pregunta}

RESPUESTA: {respuesta}"""


def _detectar_pii(texto: str) -> list[str]:
    hallazgos = []
    for tipo, patron in _PII_PATTERNS.items():
        if patron.search(texto):
            hallazgos.append(f"posible PII ({tipo}) en la respuesta")
    return hallazgos


def _responde_la_pregunta(pregunta: str, respuesta: str) -> bool:
    """LLM-judge ligero. Si falla, no bloquea (fail-open) — solo se loguea."""
    try:
        from app.infrastructure.llm.client import get_chat_model

        judge = get_chat_model()
        resultado = judge.invoke([
            SystemMessage(content="Eres un evaluador estricto y breve."),
            HumanMessage(content=_JUDGE_PROMPT.format(pregunta=pregunta, respuesta=respuesta)),
        ])
        veredicto = str(resultado.content).strip().upper()
        return veredicto.startswith("S")
    except Exception:
        logger.exception("fiscalizador: LLM-judge falló, se omite el chequeo")
        return True


def fiscalizer_node(state: AgentState) -> dict:
    mensajes = state["messages"]
    ultimo = mensajes[-1]
    if not isinstance(ultimo, AIMessage):
        return {"fiscal_issues": []}

    respuesta = str(ultimo.content)
    pregunta_original = next(
        (m.content for m in mensajes if isinstance(m, HumanMessage)), ""
    )

    issues = _detectar_pii(respuesta)

    hubo_tools = any(
        getattr(m, "tool_calls", None) for m in mensajes if isinstance(m, AIMessage)
    )
    if hubo_tools and "SQL:" not in respuesta and len(respuesta) < 40:
        issues.append("respuesta muy corta pese a haber usado herramientas — posible falta de detalle")

    if pregunta_original and not _responde_la_pregunta(str(pregunta_original), respuesta):
        issues.append("el evaluador considera que la respuesta no atiende la pregunta original")

    if issues:
        logger.warning("fiscalizador encontró %d issue(s): %s", len(issues), issues)

    return {"fiscal_issues": issues}

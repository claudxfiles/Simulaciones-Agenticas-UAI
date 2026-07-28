"""Servicio de aplicación: orquesta una vuelta de conversación.

Invoca el grafo LangGraph y, además, registra cada vuelta en la tabla de
trazabilidad (paso 07 del roadmap) — query, respuesta, tool usada, issues
del fiscalizador y latencia.
"""
from langchain_core.messages import AIMessage, HumanMessage

from app.domain.models import InvokeRequest, InvokeResponse
from app.infrastructure.persistence.trace_store import Timer, record_interaction


class AgentService:
    def __init__(self, graph):
        self._graph = graph

    async def invoke(self, request: InvokeRequest) -> InvokeResponse:
        config = {"configurable": {"thread_id": request.session_id}}

        with Timer() as timer:
            result = await self._graph.ainvoke(
                {"messages": [HumanMessage(content=request.message)]},
                config=config,
            )
        latency_ms = timer.elapsed_ms

        tool_calls: list[str] = []
        for message in result["messages"]:
            for call in getattr(message, "tool_calls", None) or []:
                tool_calls.append(call["name"])

        reply = ""
        last = result["messages"][-1]
        if isinstance(last, AIMessage):
            reply = str(last.text)

        blocked = bool(result.get("blocked"))
        fiscal_issues = result.get("fiscal_issues") or []

        record_interaction(
            session_id=request.session_id,
            query=request.message,
            response=reply,
            agent=", ".join(tool_calls) if tool_calls else None,
            blocked=blocked,
            fiscal_issues=fiscal_issues,
            latency_ms=latency_ms,
        )

        return InvokeResponse(
            session_id=request.session_id,
            reply=reply,
            blocked=blocked,
            tool_calls=tool_calls,
            fiscal_issues=fiscal_issues,
            latency_ms=latency_ms,
        )
